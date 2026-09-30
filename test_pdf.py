import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
import pdf


def fixture(path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    stream = DecodedStreamObject()
    stream.set_data(b'0 0 0 rg 20 20 80 80 re f\n' * 20000)
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata({'/Title': 'Compression test'})
    writer.add_outline_item('Bookmark', 0)
    writer.write(path)


class CompressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'Исходный документ.pdf'
        self.output = self.root / 'Результат.pdf'
        fixture(self.source)

    def compress(self, **kwargs):
        settings = dict(quality='ebook', compatibility='1.4', force_fallback=False)
        settings.update(kwargs)
        return pdf.compress_pdf(self.source, self.output, **settings)

    def test_fallback_preserves_outline_and_metadata(self):
        self.compress(force_fallback=True)
        result = PdfReader(self.output)
        self.assertEqual(len(result.pages), 1)
        self.assertEqual(result.metadata.title, 'Compression test')
        self.assertEqual(result.outline[0].title, 'Bookmark')
        self.assertLess(self.output.stat().st_size, self.source.stat().st_size)

    def test_invalid_target(self):
        for target in (0, -1, float('nan'), float('inf'), 1e-100):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.compress(target_size_mb=target)
        self.assertFalse(self.output.exists())

    def test_same_file(self):
        with self.assertRaises(ValueError):
            pdf.compress_pdf(self.source, self.source, 'ebook', '1.4', False)

    def test_hardlink(self):
        os.link(self.source, self.output)
        with self.assertRaises(ValueError):
            self.compress()

    def test_failed_target_preserves_output_and_cleans_temps(self):
        self.output.write_bytes(b'previous output')
        with patch.object(pdf, 'find_ghostscript', return_value='mock'), patch.object(
            pdf, 'run_ghostscript', side_effect=RuntimeError('failure')
        ), self.assertRaises(RuntimeError):
            self.compress(target_size_mb=1)
        self.assertEqual(self.output.read_bytes(), b'previous output')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         sorted([self.source.name, self.output.name]))

    def test_failed_replace_preserves_output(self):
        self.output.write_bytes(b'previous output')
        with patch.object(Path, 'replace', side_effect=PermissionError('locked')), self.assertRaises(PermissionError):
            self.compress(force_fallback=True)
        self.assertEqual(self.output.read_bytes(), b'previous output')

    def test_target_with_fallback_rejected(self):
        with self.assertRaises(ValueError):
            self.compress(force_fallback=True, target_size_mb=1)

    def test_all_ghostscript_presets_with_target(self):
        gs = Path('.build-deps/ghostscript/bin/gswin64c.exe').resolve()
        if not gs.exists():
            self.skipTest('Build dependency Ghostscript unavailable')
        with patch.object(pdf, 'find_ghostscript', return_value=str(gs)):
            for quality in pdf.QUALITY_PRESETS:
                with self.subTest(quality=quality):
                    self.compress(quality=quality, target_size_mb=1)
                    self.assertEqual(len(PdfReader(self.output).pages), 1)
                    self.assertLess(self.output.stat().st_size, self.source.stat().st_size)


if __name__ == '__main__':
    unittest.main()

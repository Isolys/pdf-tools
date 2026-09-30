"""Integration checks of both built EXEs, without Python/Ghostscript on PATH."""
import ctypes
import os
from pathlib import Path
import subprocess
import time
from pypdf import PdfReader
from test_pdf import fixture

root = Path(__file__).resolve().parent
work = root / 'build' / 'Проверка сборки'
work.mkdir(parents=True, exist_ok=True)
source = work / 'Документ с пробелами.pdf'
fixture(source)
env = dict(os.environ, PATH=str(Path(os.environ['SystemRoot']) / 'System32'),
           GHOSTSCRIPT=str(work / 'missing.exe'))
for label, exe in [('single', root / 'release/PDF-Tools.exe'),
                   ('portable', root / 'dist/portable/PDF-Tools/PDF-Tools.exe')]:
    for mode, options in [('normal', []), ('target', ['--target-size-mb', '0.1']),
                          ('default', ['-q', 'default', '--target-size-mb', '0.1']),
                          ('fallback', ['--fallback-pypdf'])]:
        output = work / f'{label}-{mode}.pdf'
        output.unlink(missing_ok=True)
        result = subprocess.run([str(exe), str(source), str(output), *options],
                                env=env, cwd=work, timeout=60)
        assert result.returncode == 0, (label, mode, result.returncode)
        assert len(PdfReader(output).pages) == 1
        assert output.stat().st_size < source.stat().st_size
        print(label, mode, source.stat().st_size, '->', output.stat().st_size, flush=True)
    bad = work / f'{label}-invalid.pdf'
    bad.unlink(missing_ok=True)
    result = subprocess.run([str(exe), str(source), str(bad), '--target-size-mb', 'nan'],
                            env=env, cwd=work, timeout=60)
    assert result.returncode == 1 and not bad.exists()

    # Start the actual GUI, locate its file picker, then cancel it normally.
    process = subprocess.Popen([str(exe)], cwd=work, env=env)
    windows = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def inspect(hwnd, _):
        title = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(ctypes.c_void_p(hwnd), title, len(title))
        if title.value == 'Выберите PDF-файл':
            windows.append(hwnd)
        return True
    callback = callback_type(inspect)
    deadline = time.monotonic() + 25
    while not windows and time.monotonic() < deadline:
        ctypes.windll.user32.EnumWindows(callback, 0)
        time.sleep(0.2)
    if not windows:
        process.terminate()
        process.wait(timeout=10)
        raise AssertionError(f'{label}: GUI did not open')
    for hwnd in windows:
        ctypes.windll.user32.PostMessageW(ctypes.c_void_p(hwnd), 0x0010, 0, 0)
    assert process.wait(timeout=15) == 0
    print(label, 'GUI opened and closed normally', flush=True)
print('All packaged smoke checks passed.')

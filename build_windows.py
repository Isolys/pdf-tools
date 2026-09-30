"""Build both Windows x64 distributions. Run with the build venv's Python."""
from pathlib import Path
import hashlib
import importlib.metadata
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
GS = ROOT / '.build-deps' / 'ghostscript'
RELEASE = ROOT / 'release'


def main():
    if sys.platform != 'win32' or sys.maxsize <= 2**32:
        raise SystemExit('Build using 64-bit Python on Windows.')
    if not (GS / 'bin' / 'gswin64c.exe').is_file():
        raise SystemExit('Extract Ghostscript 10.08.0 Windows x64 into .build-deps/ghostscript first.')
    RELEASE.mkdir(exist_ok=True)
    common = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
              '--windowed', '--noupx', '--name', 'PDF-Tools',
              '--version-file', str(ROOT / 'windows_version.txt')]
    for folder in ('bin', 'lib', 'Resource', 'iccprofiles'):
        common += ['--add-data', f'{GS / folder};ghostscript/{folder}']
    common += ['--add-data', f'{GS / "doc" / "COPYING"};licenses/ghostscript']
    # Also process GS binaries as binaries so PyInstaller resolves their VC runtime.
    for binary in ('gswin64c.exe', 'gsdll64.dll'):
        common += ['--add-binary', f'{GS / "bin" / binary};ghostscript/bin']
    # Include dependency license files, including Python and pypdf.
    license_dir = ROOT / 'build' / 'licenses'
    license_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', license_dir / 'Python.txt')
    for dist_name in ('pypdf',):
        dist = importlib.metadata.distribution(dist_name)
        for file in dist.files or []:
            if 'license' in str(file).lower() and Path(str(file)).suffix.lower() != '.py':
                shutil.copy2(dist.locate_file(file), license_dir / f'{dist_name}-{Path(str(file)).name}')
    common += ['--add-data', f'{license_dir};licenses']
    # Child processes must find the VC runtime even on a clean Windows install.
    # Place DLLs next to Ghostscript as well as in the Python runtime directory.
    system32 = Path(__import__('os').environ['SystemRoot']) / 'System32'
    for name in ('MSVCP140.dll', 'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll'):
        candidates = [Path(sys.base_prefix) / name, system32 / name]
        runtime = next((p for p in candidates if p.is_file()), None)
        if runtime is None:
            raise SystemExit(f'Missing build runtime: {name}')
        common += ['--add-binary', f'{runtime};ghostscript/bin']
    for mode, destination in (('--onedir', 'portable'), ('--onefile', 'single')):
        subprocess.run(common + [mode, '--distpath', str(ROOT / 'dist' / destination),
                                  str(ROOT / 'pdf.py')], cwd=ROOT, check=True)
    shutil.copy2(ROOT / 'dist/single/PDF-Tools.exe', RELEASE / 'PDF-Tools.exe')
    portable = ROOT / 'dist/portable/PDF-Tools'
    shutil.copy2(ROOT / 'README.md', portable / 'README.md')
    shutil.copy2(ROOT / 'THIRD-PARTY.txt', portable / 'THIRD-PARTY.txt')
    with zipfile.ZipFile(RELEASE / 'PDF-Tools-portable.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in portable.rglob('*'):
            if file.is_file():
                archive.write(file, file.relative_to(portable.parent))
    with zipfile.ZipFile(RELEASE / 'PDF-Tools-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('pdf.py', 'build_windows.py', 'requirements-build.txt', 'windows_version.txt',
                     'README.md', 'THIRD-PARTY.txt', 'test_pdf.py', 'smoke_windows.py'):
            archive.write(ROOT / name, name)
    shutil.copy2(ROOT / 'THIRD-PARTY.txt', RELEASE / 'THIRD-PARTY.txt')
    shutil.copy2(ROOT / 'README.md', RELEASE / 'README.md')
    files = sorted(p for p in RELEASE.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (RELEASE / 'SHA256SUMS.txt').write_text(''.join(
        f'{hashlib.file_digest(p.open("rb"), "sha256").hexdigest()}  {p.name}\n' for p in files
    ), encoding='utf-8')


if __name__ == '__main__':
    main()

"""Build the one-click, per-user installer from the portable distribution."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    compiler = ROOT / '.build-deps/nsis/nsis-3.12/makensis.exe'
    payload = ROOT / 'dist/portable/PDF-Tools'
    if not compiler.is_file() or not (payload / 'PDF-Tools.exe').is_file():
        raise SystemExit('First extract NSIS 3.12 to .build-deps/nsis and build the portable app.')
    if not (ROOT / 'assets/pdf.ico').is_file():
        raise SystemExit('Missing assets/pdf.ico')
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    lines = []
    for path in sorted(payload.rglob('*')):
        if path.is_file():
            lines.append(f'Delete "$INSTDIR\\{path.relative_to(payload)}"')
    directories = sorted((p for p in payload.rglob('*') if p.is_dir()),
                         key=lambda p: len(p.parts), reverse=True)
    lines.extend(f'RMDir "$INSTDIR\\{p.relative_to(payload)}"' for p in directories)
    (build / 'uninstall-files.nsh').write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
    subprocess.run([str(compiler), '/INPUTCHARSET', 'UTF8', '/V2', str(ROOT / 'installer.nsi')],
                   cwd=ROOT, check=True)
    release = ROOT / 'release'
    shutil.copy2(ROOT / 'README.md', release / 'README.md')
    with zipfile.ZipFile(release / 'PDF-Tools-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('pdf.py', 'build_windows.py', 'build_installer.py', 'installer.nsi',
                     'requirements-build.txt', 'windows_version.txt', 'README.md',
                     'THIRD-PARTY.txt', 'test_pdf.py', 'smoke_windows.py', 'assets/pdf.ico'):
            archive.write(ROOT / name, name)
    checksums = []
    for path in sorted(release.iterdir()):
        if path.is_file() and path.name != 'SHA256SUMS.txt':
            with path.open('rb') as stream:
                checksums.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
    (release / 'SHA256SUMS.txt').write_text(''.join(checksums), encoding='utf-8')
    print(release / 'PDF-Tools-Setup.exe')


if __name__ == '__main__':
    main()



from __future__ import annotations

import argparse
import queue
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable


QUALITY_PRESETS = ("screen", "ebook", "printer", "prepress", "default")
ProgressCallback = Callable[[str, int | None, int | None], None]
GUI_LEVELS = {
    "LOW": "printer",
    "MED": "ebook",
    "HIGH": "screen",
}
GUI_LEVEL_LABELS = {
    "LOW": "Бережно",
    "MED": "Обычно",
    "HIGH": "Сильно",
}
IMAGE_COMPRESSION = {
    "screen": {"dpi": 50, "jpeg_quality": 30},
    "ebook": {"dpi": 120, "jpeg_quality": 60},
    "printer": {"dpi": 200, "jpeg_quality": 75},
    "prepress": {"dpi": 300, "jpeg_quality": 85},
}
TARGET_PROFILES = {
    "printer": [
        {"dpi": 200, "jpeg_quality": 75},
        {"dpi": 160, "jpeg_quality": 68},
        {"dpi": 120, "jpeg_quality": 60},
        {"dpi": 96, "jpeg_quality": 52},
        {"dpi": 72, "jpeg_quality": 45},
    ],
    "ebook": [
        {"dpi": 120, "jpeg_quality": 60},
        {"dpi": 96, "jpeg_quality": 52},
        {"dpi": 72, "jpeg_quality": 45},
        {"dpi": 60, "jpeg_quality": 38},
        {"dpi": 50, "jpeg_quality": 30},
        {"dpi": 40, "jpeg_quality": 24},
    ],
    "screen": [
        {"dpi": 72, "jpeg_quality": 45},
        {"dpi": 60, "jpeg_quality": 38},
        {"dpi": 50, "jpeg_quality": 30},
        {"dpi": 40, "jpeg_quality": 24},
        {"dpi": 32, "jpeg_quality": 18},
        {"dpi": 25, "jpeg_quality": 12},
    ],
}


def human_size(num_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def find_ghostscript() -> str | None:
    bundled_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    for bundled in (
        bundled_root / "ghostscript" / "bin" / "gswin64c.exe",
        Path(__file__).resolve().parent / "ghostscript" / "bin" / "gswin64c.exe",
    ):
        if bundled.exists():
            return str(bundled)

    env_path = os.environ.get("GHOSTSCRIPT")
    if env_path and Path(env_path).exists():
        return env_path

    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            return found

    for base in (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ):
        if not base:
            continue
        gs_root = Path(base) / "gs"
        if not gs_root.exists():
            continue
        matches = sorted(gs_root.glob("gs*/bin/gswin64c.exe"), reverse=True)
        if matches:
            return str(matches[0])
    return None


def ghostscript_required_message() -> str:
    return (
        "Ghostscript не найден. Если вы запускаете готовую программу, "
        "попросите прислать новую версию одним файлом. Если вы запускаете "
        "скрипт, установите Ghostscript for Windows. Нужный файл: gswin64c.exe."
    )


def run_ghostscript(
    gs_path: str,
    input_pdf: Path,
    output_pdf: Path,
    quality: str,
    compatibility: str,
    image: dict[str, int] | None = None,
) -> None:
    image_options: list[str] = []
    if image is None:
        image = IMAGE_COMPRESSION.get(quality)

    if image:
        image_options = [
            "-dDownsampleColorImages=true",
            "-dDownsampleGrayImages=true",
            "-dDownsampleMonoImages=true",
            "-dColorImageDownsampleThreshold=1.0",
            "-dGrayImageDownsampleThreshold=1.0",
            "-dMonoImageDownsampleThreshold=1.0",
            "-dColorImageDownsampleType=/Bicubic",
            "-dGrayImageDownsampleType=/Bicubic",
            "-dMonoImageDownsampleType=/Subsample",
            f"-dColorImageResolution={image['dpi']}",
            f"-dGrayImageResolution={image['dpi']}",
            f"-dMonoImageResolution={image['dpi']}",
            "-dPassThroughJPEGImages=false",
            "-dAutoFilterColorImages=false",
            "-dAutoFilterGrayImages=false",
            "-dColorImageFilter=/DCTEncode",
            "-dGrayImageFilter=/DCTEncode",
            f"-dJPEGQ={image['jpeg_quality']}",
        ]

    command = [
        gs_path,
        "-sDEVICE=pdfwrite",
        f"-dCompatibilityLevel={compatibility}",
        f"-dPDFSETTINGS=/{quality}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dSubsetFonts=true",
        *image_options,
        f"-sOutputFile={str(output_pdf)}",
        str(input_pdf),
    ]
    subprocess.run(command, check=True)


def run_ghostscript_to_target(
    gs_path: str,
    input_pdf: Path,
    output_pdf: Path,
    quality: str,
    compatibility: str,
    target_size_bytes: int,
    progress: ProgressCallback | None = None,
) -> str:
    profiles = TARGET_PROFILES.get(quality) or [IMAGE_COMPRESSION.get(quality, {})]
    best_pdf: Path | None = None
    best_size: int | None = None
    tried: list[str] = []

    try:
        for index, image in enumerate(profiles, start=1):
            if progress:
                progress(
                    f"Пробую качество: {image['dpi']} dpi / JPEG {image['jpeg_quality']}",
                    index - 1,
                    len(profiles),
                )

            fd, tmp_name = tempfile.mkstemp(
                prefix=f"{output_pdf.stem}.target{index}.",
                suffix=".tmp.pdf",
                dir=str(output_pdf.parent),
            )
            os.close(fd)
            candidate_pdf = Path(tmp_name)

            run_ghostscript(
                gs_path,
                input_pdf,
                candidate_pdf,
                quality,
                compatibility,
                image=image,
            )
            candidate_size = candidate_pdf.stat().st_size
            if progress:
                progress(
                    f"Получилось: {human_size(candidate_size)}",
                    index,
                    len(profiles),
                )
            if candidate_size == 0:
                candidate_pdf.unlink(missing_ok=True)
                continue

            tried.append(
                f"{image['dpi']} dpi / JPEG {image['jpeg_quality']} = "
                f"{human_size(candidate_size)}"
            )

            if best_size is None or candidate_size < best_size:
                if best_pdf and best_pdf.exists():
                    best_pdf.unlink()
                best_pdf = candidate_pdf
                best_size = candidate_size
            else:
                candidate_pdf.unlink()

            if candidate_size <= target_size_bytes:
                if output_pdf.exists():
                    output_pdf.unlink()
                candidate_pdf.replace(output_pdf)
                best_pdf = None
                return (
                    f"Целевой размер достигнут ({image['dpi']} dpi, "
                    f"JPEG {image['jpeg_quality']})"
                )

        if best_pdf is None or best_size is None:
            raise RuntimeError("Ghostscript did not create a usable PDF")

        if output_pdf.exists():
            output_pdf.unlink()
        best_pdf.replace(output_pdf)
        best_pdf = None
        return (
            f"До целевого размера дойти не удалось; лучший результат: "
            f"{human_size(best_size)}. Попытки: {'; '.join(tried)}"
        )
    finally:
        if best_pdf and best_pdf.exists():
            best_pdf.unlink()


def run_pypdf_fallback(input_pdf: Path, output_pdf: Path) -> None:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise RuntimeError(
            "Ghostscript is not installed and pypdf is not available. "
            "Install Ghostscript for best compression, or run: pip install pypdf"
        ) from exc

    reader = PdfReader(str(input_pdf), strict=False)
    writer = PdfWriter()

    for page in reader.pages:
        writer_page = writer.add_page(page)
        writer_page.compress_content_streams()

    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))

    with output_pdf.open("wb") as file_obj:
        writer.write(file_obj)


def compress_pdf(
    input_pdf: Path,
    output_pdf: Path,
    quality: str,
    compatibility: str,
    force_fallback: bool,
    target_size_mb: float | None = None,
    progress: ProgressCallback | None = None,
) -> str:
    input_pdf = input_pdf.resolve()
    output_pdf = output_pdf.resolve()

    if not input_pdf.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_pdf}")
    if input_pdf.suffix.lower() != ".pdf":
        raise ValueError("Input file must be a .pdf file")
    if input_pdf == output_pdf:
        raise ValueError("Input and output paths must be different")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{output_pdf.stem}.",
        suffix=".tmp.pdf",
        dir=str(output_pdf.parent),
    )
    os.close(fd)
    tmp_pdf = Path(tmp_name)

    try:
        gs_path = None if force_fallback else find_ghostscript()
        if gs_path and target_size_mb:
            if progress:
                progress("Начинаю сжатие до нужного размера", 0, None)
            target_size_bytes = int(target_size_mb * 1024 * 1024)
            if target_size_bytes <= 0:
                raise ValueError("Target size must be greater than 0 MB")
            method = run_ghostscript_to_target(
                gs_path,
                input_pdf,
                tmp_pdf,
                quality,
                compatibility,
                target_size_bytes,
                progress=progress,
            )
        elif gs_path:
            if progress:
                progress("Сжимаю PDF", None, None)
            run_ghostscript(gs_path, input_pdf, tmp_pdf, quality, compatibility)
            method = f"Ghostscript ({quality})"
        elif force_fallback:
            if progress:
                progress("Сжимаю PDF запасным способом", None, None)
            run_pypdf_fallback(input_pdf, tmp_pdf)
            method = "pypdf fallback"
        else:
            raise RuntimeError(ghostscript_required_message())

        input_size = input_pdf.stat().st_size
        tmp_size = tmp_pdf.stat().st_size

        if tmp_size == 0:
            raise RuntimeError("Compressed file is empty")

        if output_pdf.exists():
            output_pdf.unlink()

        if tmp_size >= input_size:
            shutil.copy2(input_pdf, output_pdf)
            if progress:
                progress("Готово: оставлен исходный файл", 1, 1)
            return f"{method}; kept original because compression did not reduce size"

        tmp_pdf.replace(output_pdf)
        if progress:
            progress("Готово", 1, 1)
        return method
    finally:
        if tmp_pdf.exists():
            tmp_pdf.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compress a PDF file. Run without arguments to open a file picker. "
            "Uses Ghostscript when available."
        )
    )
    parser.add_argument("input", nargs="?", type=Path, help="Source PDF path")
    parser.add_argument("output", nargs="?", type=Path, help="Compressed PDF path")
    parser.add_argument(
        "-q",
        "--quality",
        choices=QUALITY_PRESETS,
        default="ebook",
        help=(
            "Compression preset: screen is smallest/lowest quality, "
            "ebook is balanced, printer/prepress keep more quality."
        ),
    )
    parser.add_argument(
        "--compatibility",
        default="1.4",
        help="Output PDF compatibility level for Ghostscript, default: 1.4",
    )
    parser.add_argument(
        "--fallback-pypdf",
        action="store_true",
        help="Skip Ghostscript and use pypdf stream compression only.",
    )
    parser.add_argument(
        "--target-size-mb",
        type=float,
        default=None,
        help="Try multiple Ghostscript profiles until output is near this size in MB.",
    )
    return parser


def choose_gui_options() -> tuple[str, float | None] | None:
    import tkinter as tk
    from tkinter import messagebox

    choice: dict[str, str | float | None] = {"level": None, "target": None}

    root = tk.Tk()
    root.title("Сжать PDF")
    root.resizable(False, False)
    root.geometry("390x250")

    label = tk.Label(root, text="Насколько сильно сжать PDF?", font=("Segoe UI", 12))
    label.pack(pady=(18, 10))

    hint = tk.Label(
        root,
        text="Бережно = лучше качество\nСильно = меньше размер файла",
        font=("Segoe UI", 9),
        justify="center",
    )
    hint.pack(pady=(0, 10))

    target_frame = tk.Frame(root)
    target_frame.pack(pady=(0, 10))

    target_label = tk.Label(target_frame, text="Желаемый размер, МБ:")
    target_label.pack(side="left", padx=(0, 6))

    target_entry = tk.Entry(target_frame, width=8)
    target_entry.insert(0, "5")
    target_entry.pack(side="left")

    buttons = tk.Frame(root)
    buttons.pack(pady=4)

    def select(level: str) -> None:
        target_text = target_entry.get().strip().replace(",", ".")
        target: float | None = None
        if target_text:
            try:
                target = float(target_text)
            except ValueError:
                messagebox.showerror("Сжать PDF", "Введите число, например 5")
                return
            if target <= 0:
                messagebox.showerror("Сжать PDF", "Размер должен быть больше 0")
                return
        choice["level"] = level
        choice["target"] = target
        root.destroy()

    for level in ("LOW", "MED", "HIGH"):
        button = tk.Button(
            buttons,
            text=GUI_LEVEL_LABELS[level],
            width=12,
            command=lambda selected=level: select(selected),
        )
        button.pack(side="left", padx=6)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    if not choice["level"]:
        return None
    return str(choice["level"]), choice["target"] if isinstance(choice["target"], float) else None


def run_gui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.withdraw()

    input_name = filedialog.askopenfilename(
        title="Выберите PDF-файл",
        filetypes=(("PDF-файлы", "*.pdf"), ("Все файлы", "*.*")),
    )
    root.destroy()

    if not input_name:
        return 0

    options = choose_gui_options()
    if not options:
        return 0

    level, target_size_mb = options
    input_pdf = Path(input_name)
    target_part = f"_target_{target_size_mb:g}mb" if target_size_mb else ""
    output_pdf = input_pdf.with_name(
        f"{input_pdf.stem}_compressed_{level}{target_part}.pdf"
    )
    quality = GUI_LEVELS[level]
    before = input_pdf.stat().st_size if input_pdf.exists() else 0

    progress_root = tk.Tk()
    progress_root.title("Сжимаю PDF")
    progress_root.resizable(False, False)
    progress_root.geometry("420x150")

    status_var = tk.StringVar(value="Подготовка...")
    status_label = tk.Label(progress_root, textvariable=status_var, font=("Segoe UI", 10))
    status_label.pack(pady=(20, 10))

    progress_bar = ttk.Progressbar(progress_root, mode="indeterminate", length=340)
    progress_bar.pack(pady=(0, 12))
    progress_bar.start(12)

    wait_label = tk.Label(
        progress_root,
        text="Пожалуйста, не закрывайте это окно до окончания сжатия.",
        font=("Segoe UI", 8),
    )
    wait_label.pack()

    events: queue.Queue[tuple[str, object]] = queue.Queue()
    result: dict[str, str | Exception | None] = {"method": None, "error": None}

    def report(message: str, current: int | None, total: int | None) -> None:
        events.put(("progress", (message, current, total)))

    def worker() -> None:
        try:
            result["method"] = compress_pdf(
                input_pdf=input_pdf,
                output_pdf=output_pdf,
                quality=quality,
                compatibility="1.4",
                force_fallback=False,
                target_size_mb=target_size_mb,
                progress=report,
            )
        except Exception as exc:
            result["error"] = exc
        finally:
            events.put(("done", None))

    def poll_events() -> None:
        while True:
            try:
                event, payload = events.get_nowait()
            except queue.Empty:
                break

            if event == "progress":
                message, current, total = payload  # type: ignore[misc]
                status_var.set(str(message))
                if isinstance(current, int) and isinstance(total, int):
                    progress_bar.stop()
                    progress_bar.configure(mode="determinate", maximum=total, value=current)
                else:
                    progress_bar.configure(mode="indeterminate")
                    progress_bar.start(12)
            elif event == "done":
                progress_bar.stop()
                progress_root.destroy()
                return

        progress_root.after(100, poll_events)

    progress_root.protocol("WM_DELETE_WINDOW", lambda: None)
    threading.Thread(target=worker, daemon=True).start()
    progress_root.after(100, poll_events)
    progress_root.mainloop()

    if result["error"]:
        messagebox.showerror("Ошибка сжатия PDF", str(result["error"]))
        return 1

    method = str(result["method"])

    after = output_pdf.stat().st_size
    saved = before - after
    percent = (saved / before * 100) if before else 0

    messagebox.showinfo(
        "PDF готов",
        "\n".join(
            (
                f"Режим: {GUI_LEVEL_LABELS[level]}",
                f"Цель: {target_size_mb:g} МБ" if target_size_mb else "Цель: не указана",
                f"Способ: {method}",
                f"Было: {human_size(before)}",
                f"Стало: {human_size(after)}",
                f"Сэкономлено: {human_size(saved)} ({percent:.1f}%)",
                f"Файл: {output_pdf}",
            )
        ),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return run_gui()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input is None or args.output is None:
        parser.error("input and output are required in command-line mode")

    input_pdf = args.input
    output_pdf = args.output
    before = input_pdf.stat().st_size if input_pdf.exists() else 0

    try:
        method = compress_pdf(
            input_pdf=input_pdf,
            output_pdf=output_pdf,
            quality=args.quality,
            compatibility=args.compatibility,
            force_fallback=args.fallback_pypdf,
            target_size_mb=args.target_size_mb,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    after = output_pdf.stat().st_size
    saved = before - after
    percent = (saved / before * 100) if before else 0

    print(f"Method: {method}")
    print(f"Input:  {human_size(before)}")
    print(f"Output: {human_size(after)}")
    print(f"Saved:  {human_size(saved)} ({percent:.1f}%)")
    print(f"File:   {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

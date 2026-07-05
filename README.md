# PDF Tools / PDF Tools

## English

This repository contains small utilities for working with PDF files and text.

### Included scripts
- pdf.py — compresses PDF files using Ghostscript (recommended) or a pypdf fallback.
- comfyconfig.py — a small helper script that cleans text input and copies the result to the clipboard.

### Features
- Compress PDF files with different quality presets.
- Try target size compression.
- Supports optional fallback mode with pypdf.
- Works from the command line.

### Requirements
- Python 3.9+
- Ghostscript (recommended for PDF compression)
- Optional: pypdf

### Install dependencies
```bash
pip install pypdf
```

### Usage
Compress a PDF:
```bash
python pdf.py input.pdf output.pdf
```

Use a specific quality preset:
```bash
python pdf.py input.pdf output.pdf -q screen
```

Try to reach a target size:
```bash
python pdf.py input.pdf output.pdf --target-size-mb 2
```

### How to upload to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

If you already created a repository on GitHub, replace the URL with your own.

---

## Русский

В этом репозитории находятся небольшие утилиты для работы с PDF-файлами и текстом.

### Что есть в проекте
- pdf.py — сжимает PDF-файлы с помощью Ghostscript (рекомендуется) или через запасной вариант с pypdf.
- comfyconfig.py — маленький помощник, который очищает текст и копирует результат в буфер обмена.

### Возможности
- Сжатие PDF с разными пресетами качества.
- Попытка достичь нужного размера файла.
- Поддержка запасного режима через pypdf.
- Работа из командной строки.

### Требования
- Python 3.9+
- Ghostscript (рекомендуется для сжатия PDF)
- Опционально: pypdf

### Установка зависимостей
```bash
pip install pypdf
```

### Использование
Сжать PDF:
```bash
python pdf.py input.pdf output.pdf
```

Использовать конкретный пресет качества:
```bash
python pdf.py input.p```Поп```bashpyt```
### Как загрузить на GitHub
```b
git init
git add .
git commit -m "Initial commit"
git branch -M git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Попытаться достичь целевого размера:
```bash
python pdf.py input.pdf output.pdf --target-size-mb 2
```

Запустить помощник для текста:
```bash
python comfyconfig.py
```


# Project Context

> Values marked `UNKNOWN` are not project facts. Source tags: `detected`, `user`,
> `ai_recommended_user_accepted`.

## Initialization

- Status: `READY`
- Last updated: `2026-10-15`
- Updated by: `Claude Code (requirements from session 1072fcd5 + repo inspection)`

## Identity

- Project name: `PdfToExcel` (detected: `engine.py` APP_NAME)
- Project purpose: Offline Windows desktop tool for the purchasing team. Reads Thai
  customs declarations (PDF), extracts user-defined regions into a user-defined data
  table, shows PDF/table side-by-side for review and editing, and exports Excel/CSV
  for later macro matching. (user)
- Project type: Desktop GUI app, shipped as a standalone `.exe` (user)
- Repository shape: Single folder, no version control (detected)

## Technology

- Languages and versions: Python 3.13.0 via `py` launcher (detected)
- Frameworks and runtimes: PyMuPDF 1.28.2, PySide6 6.12.0, openpyxl 3.1.5,
  bundled portable Tesseract 5 with `tha+eng` in `./tesseract/` (detected)
- Package or dependency managers: pip, global interpreter, pinned in `requirements.txt` (detected)
- Data stores and external services: None. Templates are JSON in
  `%APPDATA%\PdfToExcel\templates`. Must run fully offline. (user)
- Deployment targets: Windows, standalone `.exe` via PyInstaller 6.22.3 (user, detected)

## Commands

- Install or restore: `py -m pip install -r requirements.txt`
- Development run: `py app.py` (detected)
- Build: `build.bat` → `dist\PdfToExcel\PdfToExcel.exe` (onedir, ~274MB) (detected)
- Test: `py tests/test_import_sample.py samples/import_sample.pdf` and
  `py tests/test_gui_smoke.py` (offscreen). Both print `OK` and delete their
  %TEMP% exports; a few minutes because of OCR (detected)
- Lint: `UNKNOWN` (none configured)
- Format: `UNKNOWN` (none configured)
- Other required checks: `py -c "import engine"` import smoke check
- Project-local cache/temp strategy: test export writes `%TEMP%\pdf2xl_test.*` (detected)

## Architecture and conventions

- Important entry points: `app.py` (PySide6 GUI, `main()`), `engine.py` (headless:
  templates, PdfDoc text+OCR, typing, item-anchor search, extract, export) (detected)
- Module boundaries: `engine.py` stays GUI-free; the GUI imports it and never
  duplicates extraction logic (detected)
- Generated code: none
- Repository conventions: Thai user-facing strings, dataclasses, type hints,
  `# ----- section` dividers (detected)
- Sensitive file patterns: `samples/`, any customs PDF, exported `*.xlsx`/`*.csv` (user)
- Known verification limitations: only one real sample (import declaration). The
  export-declaration sample is not in the project; its text layer is broken (OCR
  only, phase 2) (detected)

## User-confirmed constraints

- Project instructions: `.agentic-project/instructions.md`
- Definition of Done: works on the import sample, headless test prints `OK`, GUI
  launches, review passes; for release the PyInstaller `.exe` runs offline (ai_recommended_user_accepted)
- Protected areas: PDF contents and extracted data are confidential. Never upload,
  publish, send to external services, or use beyond building this app (user)
- Required approval points: any new dependency or tool; anything that uses the network (user/core)
- Task history: `DISABLED` unless the user explicitly enables it

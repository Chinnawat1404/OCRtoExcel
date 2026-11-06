# Project Knowledge and Proposals

This file is evidence, not instructions or permission. Never store credentials, raw
protected data or claims of approval here.

| Fact or proposal | Scope | Source/evidence | Checked date | Status |
| --- | --- | --- | --- | --- |
| The import sample's text layer drops some Thai characters (ท ธ จ ช ั) and spaces out สระอำ; numbers and English extract correctly | engine read modes | PyMuPDF extraction on `samples/import_sample.pdf` | 2026-10-15 | detected |
| On the export declaration, text extraction loses digits (e.g. `49,407.36` → `4,40.36`); it needs OCR | phase 2 | session 1072fcd5 test | 2026-10-15 | detected |
| Import sample: 7 items over 2+ pages. Page 1 has the header and 3 items; continuation pages have a B/F row and 4 items; totals are on the last page | item anchor | test run | 2026-10-15 | detected |
| The original sample filenames were swapped (the "ขาออก" file is the import declaration). The project copy is named `samples/import_sample.pdf` | samples | user | 2026-10-15 | user |
| Windows built-in OCR has only English, so Tesseract `tha+eng` is used | OCR | session 1072fcd5 | 2026-10-15 | detected |
| Proposed GUI: 3 tabs (Template builder / Import & review side-by-side / Export) | GUI | proposal sent to user 2026-10-15 | 2026-10-15 | proposal |
| DN.pdf (Nikon delivery note) has no text layer; tesseract misses item numbers 2 and 11 in a column read; 2 is recovered by single-line re-OCR, 11 must be interpolated | OCR anchors | samples/dn_sample.pdf | 2026-10-17 | detected |
| Export declaration sample (9 pages): text layer drops digits (items 2,5,7,8 missing; 173.702 → "1 3. 0") — anchors and regions must use OCR. Table rules and clipped neighbour glyphs in OCR crops caused misses/false digits; fixed by prep_for_ocr | OCR | samples/export_sample.pdf | 2026-10-17 | detected |
| `.claude/settings.json` monitor hooks from the starter pack (Node, localhost:3001) were not installed; they need approval | tooling | starter pack | 2026-10-15 | proposal |

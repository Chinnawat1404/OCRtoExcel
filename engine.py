"""Extraction engine: templates, PDF reading (text layer + OCR), typing, export.

No GUI code here so it can be tested headlessly.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict

import pymupdf

APP_NAME = "PdfToExcel"
COL_TYPES = ["string", "number", "date"]   # "integer" in old templates is read as number
MODES = ["auto", "text", "ocr", "compare"]
SCOPES = ["header", "item"]
OCR_DPI = 400
SOURCE_FILE_COL = "_ไฟล์ต้นทาง"


# ---------------------------------------------------------------- paths

def resource_dir() -> str:
    if getattr(sys, "frozen", False):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
    os.makedirs(os.path.join(d, "templates"), exist_ok=True)
    return d


def templates_dir() -> str:
    return os.path.join(data_dir(), "templates")


# ---------------------------------------------------------------- template

@dataclass
class Column:
    name: str
    type: str = "string"
    joiner: str = ""


@dataclass
class Region:
    column: str
    scope: str = "header"          # header | item
    page: int = 0                  # header: page index (-1 = last page); item: page of item #1
    rect: list = field(default_factory=lambda: [0, 0, 0, 0])
    mode: str = "auto"


@dataclass
class SumCheck:
    header_column: str             # column holding the document total
    item_column: str               # item column to sum


@dataclass
class Template:
    name: str
    columns: list = field(default_factory=list)
    regions: list = field(default_factory=list)
    anchor: dict | None = None     # {"page": int, "rect": [..], "mode": "text"|"ocr"}
    checks: list = field(default_factory=list)
    include_source_file: bool = True

    def column(self, name):
        return next((c for c in self.columns if c.name == name), None)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @staticmethod
    def from_dict(d) -> "Template":
        return Template(
            name=d["name"],
            columns=[Column(**{**c, "type": "number" if c.get("type") == "integer" else c.get("type", "string")})
                     for c in d.get("columns", [])],
            regions=[Region(**r) for r in d.get("regions", [])],
            anchor=d.get("anchor"),
            checks=[SumCheck(**c) for c in d.get("checks", [])],
            include_source_file=d.get("include_source_file", True),
        )

    def save(self):
        path = os.path.join(templates_dir(), safe_name(self.name) + ".json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return path


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]+', "_", s).strip() or "template"


def list_templates() -> list[str]:
    return sorted(f[:-5] for f in os.listdir(templates_dir()) if f.endswith(".json"))


def load_template(name: str) -> Template:
    with open(os.path.join(templates_dir(), safe_name(name) + ".json"), encoding="utf-8") as f:
        return Template.from_dict(json.load(f))


def delete_template(name: str):
    os.remove(os.path.join(templates_dir(), safe_name(name) + ".json"))


# ---------------------------------------------------------------- OCR

def tesseract_paths():
    base = os.path.join(resource_dir(), "tesseract")
    return os.path.join(base, "tesseract.exe"), os.path.join(base, "tessdata")


def _run_tesseract(png: bytes, psm: int, lang="tha+eng", out="txt", extra=()) -> str:
    exe, tessdata = tesseract_paths()
    args = [exe, "-", "-", "--tessdata-dir", tessdata, "-l", lang, "--psm", str(psm)]
    if out == "tsv":
        args += ["-c", "tessedit_create_tsv=1"]   # no "tsv" config file in bundled tessdata
    for kv in extra:
        args += ["-c", kv]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    r = subprocess.run(args, input=png, capture_output=True, creationflags=flags)
    return r.stdout.decode("utf-8", errors="replace")


_DARK = bytes(1 if i < 140 else 0 for i in range(256))
WHITE = bytes([255])
TAB = chr(9)
LINE_FRACTION = 0.6           # a pixel row/column this dark across the crop is a table line
OCR_PAD = 12                  # px of white border tesseract likes around the text
LINE_MAX_THICKNESS = 8        # px; a table rule at OCR_DPI is thinner than a text line
MIN_HEIGHT_FOR_VLINES = 120   # px (~22pt at OCR_DPI)
LINE_CONTEXT = 0.6            # crop this fraction of the box height above/below for OCR ...
LINE_CONTEXT_MIN = 5          # ... and at least this many pt
SINGLE_LINE_BOX = 1.6         # box lower than this many text lines -> the user wants one line
MIN_WORD_CONF = 40            # OCR words below this confidence are noise ...
MIN_THAI_WORD_CONF = 20       # ... Thai words get lower scores from tesseract
SPACE_GAP = 0.3               # gap between Thai tokens wider than this x line height = a space


def prep_for_ocr(pix) -> tuple[bytes, int, int]:
    """Clean a grayscale crop for tesseract: erase table lines, trim to the ink, pad.

    Returns (png bytes, x offset px, y offset px) of the trimmed image inside the crop.
    """
    w, h, st = pix.width, pix.height, pix.stride
    buf = bytearray(pix.samples)
    dark = buf.translate(_DARK)
    def lines(n, size, get):
        """Indices of thin solid ink runs spanning the crop (table rules)."""
        cand = []
        for i in range(n):
            px = get(i)
            ink = sum(px)
            if ink > LINE_FRACTION * size:
                cand.append(i)
        out, run = set(), []
        for i in cand + [None]:
            if run and (i is None or i != run[-1] + 1):
                if len(run) <= LINE_MAX_THICKNESS:        # text is much thicker than a rule
                    out.update(run)
                run = []
            if i is not None:
                run.append(i)
        return out

    line_rows = lines(h, w, lambda y: dark[y * st:y * st + w])
    # vertical rules only in tall crops and only when nearly solid: the stem of a "1"
    # fills most of a short, tight crop
    line_cols = set()
    if h >= MIN_HEIGHT_FOR_VLINES:
        line_cols = {x for x in lines(w, h, lambda x: dark[x:x + st * h:st])
                     if sum(dark[x:x + st * h:st]) > 0.9 * h}
    for y in {y + d for y in line_rows for d in (-2, -1, 0, 1, 2)} & set(range(h)):
        buf[y * st:y * st + w] = WHITE * w
    for x in {x + d for x in line_cols for d in (-2, -1, 0, 1, 2)} & set(range(w)):
        buf[x:x + st * h:st] = WHITE * h
    dark = buf.translate(_DARK)
    rows = [y for y in range(h) if any(dark[y * st:y * st + w])]
    cols = [x for x in range(w) if any(dark[x:x + st * h:st])]
    if not rows or not cols:
        return pix.tobytes("png"), 0, 0
    x0, x1 = max(cols[0] - OCR_PAD, 0), min(cols[-1] + OCR_PAD + 1, w)
    y0, y1 = max(rows[0] - OCR_PAD, 0), min(rows[-1] + OCR_PAD + 1, h)
    cw, ch = x1 - x0, y1 - y0
    pad = OCR_PAD
    out = bytearray(WHITE * ((cw + 2 * pad) * (ch + 2 * pad)))
    ow = cw + 2 * pad
    for y in range(ch):
        o = (y + pad) * ow + pad
        out[o:o + cw] = buf[(y0 + y) * st + x0:(y0 + y) * st + x1]
    clean = pymupdf.Pixmap(pymupdf.csGRAY, ow, ch + 2 * pad, bytes(out), False)
    return clean.tobytes("png"), x0 - pad, y0 - pad


class PdfDoc:
    """Wraps a PDF with cached text/OCR lookups."""

    def __init__(self, path: str):
        self.path = path
        self.doc = pymupdf.open(path)
        self._words: dict[int, list] = {}
        self._ocr: dict[tuple, list[str]] = {}

    def __len__(self):
        return len(self.doc)

    def words(self, page: int):
        if page not in self._words:
            self._words[page] = self.doc[page].get_text("words")
        return self._words[page]

    def text_lines(self, page: int, rect) -> list[str]:
        x0, y0, x1, y1 = rect
        hits = [w for w in self.words(page)
                if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
        return group_lines([(w[0], (w[1] + w[3]) / 2, w[3] - w[1], w[4]) for w in hits])

    def ocr_lines(self, page: int, rect) -> list[str]:
        key = (page, tuple(round(v, 1) for v in rect))
        if key not in self._ocr:
            r = pymupdf.Rect(rect)
            if r.is_empty or page >= len(self.doc):
                self._ocr[key] = []
            else:
                lines = self._ocr_lines_in_box(page, r)
                if not lines:                           # fallback: OCR exactly the drawn box
                    pix = self.doc[page].get_pixmap(clip=r, dpi=OCR_DPI, colorspace=pymupdf.csGRAY)
                    psm = 7 if r.height < 16 else 6
                    png, _, _ = prep_for_ocr(pix)
                    txt = _run_tesseract(png, psm)
                    if psm == 7 and not txt.strip():
                        txt = _run_tesseract(png, 6)   # a rule left in the crop can defeat psm 7
                    lines = [clean_ocr(l) for l in txt.splitlines() if clean_ocr(l)]
                self._ocr[key] = lines
        return self._ocr[key]

    def _ocr_lines_in_box(self, page: int, r) -> list[str]:
        """OCR a crop taller than the box, then keep the text lines centred inside it.

        The margin keeps Thai tone marks/upper vowels that a tight box would cut, and
        a neighbouring line partly inside the box is dropped instead of read as noise.
        """
        my = max(LINE_CONTEXT_MIN, LINE_CONTEXT * r.height)
        big = pymupdf.Rect(r.x0 - 2, r.y0 - my, r.x1 + 2, r.y1 + my) & self.doc[page].rect
        pix = self.doc[page].get_pixmap(clip=big, dpi=OCR_DPI, colorspace=pymupdf.csGRAY)
        png, ox, oy = prep_for_ocr(pix)
        tsv = _run_tesseract(png, 6, out="tsv")
        k = 72 / OCR_DPI
        groups: dict[tuple, list] = {}
        for line in tsv.splitlines()[1:]:
            p = line.split(TAB)
            if len(p) != 12 or p[0] != "5" or not p[11].strip():
                continue
            thai = any(_is_thai(c) for c in p[11])
            if float(p[10] or 0) < (MIN_THAI_WORD_CONF if thai else MIN_WORD_CONF):
                continue                                # noise (Thai words score lower)
            left, top, w, h = (int(v) for v in p[6:10])
            x0 = big.x0 + (left + ox) * k
            x1 = big.x0 + (left + w + ox) * k
            if not (r.x0 <= (x0 + x1) / 2 <= r.x1):
                continue                                # word outside the box left/right
            groups.setdefault((p[2], p[3], p[4]), []).append(
                (x0, big.y0 + (top + oy) * k, big.y0 + (top + h + oy) * k, p[11].strip(), x1))
        lines = []                                      # (center y, height, score, text)
        for words in groups.values():
            ys0, ys1 = min(w[1] for w in words), max(w[2] for w in words)
            chars = sum(len(w[3]) for w in words if r.y0 <= (w[1] + w[2]) / 2 <= r.y1)
            cover = max(0.0, min(ys1, r.y1) - max(ys0, r.y0)) / max(ys1 - ys0, 1e-6)
            words.sort(key=lambda w: w[0])
            # score: how much of the line lies in the box x how much text of it is inside
            gap = SPACE_GAP * (ys1 - ys0)              # a real space is a visible gap
            spaced = [i > 0 and words[i][0] - words[i - 1][4] > gap for i in range(len(words))]
            lines.append(((ys0 + ys1) / 2, ys1 - ys0, cover * chars,
                          join_words([w[3] for w in words], spaced)))
        lines = [l for l in lines if l[2] > 0]
        if not lines:
            return []
        tallest = max(l[1] for l in lines)               # ignore loose marks/dots for the
        heights = sorted(l[1] for l in lines if l[1] >= 0.5 * tallest)   # line height
        if r.height < SINGLE_LINE_BOX * heights[len(heights) // 2]:
            # a box about one line high means one line: the best-covered one
            # (a neighbour line or loose tone marks caught by a generous box are dropped)
            best = max(lines, key=lambda l: l[2])
            return [clean_ocr(best[3])] if clean_ocr(best[3]) else []
        return [clean_ocr(l[3]) for l in sorted(lines) if r.y0 <= l[0] <= r.y1 and clean_ocr(l[3])]

    def ocr_words(self, page: int, rect, psm: int = 6, min_conf: float = 60):
        """Digit word boxes (pdf coords) from OCR — used for item-number search."""
        r = pymupdf.Rect(rect) & self.doc[page].rect
        if r.is_empty:
            return []
        pix = self.doc[page].get_pixmap(clip=r, dpi=OCR_DPI, colorspace=pymupdf.csGRAY)
        png, ox, oy = prep_for_ocr(pix)
        tsv = _run_tesseract(png, psm, lang="eng", out="tsv",
                             extra=["tessedit_char_whitelist=0123456789"])
        k = 72 / OCR_DPI
        out = []
        for line in tsv.splitlines()[1:]:
            p = line.split("\t")
            if len(p) == 12 and p[11].strip() and float(p[10] or 0) >= min_conf:
                left, top, w, h = (int(v) for v in p[6:10])
                left, top = left + ox, top + oy
                out.append((r.x0 + left * k, r.y0 + top * k, r.x0 + (left + w) * k,
                            r.y0 + (top + h) * k, p[11].strip()))
        return out


def group_lines(items) -> list[str]:
    """items: (x, y_center, height, text) -> lines sorted top-down, words left-right."""
    items = sorted(items, key=lambda t: (t[1], t[0]))
    lines: list[list] = []
    for it in items:
        if lines and abs(lines[-1][-1][1] - it[1]) < max(it[2], 4) * 0.5:
            lines[-1].append(it)
        else:
            lines.append([it])
    return [" ".join(w[3] for w in sorted(l, key=lambda t: t[0])) for l in lines]


def _is_thai(ch: str) -> bool:
    return 0x0E00 <= ord(ch) <= 0x0E7F


def _is_thai_mark(ch: str) -> bool:
    """Thai vowel/tone marks written above or below a consonant (never start a word)."""
    c = ord(ch)
    return c == 0x0E31 or 0x0E34 <= c <= 0x0E3A or 0x0E47 <= c <= 0x0E4E


def join_words(words: list[str], spaced: list[bool] | None = None) -> str:
    """Join OCR word tokens.

    Between two Thai tokens a space is kept only where the image shows a real gap
    (spaced[i]); tesseract splits Thai text into tokens that are not words.
    """
    out = ""
    for i, w in enumerate(words):
        if out and w[0] not in ")]}.,:;%" and out[-1] not in "([{":
            if _is_thai_mark(w[0]):
                pass                                    # a mark belongs to the previous letter
            elif not (_is_thai(out[-1]) and _is_thai(w[0])) or (spaced and spaced[i]):
                out += " "
        out += w
    return out


def clean_ocr(s: str) -> str:
    return s.strip().strip("|").strip()


# ---------------------------------------------------------------- typing

_GARBLE = re.compile(r"[ª´Î¨Â£ÃÁ¸Éµ¦³°ÊÅ»�]")
_DATE = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})")
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_NUM = re.compile(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


def convert(raw: str, ctype: str):
    """Return (value, ok). ok=False means raw doesn't look like the declared type."""
    s = raw.strip()
    if ctype == "string":
        return s, not _GARBLE.search(s)
    if not s:
        return None, True
    if ctype in ("number", "integer"):                 # one numeric type: 12 and 12.5 both valid
        m = _NUM.search(s.replace(" ", ""))
        if not m:
            return None, False
        return float(m.group(0).replace(",", "")), True
    if ctype == "date":
        m = _DATE.search(s)
        if m:
            d, mo, y = (int(g) for g in m.groups())
        else:
            m = _ISO.search(s)
            if not m:
                return None, False
            y, mo, d = (int(g) for g in m.groups())
        if y > 2400:
            y -= 543
        try:
            return dt.date(y, mo, d), True
        except ValueError:
            return None, False
    return s, True


def norm_for_compare(v) -> str:
    return re.sub(r"\s+", "", str(v)).upper().replace("O", "0")


# ---------------------------------------------------------------- extraction

@dataclass
class Cell:
    value: object = None
    raw: str = ""
    source: str = ""               # text | ocr | manual
    flag: str = ""                 # non-empty = needs attention
    page: int = -1
    rect: list | None = None


@dataclass
class FileResult:
    path: str
    rows: list = field(default_factory=list)      # list[dict[col, Cell]]
    issues: list = field(default_factory=list)    # list[str]


def read_region(doc: PdfDoc, page: int, rect, col: Column, mode: str) -> Cell:
    def from_lines(lines):
        raw = col.joiner.join(lines)
        val, ok = convert(raw, col.type)
        return raw, val, ok

    if page < 0:
        page = len(doc) + page                 # -1 = last page
    if page < 0 or page >= len(doc):
        return Cell(flag="ไม่พบหน้า", page=page, rect=list(rect))

    if mode == "ocr":
        raw, val, ok = from_lines(doc.ocr_lines(page, rect))
        return Cell(val, raw, "ocr", "" if ok else "รูปแบบไม่ตรงชนิดข้อมูล", page, list(rect))

    raw_t, val_t, ok_t = from_lines(doc.text_lines(page, rect))
    if mode == "text":
        return Cell(val_t, raw_t, "text", "" if ok_t else "รูปแบบไม่ตรงชนิดข้อมูล", page, list(rect))

    if mode == "auto":
        if ok_t and raw_t:
            return Cell(val_t, raw_t, "text", "", page, list(rect))
        raw_o, val_o, ok_o = from_lines(doc.ocr_lines(page, rect))
        if ok_o and raw_o:
            return Cell(val_o, raw_o, "ocr", "", page, list(rect))
        if not raw_t and not raw_o:
            return Cell(None, "", "text", "", page, list(rect))
        return Cell(val_t if raw_t else val_o, raw_t or raw_o, "text" if raw_t else "ocr",
                    f"อ่านไม่ชัด (ข้อความ: {raw_t!r} / OCR: {raw_o!r})", page, list(rect))

    # compare
    raw_o, val_o, ok_o = from_lines(doc.ocr_lines(page, rect))
    same = norm_for_compare(val_t if val_t is not None else raw_t) == \
        norm_for_compare(val_o if val_o is not None else raw_o)
    best_ocr = ok_o and (not ok_t or not raw_t)
    val, raw, src = (val_o, raw_o, "ocr") if best_ocr else (val_t, raw_t, "text")
    flag = "" if same else f"ข้อความกับ OCR ไม่ตรงกัน (ข้อความ: {raw_t!r} / OCR: {raw_o!r})"
    return Cell(val, raw, src, flag, page, list(rect))


def locate_first_item(doc: PdfDoc, anchor: dict):
    """Find the item number "1" inside the anchor box -> (x0, y0, x1, y1) or None.

    Lets the user draw a loose box (even around the whole first item block).
    """
    page = anchor.get("page", 0)
    if page >= len(doc):
        return None
    x0, y0, x1, y1 = anchor["rect"]
    def ones(words):
        return [w for w in words if w[4].strip() == "1"
                and x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]

    if anchor.get("mode") == "ocr":
        # OCR the drawn box (works for loose boxes); a tiny box is too small for
        # tesseract, then OCR the whole column strip instead
        hits = ones(doc.ocr_words(page, (x0 - 6, y0 - 6, x1 + 6, y1 + 6)))
        if not hits:
            hits = ones(doc.ocr_words(page, (x0 - 6, 0, x1 + 6, doc.doc[page].rect.height)))
    else:
        hits = ones(doc.words(page))
    if not hits:
        return None
    top = min((w[1] + w[3]) / 2 for w in hits)           # top-most line (3pt tolerance) ...
    line = [w for w in hits if (w[1] + w[3]) / 2 - top <= 3]
    w = min(line, key=lambda w: w[0])                    # ... then left-most on that line
    return (w[0], w[1], w[2], w[3])


def resolve_anchor(doc: PdfDoc, anchor: dict) -> dict:
    """Tighten the anchor to the "1" it contains and fix the reference y of item #1.

    Templates saved by the app already carry a tight rect and "ref_y"; older ones
    (box center as reference) are corrected here so their regions don't shift.
    """
    a = dict(anchor)
    if "ref_y" in a:
        return a
    hit = locate_first_item(doc, a)
    if hit:
        a["rect"] = list(hit)
        a["ref_y"] = (hit[1] + hit[3]) / 2
    else:
        a["ref_y"] = (a["rect"][1] + a["rect"][3]) / 2
    return a


FIRST_ITEM_TOLERANCE = 15     # pt item #1 may sit above the template's position
MAX_ITEM_GAP = 5              # accept item numbers up to expected + 5 (unreadable numbers)
OCR_STRIP_MARGIN = 15         # pt added left/right of the anchor when OCR-ing the column
X_ALIGN_TOLERANCE = 6         # pt an item number's center may sit left/right of the anchor's


def find_items(doc: PdfDoc, anchor: dict, cancel=None, info: dict | None = None):
    """Return list of (item_no, page, y_center) found by walking 1,2,3... in the anchor x-band.

    Numbers that could not be read are tolerated (gaps): the slice between the
    neighbours is re-read with single-line OCR, else on the same page the y is
    interpolated. info (optional dict) receives "approx" (item numbers placed by
    interpolation) and "missing" (numbers not found, gap across pages).
    cancel: optional callable checked per page; it aborts by raising.
    """
    x0, y0, x1, y1 = anchor["rect"]
    xc = (x0 + x1) / 2
    x_tol = max(X_ALIGN_TOLERANCE, 1.5 * (y1 - y0))   # wider for multi-digit numbers / big fonts
    pad = 4
    found = []
    stray = []
    expected = 1
    start_page = anchor.get("page", 0)
    for pg in range(start_page, len(doc)):
        if cancel:
            cancel()
        band = (x0 - pad, 0, x1 + pad, doc.doc[pg].rect.height)
        if anchor.get("mode") == "ocr":
            # tesseract misses different digits depending on the crop: read a narrow and a
            # wide strip and merge (same number at the same height counted once)
            words = doc.ocr_words(pg, band)
            for w in doc.ocr_words(pg, (x0 - OCR_STRIP_MARGIN, 0, x1 + OCR_STRIP_MARGIN, band[3])):
                if not any(v[4] == w[4] and abs(v[1] - w[1]) < 3 for v in words):
                    words.append(w)
        else:
            words = [w for w in doc.words(pg) if band[0] <= (w[0] + w[2]) / 2 <= band[2]]
        # keep only numbers aligned with the item-number column (drops clipped neighbour glyphs)
        words = [w for w in words if abs((w[0] + w[2]) / 2 - xc) <= x_tol]
        nums = sorted(((int(w[4]), (w[1] + w[3]) / 2) for w in words if w[4].isdigit()),
                      key=lambda t: t[1])
        for i, (n, yc) in enumerate(nums):
            if pg == start_page and yc < y0 - FIRST_ITEM_TOLERANCE:
                continue                              # above item #1 on first page
            below_prev = not found or pg > found[-1][1] or yc > found[-1][2]
            # a jump (n > expected) is a stray digit when the expected number follows on this
            # page and is itself followed by expected + 1 (a lone fake digit doesn't count)
            rest = nums[i + 1:]
            jump_ok = n == expected or not any(
                m == expected and any(m2 == expected + 1 for m2, _ in rest[j + 1:])
                for j, (m, _) in enumerate(rest))
            if expected <= n <= expected + MAX_ITEM_GAP and below_prev and jump_ok and (n == 1 or found):
                found.append((n, pg, yc))
                expected = n + 1
            elif n > expected:
                stray.append((n, pg))
    approx, missing = _fill_gaps(doc, anchor, found, pad, cancel)
    if info is not None:
        info["approx"] = approx
        info["missing"] = missing
    return found, stray


def _fill_gaps(doc: PdfDoc, anchor: dict, found: list, pad: float, cancel=None):
    """Fill missing numbers between found neighbours in place; return (approx, missing)."""
    x0, _, x1, _ = anchor["rect"]
    approx, missing = [], []
    out = []
    for a, b in zip(found, found[1:] + [None]):
        out.append(a)
        if b is None or b[0] - a[0] <= 1:
            continue
        na, pa, ya = a
        nb, pb, yb = b
        if pa != pb:
            missing.extend(range(na + 1, nb))
            continue
        pitch = (yb - ya) / (nb - na)
        for k in range(na + 1, nb):
            if cancel:
                cancel()
            yk = ya + (k - na) * pitch
            sl = (x0 - pad, yk - pitch / 2, x1 + pad, yk + pitch / 2)
            if anchor.get("mode") == "ocr":
                words = doc.ocr_words(pa, sl, psm=7, min_conf=0)
            else:                                   # text layer: no OCR, just look in the slice
                words = [w for w in doc.words(pa)
                         if sl[0] <= (w[0] + w[2]) / 2 <= sl[2] and sl[1] <= (w[1] + w[3]) / 2 <= sl[3]]
            hit = [w for w in words if w[4] == str(k)]
            if hit:
                hy = (hit[0][1] + hit[0][3]) / 2
                # near the pitch: keep yk (a rule under the digit skews its OCR box);
                # far from it: rows have uneven heights, the hit is the better position
                out.append((k, pa, hy if abs(hy - yk) > pitch / 4 else yk))
            else:
                out.append((k, pa, yk))
                approx.append(k)
    found[:] = out
    return approx, missing


def extract(doc: PdfDoc, tpl: Template, progress=None, cancel=None) -> FileResult:
    """cancel: optional callable checked before every region/page read; it aborts by raising."""
    res = FileResult(doc.path)
    cols = {c.name: c for c in tpl.columns}
    header_regions = [r for r in tpl.regions if r.scope == "header" and r.column in cols]
    item_regions = [r for r in tpl.regions if r.scope == "item" and r.column in cols]

    header: dict[str, Cell] = {}
    for r in header_regions:
        if cancel:
            cancel()
        c = read_region(doc, r.page, r.rect, cols[r.column], r.mode)
        header[r.column] = merge_cell(header.get(r.column), c, cols[r.column])

    items = []
    if item_regions:
        if not tpl.anchor:
            res.issues.append("มีกรอบรายการ แต่ยังไม่ได้กำหนดจุดอ้างอิงเลขรายการ")
        else:
            anchor = resolve_anchor(doc, tpl.anchor)
            info: dict = {}
            found, stray = find_items(doc, anchor, cancel, info)
            for n in info.get("approx", []):
                res.issues.append(f"รายการ {n}: อ่านเลขรายการไม่ออก ใช้ตำแหน่งประมาณ")
            for n in info.get("missing", []):
                res.issues.append(f"ไม่พบเลขรายการ {n}")
            if not found:
                res.issues.append("ไม่พบเลขรายการ (1, 2, 3 ...) ในตำแหน่งที่กำหนด")
            for n, pg in stray:
                res.issues.append(f"พบเลขรายการ {n} ในหน้า {pg + 1} ที่อยู่นอกลำดับ — อาจมีรายการขาดหายหรือ layout ต่างจาก format")
            if found:
                _, p1, y1 = found[0]
                ref_y = anchor["ref_y"]
                ax = (anchor["rect"][0] + anchor["rect"][2]) / 2
                aw = anchor["rect"][2] - anchor["rect"][0]
                total = len(found) * len(item_regions)
                done = 0
                for n, pg, yc in found:
                    dy = yc - ref_y
                    row = {}
                    for r in item_regions:
                        if cancel:
                            cancel()
                        rr = [r.rect[0], r.rect[1] + dy, r.rect[2], r.rect[3] + dy]
                        if (cols[r.column].type == "number" and rr[0] <= ax <= rr[2]
                                and rr[1] <= yc <= rr[3] and rr[2] - rr[0] <= max(3 * aw, 30)):
                            # box over the item number itself: use the number already found
                            val, ok = convert(str(n), cols[r.column].type)
                            c = Cell(val, str(n), "anchor", "" if ok else "รูปแบบไม่ตรงชนิดข้อมูล",
                                     pg, rr)
                        else:
                            c = read_region(doc, pg, rr, cols[r.column], r.mode)
                        row[r.column] = merge_cell(row.get(r.column), c, cols[r.column])
                        done += 1
                        if progress:
                            progress(done, total)
                    items.append(row)

    if not items:
        items = [{}]
    for it in items:
        row = {name: Cell() for name in cols}
        row.update(header)
        row.update(it)
        res.rows.append(row)

    for chk in tpl.checks:
        hc = header.get(chk.header_column)
        if not hc or hc.value is None:
            continue
        vals = [r[chk.item_column].value for r in res.rows
                if chk.item_column in r and isinstance(r[chk.item_column].value, (int, float))]
        s = round(sum(vals), 4)
        if abs(s - float(hc.value)) > 0.01:
            res.issues.append(f"ผลรวม '{chk.item_column}' = {s:,.2f} ไม่ตรงกับ '{chk.header_column}' = {float(hc.value):,.2f}")

    for i, row in enumerate(res.rows, 1):
        for name, c in row.items():
            if c.flag:
                res.issues.append(f"แถว {i} / {name}: {c.flag}")
    return res


def merge_cell(prev: Cell | None, new: Cell, col: Column) -> Cell:
    """Several boxes for one column -> concatenate raw text."""
    if prev is None:
        return new
    raw = col.joiner.join(x for x in (prev.raw, new.raw) if x)
    val, ok = convert(raw, col.type)
    flag = "; ".join(f for f in (prev.flag, new.flag, "" if ok else "รูปแบบไม่ตรงชนิดข้อมูล") if f)
    return Cell(val, raw, prev.source, flag, prev.page, prev.rect)


# ---------------------------------------------------------------- export

def export(results: list[FileResult], tpl: Template, out_base: str, write_csv=True):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers = [c.name for c in tpl.columns]
    if tpl.include_source_file:
        headers.append(SOURCE_FILE_COL)

    wb = Workbook()
    ws = wb.active
    ws.title = safe_name(tpl.name)[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    flat = []
    for fr in results:
        for row in fr.rows:
            vals = []
            for c in tpl.columns:
                v = row.get(c.name, Cell()).value
                vals.append(v)
            if tpl.include_source_file:
                vals.append(os.path.basename(fr.path))
            flat.append(vals)

    for r_i, vals in enumerate(flat, start=2):
        for c_i, v in enumerate(vals, start=1):
            cell = ws.cell(row=r_i, column=c_i, value=v)
            ctype = tpl.columns[c_i - 1].type if c_i <= len(tpl.columns) else "string"
            if ctype == "string":
                cell.number_format = "@"
            elif ctype == "date":
                cell.number_format = "yyyy-mm-dd"
            elif ctype == "number":
                cell.number_format = "#,##0.00####"
    for i, h in enumerate(headers, start=1):
        width = max([len(str(h))] + [len(str(v[i - 1])) for v in flat if v[i - 1] is not None][:200])
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(max(width + 2, 8), 60)
    ws.freeze_panes = "A2"

    xlsx = out_base + ".xlsx"
    wb.save(xlsx)
    paths = [xlsx]
    if write_csv:
        path = out_base + ".csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for vals in flat:
                w.writerow([_csv_value(v) for v in vals])
        paths.append(path)
    return paths


def _csv_value(v):
    if v is None:
        return ""
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)                      # 4000.0 -> 4000
    return v


def default_export_name(tpl: Template) -> str:
    return f"{safe_name(tpl.name)}_{dt.datetime.now():%Y%m%d_%H%M}"

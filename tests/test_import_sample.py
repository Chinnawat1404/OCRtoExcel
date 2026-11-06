"""Headless check of the engine against the import declaration sample.

Run:  py tests\\test_import_sample.py "<path to import sample pdf>"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import datetime as dt
from engine import Template, Column, Region, SumCheck, PdfDoc, extract, export

tpl = Template(
    name="ทดสอบขาเข้า",
    columns=[
        Column("เลขที่ใบขน"), Column("ใบตราส่ง"), Column("วันนำเข้า", "date"),
        Column("พิกัด"), Column("ราคา USD", "number"), Column("ราคา THB", "number"),
        Column("น้ำหนักสุทธิ", "number"), Column("ปริมาณ", "number"),
        Column("invoice"), Column("ชนิดของ"), Column("รวม THB", "number"),
    ],
    regions=[
        Region("เลขที่ใบขน", "header", 0, [497, 38, 582, 55], "ocr"),
        Region("ใบตราส่ง", "header", 0, [36, 232, 200, 250], "auto"),
        Region("วันนำเข้า", "header", 0, [230, 260, 275, 274], "auto"),
        Region("พิกัด", "item", 0, [60, 388, 112, 400], "text"),
        Region("ราคา USD", "item", 0, [112, 385, 175, 398], "text"),
        Region("ราคา THB", "item", 0, [112, 408, 175, 420], "text"),
        Region("น้ำหนักสุทธิ", "item", 0, [112, 430, 175, 444], "text"),
        Region("ปริมาณ", "item", 0, [205, 427, 270, 440], "text"),
        Region("invoice", "item", 0, [58, 471, 180, 482], "text"),
        Region("ชนิดของ", "item", 0, [274, 447, 420, 468], "ocr"),
        Region("รวม THB", "header", -1, [125, 676, 176, 696], "auto"),
    ],
    anchor={"page": 0, "rect": [38, 407, 50, 418], "mode": "text", "ref_y": 412.5},  # legacy reference
    checks=[SumCheck("รวม THB", "ราคา THB")],
)

doc = PdfDoc(sys.argv[1])
res = extract(doc, tpl)
for i, row in enumerate(res.rows, 1):
    print(i, {k: (c.value, c.source) for k, c in row.items()})
print("ISSUES:", *res.issues, sep="\n  ")

r0 = res.rows[0]
assert len(res.rows) == 7, len(res.rows)
assert r0["เลขที่ใบขน"].value == "PPKR100061568", r0["เลขที่ใบขน"].value
assert r0["ใบตราส่ง"].value == "HHSW00875836"
assert r0["วันนำเข้า"].value == dt.date(2026, 10, 5), r0["วันนำเข้า"].value
assert r0["พิกัด"].value == "8507.60.90"
assert r0["ราคา USD"].value == 64000.0
assert r0["ราคา THB"].value == 2139808.0
assert r0["น้ำหนักสุทธิ"].value == 236.0
assert r0["ปริมาณ"].value == 4000.0
assert r0["invoice"].value.endswith("TXDO2026090107")
assert res.rows[3]["ราคา USD"].value == 88000.0          # item 4 on page 2
assert res.rows[6]["น้ำหนักสุทธิ"].value == 100.3        # item 7

# the reference is the "1" found in the anchor box: a loose box around the whole
# first item block must give the same rows as a tight box around the "1"
import copy
tight, loose = copy.deepcopy(tpl), copy.deepcopy(tpl)
tight.anchor = {"page": 0, "rect": [40, 408, 50, 428], "mode": "text"}
loose.anchor = {"page": 0, "rect": [37, 384, 575, 486], "mode": "text"}
res = extract(doc, tight)
res2 = extract(doc, loose)
item_cols = [r.column for r in tpl.regions if r.scope == "item"]
assert len(res2.rows) == len(res.rows), len(res2.rows)
for a, b in zip(res.rows, res2.rows):
    for col in item_cols:
        assert a[col].value == b[col].value, (col, a[col].value, b[col].value)
# OCR of a box about one line high returns that one line, even when the box is drawn
# into the line above (to keep Thai tone marks) or cuts the marks
import pymupdf
for box in ([275, 460, 572, 470], [275, 456, 572, 470], [275, 462.5, 572, 468.5]):
    lines = doc._ocr_lines_in_box(0, pymupdf.Rect(box))
    assert len(lines) == 1 and "ชาร์ต" in lines[0] and "LITHIUM" not in lines[0], (box, lines)
lines = doc._ocr_lines_in_box(0, pymupdf.Rect(275, 452, 572, 470))   # a two-line box
assert len(lines) == 2 and "LITHIUM" in lines[0] and "ชาร์ต" in lines[1], lines

out = os.path.join(os.environ["TEMP"], "pdf2xl_test")
paths = export([res], tpl, out)
print(paths)
for p in paths:                                           # confidential data: clean up
    os.remove(p)
print("OK")

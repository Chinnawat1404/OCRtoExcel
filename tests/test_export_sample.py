"""Headless check on the export declaration sample (9 pages, unreliable text layer -> OCR).

Run:  py tests\test_export_sample.py [path to export sample pdf]
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from engine import Template, Column, Region, PdfDoc, extract

SAMPLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "samples", "export_sample.pdf")

tpl = Template(
    name="ทดสอบขาออก",
    columns=[Column("ลำดับ", "number"), Column("ราคา USD", "number"), Column("น้ำหนัก (KGM)", "number")],
    regions=[
        Region("ลำดับ", "item", 0, [36, 368, 50, 383], "ocr"),
        Region("ราคา USD", "item", 0, [415, 350, 480, 365], "ocr"),
        Region("น้ำหนัก (KGM)", "item", 0, [335, 342, 400, 353], "ocr"),
    ],
    anchor={"page": 0, "rect": [36, 368, 50, 383], "mode": "ocr"},     # text layer drops digits
)

t0 = time.time()
res = extract(PdfDoc(SAMPLE), tpl)
assert len(res.rows) == 34, len(res.rows)
assert [r["ลำดับ"].value for r in res.rows] == list(range(1, 35))
assert not res.issues, res.issues
usd = round(sum(r["ราคา USD"].value for r in res.rows), 2)
kgm = round(sum(r["น้ำหนัก (KGM)"].value for r in res.rows), 3)
assert usd == 2832448.80, usd                      # document total on the last page
assert kgm == 5160.396, kgm                        # N/W total on the last page
print("items:", len(res.rows), f"time: {time.time() - t0:.1f}s")
print("OK")

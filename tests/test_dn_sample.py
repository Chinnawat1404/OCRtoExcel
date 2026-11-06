"""Headless check of gap-tolerant item finding on a scanned-like sample (no text layer).

Run:  py tests\test_dn_sample.py [path to dn sample pdf]
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from engine import Template, Column, Region, PdfDoc, extract, find_items, resolve_anchor

SAMPLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "samples", "dn_sample.pdf")

tpl = Template(
    name="ทดสอบ DN",
    columns=[Column("ชื่อของเสีย")],
    regions=[Region("ชื่อของเสีย", "item", 0, [76, 100, 236, 111], "ocr")],
    anchor={"page": 0, "rect": [40, 100, 58, 112], "mode": "ocr"},
)

t0 = time.time()
doc = PdfDoc(SAMPLE)
info = {}
found, stray = find_items(doc, resolve_anchor(doc, tpl.anchor), info=info)
nums = [n for n, _, _ in found]
assert nums == list(range(1, 17)), nums
assert 2 not in info["approx"], info                      # re-read by single-line OCR
ys = [y for _, _, y in found]
assert ys == sorted(ys), ys

res = extract(doc, tpl)
assert len(res.rows) == 16, len(res.rows)
approx_issues = [s for s in res.issues if "ใช้ตำแหน่งประมาณ" in s]
assert all(s.startswith("รายการ 11:") for s in approx_issues), approx_issues
assert 11 in info["approx"] or not approx_issues
assert "vinyl" in res.rows[1]["ชื่อของเสีย"].raw.lower()   # row 2 (short check only)
print("items:", len(res.rows), "approx:", info["approx"], "missing:", info["missing"],
      f"time: {time.time() - t0:.1f}s")
print("OK")

"""Offscreen smoke test of the GUI: template tab, import tab worker, manual edit, export.

Run:  py tests\\test_gui_smoke.py [path to import sample pdf]
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtCore import QEvent, QItemSelectionModel, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import engine
from engine import Template, Column, Region, SumCheck
import app as gui

SAMPLE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "samples", "import_sample.pdf")
TPL_NAME = "_ทดสอบ_GUI_smoke"
TPL_NAME2 = "_ทดสอบ_GUI_smoke2"
TPL_NAME3 = "_ทดสอบ_GUI_smoke3"
OUT = os.path.join(os.environ["TEMP"], "pdf2xl_gui_smoke")

tpl = Template(
    name=TPL_NAME,
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
    anchor={"page": 0, "rect": [38, 407, 50, 418], "mode": "text", "ref_y": 412.5},
    checks=[SumCheck("รวม THB", "ราคา THB")],
)

qapp = QApplication.instance() or QApplication(sys.argv)
win = gui.MainWindow()
win.show()
try:
    # ---- template tab
    tt = win.template_tab
    tt.set_template(tpl)
    tt.save()
    assert TPL_NAME in engine.list_templates()
    assert tt.reg_table.rowCount() == len(tpl.regions)
    tt.open_sample(SAMPLE)
    assert tt.pdf.view.page_count() >= 2
    tt.pdf.view.next_page(); tt.pdf.view.prev_page(); tt.pdf.view.zoom_in(); tt.pdf.view.fit_width()
    c = tt.test_region(3)                                   # พิกัด, item #1
    assert c.value == "8507.60.90", c.value
    tt._anchor_mode = True
    tt.pdf.view.rectDrawn.emit([37, 384, 575, 486])          # loose box around item #1
    a = tt.tpl.anchor
    assert a["mode"] == "ocr", a
    assert 43 <= a["rect"][0] and a["rect"][2] <= 48, a        # tightened to the "1"
    assert abs(a["ref_y"] - 418.15) < 2.5, a                 # OCR box vs text-layer box
    # keep the legacy reference the item boxes of this test were drawn against
    tt.tpl.anchor = {"page": 0, "rect": [38, 407, 50, 418], "mode": "text", "ref_y": 412.5}
    tt.refresh_regions()

    # ---- F3: New refuses an existing name; rename collision asks (hook)
    assert tt.new_template(TPL_NAME) is False
    assert tt.tpl.name == TPL_NAME and tt.tpl.columns, "existing template must not be replaced"
    engine.Template(TPL_NAME2).save()
    tt.confirm_overwrite = lambda name: False
    assert tt.rename(TPL_NAME2) is False and tt.tpl.name == TPL_NAME
    # ---- F7: unsaved edits block a combo switch when the user declines
    tt.add_column("ชั่วคราว")
    assert tt.is_dirty()
    tt.confirm_discard = lambda: False
    tt.on_combo_changed(engine.safe_name(TPL_NAME2))
    assert tt.tpl.name == TPL_NAME and tt.tpl.column("ชั่วคราว")
    assert tt.new_template("_ทดสอบ_GUI_ไม่ควรสร้าง") is False
    del tt.tpl.columns[-1]
    tt.refresh()
    assert not tt.is_dirty()
    engine.delete_template(TPL_NAME2)

    # ---- T002: template undo/redo
    tt.reset_history()
    assert not tt.can_undo() and not tt.btn_undo.isEnabled()
    n = len(tt.tpl.regions)
    tt.add_region(Region("พิกัด", "item", 0, [1, 1, 20, 20], "text"))
    assert len(tt.tpl.regions) == n + 1 and tt.can_undo() and tt.btn_undo.isEnabled()
    tt.undo()
    assert len(tt.tpl.regions) == n and tt.reg_table.rowCount() == n and tt.can_redo()
    tt.redo()
    assert len(tt.tpl.regions) == n + 1 and tt.tpl.regions[-1].rect == [1, 1, 20, 20]
    tt.undo()
    assert not tt.is_dirty(), "undo back to saved state must not be dirty"
    tt.col_table.item(3, 0).setText("พิกัดใหม่")             # rename column via the table
    assert tt.tpl.columns[3].name == "พิกัดใหม่" and any(r.column == "พิกัดใหม่" for r in tt.tpl.regions)
    assert tt.is_dirty()
    tt.undo()
    assert tt.tpl.columns[3].name == "พิกัด" and tt.col_table.item(3, 0).text() == "พิกัด"
    assert not any(r.column == "พิกัดใหม่" for r in tt.tpl.regions) and not tt.is_dirty()
    tt.redo()
    assert tt.tpl.columns[3].name == "พิกัดใหม่"
    tt.undo()
    assert len(tt.tpl.checks) == 1 and not hasattr(tt, "chk_list")   # AC6: kept, not editable

    # ---- T006 AC2: multi-select delete of columns / regions is one undo step
    def select_rows(table, rows):
        table.clearSelection()
        for r in rows:
            table.selectionModel().select(table.model().index(r, 0),
                                          QItemSelectionModel.Select | QItemSelectionModel.Rows)
    tt.reset_history()
    before = tt._snap()
    names = [c.name for c in tt.tpl.columns]
    select_rows(tt.col_table, [8, 9])
    tt.on_remove_column()
    assert [c.name for c in tt.tpl.columns] == names[:8] + names[10:], [c.name for c in tt.tpl.columns]
    assert len(tt._undo) == 1
    tt.undo()
    assert tt._snap() == before and not tt.can_undo()
    n = len(tt.tpl.regions)
    select_rows(tt.reg_table, [0, 2])
    assert tt.selected_regions() == [0, 2]
    tt.on_remove_region()
    assert len(tt.tpl.regions) == n - 2 and tt.reg_table.rowCount() == n - 2 and len(tt._undo) == 1
    assert tt.tpl.regions[0].column == "ใบตราส่ง"
    tt.undo()
    assert tt._snap() == before and not tt.can_undo()
    tt.reg_table.selectAll()
    assert tt.selected_regions() == list(range(n))
    tt.reg_table.clearSelection()

    # ---- T006 AC3: select a region -> editable box with 8 handles; resize = one undo step
    v = tt.pdf.view
    tt.reg_table.selectRow(3)
    assert v.highlight and v.highlight[2] == 3 and len(v._handles) == 8, v.highlight
    old = list(tt.tpl.regions[3].rect)
    v.boxEdited.emit(3, [60.0, 380.0, 120.0, 402.0])        # what a drag release emits
    assert tt.tpl.regions[3].rect == [60, 380, 120, 402] and len(tt._undo) == 1
    assert tt.reg_table.item(3, 4).text() == "60, 380, 120, 402"
    assert v.highlight[1] == [60, 380, 120, 402] and tt.selected_regions() == [3]
    tt.undo()
    assert tt.tpl.regions[3].rect == old and not tt.can_undo()
    # real mouse drag of the bottom-right handle on the viewport
    tt.reg_table.selectRow(3)
    qapp.processEvents()
    br = v.mapFromScene(QPointF(old[2], old[3]))
    to = v.mapFromScene(QPointF(old[2] + 20, old[3] + 10))
    QTest.mousePress(v.viewport(), Qt.LeftButton, Qt.NoModifier, br)
    QTest.mouseMove(v.viewport(), to)
    QTest.mouseRelease(v.viewport(), Qt.LeftButton, Qt.NoModifier, to)
    r3 = tt.tpl.regions[3].rect
    assert r3[:2] == old[:2] and abs(r3[2] - old[2] - 20) < 1.5 and abs(r3[3] - old[3] - 10) < 1.5, r3
    assert len(tt._undo) == 1
    tt.undo()
    assert tt.tpl.regions[3].rect == old

    # ---- T006 AC4: deleting the highlighted region removes its highlight
    tt.reg_table.selectRow(0)
    assert v.highlight is not None
    tt.on_remove_region()
    assert v.highlight is None and not tt.selected_regions()
    tt.undo()
    assert tt._snap() == before

    # ---- T006 AC6: page spinbox and tab-scoped shortcuts
    win.tabs.setCurrentIndex(0)
    win.activateWindow()
    v.setFocus()
    qapp.processEvents()
    v.set_page(0)
    assert tt.pdf.spin.value() == 1 and tt.pdf.spin.suffix() == f" / {v.page_count()}"
    tt.pdf.spin.setValue(2)
    assert v.page == 1
    QTest.keyClick(v, Qt.Key_PageUp)
    assert v.page == 0 and tt.pdf.spin.value() == 1, v.page
    QTest.keyClick(v, Qt.Key_PageDown)
    assert v.page == 1, v.page
    z = v.zoom
    QTest.keyClick(v, Qt.Key_Equal, Qt.ControlModifier)
    assert v.zoom > z and tt.pdf.zoom_lbl.text() == f"{v.zoom * 100:.0f}%"
    QTest.keyClick(v, Qt.Key_Minus, Qt.ControlModifier)
    assert abs(v.zoom - z) < 1e-6
    # R4: PgDn in a table moves within the table, not the PDF; spinbox PgDn = one page
    tt.col_table.setFocus()
    QTest.keyClick(tt.col_table, Qt.Key_PageDown)
    assert v.page == 1, v.page
    v.set_page(0)
    QTest.keyClick(tt.pdf.spin, Qt.Key_PageDown)
    assert v.page == 1, v.page
    v.set_page(0)

    # ---- T006 R1: the window fits a 1280x720 screen
    assert win.minimumSizeHint().width() <= 1200, win.minimumSizeHint()

    def drag(p0, p1):
        QTest.mousePress(v.viewport(), Qt.LeftButton, Qt.NoModifier, v.mapFromScene(p0))
        QTest.mouseMove(v.viewport(), v.mapFromScene(p1))
        QTest.mouseRelease(v.viewport(), Qt.LeftButton, Qt.NoModifier, v.mapFromScene(p1))

    # ---- T006 R5: a short box can be moved by dragging its middle
    tt.reset_history()
    tt.add_region(Region("พิกัด", "item", 0, [300, 300, 360, 306], "text"))
    k = len(tt.tpl.regions) - 1
    qapp.processEvents()
    drag(QPointF(330, 303), QPointF(340, 313))
    rk = tt.tpl.regions[k].rect
    assert abs(rk[0] - 310) < 1.5 and abs(rk[1] - 310) < 1.5 and abs((rk[2] - rk[0]) - 60) < 0.2 \
        and abs((rk[3] - rk[1]) - 6) < 0.2, rk

    # ---- T006 R3: dragging beyond the page clamps the box to the page
    v.set_zoom(0.4)                                         # page plus empty margin visible
    qapp.processEvents()
    pw, ph = v.sceneRect().width(), v.sceneRect().height()
    rk = tt.tpl.regions[k].rect
    drag(QPointF(rk[0] + 30, rk[1] + 3), QPointF(rk[0] + 30 + pw, rk[1] + 3))     # move far right
    rk = tt.tpl.regions[k].rect
    assert abs(rk[2] - pw) < 1.5 and abs((rk[2] - rk[0]) - 60) < 0.2, (rk, pw)
    drag(QPointF(rk[2], rk[3]), QPointF(rk[2] + 100, ph + 100))                  # resize past corner
    rk = tt.tpl.regions[k].rect
    assert rk[2] <= pw + 0.1 and rk[3] <= ph + 0.1, (rk, pw, ph)
    while tt.can_undo():
        tt.undo()
    assert len(tt.tpl.regions) == k and tt._snap() == before
    v.fit_width()
    v.set_page(0)

    # ---- T007 AC1/AC3: tool modes (pointer default, no drawing on empty space; draw over boxes)
    assert v.tool == "pointer" and tt.pdf.tool_buttons["pointer"].isChecked()
    assert list(tt.pdf.tool_buttons) == ["pointer", "hand", "draw"]
    assert tt.pdf.bar.itemAt(0).widget() is tt.pdf.tool_buttons["pointer"]
    drawn = []
    v.rectDrawn.disconnect(tt.on_rect_drawn)                # avoid the modal RegionDialog
    v.rectDrawn.connect(drawn.append)
    tt.reg_table.clearSelection()
    drag(QPointF(5, 5), QPointF(30, 30))                    # empty corner of the page
    assert drawn == [] and v.highlight is None
    tt.reg_table.selectRow(3)
    tt.pdf.tool_buttons["draw"].click()
    assert v.tool == "draw" and tt.pdf.tool_buttons["draw"].isChecked() and not v._handles
    r3 = tt.tpl.regions[3].rect
    drag(QPointF(r3[0] + 5, r3[1] + 3), QPointF(r3[0] + 40, r3[1] + 30))   # starts inside a box
    assert len(drawn) == 1 and tt.tpl.regions[3].rect == r3, drawn
    assert v.tool == "draw"                                 # stays in draw mode
    tt.pdf.tool_buttons["hand"].click()
    assert v.tool == "hand" and v.dragMode() == gui.QGraphicsView.ScrollHandDrag
    drag(QPointF(r3[0] + 5, r3[1] + 3), QPointF(r3[0] + 40, r3[1] + 30))
    assert len(drawn) == 1 and tt.tpl.regions[3].rect == r3
    v.set_zoom(3.0)                                         # hand drag scrolls the view
    qapp.processEvents()
    sb = v.verticalScrollBar()
    sb.setValue(sb.maximum() // 2)
    y0 = sb.value()
    p0, p1 = QPointF(200, 200), QPointF(200, 120)
    QTest.mousePress(v.viewport(), Qt.LeftButton, Qt.NoModifier, p0.toPoint())
    QApplication.sendEvent(v.viewport(), QMouseEvent(QEvent.MouseMove, p1, v.viewport().mapToGlobal(p1),
                                                     Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    QTest.mouseRelease(v.viewport(), Qt.LeftButton, Qt.NoModifier, p1.toPoint())
    assert sb.value() > y0, (y0, sb.value())
    v.fit_width()
    v.rectDrawn.disconnect(drawn.append)
    v.rectDrawn.connect(tt.on_rect_drawn)

    # ---- T007 AC2: V/H/R shortcuts (ignored while typing) and Space-hold hand
    v.setFocus()
    qapp.processEvents()
    for key, tool in ((Qt.Key_V, "pointer"), (Qt.Key_R, "draw"), (Qt.Key_H, "hand"), (Qt.Key_V, "pointer")):
        QTest.keyClick(v, key)
        assert v.tool == tool and tt.pdf.tool_buttons[tool].isChecked(), (key, v.tool)
    v.set_tool("draw")
    QTest.keyPress(v, Qt.Key_Space)
    assert v.tool == "hand"
    QTest.keyRelease(v, Qt.Key_Space)
    assert v.tool == "draw"
    v.set_tool("pointer")
    nreg = len(tt.tpl.regions)
    tt.col_table.editItem(tt.col_table.item(0, 0))          # column-name editor (QLineEdit)
    qapp.processEvents()
    ed = QApplication.focusWidget()
    assert isinstance(ed, gui.QLineEdit), ed
    QTest.keyClick(ed, Qt.Key_R)
    QTest.keyClick(ed, Qt.Key_Delete)
    assert v.tool == "pointer" and len(tt.tpl.regions) == nreg
    QTest.keyClick(ed, Qt.Key_Escape)                       # cancel the edit
    qapp.processEvents()
    assert tt.tpl.columns[0].name == "เลขที่ใบขน", tt.tpl.columns[0].name

    # ---- T007 AC5: Delete / Backspace delete selected regions or the anchor (one undo step)
    tt.reset_history()
    before = tt._snap()
    select_rows(tt.reg_table, [0, 2])
    v.setFocus()
    QTest.keyClick(v, Qt.Key_Delete)
    assert len(tt.tpl.regions) == nreg - 2 and len(tt._undo) == 1 and v.highlight is None
    tt.undo()
    select_rows(tt.reg_table, [1])
    tt.reg_table.setFocus()
    QTest.keyClick(tt.reg_table, Qt.Key_Backspace)
    assert len(tt.tpl.regions) == nreg - 1 and len(tt._undo) == 1
    tt.undo()
    assert tt._snap() == before
    anchor0 = dict(tt.tpl.anchor)
    tt._on_box_clicked("anchor")
    assert v.highlight and v.highlight[2] == "anchor" and not tt.selected_regions()
    v.setFocus()
    QTest.keyClick(v, Qt.Key_Delete)
    assert tt.tpl.anchor is None and len(tt.tpl.regions) == nreg and len(tt._undo) == 1
    tt.undo()
    assert tt.tpl.anchor == anchor0 and tt._snap() == before
    tt.col_table.setFocus()
    tt.col_table.setCurrentCell(0, 0)
    select_rows(tt.reg_table, [0])
    QTest.keyClick(tt.col_table, Qt.Key_Delete)             # columns table: no region deletion
    assert len(tt.tpl.regions) == nreg and len(tt.tpl.columns) == len(tpl.columns)
    tt.reg_table.clearSelection()

    # ---- T007 AC3: anchor tool flow: draw -> anchor set -> back to pointer
    tt.on_anchor_mode()
    assert v.tool == "draw"
    v.rectDrawn.emit([37, 384, 575, 486])
    assert v.tool == "pointer" and tt.tpl.anchor["mode"] == "ocr"
    tt.undo()
    assert tt._snap() == before

    # ---- F6: engine cancel hook aborts extraction
    class _Stop(Exception):
        pass
    def _cancel():
        raise _Stop()
    try:
        engine.extract(tt._sample_doc, tpl, cancel=_cancel)
        raise AssertionError("cancel ignored")
    except _Stop:
        pass

    # ---- OCR-mode anchor (engine.ocr_words via tesseract TSV)
    ocr_tpl = engine.Template.from_dict(__import__("json").loads(tpl.to_json()))
    ocr_tpl.anchor["mode"] = "ocr"
    found, _ = engine.find_items(tt._sample_doc, ocr_tpl.anchor)
    assert [n for n, _, _ in found] == list(range(1, 8)), found

    # ---- T006 AC1: close the sample PDF
    tt.close_sample()
    assert tt.sample_path is None and tt._sample_doc is None and tt.pdf.view.doc is None
    assert not tt.pdf.view.scene().items() and tt.pdf.spin.suffix() == " / 0"
    assert not tt.btn_close_pdf.isEnabled() and not any(b.isEnabled() for b in tt.sample_buttons)
    assert tt.test_region(3) is None and tt.test_file() is None

    # ---- import tab
    it = win.import_tab
    # ---- T007 AC4: import tab offers pointer + hand only, default pointer
    assert list(it.pdf.tool_buttons) == ["pointer", "hand"] and it.pdf.view.tool == "pointer"
    it.pdf.view.set_tool("draw")
    assert it.pdf.view.tool == "pointer"
    it.combo.setCurrentText(engine.safe_name(TPL_NAME))
    assert it.tpl and it.tpl.name == TPL_NAME
    it.add_files([SAMPLE])
    it.start_extraction()
    assert not it.combo.isEnabled() and not it.file_buttons[0].isEnabled()   # F2
    t0 = time.time()
    while it.worker is not None and time.time() - t0 < 600:
        qapp.processEvents()
        time.sleep(0.02)
    qapp.processEvents()
    fr = it.current_result()
    assert fr is not None, "extraction did not finish"
    assert len(fr.rows) == 7, len(fr.rows)
    assert it.table.rowCount() == 7 and it.table.columnCount() == len(tpl.columns)
    col_usd = [c.name for c in tpl.columns].index("ราคา USD")
    assert it.table.item(3, col_usd).text() == "88,000", it.table.item(3, col_usd).text()
    assert it.file_list.item(0).text().startswith(("✅", "⚠️"))
    it.on_cell_clicked(3, col_usd)
    assert it.pdf.view.page == fr.rows[3]["ราคา USD"].page

    # ---- F5: header cell on the last page (-1) jumps to the last page
    col_tot = [c.name for c in tpl.columns].index("รวม THB")
    it.pdf.view.set_highlight(-1, fr.rows[0]["รวม THB"].rect)
    assert it.pdf.view.page == it.pdf.view.page_count() - 1, it.pdf.view.page
    it.pdf.view.set_page(0)

    # ---- F1: saving a template elsewhere keeps current results
    tt.save()
    qapp.processEvents()
    assert it.current_result() is fr and it.table.rowCount() == 7

    # ---- manual edit via the table item (as the user would)
    it.table.item(0, col_usd).setText("1,234.5")
    cell = fr.rows[0]["ราคา USD"]
    assert cell.source == "manual" and cell.value == 1234.5 and cell.flag == "", cell
    item = it.table.item(0, col_usd)
    assert item.text() == "1,234.5" and item.background().color() == gui.MANUAL_COLOR   # F4 in place
    it.table.item(1, col_usd).setText("abc")                # bad number -> flagged
    assert fr.rows[1]["ราคา USD"].flag and it.table.item(1, col_usd).background().color() == gui.FLAG_COLOR
    it.table.item(1, col_usd).setText("88,000")
    assert fr.rows[1]["ราคา USD"].flag == ""

    # ---- T002: import-tab undo/redo of a cell edit
    orig = fr.rows[2]["ราคา USD"]
    orig_text = it.table.item(2, col_usd).text()
    it.table.item(2, col_usd).setText("5")
    assert fr.rows[2]["ราคา USD"].source == "manual" and it.can_undo()
    it.undo()
    c2 = fr.rows[2]["ราคา USD"]
    assert c2 is orig and c2.source != "manual" and c2.flag == orig.flag
    assert it.table.item(2, col_usd).text() == orig_text and it.can_redo()
    it.redo()
    assert fr.rows[2]["ราคา USD"].value == 5.0 and it.table.item(2, col_usd).background().color() == gui.MANUAL_COLOR
    it.undo()
    assert fr.rows[2]["ราคา USD"] is orig

    # ---- export
    issues = it.all_issues()
    paths = it.export_to(OUT)
    assert all(os.path.exists(p) for p in paths), paths
    from openpyxl import load_workbook
    ws = load_workbook(paths[0]).active
    assert ws.max_row == 8, ws.max_row
    assert ws.cell(row=2, column=col_usd + 1).value == 1234.5
    # ---- F1: rename / delete of the active template keep results
    assert tt.rename(TPL_NAME3)
    qapp.processEvents()
    assert it.current_result() is fr and it._tpl_name == engine.safe_name(TPL_NAME3), it._tpl_name
    assert it.combo.currentText() == engine.safe_name(TPL_NAME3)
    tt.delete(engine.safe_name(TPL_NAME3))
    qapp.processEvents()
    assert it.current_result() is fr and it.tpl is not None and it.table.rowCount() == 7
    assert len(it.export_to(OUT)) == 2
    print("rows:", len(fr.rows), "issues:", len(issues), "exported:", paths)
    print("OK")
finally:
    win.close()
    for n in (TPL_NAME, TPL_NAME2, TPL_NAME3):
        if n in engine.list_templates():
            engine.delete_template(n)
    for ext in (".xlsx", ".csv"):                            # confidential data: clean up
        if os.path.exists(OUT + ext):
            os.remove(OUT + ext)

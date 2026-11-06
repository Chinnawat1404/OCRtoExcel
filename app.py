"""PdfToExcel desktop GUI (PySide6) over engine.py.

Tab 1 builds templates (columns, regions drawn on a sample PDF, anchor).
Tab 2 imports PDFs, extracts in a background thread, lets the user review/edit, exports.
All extraction/typing/export logic lives in engine.py.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

import pymupdf
from PySide6.QtCore import Qt, QEvent, QRectF, QThread, Signal, QPointF, QItemSelectionModel
from PySide6.QtGui import (QPalette, QBrush, QColor, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap,
                           QFont, QShortcut)
from PySide6.QtWidgets import (QGridLayout, QSizePolicy, 
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGraphicsItem, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
    QGraphicsSimpleTextItem, QGraphicsView, QGroupBox, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QSplitter, QStyle, QTableWidget,
    QTableWidgetItem, QTabWidget, QToolButton, QVBoxLayout, QWidget, QButtonGroup, QLineEdit,
    QTextEdit, QAbstractSpinBox,
)

import engine
from engine import Cell, Column, FileResult, PdfDoc, Region, SumCheck, Template

APP_TITLE = "PdfToExcel – อ่านใบขนสินค้า"
TYPE_LABELS = {"string": "ข้อความ", "number": "ตัวเลข", "date": "วันที่"}
SCOPE_LABELS = {"header": "หัวเอกสาร (ค่าเดียวทุกแถว)", "item": "รายการ (วาดที่รายการที่ 1)"}
MODE_LABELS = {"auto": "อัตโนมัติ", "text": "ข้อความในไฟล์", "ocr": "OCR (อ่านจากภาพ)",
               "compare": "เทียบข้อความกับ OCR"}
UI_MODES = ["ocr", "text"]          # read modes offered in the UI (OCR is the default)
LEGACY_MODES = {"auto": "ocr", "compare": "ocr"}
LAST_PAGE_LABEL = "หน้าสุดท้าย"
FLAG_COLOR = QColor(255, 235, 120)
MANUAL_COLOR = QColor(200, 230, 255)
PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#46a0a0",
           "#c03cc0", "#808000", "#9a6324", "#000075"]
RENDER_ZOOM = 2.0       # pixmap resolution relative to PDF points
UNDO_LIMIT = 200        # max undo steps kept per tab
TOP_GROUP_HEIGHT = 170  # import tab: file list group == issues group height
HANDLE_PX = 7          # grab distance (screen pixels) of a resize handle
HANDLE_CURSORS = {"tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor, "tr": Qt.SizeBDiagCursor,
                  "bl": Qt.SizeBDiagCursor, "t": Qt.SizeVerCursor, "b": Qt.SizeVerCursor,
                  "l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor, "move": Qt.SizeAllCursor}


def color_for(i: int) -> QColor:
    return QColor(PALETTE[i % len(PALETTE)])


def fmt_rect(rect) -> str:
    return ", ".join(f"{v:.0f}" for v in rect)


def fmt_value(v) -> str:
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    return str(v)


def file_status(fr: FileResult | None) -> str:
    if fr is None:
        return "⏳"
    return f"⚠️({len(fr.issues)})" if fr.issues else "✅"


# ---------------------------------------------------------------- icons / tool buttons

def _painted_icon(draw) -> QIcon:
    """Icon drawn in the theme's text colour (visible on light and dark themes)."""
    pal = QApplication.palette()
    icon = QIcon()
    for mode, color in ((QIcon.Normal, pal.color(QPalette.Active, QPalette.ButtonText)),
                        (QIcon.Disabled, pal.color(QPalette.Disabled, QPalette.ButtonText))):
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(color, 3, Qt.SolidLine, Qt.RoundCap))
        draw(p)
        p.end()
        icon.addPixmap(pm, mode)
    return icon


def zoom_icon(plus: bool) -> QIcon:
    def draw(p: QPainter):
        p.drawEllipse(3, 3, 18, 18)
        p.drawLine(19, 19, 28, 28)
        p.drawLine(8, 12, 16, 12)
        if plus:
            p.drawLine(12, 8, 12, 16)
    return _painted_icon(draw)


def fit_width_icon() -> QIcon:
    def draw(p: QPainter):
        p.drawLine(3, 6, 3, 26)
        p.drawLine(29, 6, 29, 26)
        p.drawLine(8, 16, 24, 16)
        p.drawLine(8, 16, 12, 12)
        p.drawLine(8, 16, 12, 20)
        p.drawLine(24, 16, 20, 12)
        p.drawLine(24, 16, 20, 20)
    return _painted_icon(draw)


def pointer_icon() -> QIcon:
    def draw(p: QPainter):
        pen = p.pen()
        pen.setWidthF(2.2)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolygon([QPointF(8, 3), QPointF(8, 25), QPointF(13.5, 19.5), QPointF(17.5, 28),
                       QPointF(21, 26.5), QPointF(17, 18.5), QPointF(24, 18.5)])
    return _painted_icon(draw)


def hand_icon() -> QIcon:
    def draw(p: QPainter):
        pen = p.pen()
        pen.setWidthF(2.2)
        p.setPen(pen)
        for x, top in ((9, 8), (14, 4), (19, 5), (24, 9)):      # fingers
            p.drawLine(QPointF(x, top), QPointF(x, 17))
        p.drawLine(QPointF(4, 15), QPointF(9, 21))               # thumb
        p.drawArc(6, 10, 21, 19, 180 * 16, 180 * 16)             # palm
        p.drawLine(QPointF(24, 9), QPointF(24, 20))
    return _painted_icon(draw)


def draw_box_icon() -> QIcon:
    def draw(p: QPainter):
        pen = p.pen()
        pen.setWidthF(2)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawRect(3, 7, 20, 16)
        pen.setStyle(Qt.SolidLine)
        pen.setWidthF(2.5)
        p.setPen(pen)
        p.drawLine(24, 18, 24, 30)                               # crosshair
        p.drawLine(18, 24, 30, 24)
    return _painted_icon(draw)


def text_input_focused() -> bool:
    """True while the user types somewhere (line/text edit, spinbox, cell editor, editable combo)."""
    w = QApplication.focusWidget()
    return isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox))


def tool_button(parent: QWidget, icon: QIcon | QStyle.StandardPixmap, tip: str, slot) -> QToolButton:
    b = QToolButton(parent)
    b.setIcon(icon if isinstance(icon, QIcon) else parent.style().standardIcon(icon))
    b.setToolTip(tip)
    b.setAutoRaise(True)
    b.clicked.connect(slot)
    return b


def add_shortcuts(scope: QWidget, pairs):
    """Shortcuts active only while focus is inside scope (one tab)."""
    for key, slot in pairs:
        sc = QShortcut(QKeySequence(key), scope)
        sc.setContext(Qt.WidgetWithChildrenShortcut)
        sc.activated.connect(slot)


def _handle_points(r: QRectF) -> dict[str, QPointF]:
    cx, cy = r.center().x(), r.center().y()
    return {"tl": r.topLeft(), "t": QPointF(cx, r.top()), "tr": r.topRight(), "r": QPointF(r.right(), cy),
            "br": r.bottomRight(), "b": QPointF(cx, r.bottom()), "bl": r.bottomLeft(), "l": QPointF(r.left(), cy)}


def _qrect(rect) -> QRectF:
    return QRectF(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])


def _plain(r: QRectF) -> list:
    return [round(r.left(), 1), round(r.top(), 1), round(r.right(), 1), round(r.bottom(), 1)]


# ---------------------------------------------------------------- PDF view

class PdfView(QGraphicsView):
    """Shows one PDF page; scene coordinates are PDF points.

    Boxes may carry a key (5th tuple element). In draw mode a click on a keyed box emits
    boxClicked(key); the highlight given a key is editable: 8 handles resize it, dragging
    inside moves it, and the release emits boxEdited(key, rect).
    """

    rectDrawn = Signal(list)          # [x0, y0, x1, y1] in PDF points
    boxClicked = Signal(object)       # key of a clicked box
    boxEdited = Signal(object, list)  # key, new [x0, y0, x1, y1] in PDF points
    pageChanged = Signal(int)
    zoomChanged = Signal(float)
    toolChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.doc: pymupdf.Document | None = None
        self.page = 0
        self.zoom = 1.0
        self.boxes: list[tuple] = []          # page, rect, color, label[, key]
        self.highlight: tuple[int, list, object] | None = None   # page, rect, key
        self._hl_item: QGraphicsRectItem | None = None
        self._handles: list[QGraphicsRectItem] = []
        self._edit: tuple[str, QPointF, QRectF] | None = None    # mode, start, original rect
        self._draw_start: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None
        self.draw_enabled = False         # owner supports selecting/editing/drawing boxes
        self.clicking = False             # True while boxClicked is being handled
        self.tool = "pointer"             # pointer | hand | draw
        self._space_prev: str | None = None   # tool to restore after a Space-hold hand
        self.set_tool("pointer")

    # ---- document / page
    def set_document(self, path: str | None):
        if self.doc is not None:
            self.doc.close()
        self.doc = pymupdf.open(path) if path else None
        self.page = 0
        self.highlight = None
        self.render()
        self.pageChanged.emit(0)

    def page_count(self) -> int:
        return len(self.doc) if self.doc else 0

    def set_page(self, page: int):
        if not self.doc:
            return
        page = max(0, min(page, len(self.doc) - 1))
        if page != self.page:
            self.page = page
            self.render()
            self.pageChanged.emit(page)

    def next_page(self):
        self.set_page(self.page + 1)

    def prev_page(self):
        self.set_page(self.page - 1)

    # ---- zoom
    def set_zoom(self, z: float):
        self.zoom = max(0.2, min(z, 8.0))
        self.resetTransform()
        self.scale(self.zoom, self.zoom)
        self.zoomChanged.emit(self.zoom)

    def zoom_in(self):
        self.set_zoom(self.zoom * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom / 1.25)

    def fit_width(self):
        if self.doc:
            w = self.doc[self.page].rect.width
            self.set_zoom((self.viewport().width() - 20) / w)

    # ---- boxes
    def set_boxes(self, boxes):
        self.boxes = list(boxes)
        self.render()

    def set_highlight(self, page: int | None, rect=None, key=None, jump: bool = True):
        """Highlight rect on page (-1 = last). jump: switch to that page and scroll it into view."""
        self.highlight = (page, list(rect), key) if page is not None and rect else None
        if jump and self.highlight and self.doc:
            idx = max(0, min(self._page_index(page), len(self.doc) - 1))
            if idx != self.page:
                self.page = idx
                self.pageChanged.emit(idx)
        self.render()
        if jump and self.highlight:
            r = _qrect(rect)
            if not self.mapToScene(self.viewport().rect()).boundingRect().contains(r):
                self.centerOn(r.center())

    def _page_index(self, p: int) -> int:
        return p + self.page_count() if p < 0 else p

    def _editable(self) -> bool:
        return (self.draw_enabled and self.tool == "pointer" and self.highlight is not None and self.highlight[2] is not None
                and self._hl_item is not None)

    def render(self):
        sc = self.scene()
        sc.clear()
        self._rubber = None
        self._hl_item = None
        self._handles = []
        self._edit = None
        if not self.doc:
            return
        pg = self.doc[self.page]
        pix = pg.get_pixmap(matrix=pymupdf.Matrix(RENDER_ZOOM, RENDER_ZOOM))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(img))
        item.setScale(1 / RENDER_ZOOM)
        item.setTransformationMode(Qt.SmoothTransformation)
        sc.addItem(item)
        sc.setSceneRect(0, 0, pg.rect.width, pg.rect.height)
        hl_key = self.highlight[2] if self.highlight else None
        for b in self.boxes:
            p, rect, color, label = b[:4]
            if self._page_index(p) != self.page:
                continue
            self._add_rect(rect, color, label, 1.0)
        if self.highlight and self._page_index(self.highlight[0]) == self.page:
            self._hl_item = self._add_rect(self.highlight[1], QColor("#ff0000"), "", 2.5, fill=True)
            if self.draw_enabled and self.tool == "pointer" and hl_key is not None:
                for _ in range(8):
                    h = QGraphicsRectItem(-3.5, -3.5, 7, 7)
                    h.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                    pen = QPen(QColor("#ff0000"), 1)
                    pen.setCosmetic(True)
                    h.setPen(pen)
                    h.setBrush(QBrush(QColor("#ffffff")))
                    h.setZValue(10)
                    sc.addItem(h)
                    self._handles.append(h)
                self._place_handles(self._hl_item.rect())

    def _place_handles(self, r: QRectF):
        for h, pt in zip(self._handles, _handle_points(r).values()):
            h.setPos(pt)

    def _add_rect(self, rect, color: QColor, label: str, width: float, fill=False) -> QGraphicsRectItem:
        r = _qrect(rect)
        pen = QPen(color, width)
        pen.setCosmetic(True)
        it = self.scene().addRect(r, pen)
        if fill:
            c = QColor(color)
            c.setAlpha(50)
            it.setBrush(QBrush(c))
        if label:
            t = QGraphicsSimpleTextItem(label)
            t.setBrush(QBrush(color))
            f = QFont()
            f.setPointSizeF(5)
            t.setFont(f)
            t.setPos(r.left(), r.top() - 7)
            self.scene().addItem(t)
        return it

    # ---- hit testing for box editing
    def _hit(self, vp) -> str | None:
        """Handle name ('tl' .. 'l') or 'move' under viewport point vp, for the editable highlight."""
        if not self._editable():
            return None
        r = self._hl_item.rect()
        on_screen = self.mapFromScene(r).boundingRect()
        # grab zone at most a quarter of the box on screen (min 3px): the middle stays movable
        tx = max(3, min(HANDLE_PX, on_screen.width() // 4))
        ty = max(3, min(HANDLE_PX, on_screen.height() // 4))
        inner = QRectF(on_screen).adjusted(on_screen.width() / 4, on_screen.height() / 4,
                                           -on_screen.width() / 4, -on_screen.height() / 4)
        if inner.contains(QPointF(vp)):                    # central half always moves (tiny boxes)
            return "move"
        best, best_d = None, None
        for name, pt in _handle_points(r).items():          # nearest handle wins (small boxes)
            d = self.mapFromScene(pt) - vp
            if abs(d.x()) <= tx and abs(d.y()) <= ty:
                dist = d.x() * d.x() + d.y() * d.y()
                if best_d is None or dist < best_d:
                    best, best_d = name, dist
        if best:
            return best
        return "move" if r.contains(self.mapToScene(vp)) else None

    def _box_at(self, sp: QPointF):
        for b in reversed(self.boxes):
            key = b[4] if len(b) > 4 else None
            if key is not None and self._page_index(b[0]) == self.page and _qrect(b[1]).contains(sp):
                return key
        return None

    # ---- tools: pointer (select/move/resize), hand (scroll), draw (new boxes)
    def set_draw_enabled(self, on: bool):
        self.draw_enabled = on
        self.viewport().setMouseTracking(on)
        self.set_tool(self.tool)

    def set_tool(self, tool: str):
        if tool == "draw" and not self.draw_enabled:
            tool = "pointer"
        changed = tool != self.tool
        self.tool = tool
        if self._rubber is not None:                       # tool switched mid-draw
            self.scene().removeItem(self._rubber)
            self._rubber = None
        editing = self._edit is not None
        self._draw_start = None
        self._edit = None
        if editing:                                        # tool switched mid-resize/move:
            self.render()                                  # drop the unsaved drag
        self.setDragMode(QGraphicsView.ScrollHandDrag if tool == "hand" else QGraphicsView.NoDrag)
        if tool == "draw":
            self.viewport().setCursor(Qt.CrossCursor)
        elif tool == "pointer":
            self.viewport().setCursor(Qt.ArrowCursor)
        # hand: ScrollHandDrag sets the open/closed hand cursors itself
        if changed:
            if self.highlight and self.draw_enabled:
                self.render()                                 # show/hide resize handles
            self.toolChanged.emit(tool)

    def mousePressEvent(self, e):
        self.setFocus(Qt.MouseFocusReason)                  # PgUp/PgDn then page this PDF
        if self.tool == "draw" and self.draw_enabled and self.doc and e.button() == Qt.LeftButton:
            self._draw_start = self.mapToScene(e.position().toPoint())    # even over existing boxes
            pen = QPen(QColor("#0078d7"), 1, Qt.DashLine)
            pen.setCosmetic(True)
            self._rubber = self.scene().addRect(QRectF(self._draw_start, self._draw_start), pen)
            return
        if self.tool == "pointer" and self.draw_enabled and self.doc and e.button() == Qt.LeftButton:
            vp = e.position().toPoint()
            sp = self.mapToScene(vp)
            mode = self._hit(vp)
            if mode is None:
                key = self._box_at(sp)
                if key is not None:
                    self.clicking = True               # owner must not scroll (jump=False)
                    try:
                        self.boxClicked.emit(key)      # the owner selects it -> editable highlight
                    finally:
                        self.clicking = False
                    sp = self.mapToScene(vp)           # in case the view scrolled anyway
                    mode = self._hit(vp)
                    if mode is None:
                        return
            if mode is not None:
                self._edit = (mode, sp, QRectF(self._hl_item.rect()))
                return
            self.clicking = True
            try:
                self.boxClicked.emit(None)             # click on empty space: deselect, never draw
            finally:
                self.clicking = False
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        vp = e.position().toPoint()
        if self._edit is not None and self._hl_item is not None:
            mode, start, orig = self._edit
            d = self.mapToScene(vp) - start
            r = QRectF(orig)
            if mode == "move":
                r.translate(d)
            else:
                if "l" in mode:
                    r.setLeft(orig.left() + d.x())
                if "r" in mode:
                    r.setRight(orig.right() + d.x())
                if "t" in mode:
                    r.setTop(orig.top() + d.y())
                if "b" in mode:
                    r.setBottom(orig.bottom() + d.y())
                r = r.normalized()
            page = self.sceneRect()                     # keep the box on the page
            if mode == "move":
                r.moveLeft(max(page.left(), min(r.left(), page.right() - r.width())))
                r.moveTop(max(page.top(), min(r.top(), page.bottom() - r.height())))
            else:
                r = r.intersected(page)
            self._hl_item.setRect(r)
            self._place_handles(r)
            return
        if self._draw_start is not None and self._rubber is not None:
            self._rubber.setRect(QRectF(self._draw_start, self.mapToScene(vp)).normalized())
            return
        if self.draw_enabled and self.tool == "pointer":
            mode = self._hit(vp)
            if mode:
                self.viewport().setCursor(HANDLE_CURSORS[mode])
            else:
                self.viewport().setCursor(Qt.PointingHandCursor if self._box_at(self.mapToScene(vp)) is not None
                                          else Qt.ArrowCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._edit is not None:
            _, _, orig = self._edit
            self._edit = None
            if self._hl_item is None:
                return
            r = self._hl_item.rect()
            key = self.highlight[2] if self.highlight else None
            if key is not None and r.width() > 2 and r.height() > 2 and _plain(r) != _plain(orig):
                self.boxEdited.emit(key, _plain(r))
            elif self._hl_item is not None:
                self._hl_item.setRect(orig)               # click without drag / too small: revert
                self._place_handles(orig)
            return
        if self._draw_start is not None:
            r = QRectF(self._draw_start, self.mapToScene(e.position().toPoint())).normalized()
            self._draw_start = None
            if self._rubber is not None:
                self.scene().removeItem(self._rubber)
                self._rubber = None
            if r.width() > 2 and r.height() > 2:
                self.rectDrawn.emit(_plain(r))
            return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_PageUp and not e.modifiers():
            self.prev_page()
            return
        if e.key() == Qt.Key_PageDown and not e.modifiers():
            self.next_page()
            return
        if e.key() == Qt.Key_Space and not e.modifiers():
            if not e.isAutoRepeat() and self._space_prev is None and self.tool != "hand" \
                    and self._edit is None and self._draw_start is None:
                self._space_prev = self.tool                 # temporary hand while Space is held
                self.set_tool("hand")
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat() and self._space_prev is not None:
            prev, self._space_prev = self._space_prev, None
            self.set_tool(prev)
            return
        super().keyReleaseEvent(e)

    def focusOutEvent(self, e):
        if self._space_prev is not None:                   # Space released elsewhere
            prev, self._space_prev = self._space_prev, None
            self.set_tool(prev)
        super().focusOutEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.zoom_in() if e.angleDelta().y() > 0 else self.zoom_out()
            return
        super().wheelEvent(e)


class PdfPanel(QWidget):
    """PdfView plus the shared compact navigation/zoom toolbar."""

    TOOLS = {"pointer": (pointer_icon, "เลือก / ย้าย / ปรับขนาดกรอบ (V)", "V"),
             "hand": (hand_icon, "มือเลื่อนภาพ (H หรือกด Space ค้าง)", "H"),
             "draw": (draw_box_icon, "วาดกรอบใหม่ (R)", "R")}

    def __init__(self, parent=None, tools=("pointer", "hand")):
        super().__init__(parent)
        self.view = PdfView(self)
        self.bar = QHBoxLayout()
        self.bar.setSpacing(2)
        v = self.view
        if "draw" in tools:
            v.set_draw_enabled(True)
        self.tools = tuple(tools)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_buttons: dict[str, QToolButton] = {}
        for name in self.tools:
            make, tip, _ = self.TOOLS[name]
            b = tool_button(self, make(), tip, lambda _=False, n=name: self.view.set_tool(n))
            b.setCheckable(True)
            self.tool_group.addButton(b)
            self.tool_buttons[name] = b
            self.bar.addWidget(b)
        v.toolChanged.connect(self._sync_tool_buttons)
        self._sync_tool_buttons(v.tool)
        self.btn_prev = tool_button(self, QStyle.SP_ArrowUp, "หน้าก่อน (PgUp เมื่อคลิกที่ภาพ PDF หรือช่องเลขหน้า)", v.prev_page)
        self.btn_next = tool_button(self, QStyle.SP_ArrowDown, "หน้าถัดไป (PgDn เมื่อคลิกที่ภาพ PDF หรือช่องเลขหน้า)", v.next_page)
        self.spin = QSpinBox(self)
        self.spin.setToolTip("พิมพ์เลขหน้าที่ต้องการ")
        self.spin.setKeyboardTracking(False)
        self.spin.valueChanged.connect(lambda n: self.view.set_page(n - 1))
        self.spin.installEventFilter(self)                # PgUp/PgDn = one page, not 10
        self.btn_zoom_out = tool_button(self, zoom_icon(False), "ซูมออก (Ctrl+-)", v.zoom_out)
        self.btn_zoom_in = tool_button(self, zoom_icon(True), "ซูมเข้า (Ctrl+= หรือ Ctrl+ล้อเมาส์)", v.zoom_in)
        self.zoom_lbl = QLabel(self)
        self.zoom_lbl.setMinimumWidth(42)
        self.zoom_lbl.setAlignment(Qt.AlignCenter)
        self.btn_fit = tool_button(self, fit_width_icon(), "พอดีความกว้าง (Ctrl+0)", v.fit_width)
        self.lbl = QLabel(self)               # "no file" hint
        self.lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # never widens the bar
        self.btn_prev.hide()                  # the page spinbox has its own up/down arrows
        self.btn_next.hide()
        for w in (self.spin, self.btn_fit, self.btn_zoom_out, self.btn_zoom_in, self.zoom_lbl, self.lbl):
            self.bar.addWidget(w)
        self.bar.addStretch()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self.bar)
        lay.addWidget(self.view)
        v.pageChanged.connect(self.update_label)
        v.zoomChanged.connect(self.update_label)
        self.update_label()

    def _sync_tool_buttons(self, tool: str):
        b = self.tool_buttons.get(tool)
        if b is not None and not b.isChecked():
            b.setChecked(True)

    def set_tool_shortcut(self, name: str):
        """V/H/R: ignored while the user is typing in a text field."""
        if not text_input_focused():
            self.view.set_tool(name)

    def eventFilter(self, obj, e):
        if (obj is self.spin and e.type() == QEvent.KeyPress and not e.modifiers()
                and e.key() in (Qt.Key_PageUp, Qt.Key_PageDown)):
            self.view.prev_page() if e.key() == Qt.Key_PageUp else self.view.next_page()
            return True
        return super().eventFilter(obj, e)

    def install_shortcuts(self, scope: QWidget):
        """Zoom shortcuts scoped to the owning tab (PgUp/PgDn live in the view and spinbox)."""
        v = self.view
        add_shortcuts(scope, (("Ctrl+=", v.zoom_in), ("Ctrl++", v.zoom_in), ("Ctrl+-", v.zoom_out),
                              ("Ctrl+0", v.fit_width)))
        add_shortcuts(scope, [(self.TOOLS[n][2], lambda n=n: self.set_tool_shortcut(n)) for n in self.tools])

    def open(self, path: str | None):
        self.view.set_document(path)
        self.view.fit_width()
        self.update_label()

    def update_label(self, *_):
        v = self.view
        n = v.page_count()
        self.spin.blockSignals(True)
        self.spin.setRange(1 if n else 0, max(n, 0))
        self.spin.setSuffix(f" / {n}")
        self.spin.setValue(v.page + 1 if n else 0)
        self.spin.blockSignals(False)
        for w in (self.spin, self.btn_prev, self.btn_next, self.btn_zoom_in, self.btn_zoom_out, self.btn_fit):
            w.setEnabled(bool(n))
        self.btn_prev.setEnabled(bool(n) and v.page > 0)
        self.btn_next.setEnabled(bool(n) and v.page < n - 1)
        self.zoom_lbl.setText(f"{v.zoom * 100:.0f}%" if n else "")
        self.lbl.setText("" if n else "ยังไม่ได้เปิดไฟล์")


# ---------------------------------------------------------------- dialogs

class RegionDialog(QDialog):
    """Pick column, scope, page and mode for a freshly drawn box."""

    def __init__(self, columns: list[str], page: int, parent=None, region: Region | None = None):
        super().__init__(parent)
        self.setWindowTitle("กำหนดกรอบข้อมูล")
        self.col = QComboBox()
        self.col.addItems(columns)
        self.scope = QComboBox()
        for k, v in SCOPE_LABELS.items():
            self.scope.addItem(v, k)
        self.page = QSpinBox()
        self.page.setRange(1, 9999)
        self.page.setValue(page + 1)
        self.last = QCheckBox(LAST_PAGE_LABEL)
        self.last.toggled.connect(lambda on: self.page.setEnabled(not on))
        self.mode = QComboBox()
        for k in UI_MODES:
            self.mode.addItem(MODE_LABELS[k], k)
        if region:
            self.col.setCurrentText(region.column)
            self.scope.setCurrentIndex(engine.SCOPES.index(region.scope))
            self.mode.setCurrentIndex(max(0, self.mode.findData(LEGACY_MODES.get(region.mode, region.mode))))
            if region.page < 0:
                self.last.setChecked(True)
            else:
                self.page.setValue(region.page + 1)
        form = QFormLayout(self)
        form.addRow("คอลัมน์", self.col)
        form.addRow("ขอบเขต", self.scope)
        pg = QHBoxLayout()
        pg.addWidget(self.page)
        pg.addWidget(self.last)
        form.addRow("หน้า", pg)
        form.addRow("วิธีอ่าน", self.mode)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("ตกลง")
        bb.button(QDialogButtonBox.Cancel).setText("ยกเลิก")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def result_region(self, rect) -> Region:
        page = -1 if self.last.isChecked() else self.page.value() - 1
        return Region(self.col.currentText(), self.scope.currentData(), page, list(rect),
                      self.mode.currentData())


def ask_continue(parent, title: str, issues: list[str]) -> bool:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(f"พบข้อสังเกต {len(issues)} รายการ ต้องการส่งออกต่อหรือไม่?"))
    txt = QPlainTextEdit("\n".join(issues))
    txt.setReadOnly(True)
    txt.setMinimumSize(600, 300)
    lay.addWidget(txt)
    bb = QDialogButtonBox()
    bb.addButton("ส่งออกต่อ", QDialogButtonBox.AcceptRole)
    bb.addButton("ยกเลิก", QDialogButtonBox.RejectRole)
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    lay.addWidget(bb)
    return dlg.exec() == QDialog.Accepted


def add_undo_ui(tab: QWidget, layout: QHBoxLayout):
    """Add undo/redo icon buttons and tab-scoped Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z shortcuts.

    tab must provide undo(), redo(), can_undo(), can_redo().
    """
    tab.btn_undo = tool_button(tab, QStyle.SP_ArrowBack, "ย้อนกลับการแก้ไขล่าสุด (Ctrl+Z)", tab.undo)
    tab.btn_redo = tool_button(tab, QStyle.SP_ArrowForward,
                               "ทำซ้ำการแก้ไขที่ย้อนกลับ (Ctrl+Y หรือ Ctrl+Shift+Z)", tab.redo)
    layout.addWidget(tab.btn_undo)
    layout.addWidget(tab.btn_redo)
    add_shortcuts(tab, (("Ctrl+Z", tab.undo), ("Ctrl+Y", tab.redo), ("Ctrl+Shift+Z", tab.redo)))


def editor_open(tab: QWidget) -> bool:
    """True while a table cell editor is open (its own undo should win)."""
    return any(t.state() == QAbstractItemView.EditingState for t in tab.findChildren(QTableWidget))


def pick_template_combo(combo: QComboBox, select: str | None = None):
    combo.blockSignals(True)
    combo.clear()
    combo.addItems(engine.list_templates())
    if select:
        combo.setCurrentText(select)
    combo.blockSignals(False)


# ---------------------------------------------------------------- template tab

class TemplateTab(QWidget):
    templatesChanged = Signal()
    templateRenamed = Signal(str, str)        # old name, new name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tpl: Template = Template("แม่แบบใหม่")
        self.sample_path: str | None = None
        self._sample_doc: PdfDoc | None = None
        self._anchor_mode = False
        self._loading = False

        # template bar
        self.combo = QComboBox()
        self._saved_json = ""
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("แม่แบบ (Template):"))
        bar.addWidget(self.combo, 1)
        for text, slot in (("ใหม่", self.on_new), ("บันทึก", self.on_save),
                           ("เปลี่ยนชื่อ", self.on_rename), ("ลบ", self.on_delete)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        self._undo: list[str] = []          # snapshots (template without its name)
        self._redo: list[str] = []
        self._last_snap = ""
        add_undo_ui(self, bar)

        # columns
        self.col_table = QTableWidget(0, 3)
        self.col_table.setHorizontalHeaderLabels(["ชื่อคอลัมน์", "ชนิดข้อมูล", "ตัวเชื่อมหลายบรรทัด"])
        self.col_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.col_table.setSelectionMode(QAbstractItemView.ExtendedSelection)   # Ctrl/Shift click
        self.col_table.itemChanged.connect(self._sync_columns)
        cbar = QGridLayout()                               # 2 rows x 3 equal-width buttons
        for i, (text, slot, tip) in enumerate((("เพิ่มคอลัมน์", self.on_add_column, ""),
                                ("ลบคอลัมน์ที่เลือก", self.on_remove_column, ""),
                                ("เลือกทั้งหมด", self.col_table.selectAll, ""),
                                ("▲ เลื่อนขึ้น", lambda: self.move_column(-1), "เลื่อนคอลัมน์ที่เลือกขึ้น"),
                                ("▼ เลื่อนลง", lambda: self.move_column(1), "เลื่อนคอลัมน์ที่เลือกลง"))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            cbar.addWidget(b, i // 3, i % 3)
        for c in range(3):
            cbar.setColumnStretch(c, 1)
        self.chk_source = QCheckBox("เพิ่มคอลัมน์ชื่อไฟล์ต้นทาง")
        self.chk_source.toggled.connect(self._on_source_toggled)
        gcol = QGroupBox("1) คอลัมน์ของตาราง")
        lc = QVBoxLayout(gcol)
        lc.addWidget(self.col_table)
        lc.addLayout(cbar)
        lc.addWidget(self.chk_source)                      # own row: keeps the left pane narrow

        # regions
        self.reg_table = QTableWidget(0, 5)
        self.reg_table.setHorizontalHeaderLabels(["คอลัมน์", "ขอบเขต", "หน้า", "วิธีอ่าน", "ตำแหน่ง"])
        self.reg_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reg_table.setSelectionMode(QAbstractItemView.ExtendedSelection)   # Ctrl/Shift click
        self.reg_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.reg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reg_table.itemSelectionChanged.connect(self._on_region_selected)
        self.reg_table.doubleClicked.connect(self.on_edit_region)
        self.anchor_lbl = QLabel()
        self.anchor_lbl.setWordWrap(True)
        rgrid = QGridLayout()                              # 2 rows x 3 equal-width buttons
        self.sample_buttons: list[QPushButton] = []        # need an open sample PDF
        for i, (text, slot) in enumerate((("แก้ไขกรอบ", self.on_edit_region),
                                          ("ลบกรอบที่เลือก", self.on_remove_region),
                                          ("เลือกทั้งหมด", self.reg_table.selectAll),
                                          ("ตั้งจุดอ้างอิง", self.on_anchor_mode),
                                          ("ทดลองอ่าน", self.on_test_region),
                                          ("ทดลองทั้งไฟล์", self.on_test_file))):
            b = QPushButton(text)
            if slot == self.on_anchor_mode:
                b.setToolTip("ตั้งจุดอ้างอิงเลขรายการ: วาดกรอบครอบเลข 1 ของรายการแรก")
            b.clicked.connect(slot)
            rgrid.addWidget(b, i // 3, i % 3)
            if slot in (self.on_anchor_mode, self.on_test_region, self.on_test_file):
                self.sample_buttons.append(b)
        for c in range(3):
            rgrid.setColumnStretch(c, 1)
        greg = QGroupBox("2) กรอบข้อมูล")
        greg.setToolTip("ลากบนภาพ PDF เพื่อวาดกรอบใหม่ / คลิกกรอบเพื่อย้ายหรือปรับขนาด")
        hint = QLabel("ลากบนภาพ PDF เพื่อวาดกรอบใหม่ คลิกกรอบเพื่อย้ายหรือปรับขนาด")
        hint.setWordWrap(True)
        lr = QVBoxLayout(greg)
        lr.addWidget(hint)
        lr.addWidget(self.reg_table)
        lr.addWidget(self.anchor_lbl)
        lr.addLayout(rgrid)

        # test output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("ผลการทดลองอ่านจะแสดงที่นี่")

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(gcol, 3)
        ll.addWidget(greg, 3)
        ll.addWidget(self.output, 2)

        # pdf
        self.pdf = PdfPanel(tools=("pointer", "hand", "draw"))      # default tool: pointer
        self.pdf.view.rectDrawn.connect(self.on_rect_drawn)
        self.pdf.view.boxClicked.connect(self._on_box_clicked)
        self.pdf.view.boxEdited.connect(self.on_box_edited)
        self.pdf.view.toolChanged.connect(self._on_tool_changed)
        self.pdf.install_shortcuts(self)
        b_open = QPushButton("เปิด PDF ตัวอย่าง")
        b_open.clicked.connect(self.on_open_sample)
        self.btn_close_pdf = QPushButton("ปิด PDF")
        self.btn_close_pdf.setToolTip("ปิด PDF ตัวอย่าง")
        self.btn_close_pdf.clicked.connect(self.close_sample)
        n_tools = len(self.pdf.tools)                          # tool buttons stay first
        self.pdf.bar.insertWidget(n_tools, b_open)                  # one toolbar row above the PDF
        self.pdf.bar.insertWidget(n_tools + 1, self.btn_close_pdf)
        for w in (self.pdf.view, self.reg_table):             # Delete/Backspace: only here
            for key in (QKeySequence.Delete, QKeySequence(Qt.Key_Backspace)):
                sc = QShortcut(QKeySequence(key), w)
                sc.setContext(Qt.WidgetShortcut)
                sc.activated.connect(self.delete_selected)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.pdf)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([500, 700])
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(split)

        pick_template_combo(self.combo)
        if self.combo.count():
            self.load(self.combo.currentText())
        else:
            self.set_template(self.tpl)
        self._update_sample_buttons()

    # ---- template lifecycle
    def load(self, name: str):
        if not name:
            return
        self.set_template(engine.load_template(name))

    def set_template(self, tpl: Template):
        for rg in tpl.regions:                   # UI offers only OCR/text; saving persists this
            rg.mode = LEGACY_MODES.get(rg.mode, rg.mode)
        self.tpl = tpl
        self._saved_json = tpl.to_json()
        self.reset_history()
        self.refresh()

    # ---- undo / redo (snapshot based; the template name is not part of history)
    def _snap(self) -> str:
        d = asdict(self.tpl)
        d.pop("name")
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    def reset_history(self):
        self._undo.clear()
        self._redo.clear()
        self._last_snap = self._snap()
        self._update_undo_buttons()

    def _commit(self):
        """Record a step if the template changed since the last recorded state."""
        if self._loading:
            return
        snap = self._snap()
        if snap != self._last_snap:
            self._undo.append(self._last_snap)
            del self._undo[:-UNDO_LIMIT]
            self._redo.clear()
            self._last_snap = snap
        self._update_undo_buttons()

    def _restore(self, snap: str):
        d = json.loads(snap)
        d["name"] = self.tpl.name
        self.tpl = Template.from_dict(d)
        self._last_snap = snap
        self._clear_region_selection()             # indices may point elsewhere after a restore
        self.refresh()
        self._update_undo_buttons()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self):
        if self._undo and not editor_open(self):
            self._redo.append(self._last_snap)
            self._restore(self._undo.pop())

    def redo(self):
        if self._redo and not editor_open(self):
            self._undo.append(self._last_snap)
            self._restore(self._redo.pop())

    def _update_undo_buttons(self):
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(self.can_undo())
            self.btn_redo.setEnabled(self.can_redo())

    def _on_source_toggled(self, on: bool):
        if not self._loading:
            self.tpl.include_source_file = on
            self._commit()

    def is_dirty(self) -> bool:
        return json.loads(self.tpl.to_json()) != json.loads(self._saved_json)   # ignore key order

    def confirm_discard(self) -> bool:
        """Dialog wrapper; tests may replace it."""
        return QMessageBox.question(
            self, "ยังไม่ได้บันทึก",
            f"แม่แบบ '{self.tpl.name}' มีการแก้ไขที่ยังไม่ได้บันทึก ต้องการทิ้งการแก้ไขหรือไม่?"
        ) == QMessageBox.Yes

    def on_combo_changed(self, name: str):
        if self.is_dirty() and not self.confirm_discard():
            pick_template_combo(self.combo, engine.safe_name(self.tpl.name))   # revert
            return
        self.load(name)

    def save(self) -> str:
        path = self.tpl.save()
        self._saved_json = self.tpl.to_json()
        pick_template_combo(self.combo, engine.safe_name(self.tpl.name))
        self.templatesChanged.emit()
        return path

    def exists(self, name: str) -> bool:
        return engine.safe_name(name) in engine.list_templates()

    def confirm_overwrite(self, name: str) -> bool:
        """Dialog wrapper; tests may replace it."""
        return QMessageBox.question(
            self, "ชื่อซ้ำ", f"มีแม่แบบชื่อ '{engine.safe_name(name)}' อยู่แล้ว ต้องการเขียนทับหรือไม่?"
        ) == QMessageBox.Yes

    def new_template(self, name: str) -> bool:
        """Create and save an empty template; refuses names that already exist."""
        if self.exists(name):
            return False
        if self.is_dirty() and not self.confirm_discard():
            return False
        self.set_template(Template(name))
        self.save()
        return True

    def on_new(self):
        name, ok = QInputDialog.getText(self, "แม่แบบใหม่", "ชื่อแม่แบบ (Template):")
        if ok and name.strip() and not self.new_template(name.strip()):
            QMessageBox.warning(self, "แม่แบบใหม่", "มีแม่แบบชื่อนี้อยู่แล้ว กรุณาใช้ชื่ออื่น")

    def on_save(self):
        if not self.tpl.columns:
            QMessageBox.warning(self, "บันทึก", "ยังไม่มีคอลัมน์")
            return
        path = self.save()
        QMessageBox.information(self, "บันทึก", f"บันทึกแล้ว:\n{path}")

    def on_rename(self):
        old = self.tpl.name
        name, ok = QInputDialog.getText(self, "เปลี่ยนชื่อ", "ชื่อใหม่:", text=old)
        if ok and name.strip() and name.strip() != old:
            self.rename(name.strip())

    def rename(self, new_name: str) -> bool:
        old = self.tpl.name
        same_file = engine.safe_name(old) == engine.safe_name(new_name)
        if not same_file and self.exists(new_name) and not self.confirm_overwrite(new_name):
            return False
        self.tpl.name = new_name
        self.save()
        self.templateRenamed.emit(old, new_name)
        if engine.safe_name(old) in engine.list_templates() and engine.safe_name(old) != engine.safe_name(new_name):
            engine.delete_template(old)
        pick_template_combo(self.combo, engine.safe_name(new_name))
        self.templatesChanged.emit()
        return True

    def on_delete(self):
        name = self.combo.currentText()
        if name and QMessageBox.question(self, "ลบ", f"ลบ Template '{name}'?") == QMessageBox.Yes:
            self.delete(name)

    def delete(self, name: str):
        engine.delete_template(name)
        pick_template_combo(self.combo)
        self.templatesChanged.emit()
        if self.combo.count():
            self.load(self.combo.currentText())
        else:
            self.set_template(Template("แม่แบบใหม่"))

    # ---- refresh widgets from self.tpl
    def refresh(self):
        self._loading = True
        t = self.tpl
        self.col_table.setRowCount(0)
        for c in t.columns:
            self._append_column_row(c)
        self.chk_source.setChecked(t.include_source_file)
        self._loading = False
        self.refresh_regions()

    def _append_column_row(self, c: Column):
        r = self.col_table.rowCount()
        self.col_table.insertRow(r)
        self.col_table.setItem(r, 0, QTableWidgetItem(c.name))
        cb = QComboBox()
        for k, v in TYPE_LABELS.items():
            cb.addItem(v, k)
        cb.setCurrentIndex(engine.COL_TYPES.index(c.type) if c.type in engine.COL_TYPES else 0)
        cb.currentIndexChanged.connect(self._sync_columns)
        self.col_table.setCellWidget(r, 1, cb)
        self.col_table.setItem(r, 2, QTableWidgetItem(c.joiner))

    def _sync_columns(self, *_):
        if self._loading:
            return
        old = [c.name for c in self.tpl.columns]
        cols = []
        for r in range(self.col_table.rowCount()):
            name = (self.col_table.item(r, 0).text() if self.col_table.item(r, 0) else "").strip()
            ctype = self.col_table.cellWidget(r, 1).currentData()
            joiner = self.col_table.item(r, 2).text() if self.col_table.item(r, 2) else ""
            cols.append(Column(name, ctype, joiner))
        # follow renames in regions/checks
        if len(old) == len(cols):
            ren = {o: c.name for o, c in zip(old, cols) if o != c.name}
            for rg in self.tpl.regions:
                rg.column = ren.get(rg.column, rg.column)
            for ch in self.tpl.checks:
                ch.header_column = ren.get(ch.header_column, ch.header_column)
                ch.item_column = ren.get(ch.item_column, ch.item_column)
        self.tpl.columns = cols
        self.refresh_regions()

    def refresh_regions(self):
        view = self.pdf.view
        key = view.highlight[2] if view.highlight else None
        selected = self.selected_regions()
        n = len(self.tpl.regions)
        self.reg_table.blockSignals(True)
        self.reg_table.setRowCount(0)
        names = [c.name for c in self.tpl.columns]
        for rg in self.tpl.regions:
            r = self.reg_table.rowCount()
            self.reg_table.insertRow(r)
            page = LAST_PAGE_LABEL if rg.page < 0 else str(rg.page + 1)
            for i, v in enumerate((rg.column, "หัวเอกสาร" if rg.scope == "header" else "รายการ",
                                   page, MODE_LABELS.get(rg.mode, rg.mode), fmt_rect(rg.rect))):
                self.reg_table.setItem(r, i, QTableWidgetItem(v))
        sm = self.reg_table.selectionModel()
        for i in selected:                       # keep the selection across the rebuild
            if i < n:
                sm.select(self.reg_table.model().index(i, 0),
                          QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.reg_table.blockSignals(False)
        a = self.tpl.anchor
        self.anchor_lbl.setText(
            f"จุดอ้างอิงเลขรายการ: หน้า {a['page'] + 1}, [{fmt_rect(a['rect'])}]" if a
            else "จุดอ้างอิงเลขรายการ: ยังไม่ได้กำหนด")
        boxes = []
        for i, rg in enumerate(self.tpl.regions):
            idx = names.index(rg.column) if rg.column in names else 0
            boxes.append((rg.page, rg.rect, color_for(idx), rg.column, i))
        if a:
            boxes.append((a["page"], a["rect"], QColor("#ff00ff"), "เลขรายการ", "anchor"))
        view.boxes = boxes
        # re-apply the highlight with current coordinates; drop it if its target is gone (stale)
        if isinstance(key, int) and key < n:
            view.set_highlight(self.tpl.regions[key].page, self.tpl.regions[key].rect, key, jump=False)
        elif key == "anchor" and a:
            view.set_highlight(a["page"], a["rect"], "anchor", jump=False)
        else:
            view.set_highlight(None)
        self._commit()             # every template mutation ends in a refresh -> one undo step

    # ---- columns
    def add_column(self, name: str, ctype: str = "string", joiner: str = ""):
        self.tpl.columns.append(Column(name, ctype, joiner))
        self.refresh()

    def on_add_column(self):
        n = len(self.tpl.columns) + 1
        self.add_column(f"คอลัมน์{n}")

    def selected_columns(self) -> list[int]:
        rows = sorted({ix.row() for ix in self.col_table.selectionModel().selectedIndexes()})
        if not rows and self.col_table.currentRow() >= 0:
            rows = [self.col_table.currentRow()]
        return [r for r in rows if r < len(self.tpl.columns)]

    def on_remove_column(self):
        rows = self.selected_columns()
        for r in reversed(rows):                 # all selected columns -> one refresh = one undo step
            del self.tpl.columns[r]
        if rows:
            self.col_table.clearSelection()
            self.refresh()

    def move_column(self, d: int):
        r = self.col_table.currentRow()
        j = r + d
        if 0 <= r < len(self.tpl.columns) and 0 <= j < len(self.tpl.columns):
            cols = self.tpl.columns
            cols[r], cols[j] = cols[j], cols[r]
            self.refresh()
            self.col_table.setCurrentCell(j, 0)

    # ---- sample / regions
    def open_sample(self, path: str):
        self.sample_path = path
        if self._sample_doc is not None:
            self._sample_doc.doc.close()
        self._sample_doc = PdfDoc(path)
        self.pdf.open(path)
        self.refresh_regions()
        self._update_sample_buttons()

    def close_sample(self):
        """Close the sample PDF: empty view, reset page label, disable sample-only buttons."""
        self._anchor_mode = False
        if self._sample_doc is not None:
            self._sample_doc.doc.close()
        self._sample_doc = None
        self.sample_path = None
        self._clear_region_selection()
        self.pdf.open(None)
        self.output.clear()
        self._update_sample_buttons()

    def _update_sample_buttons(self):
        on = self._sample_doc is not None
        for b in self.sample_buttons:
            b.setEnabled(on)
        self.btn_close_pdf.setEnabled(on)

    def on_open_sample(self):
        path, _ = QFileDialog.getOpenFileName(self, "เปิด PDF ตัวอย่าง", "", "PDF (*.pdf)")
        if path:
            self.open_sample(path)

    def _on_tool_changed(self, tool: str):
        if tool != "draw" and self._anchor_mode and self.pdf.view._space_prev is None:
            self._anchor_mode = False                  # user left the anchor drawing
            self.output.setPlainText("ยกเลิกการตั้งจุดอ้างอิง")

    def on_anchor_mode(self):
        if not self._sample_doc:
            self.output.setPlainText("กรุณาเปิด PDF ตัวอย่างก่อน")
            return
        self._anchor_mode = True
        self.pdf.view.set_tool("draw")                 # back to pointer once the anchor box is drawn
        self.output.setPlainText("วาดกรอบรอบเลข \"1\" ของรายการที่ 1 บนภาพ PDF")

    def _tight_anchor(self, page: int, rect, mode: str) -> tuple[dict, bool]:
        """Anchor dict tightened to the "1" inside rect (ref_y set), and whether a "1" was found."""
        anchor = {"page": page, "rect": list(rect), "mode": mode}
        hit = engine.locate_first_item(self._sample_doc, anchor) if self._sample_doc else None
        if hit:
            anchor["rect"] = [round(v, 1) for v in hit]
            anchor["ref_y"] = round((hit[1] + hit[3]) / 2, 2)
        return anchor, hit is not None

    def set_anchor(self, page: int, rect, mode: str = "text") -> bool:
        """Store the anchor tightened to the "1" inside the box. False if no "1" was found."""
        self.tpl.anchor, found = self._tight_anchor(page, rect, mode)
        self.refresh_regions()
        return found

    def add_region(self, region: Region):
        self.tpl.regions.append(region)
        self.refresh_regions()
        self.reg_table.selectRow(len(self.tpl.regions) - 1)

    def on_rect_drawn(self, rect: list):
        page = self.pdf.view.page
        if self._anchor_mode:
            self._anchor_mode = False
            self.pdf.view.set_tool("pointer")
            mode = "ocr"                          # text layers can drop digits: OCR by default
            if self.set_anchor(page, rect, mode):
                self.output.setPlainText(f"ตั้งจุดอ้างอิงแล้ว — พบเลขรายการ 1 ในกรอบ (วิธีอ่าน: {mode})")
            else:
                QMessageBox.warning(self, "จุดอ้างอิงเลขรายการ",
                                    "ไม่พบเลข 1 ในกรอบที่วาด\nกรุณาวาดกรอบครอบเลขลำดับรายการที่ 1 อีกครั้ง")
            return
        if not self.tpl.columns:
            QMessageBox.warning(self, "กรอบข้อมูล", "กรุณาเพิ่มคอลัมน์ก่อน")
            self.refresh_regions()
            return
        dlg = RegionDialog([c.name for c in self.tpl.columns], page, self)
        if dlg.exec() == QDialog.Accepted:
            self.add_region(dlg.result_region(rect))
        else:
            self.refresh_regions()

    def selected_regions(self) -> list[int]:
        return sorted(ix.row() for ix in self.reg_table.selectionModel().selectedRows())

    def selected_region(self) -> int:
        rows = self.selected_regions()
        cur = self.reg_table.currentRow()
        return cur if cur in rows else (rows[0] if rows else -1)

    def _clear_region_selection(self):
        self.reg_table.blockSignals(True)
        self.reg_table.clearSelection()
        self.reg_table.blockSignals(False)
        self.pdf.view.set_highlight(None)

    def _on_region_selected(self):
        i = self.selected_region()
        if 0 <= i < len(self.tpl.regions):
            rg = self.tpl.regions[i]
            v = self.pdf.view                  # a click on the PDF must not scroll under the mouse
            v.set_highlight(rg.page, rg.rect, i, jump=not v.clicking)   # keyed -> editable box
        else:
            self.pdf.view.set_highlight(None)
        self.pdf.update_label()

    def _on_box_clicked(self, key):
        """A box was clicked on the PDF: select it (its highlight becomes editable).

        key None = click on empty space: clear the selection.
        """
        if key is None:
            self._clear_region_selection()
        elif key == "anchor":
            a = self.tpl.anchor
            self._clear_region_selection()
            if a:
                self.pdf.view.set_highlight(a["page"], a["rect"], "anchor", jump=False)
        elif isinstance(key, int) and 0 <= key < len(self.tpl.regions):
            self.reg_table.setCurrentCell(key, 0)
            self.reg_table.selectRow(key)
            if self.selected_region() != key:          # e.g. Ctrl held toggled it off
                self.reg_table.clearSelection()
                self.reg_table.selectRow(key)

    def on_box_edited(self, key, rect: list):
        """Drag release on an editable box: store the new rect (PDF points) as one undo step.

        Item regions keep their coordinates relative to item #1 as drawn on the sample.
        """
        if key == "anchor":
            a = self.tpl.anchor
            if not a:
                return
            anchor, found = self._tight_anchor(a["page"], rect, a.get("mode", "ocr"))
            if found:
                self.tpl.anchor = anchor                 # tightened again -> ref_y follows the box
                self.output.setPlainText("ย้ายจุดอ้างอิงแล้ว — พบเลขรายการ 1 ในกรอบ")
            else:
                self.output.setPlainText("ไม่พบเลข 1 ในกรอบใหม่ — คงจุดอ้างอิงเดิมไว้")
            self.refresh_regions()
            return
        if isinstance(key, int) and 0 <= key < len(self.tpl.regions):
            self.tpl.regions[key].rect = [float(v) for v in rect]
            self.refresh_regions()

    def on_edit_region(self, *_):
        i = self.selected_region()
        if i < 0:
            return
        rg = self.tpl.regions[i]
        dlg = RegionDialog([c.name for c in self.tpl.columns], max(rg.page, 0), self, rg)
        if dlg.exec() == QDialog.Accepted:
            self.tpl.regions[i] = dlg.result_region(rg.rect)
            self.refresh_regions()

    def on_remove_region(self):
        rows = [i for i in self.selected_regions() if i < len(self.tpl.regions)]
        for i in reversed(rows):                 # all selected boxes -> one refresh = one undo step
            del self.tpl.regions[i]
        if rows:
            self._clear_region_selection()       # also removes the highlight of a deleted box
            self.refresh_regions()

    def delete_selected(self):
        """Delete/Backspace on the PDF view or regions table: selected regions, else a selected anchor."""
        if text_input_focused():
            return
        if self.selected_regions():
            self.on_remove_region()
            return
        hl = self.pdf.view.highlight
        if hl and hl[2] == "anchor" and self.tpl.anchor:
            self.tpl.anchor = None
            self._clear_region_selection()
            self.refresh_regions()                 # one undo step

    # ---- test reads
    def test_region(self, index: int) -> Cell | None:
        if not self._sample_doc or not (0 <= index < len(self.tpl.regions)):
            return None
        rg = self.tpl.regions[index]
        col = self.tpl.column(rg.column) or Column(rg.column)
        return engine.read_region(self._sample_doc, rg.page, rg.rect, col, rg.mode)

    def on_test_region(self):
        if not self._sample_doc:
            self.output.setPlainText("กรุณาเปิด PDF ตัวอย่างก่อน")
            return
        i = self.selected_region()
        if i < 0:
            self.output.setPlainText("กรุณาเลือกกรอบในรายการก่อน")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            c = self.test_region(i)
        finally:
            QApplication.restoreOverrideCursor()
        self.output.setPlainText(
            f"ค่า: {fmt_value(c.value)}\nข้อความดิบ: {c.raw!r}\nอ่านจาก: {c.source}\n"
            f"ข้อสังเกต: {c.flag or '-'}")

    def test_file(self) -> FileResult | None:
        if not self.sample_path:
            return None
        doc = PdfDoc(self.sample_path)
        try:
            return engine.extract(doc, self.tpl)
        finally:
            doc.doc.close()

    def on_test_file(self):
        if not self.sample_path:
            self.output.setPlainText("กรุณาเปิด PDF ตัวอย่างก่อน")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fr = self.test_file()
        finally:
            QApplication.restoreOverrideCursor()
        lines = [f"อ่านได้ {len(fr.rows)} แถว", f"ข้อสังเกต {len(fr.issues)} รายการ"]
        lines += ["  - " + s for s in fr.issues]
        self.output.setPlainText("\n".join(lines))


# ---------------------------------------------------------------- extraction worker

class Cancelled(Exception):
    pass


class ExtractWorker(QThread):
    fileStarted = Signal(int)
    progress = Signal(int, int, int)            # file index, done, total
    fileDone = Signal(int, object)              # file index, FileResult
    allDone = Signal()

    def __init__(self, paths: list[str], tpl: Template, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.tpl = tpl
        self._stop = False

    def stop(self):
        self._stop = True

    def _check_cancel(self):
        if self._stop:
            raise Cancelled()                            # abort mid-file

    def run(self):
        try:
            for i, p in enumerate(self.paths):
                if self._stop:
                    break
                self.fileStarted.emit(i)
                doc = None
                try:
                    doc = PdfDoc(p)
                    fr = engine.extract(doc, self.tpl,
                                        progress=lambda d, t, i=i: self.progress.emit(i, d, t),
                                        cancel=self._check_cancel)
                except Cancelled:
                    break
                except Exception as e:                   # keep going with other files
                    fr = FileResult(p, [], [f"อ่านไฟล์ไม่สำเร็จ: {e}"])
                finally:
                    if doc is not None:
                        doc.doc.close()
                self.fileDone.emit(i, fr)
        finally:
            self.allDone.emit()                          # always reset the UI


# ---------------------------------------------------------------- import tab

class ImportTab(QWidget):
    extractionFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tpl: Template | None = None
        self.paths: list[str] = []
        self.results: dict[str, FileResult] = {}
        self.worker: ExtractWorker | None = None
        self._filling = False

        self.combo = QComboBox()
        self.combo.currentTextChanged.connect(self.on_combo_changed)
        self._tpl_name = ""
        self._reload_pending = False
        top = QHBoxLayout()
        top.addWidget(QLabel("แม่แบบ (Template):"))
        top.addWidget(self.combo, 1)
        self.btn_run = QPushButton("อ่านข้อมูล")
        self.btn_run.clicked.connect(self.start_extraction)
        self.btn_export = QPushButton("ส่งออก Excel")
        self.btn_export.clicked.connect(self.on_export)
        top.addWidget(self.btn_run)
        self.btn_cancel = QPushButton("ยกเลิก")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_extraction)
        top.addWidget(self.btn_cancel)
        self._undo: list[tuple] = []        # (path, row, col, previous Cell, new Cell)
        self._redo: list[tuple] = []
        add_undo_ui(self, top)
        self._update_undo_buttons()
        top.addWidget(self.btn_export)

        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.show_file)
        fbar = QHBoxLayout()
        self.file_buttons = []
        for text, slot in (("เพิ่มไฟล์ PDF", self.on_add_files), ("เอาออก", self.on_remove_file),
                           ("ล้างทั้งหมด", self.clear_files)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            fbar.addWidget(b)
            self.file_buttons.append(b)
        gfiles = QGroupBox("ไฟล์ที่นำเข้า")
        lf = QVBoxLayout(gfiles)
        lf.addWidget(self.file_list)
        lf.addLayout(fbar)

        self.progress = QProgressBar()
        self.progress.setFormat("%p%")
        self.progress.setTextVisible(True)
        self.status = QLabel("")
        status_row = QVBoxLayout()                         # full-width bar, details below it
        status_row.setSpacing(2)
        status_row.addWidget(self.progress)
        status_row.addWidget(self.status)
        self.progress.hide()                               # shown only while reading

        self.pdf = PdfPanel()
        self.pdf.install_shortcuts(self)
        self.table = QTableWidget()
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.currentCellChanged.connect(lambda r, c, *_: self.on_cell_clicked(r, c))
        self.table.itemChanged.connect(self.on_item_changed)
        self.issues = QListWidget()
        gi = QGroupBox("ข้อสังเกตของไฟล์ที่เลือก")
        QVBoxLayout(gi).addWidget(self.issues)

        # symmetric halves: [file list | issues] on top with the same fixed height, then [PDF | table]
        for g in (gfiles, gi):
            g.setFixedHeight(TOP_GROUP_HEIGHT)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(gfiles)
        ll.addWidget(self.pdf, 1)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(gi)
        rl.addWidget(self.table, 1)
        self.split = QSplitter()
        self.split.addWidget(left)
        self.split.addWidget(right)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setSizes([1000, 1000])

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(status_row)
        lay.addWidget(self.split, 1)

        self.reload_templates()

    # ---- templates
    def reload_templates(self):
        """Refresh the list after templates were saved/renamed/deleted elsewhere.

        Keeps current results; only switches template when the current one is gone.
        """
        if self.busy():
            self._reload_pending = True
            return
        self._reload_pending = False
        cur = self._tpl_name
        pick_template_combo(self.combo, cur)
        name = self.combo.currentText()
        if name != cur and self.results and self.tpl is not None:
            # active template was deleted: keep results + in-memory template (export still works)
            self.status.setText(f"แม่แบบ '{cur}' ถูกลบแล้ว — ผลการอ่านเดิมยังอยู่และส่งออกได้")
        elif name != cur or self.tpl is None:
            self.select_template(name)
        elif not self.results:
            self.select_template(name)                    # pick up saved edits
        else:
            self.status.setText('แม่แบบถูกแก้ไข — กด "อ่านข้อมูล" อีกครั้งเพื่อใช้แม่แบบล่าสุด')

    def on_template_renamed(self, old: str, new: str):
        """Follow a rename of the active template without dropping results."""
        if engine.safe_name(old) == self._tpl_name:
            self._tpl_name = engine.safe_name(new)
            if self.tpl is not None:
                self.tpl.name = new

    def confirm_clear(self) -> bool:
        """Dialog wrapper; tests may replace it."""
        return QMessageBox.question(
            self, "เปลี่ยนแม่แบบ", "การเปลี่ยนแม่แบบจะล้างผลการอ่านที่มีอยู่ ต้องการดำเนินการต่อหรือไม่?"
        ) == QMessageBox.Yes

    def on_combo_changed(self, name: str):
        if name == self._tpl_name:
            return
        if self.busy() or (self.results and not self.confirm_clear()):
            pick_template_combo(self.combo, self._tpl_name)   # revert
            return
        self.select_template(name)

    def select_template(self, name: str):
        if self.busy():
            return
        self._tpl_name = name
        if self.combo.currentText() != name:
            pick_template_combo(self.combo, name)
        self.tpl = engine.load_template(name) if name else None
        self.results.clear()
        self.reset_history()
        self.refresh_files()
        self.show_file(self.file_list.currentRow())

    # ---- files
    def add_files(self, paths: list[str]):
        if self.busy():
            return
        for p in paths:
            p = os.path.abspath(p)
            if p not in self.paths:
                self.paths.append(p)
        self.refresh_files()
        if self.file_list.currentRow() < 0 and self.paths:
            self.file_list.setCurrentRow(0)

    def on_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "เพิ่มไฟล์ PDF", "", "PDF (*.pdf)")
        if paths:
            self.add_files(paths)

    def on_remove_file(self):
        r = self.file_list.currentRow()
        if r >= 0 and not self.busy():
            p = self.paths.pop(r)
            self.results.pop(p, None)
            self.reset_history()
            self.refresh_files()

    def clear_files(self):
        if self.busy():
            return
        self.paths.clear()
        self.results.clear()
        self.reset_history()
        self.refresh_files()
        self.show_file(-1)

    def refresh_files(self):
        cur = self.file_list.currentRow()
        self.file_list.blockSignals(True)
        self.file_list.clear()
        for p in self.paths:
            self.file_list.addItem(QListWidgetItem(f"{file_status(self.results.get(p))}  {os.path.basename(p)}"))
        if 0 <= cur < len(self.paths):
            self.file_list.setCurrentRow(cur)
        self.file_list.blockSignals(False)

    # ---- extraction
    def busy(self) -> bool:
        return self.worker is not None

    def set_busy(self, on: bool):
        self.progress.setVisible(on)
        self.btn_run.setEnabled(not on)
        self.btn_export.setEnabled(not on)
        self.btn_cancel.setEnabled(on)
        self.combo.setEnabled(not on)
        self._update_undo_buttons()
        for b in self.file_buttons:
            b.setEnabled(not on)

    def cancel_extraction(self):
        if self.worker is not None:
            self.worker.stop()
            self.status.setText("กำลังยกเลิก...")

    def start_extraction(self):
        if self.busy():
            return
        if not self.tpl:
            QMessageBox.warning(self, "อ่านข้อมูล", "กรุณาเลือก Template")
            return
        if not self.paths:
            QMessageBox.warning(self, "อ่านข้อมูล", "กรุณาเพิ่มไฟล์ PDF")
            return
        if self.combo.currentText() and self.combo.currentText() != self._tpl_name:
            self._tpl_name = self.combo.currentText()   # active template was deleted: use the one shown
        self.results.clear()
        self.reset_history()
        self.refresh_files()
        try:                                    # always use the latest saved template
            self.tpl = engine.load_template(self._tpl_name)
        except OSError:
            pass
        self.show_file(self.file_list.currentRow())
        self.progress.setRange(0, len(self.paths) * 100)
        self.progress.setValue(0)
        self.worker = ExtractWorker(list(self.paths), self.tpl, self)
        self.worker.fileStarted.connect(
            lambda i: self.status.setText(f"กำลังอ่าน {i + 1}/{len(self.paths)}: {os.path.basename(self.paths[i])}"))
        self.worker.progress.connect(lambda i, d, t: self.progress.setValue(i * 100 + int(100 * d / max(t, 1))))
        self.worker.fileDone.connect(self._on_file_done)
        self.worker.allDone.connect(self._on_all_done)
        self.set_busy(True)
        self.worker.start()

    def _on_file_done(self, i: int, fr: FileResult):
        self.results[fr.path] = fr
        self.progress.setValue((i + 1) * 100)
        self.refresh_files()
        if i == self.file_list.currentRow():
            self.show_file(i)

    def _on_all_done(self):
        stopped = False
        if self.worker is not None:
            self.worker.wait()
            stopped = self.worker._stop
        self.worker = None
        self.set_busy(False)
        n = sum(len(fr.issues) for fr in self.results.values())
        self.status.setText(("ยกเลิกแล้ว — " if stopped else "") +
                            f"อ่านเสร็จ {len(self.results)} ไฟล์ — ข้อสังเกต {n} รายการ")
        if self._reload_pending:
            self.reload_templates()
        self.show_file(self.file_list.currentRow())
        self.extractionFinished.emit()

    # ---- review
    def current_result(self) -> FileResult | None:
        r = self.file_list.currentRow()
        return self.results.get(self.paths[r]) if 0 <= r < len(self.paths) else None

    def show_file(self, row: int):
        path = self.paths[row] if 0 <= row < len(self.paths) else None
        if path != getattr(self, "_shown_path", None):
            self._shown_path = path
            self.pdf.open(path)
        fr = self.results.get(path) if path else None
        self.fill_table(fr)
        self.issues.clear()
        if fr:
            self.issues.addItems(fr.issues or ["ไม่มีข้อสังเกต"])

    def fill_table(self, fr: FileResult | None):
        cols = self.tpl.columns if self.tpl else []
        self._filling = True
        self.table.clear()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([c.name for c in cols])
        rows = fr.rows if fr else []
        self.table.setRowCount(len(rows))
        boxes = []
        for r, row in enumerate(rows):
            for ci, col in enumerate(cols):
                cell = row.get(col.name, Cell())
                self.table.setItem(r, ci, self._make_item(cell))
                if cell.rect and cell.page >= 0:
                    boxes.append((cell.page, cell.rect, color_for(ci), col.name if r == 0 else ""))
        self.table.resizeColumnsToContents()
        self._filling = False
        self.pdf.view.set_boxes(boxes)

    def _make_item(self, cell: Cell) -> QTableWidgetItem:
        it = QTableWidgetItem()
        self._style_item(it, cell)
        return it

    @staticmethod
    def _style_item(it: QTableWidgetItem, cell: Cell):
        it.setText(fmt_value(cell.value))
        if cell.flag:
            it.setBackground(FLAG_COLOR)
            it.setToolTip(cell.flag)
        elif cell.source == "manual":
            it.setBackground(MANUAL_COLOR)
            it.setToolTip("แก้ไขด้วยมือ")
        else:
            it.setBackground(QBrush())
            it.setToolTip("")

    def cell_at(self, r: int, c: int) -> Cell | None:
        fr = self.current_result()
        if not fr or not self.tpl or not (0 <= r < len(fr.rows)) or not (0 <= c < len(self.tpl.columns)):
            return None
        return fr.rows[r].get(self.tpl.columns[c].name)

    def on_cell_clicked(self, r: int, c: int):
        cell = self.cell_at(r, c)
        if cell and cell.rect and cell.page >= 0:
            self.pdf.view.set_highlight(cell.page, cell.rect)
            self.pdf.update_label()

    def edit_cell(self, r: int, c: int, text: str):
        """Apply a manual edit (also used by on_item_changed)."""
        fr = self.current_result()
        if not fr or not self.tpl:
            return
        col = self.tpl.columns[c]
        val, ok = engine.convert(text, col.type)
        old = fr.rows[r].get(col.name, Cell())
        new = Cell(val, text, "manual", "" if ok else "รูปแบบไม่ตรงชนิดข้อมูล", old.page, old.rect)
        self._undo.append((fr.path, r, c, old, new))
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self._set_cell(fr, r, c, new)

    # ---- undo / redo of manual cell edits
    def reset_history(self):
        self._undo.clear()
        self._redo.clear()
        self._update_undo_buttons()

    def can_undo(self) -> bool:
        return bool(self._undo) and not self.busy()

    def can_redo(self) -> bool:
        return bool(self._redo) and not self.busy()

    def _update_undo_buttons(self):
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(self.can_undo())
            self.btn_redo.setEnabled(self.can_redo())

    def _step(self, src: list, dst: list, use_new: bool):
        if not src or self.busy() or editor_open(self):
            return
        entry = src.pop()
        dst.append(entry)
        path, r, c, old, new = entry
        fr = self.results.get(path)
        if fr is None:
            return
        if path in self.paths and self.paths.index(path) != self.file_list.currentRow():
            self.file_list.setCurrentRow(self.paths.index(path))
        self._set_cell(fr, r, c, new if use_new else old)
        self.table.setCurrentCell(r, c)

    def undo(self):
        self._step(self._undo, self._redo, use_new=False)

    def redo(self):
        self._step(self._redo, self._undo, use_new=True)

    def _set_cell(self, fr: FileResult, r: int, c: int, new: Cell):
        """Store a cell, update its issue line and (if visible) its table item."""
        col = self.tpl.columns[c]
        fr.rows[r][col.name] = new
        prefix = f"แถว {r + 1} / {col.name}:"
        fr.issues = [s for s in fr.issues if not s.startswith(prefix)]
        if new.flag:
            fr.issues.append(f"{prefix} {new.flag}")
        if fr is self.current_result():
            self._filling = True                  # update in place: never replace the item
            try:                                  # from inside its own itemChanged signal
                it = self.table.item(r, c)
                if it is None:
                    self.table.setItem(r, c, self._make_item(new))
                else:
                    self._style_item(it, new)
            finally:
                self._filling = False
            self.issues.clear()
            self.issues.addItems(fr.issues or ["ไม่มีข้อสังเกต"])
        self.refresh_files()
        self._update_undo_buttons()

    def on_item_changed(self, item: QTableWidgetItem):
        if not self._filling:
            self.edit_cell(item.row(), item.column(), item.text())

    # ---- export
    def all_issues(self) -> list[str]:
        out = []
        for p in self.paths:
            fr = self.results.get(p)
            if fr is None:
                out.append(f"{os.path.basename(p)}: ยังไม่ได้อ่านข้อมูล")
            else:
                out += [f"{os.path.basename(p)}: {s}" for s in fr.issues]
        return out

    def export_to(self, out_base: str) -> list[str]:
        results = [self.results[p] for p in self.paths if p in self.results]
        return engine.export(results, self.tpl, out_base)

    def on_export(self):
        if not self.tpl or not self.results:
            QMessageBox.warning(self, "ส่งออก", "ยังไม่มีข้อมูลที่อ่านแล้ว")
            return
        issues = self.all_issues()
        if issues and not ask_continue(self, "ตรวจก่อนส่งออก", issues):
            return
        default = os.path.join(os.path.expanduser("~"), "Documents", engine.default_export_name(self.tpl) + ".xlsx")
        path, _ = QFileDialog.getSaveFileName(self, "บันทึกไฟล์ Excel", default, "Excel (*.xlsx)")
        if not path:
            return
        base = path[:-5] if path.lower().endswith(".xlsx") else path
        if os.path.exists(base + ".csv") and QMessageBox.question(
                self, "ส่งออก", f"มีไฟล์ {os.path.basename(base)}.csv อยู่แล้ว ต้องการเขียนทับหรือไม่?"
        ) != QMessageBox.Yes:
            return
        try:
            paths = self.export_to(base)
        except PermissionError:
            QMessageBox.critical(self, "ส่งออก", "บันทึกไม่ได้ — ไฟล์อาจเปิดอยู่ใน Excel กรุณาปิดแล้วลองใหม่")
            return
        except OSError as e:
            QMessageBox.critical(self, "ส่งออก", f"บันทึกไฟล์ไม่สำเร็จ — ตรวจสอบโฟลเดอร์และพื้นที่ว่าง\n({e})")
            return
        QMessageBox.information(self, "ส่งออก", "บันทึกแล้ว:\n" + "\n".join(paths))


# ---------------------------------------------------------------- main window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1400, 900)
        self.tabs = QTabWidget()
        self.template_tab = TemplateTab()
        self.import_tab = ImportTab()
        self.tabs.addTab(self.template_tab, "1. สร้างแม่แบบ (Template)")
        self.tabs.addTab(self.import_tab, "2. นำเข้า & ตรวจ / ส่งออก Excel")
        self.setCentralWidget(self.tabs)
        self.template_tab.templatesChanged.connect(self.import_tab.reload_templates)
        self.template_tab.templateRenamed.connect(self.import_tab.on_template_renamed)

    def closeEvent(self, e):
        w = self.import_tab.worker
        if w is not None and w.isRunning():
            w.stop()
            w.wait()                     # cancel takes effect after the current box
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(engine.APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: onedir, windowed, bundles tesseract (tha+eng only).
import os

ROOT = os.path.abspath(SPECPATH)
TESS = os.path.join(ROOT, "tesseract")

datas = []
for name in os.listdir(TESS):
    p = os.path.join(TESS, name)
    if os.path.isfile(p):
        datas.append((p, "tesseract"))
for lang in ("tha", "eng"):
    datas.append((os.path.join(TESS, "tessdata", lang + ".traineddata"), "tesseract/tessdata"))

excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
    "PySide6.QtQml", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtSerialBus", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtTextToSpeech", "PySide6.QtHttpServer",
    "tkinter", "matplotlib", "numpy", "pandas", "IPython",
]

a = Analysis(
    [os.path.join(ROOT, "app.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
# --- shrink: drop root copies of tesseract DLLs and unneeded Qt pieces ---
TESS_DLLS = {n.lower() for n in os.listdir(TESS) if n.lower().endswith(".dll")}
TESS_DLLS -= {"libffi-8.dll", "zlib1.dll"}   # also needed at root by Python's _ctypes / zlib
DROP_DLL_PREFIX = ("qt6quick", "qt6qml", "qt6pdf", "qt6network", "qt6opengl",
                   "qt6virtualkeyboard", "qt6svg", "qt6dbus")
KEEP_PLUGIN_DIRS = ("platforms", "styles", "imageformats")
KEEP_IMG = ("qjpeg", "qico", "qgif")

def _keep(entry):
    low = entry[0].replace("\\", "/").lower()
    parts = low.split("/")
    base = parts[-1]
    if low.startswith("tesseract/"):
        return True
    if len(parts) == 1 and base in TESS_DLLS:
        return False
    if base == "opengl32sw.dll" or base.startswith(DROP_DLL_PREFIX):
        return False
    if "pyside6/translations" in low or "pyside6/qml" in low:
        return False
    if "pyside6/plugins/" in low:
        sub = low.split("pyside6/plugins/")[1].split("/")[0]
        if sub not in KEEP_PLUGIN_DIRS:
            return False
        if sub == "imageformats" and not base.startswith(KEEP_IMG):
            return False
        if sub == "platforms" and not base.startswith("qwindows"):
            return False
    return True

a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PdfToExcel",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PdfToExcel")

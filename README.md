# OCRtoExcel (PdfToExcel)

*Create format reading with OCR and export to excel by python*

โปรแกรมเดสก์ท็อปออฟไลน์สำหรับอ่านและดึงข้อมูลจากใบขนสินค้าขาเข้า (PDF กศก.99/1) แปลงเป็นตารางข้อมูลและส่งออกเป็นไฟล์ Excel (.xlsx) / CSV

---

## ความต้องการของระบบ (Prerequisites)

- ระบบปฏิบัติการ: Windows 10 / 11 (64-bit)
- Python 3.10 ขึ้นไป (แนะนำ Python 3.13 ผ่านตัวเรียก `py`)
- Git

---

## ขั้นตอนการติดตั้งและเริ่มต้นใช้งาน (Getting Started)

อารมณ์เหมือนการสั่ง `npm install` เวลา clone โปรเจกต์เว็บมา ให้ทำตามขั้นตอนดังนี้ครับ:

### 1. Clone โปรเจกต์
```bash
git clone https://github.com/Chinnawat1404/OCRtoExcel.git
cd OCRtoExcel
```

### 2. ติดตั้ง Python Dependencies
รันคำสั่งติดตั้งแพ็กเกจตามไฟล์ `requirements.txt`:
```bash
py -m pip install -r requirements.txt
```
*(แพ็กเกจหลัก: `PySide6`, `PyMuPDF`, `openpyxl`, `pyinstaller`)*

### 3. เตรียมโฟลเดอร์ Tesseract OCR (สำหรับระบบ OCR ภาษาไทย-อังกฤษ)
โปรแกรมถูกออกแบบให้ทำงานแบบ Fully Offline โดยเรียกใช้ Portable Tesseract ที่อยู่ในโฟลเดอร์ `tesseract/` ภายในโปรเจกต์:
- โครงสร้างโฟลเดอร์ที่โปรแกรมเรียกใช้:
  ```text
  OCRtoExcel/
  ├── tesseract/
  │   ├── tesseract.exe
  │   ├── *.dll
  │   └── tessdata/
  │       ├── tha.traineddata
  │       ├── eng.traineddata
  │       └── osd.traineddata
  ```
> **หมายเหตุ:** โฟลเดอร์ `tesseract/` มีขนาดประมาณ 180MB จึงถูกยกเว้นไว้ใน `.gitignore` เพื่อไม่ให้ repository หนักเกินไป หาก clone มาใหม่ให้วางโฟลเดอร์ `tesseract/` ไว้ที่ root ของโปรเจกต์

---

## การเปิดใช้งานโปรแกรม (Development Run)

เปิดใช้งาน GUI Application:
```bash
py app.py
```

---

## การรันแบบทดสอบ (Testing)

ทดสอบระบบ GUI Smoke Test (Offscreen):
```bash
py tests/test_gui_smoke.py
```

ทดสอบการ import ตัวอย่าง (ต้องมีไฟล์ตัวอย่างใน `samples/`):
```bash
py tests/test_import_sample.py samples/import_sample.pdf
```

---

## การ Build เป็นไฟล์ .exe (Standalone)

คอมไพล์โปรแกรมเป็นโฟลเดอร์ standalone `.exe` พร้อมใช้งานด้วย PyInstaller:
```bash
build.bat
```
ไฟล์โปรแกรมที่ Build เสร็จแล้วจะอยู่ที่:
```text
dist\PdfToExcel\PdfToExcel.exe
```

---

## ข้อมูลความปลอดภัยและความเป็นส่วนตัว (Data Privacy)

- ไฟล์ตัวอย่างเอกสารศุลกากรจริงในโฟลเดอร์ `samples/` และไฟล์ที่ export ออกมา (`*.xlsx`, `*.csv`) ได้รับการยกเว้นใน `.gitignore` อย่างเข้มงวด จะไม่ถูกนำขึ้น GitHub เด็ดขาดเพื่อความปลอดภัยของข้อมูล

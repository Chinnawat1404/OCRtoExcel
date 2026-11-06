@echo off
setlocal
cd /d "%~dp0"
echo Building PdfToExcel...
py -m PyInstaller --noconfirm --clean PdfToExcel.spec
if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)
if not exist "dist\PdfToExcel\PdfToExcel.exe" (
  echo BUILD FAILED: exe not found
  pause
  exit /b 1
)
echo Done: %~dp0dist\PdfToExcel\PdfToExcel.exe
endlocal

# Tesseract OCR Installation Guide for Windows

## Quick Installation Steps

### Option 1: Download & Install (Recommended)

1. **Download the installer:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki/Downloads
   - Download: `tesseract-ocr-w64-setup-v5.x.x.exe` (64-bit for most Windows systems)

2. **Run the installer:**
   - Double-click the downloaded `.exe` file
   - Click "Install"
   - **IMPORTANT:** Note the installation path (usually `C:\Program Files\Tesseract-OCR`)
   - Complete the installation

3. **Configure pytesseract (in Python):**
   - Add this to the top of `app.py` after imports:
   ```python
   import pytesseract
   pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

4. **Test the installation:**
   Run this command in PowerShell:
   ```
   .venv\Scripts\python.exe -c "import pytesseract; print(pytesseract.get_tesseract_version())"
   ```
   You should see a version number like `tesseract 5.3.0`

### Option 2: Using Chocolatey (if you have it installed)

```
choco install tesseract
```

## After Installation

Once installed, verify it works:

```powershell
# Test Tesseract directly
tesseract --version

# Test with Python
.venv\Scripts\python.exe -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

## Troubleshooting

### If you get "Command not found"
- Make sure Tesseract is in your Windows PATH environment variable
- Or manually set the path in `app.py` as shown above

### If you get "tesseract is not installed or it's not in your PATH"
- The installation path might be different
- Check: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Or: `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
- Update the path in `app.py` accordingly

## Download Link
Download from: https://github.com/UB-Mannheim/tesseract/releases

Look for the latest release with `w64-setup` in the filename.

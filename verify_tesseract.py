#!/usr/bin/env python
"""
Tesseract OCR Verification and Setup Script
Run this after installing Tesseract to verify everything works
"""

import os
import sys

def check_tesseract():
    """Check if Tesseract is installed and accessible"""
    try:
        import pytesseract
        from pytesseract import TesseractNotFoundError
        
        # Check common installation paths on Windows
        paths_to_check = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            'tesseract'  # Check if in PATH
        ]
        
        print("🔍 Checking for Tesseract OCR installation...\n")
        
        for path in paths_to_check:
            if os.path.exists(path) or path == 'tesseract':
                try:
                    # Try to get version
                    if path != 'tesseract':
                        pytesseract.pytesseract.pytesseract_cmd = path
                    version = pytesseract.get_tesseract_version()
                    print(f"✅ Found Tesseract: {path}")
                    print(f"   Version: {version}")
                    return True
                except Exception as e:
                    continue
        
        print("❌ Tesseract OCR not found!")
        print("\nTo fix this:")
        print("1. Download from: https://github.com/UB-Mannheim/tesseract/releases")
        print("2. Install the latest tesseract-ocr-w64-setup-v5.x.x.exe")
        print("3. Run this script again\n")
        return False
        
    except ImportError:
        print("❌ pytesseract not installed!")
        print("Run: pip install pytesseract\n")
        return False

def main():
    print("=" * 60)
    print("Tesseract OCR Setup Verification")
    print("=" * 60 + "\n")
    
    if check_tesseract():
        print("\n✅ All systems ready! Receipt scanning should now work.\n")
        return 0
    else:
        print("\n⚠️ Please install Tesseract and try again.\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())

# src/IR/ocr.py
#
# OCR fallback for scanned/image-based PDFs only.

import os


# ─────────────────────────────────────────────
# Try to import OCR dependencies
# ─────────────────────────────────────────────
OCR_AVAILABLE = False
_ocr_error = None

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True

    if os.name == "nt":
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
except ImportError as e:
    _ocr_error = str(e)


try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


if OCR_AVAILABLE:
    try:
        pytesseract.get_tesseract_version()
        print("✅ OCR ready (Tesseract found)")
    except Exception as e:
        OCR_AVAILABLE = False
        _ocr_error = f"Tesseract binary not found: {e}"
        print(f"⚠️  OCR disabled — {_ocr_error}")
        print("   Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
else:
    print(f"⚠️  OCR disabled — {_ocr_error}")
    print("   Install: pip install pytesseract pillow pdf2image")


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
OCR_LANGUAGES = "eng"           # multiple langs: "eng+hin+spa"
OCR_CONFIG    = "--psm 3"       # page segmentation mode
PDF_DPI       = 200             # higher = better OCR, slower


# ─────────────────────────────────────────────
# Core OCR
# ─────────────────────────────────────────────
def _ocr_image(image, source_name: str = "image", location: str = "") -> str:
    """Run OCR on a PIL Image. Returns extracted text."""
    if not OCR_AVAILABLE:
        return ""

    try:
        text = pytesseract.image_to_string(
            image,
            lang   = OCR_LANGUAGES,
            config = OCR_CONFIG,
        )
        return text.strip()
    except Exception as e:
        print(f"   ⚠️  OCR failed for {source_name} {location}: {e}")
        return ""


def ocr_pdf(filepath: str, first_page: int = None, last_page: int = None, silent: bool = True) -> list:
    """
    Extract text from scanned/image PDF via OCR.
    Set silent=False to see per-page logs.
    """
    if not OCR_AVAILABLE or not PDF2IMAGE_AVAILABLE:
        return []

    records = []
    try:
        kwargs = {"dpi": PDF_DPI}
        if first_page: kwargs["first_page"] = first_page
        if last_page:  kwargs["last_page"]  = last_page

        images = convert_from_path(filepath, **kwargs)

        for i, img in enumerate(images, start=first_page or 1):
            text = _ocr_image(img, os.path.basename(filepath), f"page {i}")
            if text:
                records.append({
                    "source_file": os.path.basename(filepath),
                    "file_type":   "pdf",
                    "location":    f"page {i} (OCR)",
                    "text":        text,
                })
    except Exception as e:
        if not silent:
            print(f"[ERROR] Failed to OCR PDF {filepath}: {e}")

    return records
import os
import pdfplumber
from pptx import Presentation


def extract_pdf(path):
    """Extract text page-wise from a PDF."""
    records = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    records.append({
                        "source_file": os.path.basename(path),
                        "file_type": "pdf",
                        "location": f"page {i}",
                        "text": text,
                    })
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {path}: {e}")
    return records


def extract_pptx(path):
    """Extract text slide-wise from a PPTX (including speaker notes)."""
    records = []
    try:
        prs = Presentation(path)
        for i, slide in enumerate(prs.slides, start=1):
            parts = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        line = para.text.strip()
                        if line:
                            parts.append(line)

                # tables inside slides
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [c.text.strip() for c in row.cells if c.text.strip()]
                        if cells:
                            parts.append(" | ".join(cells))

            text = "\n".join(parts).strip()
            if text:
                records.append({
                    "source_file": os.path.basename(path),
                    "file_type": "pptx",
                    "location": f"slide {i}",
                    "text": text,
                })
    except Exception as e:
        print(f"[ERROR] Failed to read PPTX {path}: {e}")
    return records


def extract_folder(folder):
    """Extract all PDFs and PPTXs in a folder."""
    all_records = []
    for root, _, files in os.walk(folder):
        for fname in files:
            path = os.path.join(root, fname)
            lower = fname.lower()
            if lower.endswith(".pdf"):
                print(f"Extracting PDF : {fname}")
                all_records.extend(extract_pdf(path))
            elif lower.endswith(".pptx"):
                print(f"Extracting PPTX: {fname}")
                all_records.extend(extract_pptx(path))
    print(f"Extracted {len(all_records)} pages/slides total.")
    return all_records

if __name__ == "__main__":
    records = extract_folder(r"datatset\study_material")
    for rec in records:
        print(f"{rec['source_file']} ({rec['location']}):\n{rec['text']}\n{'-'*40}")
import os
import pdfplumber
from pptx import Presentation

import json
import pickle
import re

import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


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
                        "source_file":     os.path.basename(path),       # keep for backwards compat
                        "source_path":     os.path.normpath(path),       # ✅ FULL path (unique)
                        "source_rel_path": get_relative_path(path),      # ✅ relative path (for display)
                        "file_type":       "pdf",
                        "location":        f"page {i}",
                        "text":            text,
                    })
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {path}: {e}")
    return records

def extract_pptx(path):
    """Extract text slide-wise from a PPTX."""
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
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [c.text.strip() for c in row.cells if c.text.strip()]
                        if cells:
                            parts.append(" | ".join(cells))

            text = "\n".join(parts).strip()
            if text:
                records.append({
                    "source_file":     os.path.basename(path),
                    "source_path":     os.path.normpath(path),       # ✅
                    "source_rel_path": get_relative_path(path),      # ✅
                    "file_type":       "pptx",
                    "location":        f"slide {i}",
                    "text":            text,
                })
    except Exception as e:
        print(f"[ERROR] Failed to read PPTX {path}: {e}")
    return records

def get_relative_path(full_path):
    """Get path relative to 'study_material' folder.
    Example: 'D:/proj/dataset/study_material/CSE/3/Math/lec-1.pdf'
             → 'CSE/3/Math/lec-1.pdf'
    """
    norm = os.path.normpath(full_path)
    parts = norm.split(os.sep)
    try:
        idx = parts.index("study_material")
        return os.sep.join(parts[idx + 1:])
    except ValueError:
        return os.path.basename(full_path)


def parse_path_metadata(rel_path):
    """Extract branch, sem, subject from relative path.
    'CSE/3/Math/lec-1.pdf' → ('CSE', '3', 'Math')
    """
    parts = rel_path.split(os.sep)
    branch  = parts[0] if len(parts) > 0 else ""
    sem     = parts[1] if len(parts) > 1 else ""
    subject = parts[2] if len(parts) > 2 else ""
    return branch, sem, subject



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


# ===============Chunking=================== 

def chunk_text(text, max_words=200, overlap=40):
    """Split text into overlapping word chunks."""
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def chunk_records(records, max_words=200, overlap=40):
    chunked = []
    for rec in records:
        pieces = chunk_text(rec["text"], max_words, overlap)

        # Parse branch/sem/subject from path
        rel_path = rec.get("source_rel_path", "")
        branch, sem, subject = parse_path_metadata(rel_path)

        for j, piece in enumerate(pieces):
            chunked.append({
                "chunk_id":        len(chunked),
                "source_file":     rec["source_file"],
                "source_path":     rec.get("source_path", ""),       # ✅
                "source_rel_path": rec.get("source_rel_path", ""),   # ✅
                "branch":          branch,                            # ✅ NEW
                "semester":        sem,                               # ✅ NEW
                "subject_folder":  subject,                           # ✅ NEW (from folder)
                "file_type":       rec["file_type"],
                "location":        rec["location"],
                "chunk_index":     j,
                "text":            piece,
            })
    print(f"Created {len(chunked)} chunks.")
    return chunked

# =================Index_Building===================

INDEX_DIR = "index_store"
EMBED_MODEL = "all-MiniLM-L6-v2"   # small, fast, good quality


def tokenize(text):
    """Simple tokenizer for BM25."""
    return re.findall(r"[a-z0-9]+", text.lower())


def build_indexes(chunks):
    os.makedirs(INDEX_DIR, exist_ok=True)

    texts = [c["text"] for c in chunks]

    # ---------- 1. BM25 (keyword) index ----------
    print("Building BM25 index...")
    tokenized = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    with open(os.path.join(INDEX_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump({"bm25": bm25, "tokenized": tokenized}, f)

    # ---------- 2. Vector (semantic) index ----------
    print("Building vector index (this may take a while)...")
    model = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # so inner product == cosine similarity
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner product on normalized vectors
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, os.path.join(INDEX_DIR, "faiss.index"))

    # ---------- 3. Save chunk metadata ----------
    with open(os.path.join(INDEX_DIR, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    print("Indexes saved to", INDEX_DIR)
    
    
# =================Main function to run the whole pipeline===================

if __name__ == "__main__":
    folder = "dataset/study_material"  # Change this to your folder path
    print(f"Extracting documents from folder: {folder}")
    records = extract_folder(folder)

    print("Chunking extracted text...")
    chunks = chunk_records(records)

    print("Building indexes...")
    build_indexes(chunks)

    print("All done! You can now query the indexes for retrieval.")

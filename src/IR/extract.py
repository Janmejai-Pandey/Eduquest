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
    """Convert page/slide records into chunk records."""
    chunked = []
    for rec in records:
        pieces = chunk_text(rec["text"], max_words, overlap)
        for j, piece in enumerate(pieces):
            chunked.append({
                "chunk_id": len(chunked),
                "source_file": rec["source_file"],
                "file_type": rec["file_type"],
                "location": rec["location"],
                "chunk_index": j,
                "text": piece,
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
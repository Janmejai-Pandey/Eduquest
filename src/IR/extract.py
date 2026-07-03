import os
import pdfplumber
from pptx import Presentation

import json
import pickle
import re

import numpy as np
import faiss
from rank_bm25 import BM25Okapi
import torch
from sentence_transformers import SentenceTransformer

import llm_config as config
# ─────────────────────────────────────────────
# Path parsing helper
# ─────────────────────────────────────────────
def parse_path_metadata(full_path: str) -> dict[str, str]:
    """
    Extract branch, semester, subject, category from folder structure.

    Expected structure:
      .../dataset/study_material/<BRANCH>/<SEM>/<SUBJECT>/<CATEGORY>/file.pdf

    Example:
      "D:/JaPari/dataset/study_material/CSE/3/DSA/Lectures/lec-1.pdf"
      → {branch: 'CSE', semester: '3', subject: 'DSA', category: 'Lectures'}
    """
    norm = os.path.normpath(full_path)
    parts = norm.split(os.sep)

    metadata = {
        "branch":   "",
        "semester": "",
        "subject":  "",
        "category": "",
        "rel_path": "",
    }

    try:
        sm_idx = parts.index("study_material")
        after = parts[sm_idx + 1:]   # everything after study_material

        # relative path from study_material
        metadata["rel_path"] = os.sep.join(after)

        # Parse folder hierarchy
        if len(after) >= 1: metadata["branch"]   = after[0]
        if len(after) >= 2: metadata["semester"] = after[1]
        if len(after) >= 3: metadata["subject"]  = after[2]
        if len(after) >= 4: metadata["category"] = after[3]

    except ValueError:
        # Not under study_material — use filename only
        metadata["rel_path"] = os.path.basename(full_path)

    return metadata


# ─────────────────────────────────────────────
# PDF extraction (with path metadata)
# ─────────────────────────────────────────────
def extract_pdf(path: str) -> list[dict]:
    """Extract text page-wise from a PDF."""
    records = []
    meta = parse_path_metadata(path)

    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    records.append({
                        "source_file":     os.path.basename(path),   # keep filename for display
                        "source_path":     os.path.normpath(path),   # ✅ full path (unique)
                        "source_rel_path": meta["rel_path"],         # ✅ relative to study_material
                        "branch":          meta["branch"],           # ✅ NEW
                        "semester":        meta["semester"],         # ✅ NEW
                        "subject":         meta["subject"],          # ✅ NEW
                        "category":        meta["category"],         # ✅ NEW
                        "file_type":       "pdf",
                        "location":        f"page {i}",
                        "text":            text,
                    })
    except Exception as e:
        print(f"[ERROR] Failed to read PDF {path}: {e}")
    return records


# ─────────────────────────────────────────────
# PPTX extraction (with path metadata)
# ─────────────────────────────────────────────
def extract_pptx(path: str) -> list[dict]:
    """Extract text slide-wise from a PPTX (including tables)."""
    records = []
    meta = parse_path_metadata(path)

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
                    "source_path":     os.path.normpath(path),
                    "source_rel_path": meta["rel_path"],
                    "branch":          meta["branch"],
                    "semester":        meta["semester"],
                    "subject":         meta["subject"],
                    "category":        meta["category"],
                    "file_type":       "pptx",
                    "location":        f"slide {i}",
                    "text":            text,
                })
    except Exception as e:
        print(f"[ERROR] Failed to read PPTX {path}: {e}")
    return records


# ─────────────────────────────────────────────
# Extract all files in folder (recursive)
# ─────────────────────────────────────────────
def extract_folder(folder: str) -> list[dict]:
    """Extract all PDFs and PPTXs recursively from a folder."""
    all_records = []
    for root, _, files in os.walk(folder):
        for fname in files:
            path = os.path.join(root, fname)
            lower = fname.lower()

            if lower.endswith(".pdf"):
                print(f"📄 Extracting PDF : {fname}")
                all_records.extend(extract_pdf(path))
            elif lower.endswith(".pptx"):
                print(f"📊 Extracting PPTX: {fname}")
                all_records.extend(extract_pptx(path))

    print(f"\n✅ Extracted {len(all_records)} pages/slides from all files")
    return all_records


# =============== Chunking ===============

def chunk_text(text: str, max_words: int = 200, overlap: int = 40) -> list[str]:
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


def chunk_records(records: list[dict], max_words: int = 200, overlap: int = 40) -> list[dict]:
    """Convert page/slide records into chunk records — PRESERVES all metadata."""
    chunked = []
    for rec in records:
        pieces = chunk_text(rec["text"], max_words, overlap)
        for j, piece in enumerate(pieces):
            chunked.append({
                "chunk_id":        len(chunked),
                "source_file":     rec.get("source_file",     ""),
                "source_path":     rec.get("source_path",     ""),   # ✅
                "source_rel_path": rec.get("source_rel_path", ""),   # ✅
                "branch":          rec.get("branch",          ""),   # ✅
                "semester":        rec.get("semester",        ""),   # ✅
                "subject":         rec.get("subject",         ""),   # ✅
                "category":        rec.get("category",        ""),   # ✅
                "file_type":       rec.get("file_type",       ""),
                "location":        rec.get("location",        ""),
                "chunk_index":     j,
                "text":            piece,
            })
    print(f"✅ Created {len(chunked)} chunks with full metadata")
    return chunked

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
CURRENT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
INDEX_DIR    = os.path.join(PROJECT_ROOT, "index_store")


# ─────────────────────────────────────────────
# Lazy model loader
# ─────────────────────────────────────────────
_embed_model = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️  Using device: {DEVICE.upper()}")
if DEVICE == "cuda":
    print(f"   GPU: {torch.cuda.get_device_name(0)}")


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        print(f"📥 Loading embedding model: {config.EMBED_MODEL}")
        _embed_model = SentenceTransformer(config.EMBED_MODEL, device=DEVICE)
        print(f"✅ Embedding model loaded (dim={_embed_model.get_embedding_dimension()})")
    return _embed_model


# ─────────────────────────────────────────────
# Tokenizer for BM25
# ─────────────────────────────────────────────
def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


# ─────────────────────────────────────────────
# Build indexes
# ─────────────────────────────────────────────
def build_indexes(chunks: list):
    os.makedirs(INDEX_DIR, exist_ok=True)
    texts = [c["text"] for c in chunks]

    # BM25
    print("\n🔨 Building BM25 index...")
    tokenized = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized)
    with open(os.path.join(INDEX_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump({"bm25": bm25, "tokenized": tokenized}, f)
    print(f"✅ BM25 index built ({len(tokenized)} docs)")

    # Vector (BGE-M3 on GPU)
    print(f"\n🔨 Building vector index with {config.EMBED_MODEL} on {DEVICE.upper()}...")
    model = get_embed_model()

    # On GPU can use larger batch size
    batch_size = 64 if DEVICE == "cuda" else config.EMBED_BATCH_SIZE

    embeddings = model.encode(
        texts,
        batch_size            = batch_size,
        show_progress_bar     = True,
        convert_to_numpy      = True,
        normalize_embeddings  = config.EMBED_NORMALIZE,
    )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    faiss.write_index(index, os.path.join(INDEX_DIR, "faiss.index"))
    print(f"✅ FAISS index built (dim={dim})")

    # Save chunks
    with open(os.path.join(INDEX_DIR, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    # Save config
    idx_config = {
        "embed_model": config.EMBED_MODEL,
        "embed_dim":   dim,
        "num_chunks":  len(chunks),
        "device":      DEVICE,
    }
    with open(os.path.join(INDEX_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(idx_config, f, indent=2)

    print(f"\n✅ All indexes saved to {INDEX_DIR}") 
    
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

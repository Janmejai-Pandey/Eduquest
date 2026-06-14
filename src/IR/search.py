import os
import json
import pickle
import re

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

INDEX_DIR = "index_store"
EMBED_MODEL = "all-MiniLM-L6-v2"


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class HybridSearcher:
    def __init__(self):
        # load chunks
        with open(os.path.join(INDEX_DIR, "chunks.json"), encoding="utf-8") as f:
            self.chunks = json.load(f)

        # load BM25
        with open(os.path.join(INDEX_DIR, "bm25.pkl"), "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]

        # load FAISS
        self.faiss_index = faiss.read_index(os.path.join(INDEX_DIR, "faiss.index"))

        # load embedding model
        self.model = SentenceTransformer(EMBED_MODEL)

    # ---------- keyword search ----------
    def bm25_scores(self, query):
        scores = np.array(self.bm25.get_scores(tokenize(query)))
        return scores

    # ---------- semantic search ----------
    def vector_scores(self, query):
        q_emb = self.model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32)
        n = len(self.chunks)
        sims, ids = self.faiss_index.search(q_emb, n)  # search all
        scores = np.zeros(n)
        scores[ids[0]] = sims[0]
        return scores

    @staticmethod
    def normalize(scores):
        """Min-max normalize scores to 0..1."""
        lo, hi = scores.min(), scores.max()
        if hi - lo < 1e-9:
            return np.zeros_like(scores)
        return (scores - lo) / (hi - lo)

    # ---------- hybrid search ----------
    def search(self, query, top_k=5, alpha=0.5):
        """
        alpha = weight for semantic search.
        alpha=1.0 -> pure semantic
        alpha=0.0 -> pure keyword (BM25)
        """
        bm25 = self.normalize(self.bm25_scores(query))
        vec = self.normalize(self.vector_scores(query))

        combined = alpha * vec + (1 - alpha) * bm25
        top_ids = np.argsort(combined)[::-1][:top_k]

        results = []
        for idx in top_ids:
            c = self.chunks[idx]
            results.append({
                "score": round(float(combined[idx]), 4),
                "bm25_score": round(float(bm25[idx]), 4),
                "semantic_score": round(float(vec[idx]), 4),
                "source_file": c["source_file"],
                "location": c["location"],
                "text": c["text"][:400],  # preview
            })
        return results
    

if __name__ == "__main__":
    searcher = HybridSearcher()
    print("\nHybrid search ready. Type a query (or 'exit').")
    while True:
        query = input("\nQuery> ").strip()
        if not query or query.lower() == "exit":
            break
        results = searcher.search(query, top_k=5, alpha=0.5)
        for i, r in enumerate(results, start=1):
            print(f"\n--- Result {i} (score={r['score']}) ---")
            print(f"File    : {r['source_file']} ({r['location']})")
            print(f"BM25={r['bm25_score']}  Semantic={r['semantic_score']}")
            print(f"Text    : {r['text']}")
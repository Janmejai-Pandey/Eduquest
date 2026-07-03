import os
import json
import pickle
import re

import numpy as np
import faiss

import llm_config as config

import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🖥️  Search using: {DEVICE.upper()}")

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
CURRENT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
INDEX_DIR    = os.path.join(PROJECT_ROOT, "index_store")


# ─────────────────────────────────────────────
# Lazy model loaders
# ─────────────────────────────────────────────
_embed_model = None
_reranker    = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"📥 Loading embedding model: {config.EMBED_MODEL}")
        _embed_model = SentenceTransformer(config.EMBED_MODEL, device=DEVICE)   # ← use GPU
        print(f"✅ Embedding model loaded on {DEVICE}")
    return _embed_model

def get_reranker():
    global _reranker
    if _reranker is None:
        from FlagEmbedding import FlagReranker
        print(f"📥 Loading reranker: {config.RERANKER_MODEL}")
        # use_fp16=True works great on GPU
        _reranker = FlagReranker(
            config.RERANKER_MODEL,
            use_fp16 = config.RERANKER_USE_FP16 and DEVICE == "cuda",
        )
        print(f"✅ Reranker loaded")
    return _reranker


# ─────────────────────────────────────────────
# Tokenizer for BM25
# ─────────────────────────────────────────────
def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


# ─────────────────────────────────────────────
# Hybrid searcher with reranking
# ─────────────────────────────────────────────
class HybridSearcher:
    def __init__(self):
        # Load chunks
        with open(os.path.join(INDEX_DIR, "chunks.json"), encoding="utf-8") as f:
            self.chunks = json.load(f)

        # Load BM25
        with open(os.path.join(INDEX_DIR, "bm25.pkl"), "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]

        # Load FAISS
        self.faiss_index = faiss.read_index(os.path.join(INDEX_DIR, "faiss.index"))

        # Lazy-loaded
        self.model    = None
        self.reranker = None

        print(f"✅ HybridSearcher loaded: {len(self.chunks)} chunks")

    # ── BM25 scoring ──
    def bm25_scores(self, query: str) -> np.ndarray:
        return np.array(self.bm25.get_scores(tokenize(query)))

    # ── Vector scoring ──
    def vector_scores(self, query: str) -> np.ndarray:
        if self.model is None:
            self.model = get_embed_model()

        q_emb = self.model.encode(
            [query],
            convert_to_numpy     = True,
            normalize_embeddings = config.EMBED_NORMALIZE,
        ).astype(np.float32)

        n = len(self.chunks)
        sims, ids = self.faiss_index.search(q_emb, n)
        scores = np.zeros(n)
        scores[ids[0]] = sims[0]
        return scores

    @staticmethod
    def normalize(scores: np.ndarray) -> np.ndarray:
        lo, hi = scores.min(), scores.max()
        if hi - lo < 1e-9:
            return np.zeros_like(scores)
        return (scores - lo) / (hi - lo)

    # ── Rerank ──
    def rerank(self, query: str, candidate_indices: list) -> list:
        """Rerank candidates. Returns [(chunk_idx, score), ...] sorted DESC."""
        if self.reranker is None:
            self.reranker = get_reranker()

        pairs = [[query, self.chunks[i]["text"]] for i in candidate_indices]
        scores = self.reranker.compute_score(pairs, normalize=True)

        if not isinstance(scores, list):
            scores = [scores]

        ranked = list(zip(candidate_indices, scores))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    # ── Main search ──
    def search(
        self,
        query: str,
        top_k: int = None,
        alpha: float = None,
        rerank_pool: int = None,
        use_reranker: bool = None,
    ) -> list:
        """
        Hybrid search + reranking.
        All params default to config values from .env.
        """
        # Use config defaults if not overridden
        if top_k is None:        top_k        = config.SEARCH_TOP_K
        if alpha is None:        alpha        = config.SEARCH_ALPHA
        if rerank_pool is None:  rerank_pool  = config.SEARCH_RERANK_POOL
        if use_reranker is None: use_reranker = config.USE_RERANKER

        # ── Stage 1: Hybrid retrieval ──
        bm25   = self.normalize(self.bm25_scores(query))
        vector = self.normalize(self.vector_scores(query))
        hybrid = alpha * vector + (1 - alpha) * bm25

        n_candidates = min(rerank_pool, len(self.chunks))
        top_indices  = np.argsort(hybrid)[::-1][:n_candidates].tolist()

        # ── Stage 2: Rerank ──
        if use_reranker and len(top_indices) > top_k:
            print(f"🔄 Reranking {len(top_indices)} → top {top_k}")
            ranked = self.rerank(query, top_indices)
            final = ranked[:top_k]
        else:
            final = [(idx, float(hybrid[idx])) for idx in top_indices[:top_k]]

        # ── Build results ──
        results = []
        for idx, score in final:
            c = self.chunks[idx]
            results.append({
                "score":          round(float(score), 4),
                "bm25_score":     round(float(bm25[idx]),   4),
                "semantic_score": round(float(vector[idx]), 4),
                "source_file":    c.get("source_file", ""),
                "location":       c.get("location", ""),
                "text":           c["text"][:800],
                "branch":         c.get("branch", ""),
                "semester":       c.get("semester", ""),
                "subject":        c.get("subject", ""),
                "category":       c.get("category", ""),
            })
        return results
    
if __name__ == "__main__":
    searcher = HybridSearcher()
    query = input("Enter your query: ")
    results = searcher.search(query)
    for r in results:
        print(r)
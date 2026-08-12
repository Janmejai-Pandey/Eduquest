import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default=None, cast=str):
    """Get env variable with type casting."""
    val = os.getenv(key, default)
    if val is None or val == "":
        return default
    try:
        if cast is bool:
            return str(val).lower() in ("true", "1", "yes", "on")
        return cast(val)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════
# LLM PROVIDERS
# ═══════════════════════════════════════════════════════

# Groq (primary)
GROQ_API_KEY        = _get("GROQ_API_KEY",     "")
GROQ_MODEL          = _get("GROQ_MODEL",       "qwen/qwen3-32b")
GROQ_TEMPERATURE    = _get("GROQ_TEMPERATURE", 0.3, float)
GROQ_MAX_TOKENS     = _get("GROQ_MAX_TOKENS",  2048, int)

# OpenRouter (fallback)
OPENROUTER_API_KEY     = _get("OPENROUTER_API_KEY",     "")
OPENROUTER_MODEL       = _get("OPENROUTER_MODEL",       "qwen/qwen3-14b:free")
OPENROUTER_TEMPERATURE = _get("OPENROUTER_TEMPERATURE", 0.3, float)
OPENROUTER_MAX_TOKENS  = _get("OPENROUTER_MAX_TOKENS",  2048, int)
OPENROUTER_APP_URL     = _get("OPENROUTER_APP_URL",     "https://lwckfp59-8000.inc1.devtunnels.ms")
OPENROUTER_APP_NAME    = _get("OPENROUTER_APP_NAME",    "EduQuest")

# Retry
LLM_MAX_RETRIES = _get("LLM_MAX_RETRIES", 2, int)
LLM_RETRY_DELAY = _get("LLM_RETRY_DELAY", 2, int)


# ═══════════════════════════════════════════════════════
# EMBEDDINGS
# ═══════════════════════════════════════════════════════
EMBED_MODEL      = _get("EMBED_MODEL",      "BAAI/bge-m3")
EMBED_BATCH_SIZE = _get("EMBED_BATCH_SIZE", 32,   int)
EMBED_NORMALIZE  = _get("EMBED_NORMALIZE",  True, bool)


# ═══════════════════════════════════════════════════════
# RERANKER
# ═══════════════════════════════════════════════════════
RERANKER_MODEL    = _get("RERANKER_MODEL",    "BAAI/bge-reranker-v2-m3")
RERANKER_USE_FP16 = _get("RERANKER_USE_FP16", True, bool)
USE_RERANKER      = _get("USE_RERANKER",      True, bool)


# ═══════════════════════════════════════════════════════
# SEARCH
# ═══════════════════════════════════════════════════════
SEARCH_TOP_K       = _get("SEARCH_TOP_K",       5,   int)
SEARCH_RERANK_POOL = _get("SEARCH_RERANK_POOL", 20,  int)
SEARCH_ALPHA       = _get("SEARCH_ALPHA",       0.5, float)
SEARCH_MIN_SCORE   = _get("SEARCH_MIN_SCORE",   0.3, float)


# ═══════════════════════════════════════════════════════
# CHATBOT
# ═══════════════════════════════════════════════════════
MAX_HISTORY_TURNS   = _get("MAX_HISTORY_TURNS",   6, int)
WEB_FALLBACK_SCORE  = _get("WEB_FALLBACK_SCORE",  0.4, float)
ENABLE_WEB_FALLBACK = _get("ENABLE_WEB_FALLBACK", False, bool)


# ═══════════════════════════════════════════════════════
# Print summary on import
# ═══════════════════════════════════════════════════════
def print_config():
    print("┌─────────────────────────────────────────────")
    print("│ CONFIGURATION")
    print("├─────────────────────────────────────────────")
    print(f"│ LLM Primary    : {GROQ_MODEL}")
    print(f"│ LLM Fallback   : {OPENROUTER_MODEL}")
    print(f"│ Embed Model    : {EMBED_MODEL}")
    print(f"│ Reranker Model : {RERANKER_MODEL} (enabled: {USE_RERANKER})")
    print(f"│ Search top_k   : {SEARCH_TOP_K} (rerank pool: {SEARCH_RERANK_POOL})")
    print(f"│ Groq key       : {'✅ set' if GROQ_API_KEY       else '❌ missing'}")
    print(f"│ OpenRouter key : {'✅ set' if OPENROUTER_API_KEY else '❌ missing'}")
    print("└─────────────────────────────────────────────")


print_config()
import time
import llm_config as config


# ─────────────────────────────────────────────
# Startup warnings
# ─────────────────────────────────────────────
if not config.GROQ_API_KEY:
    print("⚠️  GROQ_API_KEY not set — will use OpenRouter directly")
if not config.OPENROUTER_API_KEY:
    print("⚠️  OPENROUTER_API_KEY not set — no fallback available")


# ─────────────────────────────────────────────
# Lazy clients
# ─────────────────────────────────────────────
_groq_client       = None
_openrouter_client = None


def get_groq_client():
    global _groq_client
    if _groq_client is None and config.GROQ_API_KEY:
        from groq import Groq
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None and config.OPENROUTER_API_KEY:
        from openai import OpenAI
        _openrouter_client = OpenAI(
            base_url = "https://openrouter.ai/api/v1",
            api_key  = config.OPENROUTER_API_KEY,
        )
    return _openrouter_client


# ─────────────────────────────────────────────
# Provider calls
# ─────────────────────────────────────────────
def _call_groq(messages: list) -> str:
    client = get_groq_client()
    if not client:
        raise RuntimeError("Groq client not available")

    response = client.chat.completions.create(
        model       = config.GROQ_MODEL,
        messages    = messages,
        temperature = config.GROQ_TEMPERATURE,
        max_tokens  = config.GROQ_MAX_TOKENS,
        reasoning_effort="low",
    )
    return response.choices[0].message.content.strip()


def _call_openrouter(messages: list) -> str:
    client = get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available")

    response = client.chat.completions.create(
        model       = config.OPENROUTER_MODEL,
        messages    = messages,
        temperature = config.OPENROUTER_TEMPERATURE,
        max_tokens  = config.OPENROUTER_MAX_TOKENS,
        extra_headers = {
            "HTTP-Referer": config.OPENROUTER_APP_URL,
            "X-Title":      config.OPENROUTER_APP_NAME,
        },
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
def get_answer(messages: list) -> str:
    """Try Groq → fall back to OpenRouter."""
    last_error = None

    # ── Try Groq ──
    if config.GROQ_API_KEY:
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                print(f"🤖 Groq → {config.GROQ_MODEL}")
                return _call_groq(messages)
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                if "rate" in err_msg or "429" in err_msg:
                    if attempt < config.LLM_MAX_RETRIES - 1:
                        print(f"   ⏳ Rate limited, waiting {config.LLM_RETRY_DELAY}s...")
                        time.sleep(config.LLM_RETRY_DELAY)
                        continue
                print(f"   ❌ Groq failed: {e}")
                break

    # ── Fallback: OpenRouter ──
    if config.OPENROUTER_API_KEY:
        for attempt in range(config.LLM_MAX_RETRIES):
            try:
                print(f"🔄 OpenRouter → {config.OPENROUTER_MODEL}")
                return _call_openrouter(messages)
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                if "rate" in err_msg or "429" in err_msg:
                    if attempt < config.LLM_MAX_RETRIES - 1:
                        print(f"   ⏳ Rate limited, waiting {config.LLM_RETRY_DELAY + 1}s...")
                        time.sleep(config.LLM_RETRY_DELAY + 1)
                        continue
                print(f"   ❌ OpenRouter failed: {e}")
                break

    return f"[LLM ERROR] All providers failed. Last error: {last_error}"


# ─────────────────────────────────────────────
# Web search stub (kept for compatibility)
# ─────────────────────────────────────────────
def get_answer_with_web_search(messages: list) -> dict:
    """No native web search in Groq/OpenRouter — returns regular answer."""
    return {
        "answer":  get_answer(messages),
        "sources": [],
        "found":   False,
    }
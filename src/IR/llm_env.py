"""
llm_env.py
Environment-driven LLM caller with automatic fallback:
  Primary   : Groq
  Fallback  : OpenRouter

Reads all config from .env at project root.
"""

import os
import time
import json
import requests
from typing import List, Dict

from dotenv import load_dotenv

# ── Load .env from project root ─────────────────────────────────────────────
_ENV_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".env")
)
load_dotenv(_ENV_PATH)


# ============== CONFIG ==============

# Groq
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.3"))
GROQ_MAX_TOKENS  = int(os.getenv("GROQ_MAX_TOKENS", "2048"))

# OpenRouter — use a KNOWN-GOOD default (many "free" models get deprecated)
OPENROUTER_API_KEY     = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL       = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))
OPENROUTER_MAX_TOKENS  = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
OPENROUTER_APP_URL     = os.getenv("OPENROUTER_APP_URL", "http://localhost:8000")
OPENROUTER_APP_NAME    = os.getenv("OPENROUTER_APP_NAME", "JaPari")

# Fallback OpenRouter models (tried in order if primary fails with 404)
OPENROUTER_FALLBACK_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]

# Retry settings
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "2"))


# ============== GROQ CALL ==============

def _call_groq(messages: List[Dict], max_tokens: int = None) -> str:
    """Call Groq API. Raises exception on failure."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in .env")

    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package not installed. Run: pip install groq")

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=GROQ_TEMPERATURE,
        max_tokens=max_tokens or GROQ_MAX_TOKENS,
    )
    return response.choices[0].message.content.strip()


# ============== OPENROUTER CALL ==============

def _call_openrouter(messages: List[Dict], model: str, max_tokens: int = None) -> str:
    """Call OpenRouter API with a specific model. Raises exception on failure."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set in .env")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_APP_URL,
        "X-Title": OPENROUTER_APP_NAME,
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": OPENROUTER_TEMPERATURE,
        "max_tokens": max_tokens or OPENROUTER_MAX_TOKENS,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    # Better error handling
    if response.status_code == 404:
        raise RuntimeError(
            f"Model '{model}' not found on OpenRouter (404). "
            f"It may have been deprecated."
        )
    if response.status_code == 401:
        raise RuntimeError(
            "OpenRouter authentication failed (401). Check your API key."
        )
    if response.status_code == 429:
        raise RuntimeError("OpenRouter rate limit hit (429).")

    response.raise_for_status()
    data = response.json()

    if "choices" not in data or not data["choices"]:
        # Sometimes OpenRouter returns errors in the JSON body
        err = data.get("error", {})
        err_msg = err.get("message", str(data))
        raise RuntimeError(f"OpenRouter returned no choices: {err_msg}")

    return data["choices"][0]["message"]["content"].strip()


# ============== SMART CALLER ==============

def get_answer(messages: List[Dict], max_tokens: int = None) -> str:
    """
    Try Groq first (with retries).
    If Groq fails → try OpenRouter with the primary model.
    If that specific model fails (usually 404) → try fallback models.
    """
    errors = []

    # ── Try Groq ─────────────────────────────────────────────────────────────
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            return _call_groq(messages, max_tokens=max_tokens)
        except Exception as e:
            errors.append(f"Groq attempt {attempt+1}: {e}")
            if attempt < LLM_MAX_RETRIES:
                time.sleep(LLM_RETRY_DELAY)

    print(f"[LLM] Groq failed after {LLM_MAX_RETRIES+1} tries, "
          f"falling back to OpenRouter...")

    # ── Try OpenRouter — first the configured model, then fallbacks ─────────
    # Build ordered list: configured model first, then unique fallbacks
    models_to_try = [OPENROUTER_MODEL]
    for m in OPENROUTER_FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    for model in models_to_try:
        print(f"[LLM] Trying OpenRouter model: {model}")
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                return _call_openrouter(messages, model, max_tokens=max_tokens)
            except Exception as e:
                errors.append(f"OpenRouter[{model}] attempt {attempt+1}: {e}")
                if "404" in str(e):
                    # Model doesn't exist — no point retrying same model
                    print(f"[LLM] Model {model} → 404, trying next...")
                    break
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(LLM_RETRY_DELAY)

    return (
        "[LLM ERROR] All providers failed.\n"
        + "\n".join(errors[-6:])
    )
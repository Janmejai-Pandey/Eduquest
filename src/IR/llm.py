import os
import re
import requests
from urllib.parse import urlparse

from google import genai
from google.genai import types


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
from config import GEMINI_API_KEY
MODEL_NAME     = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    print("⚠️  GEMINI_API_KEY not")

client = genai.Client(api_key=GEMINI_API_KEY)


# ─────────────────────────────────────────────
# Helper: Resolve Gemini's redirect URLs → real URLs
# ─────────────────────────────────────────────
_redirect_cache = {}   # cache resolved URLs to avoid repeat requests

def resolve_redirect_url(url: str, timeout: int = 5) -> str:
    """
    Gemini returns vertexaisearch.cloud.google.com redirect URLs.
    Follow them once to get the real destination.
    """
    if not url:
        return ""

    # Only resolve Google redirect URLs
    if "vertexaisearch.cloud.google.com" not in url:
        return url

    # Check cache
    if url in _redirect_cache:
        return _redirect_cache[url]

    try:
        # HEAD request follows redirects but is faster than GET
        resp = requests.head(
            url,
            allow_redirects = True,
            timeout         = timeout,
            headers         = {"User-Agent": "Mozilla/5.0"},
        )
        real_url = resp.url
        _redirect_cache[url] = real_url
        return real_url
    except Exception as e:
        print(f"⚠️  Could not resolve {url[:60]}...: {e}")
        return url   # fallback to original


def get_domain_name(url: str) -> str:
    """Extract clean domain name from URL.
    'https://www.openai.com/blog/gpt-5' → 'openai.com'
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url


# ─────────────────────────────────────────────
# Convert messages → Gemini format
# ─────────────────────────────────────────────
def convert_messages(messages: list[dict]) -> tuple:
    system_instruction = ""
    contents = []

    for msg in messages:
        role    = msg["role"]
        content = msg["content"]

        if role == "system":
            system_instruction += content + "\n\n"
        elif role == "user":
            contents.append({"role": "user",  "parts": [{"text": content}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})

    return system_instruction.strip(), contents


# ─────────────────────────────────────────────
# 1. Regular LLM answer (no web)
# ─────────────────────────────────────────────
def get_answer(messages: list[dict]) -> str:
    try:
        system_instruction, contents = convert_messages(messages)

        config = types.GenerateContentConfig(
            temperature        = 0.3,
            max_output_tokens  = 2048,
            system_instruction = system_instruction if system_instruction else None,
        )

        response = client.models.generate_content(
            model    = MODEL_NAME,
            contents = contents,
            config   = config,
        )

        return response.text.strip() if response.text else "(empty response)"

    except Exception as e:
        return f"[LLM ERROR] {type(e).__name__}: {str(e)}"


# ─────────────────────────────────────────────
# 2. LLM + Google Search grounding
# ─────────────────────────────────────────────
def get_answer_with_web_search(messages: list[dict]) -> dict:
    try:
        system_instruction, contents = convert_messages(messages)

        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        config = types.GenerateContentConfig(
            temperature        = 0.3,
            max_output_tokens  = 2048,
            tools              = [google_search_tool],
            system_instruction = system_instruction if system_instruction else None,
        )

        response = client.models.generate_content(
            model    = MODEL_NAME,
            contents = contents,
            config   = config,
        )

        answer = response.text.strip() if response.text else "(empty response)"

        # ✅ Remove auto-generated sources section from answer
        # (we'll display sources separately in UI)
        answer = re.sub(
            r"##?\s*(Sources?|References?|Citations?)\s*\n.*$",
            "",
            answer,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

        # ✅ Extract + resolve grounding sources
        sources = []
        try:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if chunk.web:
                        original_url = chunk.web.uri or ""
                        real_url     = resolve_redirect_url(original_url)
                        domain       = get_domain_name(real_url)

                        sources.append({
                            "title":  chunk.web.title or domain,
                            "url":    real_url,
                            "domain": domain,
                        })
        except (AttributeError, IndexError):
            pass

        # Dedupe by URL
        seen = set()
        unique_sources = []
        for s in sources:
            if s["url"] not in seen:
                seen.add(s["url"])
                unique_sources.append(s)

        return {
            "answer":  answer,
            "sources": unique_sources,
            "found":   bool(answer and len(unique_sources) > 0),
        }

    except Exception as e:
        return {
            "answer":  f"[WEB SEARCH ERROR] {type(e).__name__}: {str(e)}",
            "sources": [],
            "found":   False,
        }
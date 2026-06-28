from config import GEMINI_API_KEY

from google import genai
from google.genai import types


# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
MODEL_NAME     = "gemini-2.5-flash"   # fast & free

if not GEMINI_API_KEY:
    print("⚠️  GEMINI_API_KEY not set")

client = genai.Client(api_key=GEMINI_API_KEY)


# ─────────────────────────────────────────────
# Convert OpenAI-style messages → Gemini format
# ─────────────────────────────────────────────
def convert_messages(messages: list[dict]) -> tuple:
    """OpenAI format → Gemini format."""
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
            contents.append({"role": "model", "parts": [{"text": content}]})  # Gemini uses "model"

    return system_instruction.strip(), contents


# ─────────────────────────────────────────────
# 1. Regular LLM answer (no web)
# ─────────────────────────────────────────────
def get_answer(messages: list[dict]) -> str:
    """For: summaries, local RAG, follow-ups."""
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
# 2. LLM answer WITH Google Search grounding
# ─────────────────────────────────────────────
def get_answer_with_web_search(messages: list[dict]) -> dict:
    """
    Returns: { 'answer': str, 'sources': [{title, url}], 'found': bool }
    """
    try:
        system_instruction, contents = convert_messages(messages)

        # ✅ Enable Google Search grounding
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

        # Extract grounding sources
        sources = []
        try:
            grounding = response.candidates[0].grounding_metadata
            if grounding and grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if chunk.web:
                        sources.append({
                            "title": chunk.web.title or "",
                            "url":   chunk.web.uri   or "",
                        })
        except (AttributeError, IndexError):
            pass

        return {
            "answer":  answer,
            "sources": sources,
            "found":   bool(answer and len(sources) > 0),
        }

    except Exception as e:
        return {
            "answer":  f"[WEB SEARCH ERROR] {type(e).__name__}: {str(e)}",
            "sources": [],
            "found":   False,
        }
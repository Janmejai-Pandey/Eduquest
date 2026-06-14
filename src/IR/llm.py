import os
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

client = Groq(api_key=GROQ_API_KEY)


def get_answer(messages):
    """Try multiple Groq models in case of rate limit."""
    last_error = None
    for model in GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = str(e)
            continue

    return f"[LLM ERROR] All models failed. Last error: {last_error}"
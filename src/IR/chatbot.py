from search import HybridSearcher
from llm import get_answer

# ── tuneable parameters ──────────────────────────────
TOP_K             = 5     # chunks retrieved per query
MAX_HISTORY_TURNS = 6     # past turns kept in context
SEARCH_ALPHA      = 0.5   # 0 = keyword only | 1 = semantic only
MIN_SCORE         = 0.1   # ignore chunks below this score
# ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a precise and helpful document assistant.
You answer questions strictly based on the provided document excerpts (context).

Rules:
1. Use ONLY the context provided below to answer.
2. If the answer is not found in the context, respond exactly:
   "I could not find relevant information in the provided documents."
3. Always mention the source file and location (page/slide) of your answer.
4. Be factual, structured, and concise.
5. If multiple sources support the answer, mention all of them.
6. For follow-up questions, use both the context and conversation history.
7. If asked to summarize, provide bullet points.
"""


class RAGChatbot:
    def __init__(self):
        print("Loading search index...")
        self.searcher = HybridSearcher()
        self.chat_history = []
        print("Chatbot ready.\n")

    # ── retrieval ────────────────────────────────────
    def retrieve_context(self, query):
        """Retrieve top-k chunks and format as context block."""
        results = self.searcher.search(query, top_k=TOP_K, alpha=SEARCH_ALPHA)

        # filter very low scoring results
        results = [r for r in results if r["score"] >= MIN_SCORE]

        if not results:
            return "", []

        parts = []
        for i, r in enumerate(results, start=1):
            parts.append(
                f"[Excerpt {i}]\n"
                f"File     : {r['source_file']}\n"
                f"Location : {r['location']}\n"
                f"Score    : {r['score']}\n"
                f"Content  :\n{r['text']}\n"
            )

        return "\n" + "-" * 50 + "\n".join(parts) + "-" * 50, results

    # ── prompt builder ───────────────────────────────
    def build_messages(self, user_query, context_str):
        """Build full message list for LLM."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # recent history only
        recent = self.chat_history[-(MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)

        # user message with context
        user_msg = (
            f"Here are the relevant excerpts from the documents:\n"
            f"{context_str}\n\n"
            f"Based on the above excerpts, answer this question:\n"
            f"{user_query}"
        )
        messages.append({"role": "user", "content": user_msg})
        return messages

    # ── main chat ────────────────────────────────────
    def chat(self, user_query):
        """
        Returns:
            answer  (str)
            sources (list of result dicts)
        """
        user_query = user_query.strip()
        if not user_query:
            return "Please ask a question.", []

        # Step 1: retrieve
        context_str, sources = self.retrieve_context(user_query)
        if not context_str:
            return (
                "I could not find relevant information in the documents "
                "for your query. Try different keywords.",
                [],
            )

        # Step 2: build messages
        messages = self.build_messages(user_query, context_str)

        # Step 3: LLM answer
        answer = get_answer(messages)

        # Step 4: update history (store plain query, not the context-injected version)
        self.chat_history.append({"role": "user",      "content": user_query})
        self.chat_history.append({"role": "assistant",  "content": answer})

        return answer, sources

    def reset_history(self):
        self.chat_history = []
        print("Conversation history cleared.\n")
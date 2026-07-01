import os
import re
import sys

from search import HybridSearcher
from llm import get_answer, get_answer_with_web_search

from config import all_imports
all_imports()
try:
    from summariser import (           
        load_gdrive_links,
        get_subjects,
        get_lecture_files,
        summarise_single_lecture,
        summarise_lecture_series,
        SEM_FOLDERS,
    )
    SUMMARIZER_AVAILABLE = True
    print(f"✅ Summarizer loaded — {len(SEM_FOLDERS)} sem folder(s)")
except Exception as e:
    import traceback
    print(f"⚠️  Summarizer failed: {e}")
    traceback.print_exc()
    SUMMARIZER_AVAILABLE = False


# ═════════════════════════════════════════════════════════════
# WEB SEARCH STATUS
# ═════════════════════════════════════════════════════════════
WEB_SEARCH_AVAILABLE = True
print("✅ Gemini web search grounding enabled")


# ═════════════════════════════════════════════════════════════
# TUNEABLE PARAMETERS
# ═════════════════════════════════════════════════════════════
TOP_K               = 5
MAX_HISTORY_TURNS   = 6
SEARCH_ALPHA        = 0.5
MIN_SCORE           = 0.1
WEB_FALLBACK_SCORE  = 0.3
ENABLE_WEB_FALLBACK = True

# ═════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═════════════════════════════════════════════════════════════
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


WEB_SYSTEM_PROMPT = """You are a helpful AI assistant with access to Google Search.

Rules:
1. Use web information to answer accurately.
2. Use clear Markdown formatting.
3. Be concise but thorough.
4. DO NOT include a "Sources" or "References" section — those will be displayed separately.
5. DO NOT include raw URLs in your answer.
6. End with: "ℹ️ This answer was generated using Google Search."
"""


GENERAL_KNOWLEDGE_PROMPT = """You are a helpful AI assistant.
The user asked something not found in their local documents
and web search didn't return useful results.

Rules:
1. Answer based on your general knowledge.
2. Be honest if you're unsure.
3. Use clean Markdown formatting.
4. End with: "ℹ️ This answer is based on general knowledge."
"""


# ═════════════════════════════════════════════════════════════
# INTENT DETECTION & PARSING
# ═════════════════════════════════════════════════════════════

SUMMARY_KEYWORDS = [
    "summari[sz]e", "summary of", "summarise", "summarize",
    "give me a summary", "give summary", "make summary",
    "tl;dr", "quick notes", "revise",
]

SUMMARY_PATTERN = re.compile(
    r"\b(?:" + "|".join(SUMMARY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

SEM_PATTERN = re.compile(
    r"\b(?:sem(?:ester)?|sm)\s*[-:]?\s*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s+sem(?:ester)?\b",
    re.IGNORECASE,
)

LECTURE_NUM_PATTERN = re.compile(
    r"\b(?:lec(?:ture)?|lesson|chapter|ch|class)\s*[-:#]?\s*(\d+)\b",
    re.IGNORECASE,
)

ALL_PATTERN = re.compile(
    r"\b(?:all|every|complete|whole|entire|full|each)\b\s*(?:lec(?:ture)?s?|lessons?|chapters?|classes?)?",
    re.IGNORECASE,
)


# Follow-up patterns — user wants to modify the LAST summary
BRIEF_KEYWORDS = [
    "brief", "short", "shorter", "concise", "tl;dr", "tldr",
    "in points", "bullet", "key points only", "just the points",
    "simplify", "simpler", "easier", "in simple words",
    "explain again", "rephrase", "in one line", "one paragraph",
    "give the gist", "main points", "highlights only",
    "expand", "elaborate", "more detail", "with examples",
]

FOLLOWUP_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in BRIEF_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def detect_summary_intent(query: str) -> bool:
    """Check if user is asking for a NEW summary."""
    return bool(SUMMARY_PATTERN.search(query))


def is_followup_on_summary(query: str) -> bool:
    """Detect if user wants to modify the PREVIOUS summary."""
    query_lower = query.lower().strip()

    # Short queries with follow-up keywords
    if len(query_lower.split()) <= 8 and FOLLOWUP_PATTERN.search(query_lower):
        return True

    # Specific short phrases
    short_followups = [
        "shorten it", "make shorter", "shorter please",
        "in brief", "give brief", "brief version",
        "tldr", "tl;dr", "summarize that",
        "explain simply", "simpler version",
        "key points", "main points", "highlights",
        "give in brief", "more concise",
    ]
    return query_lower in short_followups or any(p in query_lower for p in short_followups)


def extract_semester(query: str) -> str | None:
    """Extract semester from query: 'sem 3', '3rd sem', 'semester 4'."""
    m = SEM_PATTERN.search(query)
    if not m:
        return None
    return m.group(1) or m.group(2)


def extract_lecture_numbers(query: str) -> list:
    """Extract lecture numbers: 'lec 1', 'lecture 2 and 3'."""
    return [int(n) for n in LECTURE_NUM_PATTERN.findall(query)]


def is_all_lectures(query: str) -> bool:
    """Check if user wants ALL lectures."""
    return bool(ALL_PATTERN.search(query))


def find_subject_match(query: str, available_subjects: list) -> str | None:
    """Find which subject the user is referring to (fuzzy match)."""
    query_lower = query.lower()

    # Direct match
    for subject in available_subjects:
        if subject.lower() in query_lower:
            return subject

    # Acronym match
    common_acronyms = {
        "dsa":    ["data structure"],
        "dbms":   ["database management"],
        "os":     ["operating system"],
        "oop":    ["object oriented", "object-oriented"],
        "cn":     ["computer network"],
        "toc":    ["theory of computation"],
        "ml":     ["machine learning"],
        "ai":     ["artificial intelligence"],
        "se":     ["software engineering"],
        "coa":    ["computer organization", "computer architecture"],
        "ada":    ["algorithm design", "algorithm analysis"],
        "daa":    ["design and analysis of algorithm"],
        "ds":     ["data structure"],
        "math":   ["mathematics", "mathematical"],
        "stats":  ["statistics", "statistical"],
        "prob":   ["probability"],
        "upl":    ["unix programming"],
        "ecs":    ["economics"],
    }

    for acronym, keywords in common_acronyms.items():
        if re.search(r"\b" + acronym + r"\b", query_lower):
            for subject in available_subjects:
                if any(kw in subject.lower() for kw in keywords):
                    return subject

    # Partial word match
    query_words = set(re.findall(r"\b[a-z]{3,}\b", query_lower))
    best_match  = None
    best_score  = 0
    for subject in available_subjects:
        subject_words = set(re.findall(r"\b[a-z]{3,}\b", subject.lower()))
        common = query_words & subject_words
        if len(common) > best_score:
            best_score = len(common)
            best_match = subject

    return best_match if best_score > 0 else None


def parse_summary_request(query: str) -> dict:
    """Parse user query and extract summary parameters."""
    return {
        "is_summary":   detect_summary_intent(query),
        "semester":     extract_semester(query),
        "lecture_nums": extract_lecture_numbers(query),
        "all_lectures": is_all_lectures(query),
    }


# ═════════════════════════════════════════════════════════════
# CHATBOT CLASS
# ═════════════════════════════════════════════════════════════

class RAGChatbot:
    def __init__(self):
        print("Loading search index...")
        self.searcher = HybridSearcher()
        self.chat_history = []

        # Remember last summary for follow-ups
        self.last_summary      = None
        self.last_summary_meta = None

        print("Chatbot ready.\n")

    # ─────────────────────────────────────────────
    # LOCAL RAG RETRIEVAL
    # ─────────────────────────────────────────────
    def retrieve_context(self, query):
        """Retrieve top-k chunks and format as context block."""
        results = self.searcher.search(query, top_k=TOP_K, alpha=SEARCH_ALPHA)
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

    def build_messages(self, user_query, context_str):
        """Build full message list for LLM."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent = self.chat_history[-(MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)

        user_msg = (
            f"Here are the relevant excerpts from the documents:\n"
            f"{context_str}\n\n"
            f"Based on the above excerpts, answer this question:\n"
            f"{user_query}"
        )
        messages.append({"role": "user", "content": user_msg})
        return messages

    # ═════════════════════════════════════════════════
    # WEB SEARCH (Gemini grounding)
    # ═════════════════════════════════════════════════
    def handle_web_search(self, user_query: str) -> tuple[str, list]:
        """Use Gemini's built-in Google Search."""

        if not ENABLE_WEB_FALLBACK:
            return self.handle_general_knowledge(user_query)

        print(f"🌐 Gemini searching Google for: {user_query}")

        messages = [{"role": "system", "content": WEB_SYSTEM_PROMPT}]
        recent = self.chat_history[-(MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_query})

        result = get_answer_with_web_search(messages)

        if not result["found"]:
            return self.handle_general_knowledge(user_query)

        answer  = result["answer"]
        sources = result["sources"]

        # ✅ Build numbered sources block (markdown)
        sources_md = "\n\n---\n\n### 🔗 Sources\n\n"
        for i, s in enumerate(sources, 1):
            domain = s.get("domain", "link")
            title  = s.get("title",  domain) or domain
            url    = s["url"]
            # Display: "1. [Title](url) — domain.com"
            sources_md += f"{i}. [{title}]({url}) — *{domain}*\n"

        # ✅ Convert sources for sidebar/sources panel
        pseudo_sources = []
        for i, s in enumerate(sources, 1):
            pseudo_sources.append({
                "source_file":    f"🌐 {s.get('title') or s.get('domain') or f'Source {i}'}",
                "location":       s.get("domain", "Web"),
                "score":          0.5,
                "bm25_score":     0.0,
                "semantic_score": 0.0,
                "text":           f"From {s.get('domain', 'web')}",
                "url":            s["url"],
                "subject":        "Web",
                "semester":       "",
                "is_web":         True,
            })

        # ✅ Compose final answer
        final_answer = (
            f"> 🌐 _Not found in local docs — searched Google._\n\n"
            f"{answer}"
            f"{sources_md}"
        )

        return final_answer, pseudo_sources

        final_answer = (
            f"> 🌐 _Not found in local docs — searched Google._\n\n"
            f"{answer}"
        )

        return final_answer, pseudo_sources

    # ═════════════════════════════════════════════════
    # GENERAL KNOWLEDGE FALLBACK
    # ═════════════════════════════════════════════════
    def handle_general_knowledge(self, user_query: str) -> tuple[str, list]:
        """Last resort: use LLM's own knowledge."""
        print(f"🧠 General knowledge for: {user_query}")

        messages = [{"role": "system", "content": GENERAL_KNOWLEDGE_PROMPT}]
        recent = self.chat_history[-(MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_query})

        answer = get_answer(messages)

        final_answer = (
            f"> 🧠 _Not found in docs or web — answering from general knowledge._\n\n"
            f"{answer}"
        )

        return final_answer, []

    # ═════════════════════════════════════════════════
    # SUMMARY FOLLOW-UP HANDLER
    # ═════════════════════════════════════════════════
    def handle_summary_followup(self, query: str) -> tuple[str | None, list]:
        """Modify or rephrase the previous summary based on user's follow-up."""

        if not self.last_summary or not self.last_summary_meta:
            return None, []

        meta = self.last_summary_meta

        followup_prompt = f"""You are reformatting a previous lecture summary based on user feedback.

ORIGINAL SUMMARY:
{self.last_summary}

USER'S REQUEST:
"{query}"

INSTRUCTIONS:
- Reformat the summary above according to the user's request.
- Keep all important facts, formulae, and concepts intact.
- If user wants "brief" or "short" → reduce to key points only (5-10 bullets).
- If user wants "in points" or "bullets" → convert to clean bullet list.
- If user wants "simpler" → use easier language and shorter sentences.
- If user wants "one paragraph" → write as a single flowing paragraph.
- If user wants "expand" or "more detail" → elaborate with examples.
- Keep proper Markdown formatting (use ## for headings, - for bullets, **bold** for emphasis).
- Do NOT add any apology or preamble. Just give the reformatted content directly.
"""

        messages = [
            {"role": "system", "content": "You are an expert at reformatting academic content."},
            {"role": "user",   "content": followup_prompt},
        ]

        new_content = get_answer(messages)

        header = (
            f"# 📝 {meta['subject']} (Sem {meta['sem']}) — Reformatted\n\n"
            f"_Based on your previous summary, reformatted as requested._\n\n"
            f"---\n\n"
        )

        footer = "\n\n---\n\n## 🔗 Source Lectures\n\n"
        for link in meta["links"]:
            footer += f"- [{link['name']}]({link['url']})\n"

        full_response = header + new_content + footer

        # Update last_summary so chained follow-ups work
        self.last_summary = new_content

        pseudo_sources = [
            {
                "source_file":    link["name"],
                "location":       f"Sem {meta['sem']} / {meta['subject']}",
                "score":          1.0,
                "bm25_score":     1.0,
                "semantic_score": 1.0,
                "text":           f"Lecture from {meta['subject']}.",
                "url":            link["url"],
                "subject":        meta["subject"],
                "semester":       meta["sem"],
            }
            for link in meta["links"]
        ]

        return full_response, pseudo_sources

    # ═════════════════════════════════════════════════
    # SUMMARY REQUEST HANDLER
    # ═════════════════════════════════════════════════
    def handle_summary_request(self, query: str) -> tuple[str, list]:
        """Handle a new summarization request."""

        if not SUMMARIZER_AVAILABLE:
            return (
                "❌ Summarization feature is not available. "
                "Please check that summariser.py is in src/IR/.",
                [],
            )

        params = parse_summary_request(query)

        # ── 1. Determine semester ────────────────
        sem = params["semester"]
        if not sem:
            for msg in reversed(self.chat_history):
                if msg["role"] == "user":
                    prev_sem = extract_semester(msg["content"])
                    if prev_sem:
                        sem = prev_sem
                        break

        if not sem:
            available = [s for s in SEM_FOLDERS.keys()]
            return (
                f"📚 To summarize lectures, please specify the semester.\n\n"
                f"**Available:** {', '.join(available)}\n\n"
                f"**Example:** *\"Summarize Lecture 1 of DSA from sem 3\"*",
                [],
            )

        # ── 2. Load links + get subjects ─────────
        try:
            links              = load_gdrive_links(sem)
            available_subjects = get_subjects(links)
        except FileNotFoundError as e:
            return f"❌ {str(e)}", []

        # ── 3. Find subject ──────────────────────
        subject = find_subject_match(query, available_subjects)

        if not subject:
            return (
                f"📚 I couldn't identify which subject you want to summarize in semester {sem}.\n\n"
                f"**Available subjects:**\n"
                + "\n".join(f"• {s}" for s in available_subjects)
                + f"\n\n**Example:** *\"Summarize Lecture 1 of {available_subjects[0]} sem {sem}\"*",
                [],
            )

        # ── 4. Get lectures ──────────────────────
        lectures = get_lecture_files(links, subject)
        if not lectures:
            return f"❌ No lectures found for **{subject}** in semester {sem}.", []

        # ── 5. Determine which lectures ──────────
        lecture_nums = params["lecture_nums"]
        want_all     = params["all_lectures"]

        if want_all:
            selected = lectures
            mode     = "series"
        elif lecture_nums:
            selected = []
            for num in lecture_nums:
                match = self._find_lecture_by_number(lectures, num)
                if match:
                    selected.append(match)

            if not selected:
                lec_list = "\n".join(
                    f"• Lecture {i+1}: {l.get('item_name', '')}"
                    for i, l in enumerate(lectures[:10])
                )
                return (
                    f"❌ Couldn't find lecture(s) {lecture_nums} in **{subject}**.\n\n"
                    f"**Available:**\n{lec_list}",
                    [],
                )
            mode = "single" if len(selected) == 1 else "series"
        else:
            lec_list = "\n".join(
                f"{i+1}. {l.get('item_name', '')}"
                for i, l in enumerate(lectures[:15])
            )
            return (
                f"📚 Found **{len(lectures)} lectures** in **{subject}** (Sem {sem}):\n\n"
                f"{lec_list}\n\n"
                f"**Tell me which one:**\n"
                f"• *\"Summarize lecture 1 of {subject}\"*\n"
                f"• *\"Summarize all lectures of {subject}\"*",
                [],
            )

        # ── 6. Run summarization ─────────────────
        try:
            if mode == "single":
                summary, success, view_url = summarise_single_lecture(sem, selected[0])
                lecture_links = [{
                    "name": selected[0].get("item_name", ""),
                    "url":  view_url,
                }]
            else:
                summary, success, lecture_links = summarise_lecture_series(
                    sem, selected, subject
                )

            if not success:
                return f"❌ Could not generate summary:\n\n{summary}", []

            # Store for follow-up requests
            self.last_summary      = summary
            self.last_summary_meta = {
                "sem":     sem,
                "subject": subject,
                "links":   lecture_links,
                "mode":    mode,
            }

            header = (
                f"# 📝 Summary: {subject} (Sem {sem})\n\n"
                f"**Mode:** {'Single Lecture' if mode == 'single' else f'Series of {len(selected)} Lectures'}\n\n"
            )

            footer = "\n\n---\n\n## 🔗 Source Lectures\n\n"
            for link in lecture_links:
                footer += f"- [{link['name']}]({link['url']})\n"

            full_response = header + summary + footer

            pseudo_sources = [
                {
                    "source_file":    link["name"],
                    "location":       f"Sem {sem} / {subject}",
                    "score":          1.0,
                    "bm25_score":     1.0,
                    "semantic_score": 1.0,
                    "text":           f"Lecture from {subject}.",
                    "url":            link["url"],
                    "subject":        subject,
                    "semester":       sem,
                }
                for link in lecture_links
            ]

            return full_response, pseudo_sources

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"❌ Error: {str(e)}", []

    def _find_lecture_by_number(self, lectures: list, num: int) -> dict | None:
        """Find a lecture matching a given number."""
        patterns = [
            rf"\b(?:lec(?:ture)?|lesson|chapter|ch)\s*[-_#]?\s*0?{num}\b",
            rf"\b0?{num}\b",
        ]
        for pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for lec in lectures:
                if regex.search(lec.get("item_name", "")):
                    return lec
        if 1 <= num <= len(lectures):
            return lectures[num - 1]
        return None

    # ═════════════════════════════════════════════════
    # MAIN CHAT METHOD — ROUTING
    # ═════════════════════════════════════════════════
    def chat(self, user_query):
        """
        Routing order:
          1. Summary follow-up   → reformat last summary
          2. New summary request → fetch & summarize
          3. Local RAG search    → answer from docs
          4. Web search fallback → Gemini's Google Search
          5. General knowledge   → LLM only (last resort)
        """
        user_query = user_query.strip()
        if not user_query:
            return "Please ask a question.", []

        # ── 1. Summary follow-up ──
        if self.last_summary and is_followup_on_summary(user_query):
            print(f"🔄 Summary follow-up: {user_query}")
            answer, sources = self.handle_summary_followup(user_query)
            if answer:
                self._save_history(user_query, answer)
                return answer, sources

        # ── 2. New summary request ──
        if detect_summary_intent(user_query):
            print(f"🎯 Summary request: {user_query}")
            answer, sources = self.handle_summary_request(user_query)
            self._save_history(user_query, answer)
            return answer, sources

        # ── 3. Local RAG search ──
        print(f"🔍 Local search: {user_query}")
        context_str, sources = self.retrieve_context(user_query)

        best_score     = max((r["score"] for r in sources), default=0)
        has_good_local = context_str and best_score >= WEB_FALLBACK_SCORE

        if has_good_local:
            print(f"   ✅ Good local results (best: {best_score:.2f})")
            messages = self.build_messages(user_query, context_str)
            answer   = get_answer(messages)

            # If LLM says "not found" → trigger web fallback
            not_found_signals = [
                "could not find",
                "not find relevant",
                "no relevant information",
                "i don't have",
                "no information about",
                "not mentioned in",
                "do not contain",
            ]
            if any(sig in answer.lower() for sig in not_found_signals):
                print(f"   ⚠️  LLM said 'not found' → web fallback")
                answer, sources = self.handle_web_search(user_query)
        else:
            if best_score > 0:
                print(f"   ⚠️  Weak local results ({best_score:.2f}) → web")
            else:
                print(f"   ⚠️  No local results → web")
            answer, sources = self.handle_web_search(user_query)

        self._save_history(user_query, answer)
        return answer, sources

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _save_history(self, user_query: str, answer: str):
        """Save user + bot turn to history."""
        self.chat_history.append({"role": "user",      "content": user_query})
        self.chat_history.append({"role": "assistant", "content": answer})

    def reset_history(self):
        """Clear all chat history including summary memory."""
        self.chat_history      = []
        self.last_summary      = None
        self.last_summary_meta = None
        print("Conversation history cleared.\n")
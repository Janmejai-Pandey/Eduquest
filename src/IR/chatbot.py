import re
import llm_config as config
from search import HybridSearcher
from llm    import get_answer, get_answer_with_web_search


# ═════════════════════════════════════════════════════════════
# IMPORTS — Summarizer (optional)
# ═════════════════════════════════════════════════════════════
try:
    from summariser_indexed import (
        load_gdrive_links,
        get_subjects,
        get_lecture_files,
        summarise_single_lecture,
        summarise_lecture_series,
        SEM_FOLDERS,
    )
    SUMMARIZER_AVAILABLE = True
    print(f"✅ Indexed summariser loaded — {len(SEM_FOLDERS)} sem folder(s)")
except Exception as e:
    print(f"⚠️  Summarizer failed: {e}")
    SUMMARIZER_AVAILABLE = False


WEB_SEARCH_AVAILABLE = config.ENABLE_WEB_FALLBACK


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
5. For follow-up questions, use both the context and conversation history.
6. If asked to summarize, provide bullet points.
"""


WEB_SYSTEM_PROMPT = """You are a helpful AI assistant.
The user asked a question that wasn't found in local documents.

Rules:
1. Answer using your general knowledge.
2. Be factual and concise.
3. Format your response in clean Markdown.
4. End with: "ℹ️ This answer is not from your local documents."
"""


GENERAL_KNOWLEDGE_PROMPT = """You are a helpful AI assistant.
The user asked something not found in their local documents.

Rules:
1. Answer based on your general knowledge.
2. Be honest if you're unsure.
3. Use clean Markdown formatting.
4. End with: "ℹ️ This answer is based on general knowledge."
"""


# ═════════════════════════════════════════════════════════════
# INTENT DETECTION
# ═════════════════════════════════════════════════════════════

# Summary keywords
SUMMARY_KEYWORDS = [
    "summari[sz]e", "summary of", "summarise", "summarize",
    "give me a summary", "give summary", "make summary",
    "make notes", "quick notes", "revision notes", "revise",
    "tl;dr", "explain briefly", "brief overview",
]

SUMMARY_PATTERN = re.compile(
    r"\b(?:" + "|".join(SUMMARY_KEYWORDS) + r")\b", re.IGNORECASE,
)

# Semester patterns
SEM_PATTERN = re.compile(
    r"\b(?:sem(?:ester)?|sm)\s*[-:]?\s*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s+sem(?:ester)?\b",
    re.IGNORECASE,
)

# Lecture number patterns
LECTURE_NUM_PATTERN = re.compile(
    r"\b(?:lec(?:ture)?|lesson|chapter|ch|class)\s*[-:#]?\s*(\d+)\b",
    re.IGNORECASE,
)

# All lectures pattern
ALL_PATTERN = re.compile(
    r"\b(?:all|every|complete|whole|entire|full|each)\b\s*(?:lec(?:ture)?s?|lessons?|chapters?|classes?)?",
    re.IGNORECASE,
)


# Clarification patterns (short user replies filling in missing info)
CLARIFICATION_PATTERNS = [
    # "of sem 3", "from sem 4", "in semester 3"
    re.compile(r"\b(?:of|from|in|for)?\s*sem(?:ester)?\s*\d+", re.IGNORECASE),
    # "sem 3", "3rd sem"
    re.compile(r"\b\d+(?:st|nd|rd|th)?\s*sem(?:ester)?\b", re.IGNORECASE),
    re.compile(r"\bsem(?:ester)?\s*[-:]?\s*\d+\b", re.IGNORECASE),
    # "of DBMS", "for DSA" — subject fill-in
    re.compile(r"\b(?:of|for|from|in)\s+[A-Za-z][A-Za-z\s&/-]{1,40}$", re.IGNORECASE),
    # Just a number "3", "4"
    re.compile(r"^\s*\d+\s*$"),
    # "lecture 3", "lec 5", "all"
    re.compile(r"^\s*(?:lec(?:ture)?|all|every)\s*\d*\s*$", re.IGNORECASE),
]


# Follow-up on completed summary
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
    return bool(SUMMARY_PATTERN.search(query))


def is_clarification_response(query: str) -> bool:
    """Detect if short user message is providing missing summary info."""
    q = query.strip()
    if not q or len(q.split()) > 8:
        return False
    return any(p.search(q) for p in CLARIFICATION_PATTERNS)


def is_followup_on_summary(query: str) -> bool:
    q = query.lower().strip()
    if len(q.split()) <= 8 and FOLLOWUP_PATTERN.search(q):
        return True
    short_followups = [
        "shorten it", "make shorter", "shorter please",
        "in brief", "give brief", "brief version",
        "tldr", "tl;dr", "summarize that",
        "explain simply", "simpler version",
        "key points", "main points", "highlights",
        "give in brief", "more concise",
    ]
    return q in short_followups or any(p in q for p in short_followups)


def extract_semester(query: str):
    m = SEM_PATTERN.search(query)
    if not m:
        return None
    return m.group(1) or m.group(2)


def extract_lecture_numbers(query: str) -> list:
    return [int(n) for n in LECTURE_NUM_PATTERN.findall(query)]


def is_all_lectures(query: str) -> bool:
    return bool(ALL_PATTERN.search(query))


def find_subject_match(query: str, available_subjects: list):
    q = query.lower()

    # Direct match
    for subject in available_subjects:
        if subject.lower() in q:
            return subject

    # Acronyms
    common_acronyms = {
        "dsa":    ["data structure"],
        "dbms":   ["database management", "database"],
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
        if re.search(r"\b" + acronym + r"\b", q):
            for subject in available_subjects:
                if any(kw in subject.lower() for kw in keywords):
                    return subject

    # Partial word overlap
    query_words = set(re.findall(r"\b[a-z]{3,}\b", q))
    best_match, best_score = None, 0
    for subject in available_subjects:
        subject_words = set(re.findall(r"\b[a-z]{3,}\b", subject.lower()))
        common = query_words & subject_words
        if len(common) > best_score:
            best_score = len(common)
            best_match = subject

    return best_match if best_score > 0 else None


def parse_summary_request(query: str) -> dict:
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

        # Remember last completed summary (for follow-ups like "give in brief")
        self.last_summary      = None
        self.last_summary_meta = None

        # Remember incomplete summary request (for progressive fill-in)
        # Structure: {semester, subject, lecture_nums, all_lectures, raw_query}
        self.pending_summary = None

        print("Chatbot ready.\n")

    # ─────────────────────────────────────────────
    # LOCAL RAG RETRIEVAL
    # ─────────────────────────────────────────────
    def retrieve_context(self, query):
        results = self.searcher.search(query)
        results = [r for r in results if r["score"] >= config.SEARCH_MIN_SCORE]

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
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        recent = self.chat_history[-(config.MAX_HISTORY_TURNS * 2):]
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
    # WEB / GENERAL KNOWLEDGE FALLBACKS
    # ═════════════════════════════════════════════════
    def handle_web_search(self, user_query):
        if not config.ENABLE_WEB_FALLBACK:
            return self.handle_general_knowledge(user_query)

        print(f"🌐 Web search: {user_query}")

        messages = [{"role": "system", "content": WEB_SYSTEM_PROMPT}]
        recent = self.chat_history[-(config.MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_query})

        result = get_answer_with_web_search(messages)
        answer = result.get("answer", "")

        final_answer = (
            f"> 🌐 _Not found in local docs._\n\n"
            f"{answer}"
        )
        return final_answer, []

    def handle_general_knowledge(self, user_query):
        print(f"🧠 General knowledge: {user_query}")

        messages = [{"role": "system", "content": GENERAL_KNOWLEDGE_PROMPT}]
        recent = self.chat_history[-(config.MAX_HISTORY_TURNS * 2):]
        messages.extend(recent)
        messages.append({"role": "user", "content": user_query})

        answer = get_answer(messages)

        final_answer = (
            f"> 🧠 _Not found in docs — answering from general knowledge._\n\n"
            f"{answer}"
        )
        return final_answer, []

    # ═════════════════════════════════════════════════
    # SUMMARY FOLLOW-UP (reformat last summary)
    # ═════════════════════════════════════════════════
    def handle_summary_followup(self, query):
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
- If user wants "brief" or "short" → reduce to key points only.
- If user wants "in points" → convert to clean bullet list.
- If user wants "simpler" → use easier language.
- If user wants "expand" or "more detail" → elaborate with examples.
- Keep proper Markdown formatting.
- Do NOT add any apology or preamble.
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
    # SUMMARY REQUEST (with progressive fill-in)
    # ═════════════════════════════════════════════════
    def handle_summary_request(self, query, is_continuation=False):
        """
        Handle summarization requests.
        If info is missing, remembers what we have and asks for the rest.
        On continuation, merges with pending info.
        """
        if not SUMMARIZER_AVAILABLE:
            return (
                "❌ Summarization feature is not available. "
                "Please check that summariser.py is in src/IR/.",
                [],
            )

        # ── Parse the current query ──
        current = parse_summary_request(query)

        # ── Merge with pending if continuing ──
        if is_continuation and self.pending_summary:
            merged = dict(self.pending_summary)
            if current["semester"]:      merged["semester"]     = current["semester"]
            if current["lecture_nums"]:  merged["lecture_nums"] = current["lecture_nums"]
            if current["all_lectures"]:  merged["all_lectures"] = True
            merged["raw_query"] = (self.pending_summary.get("raw_query", "") + " " + query).strip()
        else:
            merged = {
                "semester":     current["semester"],
                "lecture_nums": current["lecture_nums"],
                "all_lectures": current["all_lectures"],
                "subject":      None,
                "raw_query":    query,
            }

        # ── Try to find semester from history if still missing ──
        sem = merged["semester"]
        if not sem:
            for msg in reversed(self.chat_history):
                if msg["role"] == "user":
                    prev_sem = extract_semester(msg["content"])
                    if prev_sem:
                        sem = prev_sem
                        break

        # ── If no semester, save and ask ──
        if not sem:
            self.pending_summary = merged
            available = list(SEM_FOLDERS.keys())
            return (
                f"📚 To summarize lectures, please specify the semester.\n\n"
                f"**Available:** {', '.join(available)}\n\n"
                f"**Example:** *\"sem 3\"* or *\"of sem 4\"*",
                [],
            )

        merged["semester"] = sem

        # ── Load subjects for this sem ──
        try:
            links              = load_gdrive_links(sem)
            available_subjects = get_subjects(links)
        except FileNotFoundError as e:
            self.pending_summary = None
            return f"❌ {str(e)}", []

        # ── Find subject ──
        subject = merged.get("subject") or find_subject_match(merged["raw_query"], available_subjects)

        # ── If no subject, save and ask ──
        if not subject:
            self.pending_summary = merged
            subject_list = "\n".join(f"• {s}" for s in available_subjects)
            return (
                f"📚 Which subject in **Semester {sem}**?\n\n"
                f"**Available:**\n{subject_list}\n\n"
                f"**Example:** *\"{available_subjects[0]}\"*",
                [],
            )

        merged["subject"] = subject

        # ── Get lectures for subject ──
        lectures = get_lecture_files(links, subject)
        if not lectures:
            self.pending_summary = None
            return f"❌ No lectures found for **{subject}** in semester {sem}.", []

        # ── Determine which lectures ──
        lecture_nums = merged["lecture_nums"]
        want_all     = merged["all_lectures"]

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
                self.pending_summary = None
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
            # No lecture specified — save and ask
            self.pending_summary = merged
            lec_list = "\n".join(
                f"{i+1}. {l.get('item_name', '')}"
                for i, l in enumerate(lectures[:15])
            )
            return (
                f"📚 Found **{len(lectures)} lectures** in **{subject}** (Sem {sem}):\n\n"
                f"{lec_list}\n\n"
                f"**Tell me which one:**\n"
                f"• *\"lecture 1\"* or *\"lec 3\"*\n"
                f"• *\"all lectures\"* for full series",
                [],
            )

        # ✅ All info available — clear pending
        self.pending_summary = None

        # ── Run summarization ──
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
            self.pending_summary = None
            return f"❌ Error: {str(e)}", []

    def _find_lecture_by_number(self, lectures, num):
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
    # MAIN CHAT ROUTER
    # ═════════════════════════════════════════════════
    def chat(self, user_query):
        """
        Routing order:
          1. Continue pending summary (clarification response)
          2. Follow-up on last summary (reformat)
          3. New summary request
          4. Local RAG search
          5. Web/general knowledge fallback
        """
        user_query = user_query.strip()
        if not user_query:
            return "Please ask a question.", []

        # ── 1. Continue pending summary ──
        if self.pending_summary and is_clarification_response(user_query):
            print(f"🔗 Continuing pending summary: {user_query}")
            answer, sources = self.handle_summary_request(user_query, is_continuation=True)
            self._save_history(user_query, answer)
            return answer, sources

        # ── 2. Follow-up on completed summary ──
        if self.last_summary and is_followup_on_summary(user_query):
            print(f"🔄 Summary follow-up: {user_query}")
            answer, sources = self.handle_summary_followup(user_query)
            if answer:
                self._save_history(user_query, answer)
                return answer, sources

        # ── 3. New summary request ──
        if detect_summary_intent(user_query):
            print(f"🎯 Summary request: {user_query}")
            # Clear any old pending state (fresh request)
            self.pending_summary = None
            answer, sources = self.handle_summary_request(user_query)
            self._save_history(user_query, answer)
            return answer, sources

        # ── 4. Local RAG search ──
        print(f"🔍 Local search: {user_query}")
        context_str, sources = self.retrieve_context(user_query)

        best_score     = max((r["score"] for r in sources), default=0)
        has_good_local = context_str and best_score >= config.WEB_FALLBACK_SCORE

        if has_good_local:
            print(f"   ✅ Good local results (best: {best_score:.2f})")
            messages = self.build_messages(user_query, context_str)
            answer = get_answer(messages)

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
                print(f"   ⚠️  LLM said 'not found' → fallback")
                answer, sources = self.handle_web_search(user_query)
        else:
            if best_score > 0:
                print(f"   ⚠️  Weak local ({best_score:.2f}) → fallback")
            else:
                print(f"   ⚠️  No local results → fallback")
            answer, sources = self.handle_web_search(user_query)

        self._save_history(user_query, answer)
        return answer, sources

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _save_history(self, user_query, answer):
        self.chat_history.append({"role": "user",      "content": user_query})
        self.chat_history.append({"role": "assistant", "content": answer})

    def reset_history(self):
        """Clear ALL state including pending and last summary."""
        self.chat_history      = []
        self.last_summary      = None
        self.last_summary_meta = None
        self.pending_summary   = None
        print("Conversation history cleared.\n")
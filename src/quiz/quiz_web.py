import os
import re
import json
import random
from typing import Optional
from collections import defaultdict

from config import PROJECT_ROOT, chat_imports
chat_imports()
from llm import get_answer


# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
CURRENT_DIR  = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH   = os.path.join(PROJECT_ROOT, "index_store", "chunks.json")


# ─────────────────────────────────────────────
# Caches
# ─────────────────────────────────────────────
_chunks_cache = None
_url_map      = None


# ─────────────────────────────────────────────
# Load indexed chunks
# ─────────────────────────────────────────────
def load_chunks() -> list[dict]:
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Index not found: {INDEX_PATH}")
    with open(INDEX_PATH, encoding="utf-8") as f:
        _chunks_cache = json.load(f)
    print(f"✅ Quiz: loaded {len(_chunks_cache)} chunks")
    return _chunks_cache


# ─────────────────────────────────────────────
# Load URL mapping (for display links only)
# ─────────────────────────────────────────────
def load_url_map() -> dict[str, str]:
    """Map composite key → gdrive URL for display."""
    global _url_map
    if _url_map is not None:
        return _url_map

    _url_map = {}
    dataset_dir = os.path.join(PROJECT_ROOT, "dataset")
    import glob
    pattern = os.path.join(dataset_dir, "**", "gdrive_links.json")

    for json_path in glob.glob(pattern, recursive=True):
        parts = os.path.normpath(json_path).split(os.sep)
        branch, sem = "", ""
        try:
            sm_idx = parts.index("study_material")
            branch = parts[sm_idx + 1] if sm_idx + 1 < len(parts) else ""
            sem    = parts[sm_idx + 2] if sm_idx + 2 < len(parts) else ""
        except ValueError:
            pass

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                name    = item.get("item_name", "").strip()
                subject = item.get("subject", "").strip()
                url     = item.get("original_url", "")
                if name and url:
                    key = f"{branch}|{sem}|{subject}|{name}"
                    _url_map[key] = url
        except Exception:
            pass

    return _url_map


# ─────────────────────────────────────────────
# Browse tree — directly from chunk metadata
# ─────────────────────────────────────────────
def get_browse_tree() -> dict:
    """Build branch → sem → subject → categories tree."""
    chunks = load_chunks()

    tree = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(set)
        )
    )

    for chunk in chunks:
        branch   = chunk.get("branch",   "") or "Unknown"
        sem      = chunk.get("semester", "") or "?"
        subject  = chunk.get("subject",  "") or "Other"
        category = chunk.get("category", "") or "Other"
        tree[branch][sem][subject].add(category)

    result = {}
    for branch in sorted(tree.keys()):
        result[branch] = {}
        for sem in sorted(tree[branch].keys()):
            result[branch][sem] = {}
            for subject in sorted(tree[branch][sem].keys()):
                cats = sorted(list(tree[branch][sem][subject]))
                preferred = ["Lectures", "Tutorials", "PYQs", "Course Description", "Other"]
                ordered  = [c for c in preferred if c in cats]
                ordered += [c for c in cats if c not in preferred]
                result[branch][sem][subject] = ordered

    return result


# ─────────────────────────────────────────────
# Filter chunks — simple metadata filter
# ─────────────────────────────────────────────
def filter_chunks(
    branch:   Optional[str] = None,
    sem:      Optional[str] = None,
    subject:  Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """Filter by chunk metadata."""
    chunks  = load_chunks()
    url_map = load_url_map()

    filtered = []
    for chunk in chunks:
        if branch   and chunk.get("branch",   "") != branch:   continue
        if sem      and chunk.get("semester", "") != sem:      continue
        if subject  and chunk.get("subject",  "") != subject:  continue
        if category and chunk.get("category", "") != category: continue

        # Attach URL
        key = f"{chunk.get('branch', '')}|{chunk.get('semester', '')}|{chunk.get('subject', '')}|{chunk.get('source_file', '')}"
        chunk_copy = dict(chunk)
        chunk_copy["url"] = url_map.get(key, "")
        filtered.append(chunk_copy)

    return filtered


# ─────────────────────────────────────────────
# Sample + auto-count
# ─────────────────────────────────────────────
def sample_content(chunks: list[dict], num_chunks: int = 10, min_words: int = 30) -> list[dict]:
    good = [c for c in chunks if len(c.get("text", "").split()) >= min_words]
    if not good:
        good = chunks
    if len(good) <= num_chunks:
        return good
    return random.sample(good, num_chunks)


def auto_num_questions(text: str) -> int:
    words = len(text.split())
    if words < 500:    return 5
    elif words < 1500: return 8
    elif words < 4000: return 12
    elif words < 8000: return 18
    else:              return 25


# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────
def build_quiz_prompt(question_types: list[str], difficulty: str, num_questions: int) -> str:
    types_str = ", ".join(question_types)
    return f"""You are an expert quiz-master and academic question setter.

Generate EXACTLY {num_questions} high-quality quiz questions from the
provided content.

REQUIREMENTS:
- Question types to use: {types_str}
- Difficulty level: {difficulty}
- Distribute question types as evenly as possible.
- For MCQs: provide exactly 4 options labeled (A), (B), (C), (D).
- For True/False: state a clear factual statement.
- For Fill in the Blanks: use _____ for the blank.
- For Numerical Problems: include all necessary data.
- For Short Answer: expected answer 1-2 lines.
- For Long Answer: descriptive 5-10 marks style.

FORMAT (strict — follow exactly for EVERY question including the last one):

### Q1. [QuestionType] [Difficulty]
<question text>

(For MCQ:)
(A) option 1
(B) option 2
(C) option 3
(D) option 4

**Answer:** <answer>
**Explanation:** <brief explanation>

---

### Q2. [QuestionType] [Difficulty]
...

IMPORTANT:
- ALWAYS include the "---" separator AFTER each question's explanation,
  INCLUDING the very last question (Q{num_questions}).
- ALWAYS include **Answer:** and **Explanation:** for every question.
- Number them Q1 through Q{num_questions} sequentially.
- Base questions strictly on the provided content.
"""


# ─────────────────────────────────────────────
# Parse quiz — FIXED to handle last question
# ─────────────────────────────────────────────
def parse_quiz(quiz_text: str) -> list[dict]:
    """Parse quiz markdown into structured questions."""

    # Ensure trailing separator so last question is captured
    if not quiz_text.rstrip().endswith("---"):
        quiz_text = quiz_text.rstrip() + "\n\n---\n"

    questions = []
    chunks = re.split(r"(?=^#{1,3}\s*Q\d+\.)", quiz_text, flags=re.MULTILINE)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        header_match = re.match(r"#{1,3}\s*(Q\d+)\.?\s*(.*)", chunk)
        if not header_match:
            continue

        qnum   = header_match.group(1)
        header = chunk.split("\n", 1)[0].lstrip("#").strip()

        # Answer — allow end of string as termination
        ans_match = re.search(
            r"\*\*Answer:\*\*\s*(.+?)(?=\n\s*\*\*Explanation|\n\s*---|\Z)",
            chunk, flags=re.DOTALL | re.IGNORECASE,
        )
        exp_match = re.search(
            r"\*\*Explanation:\*\*\s*(.+?)(?=\n\s*---|\Z)",
            chunk, flags=re.DOTALL | re.IGNORECASE,
        )

        answer      = ans_match.group(1).strip() if ans_match else ""
        explanation = exp_match.group(1).strip() if exp_match else ""

        # Question block (remove header + answer + explanation)
        question_block = chunk
        question_block = re.sub(r"^#{1,3}\s*Q\d+\..*\n", "", question_block, count=1)
        question_block = re.sub(
            r"\*\*Answer:\*\*.*?(?=\n\s*\*\*Explanation|\n\s*---|\Z)",
            "", question_block, flags=re.DOTALL | re.IGNORECASE,
        )
        question_block = re.sub(
            r"\*\*Explanation:\*\*.*?(?=\n\s*---|\Z)",
            "", question_block, flags=re.DOTALL | re.IGNORECASE,
        )
        question_block = re.sub(r"^-{3,}$", "", question_block, flags=re.MULTILINE)
        question_block = question_block.strip()

        # Detect type
        qtype = "Unknown"
        h = header.lower()
        if   "mcq" in h:                     qtype = "MCQ"
        elif "true" in h or "false" in h:    qtype = "True/False"
        elif "fill" in h or "blank" in h:    qtype = "Fill in the Blanks"
        elif "numerical" in h:               qtype = "Numerical"
        elif "long" in h:                    qtype = "Long Answer"
        elif "short" in h:                   qtype = "Short Answer"

        # Extract MCQ options
        options = []
        if qtype == "MCQ":
            opt_matches = re.findall(
                r"^\s*\(?([A-D])\)?[\.\)]?\s+(.+?)$",
                question_block, flags=re.MULTILINE,
            )
            options = [{"letter": m[0], "text": m[1].strip()} for m in opt_matches]
            for letter, _ in opt_matches:
                question_block = re.sub(
                    rf"^\s*\(?{letter}\)?[\.\)]?\s+.+$",
                    "", question_block, flags=re.MULTILINE,
                )
            question_block = re.sub(r"\n\s*\n", "\n", question_block).strip()

        questions.append({
            "number":        qnum,
            "type":          qtype,
            "header":        header,
            "question_text": question_block,
            "options":       options,
            "answer":        answer,
            "explanation":   explanation,
        })

    return questions


def extract_correct_letter(answer_text: str) -> Optional[str]:
    """From answer like '(A) foo' or 'B' → return 'A' / 'B'."""
    m = re.search(r"\b([A-D])\b", str(answer_text))
    return m.group(1) if m else None


# ─────────────────────────────────────────────
# MAIN: Generate quiz
# ─────────────────────────────────────────────
def generate_quiz_indexed(
    branch:         str  = None,
    sem:            str  = None,
    subject:        str  = None,
    category:       str  = None,
    file_names:     list = None,   # ← NEW: specific file selection
    question_types: list = None,
    difficulty:     str  = "Medium",
    num_questions:  int  = None,
) -> dict:
    if question_types is None:
        question_types = ["MCQ", "True/False", "Short Answer"]

    # ── Pick chunks: by files OR by filters ──
    if file_names:
        chunks = filter_chunks_by_files(
            file_names = file_names,
            branch     = branch,
            sem        = sem,
            subject    = subject,
        )
        source_label = f"{len(file_names)} selected file(s)"
    else:
        chunks = filter_chunks(branch, sem, subject, category)
        source_label = "all matching files"

    if not chunks:
        return {
            "success": False,
            "error":   f"No content found for {source_label}",
            "filters": {
                "branch":     branch,
                "sem":        sem,
                "subject":    subject,
                "category":   category,
                "file_names": file_names,
            },
        }

    selected = sample_content(chunks, num_chunks=10)

    content_parts = []
    source_files  = {}
    for chunk in selected:
        fname = chunk.get("source_file", "")
        content_parts.append(
            f"--- {fname} ({chunk.get('location', '')}) ---\n{chunk['text']}"
        )
        if fname and fname not in source_files:
            source_files[fname] = {
                "name":    fname,
                "url":     chunk.get("url", ""),
                "subject": chunk.get("subject", ""),
            }

    content = "\n\n".join(content_parts)

    MAX_WORDS = 14000
    if len(content.split()) > MAX_WORDS:
        content = " ".join(content.split()[:MAX_WORDS])
        print(f"   Truncated to {MAX_WORDS} words")

    if num_questions is None:
        num_questions = auto_num_questions(content)
    num_questions = max(3, min(num_questions, 30))

    # Build label
    label_parts = [p for p in [branch, sem and f"Sem {sem}", subject, category] if p]
    label = " / ".join(label_parts) or "General"
    if file_names:
        label += f" ({len(file_names)} file{'s' if len(file_names) > 1 else ''})"

    system_prompt = build_quiz_prompt(question_types, difficulty, num_questions)
    user_msg = f"Source: {label}\n\nContent:\n{content}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]

    print(f"🎯 Quiz: {num_questions} questions ({difficulty}) — {', '.join(question_types)}")
    quiz_text = get_answer(messages)

    questions = parse_quiz(quiz_text)

    if not questions:
        return {
            "success": False,
            "error":   "Could not parse quiz",
            "raw":     quiz_text[:500],
        }

    if len(questions) < num_questions:
        print(f"⚠️  Requested {num_questions}, got {len(questions)}")

    return {
        "success":        True,
        "quiz_text":      quiz_text,
        "questions":      questions,
        "num_questions":  len(questions),
        "difficulty":     difficulty,
        "question_types": question_types,
        "label":          label,
        "filters": {
            "branch":     branch,
            "sem":        sem,
            "subject":    subject,
            "category":   category,
            "file_names": file_names,
        },
        "sources": list(source_files.values()),
    }


# ─────────────────────────────────────────────
# Smart answer comparison helpers
# ─────────────────────────────────────────────
def parse_numeric(text: str):
    """
    Try to extract a numeric value from text.
    Handles: "0.533", "8/15", "1/2", "-3.14", "2.5e-3", "42", "1,234.5"
    Returns float or None if not numeric.
    """
    import re
    if text is None:
        return None

    s = str(text).strip()
    if not s:
        return None

    # Remove common units and words (keep only math-relevant chars)
    # But save the original for fraction detection
    s_clean = s.replace(",", "").strip()

    # Try fraction first: "8/15", "-1/2"
    frac_match = re.match(r"^\s*(-?\d+\.?\d*)\s*/\s*(-?\d+\.?\d*)\s*$", s_clean)
    if frac_match:
        try:
            num = float(frac_match.group(1))
            den = float(frac_match.group(2))
            if den != 0:
                return num / den
        except (ValueError, ZeroDivisionError):
            pass

    # Try mixed number: "1 3/4"
    mixed = re.match(r"^\s*(-?\d+)\s+(\d+)\s*/\s*(\d+)\s*$", s_clean)
    if mixed:
        try:
            whole = float(mixed.group(1))
            num = float(mixed.group(2))
            den = float(mixed.group(3))
            if den != 0:
                sign = -1 if whole < 0 else 1
                return whole + sign * (num / den)
        except (ValueError, ZeroDivisionError):
            pass

    # Try to extract first number from text (handles "42 m/s" → 42)
    num_match = re.search(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", s_clean)
    if num_match:
        try:
            return float(num_match.group(0))
        except ValueError:
            pass

    return None


def compare_numeric(user_ans, correct_ans, tolerance: float = 0.01) -> bool:
    """
    Compare two answers numerically with tolerance.
    - Handles fractions (8/15), decimals (0.533), integers (42)
    - Uses relative tolerance for large numbers, absolute for small
    Returns True if within tolerance, else False.
    Returns None if either can't be parsed as number.
    """
    u_num = parse_numeric(user_ans)
    c_num = parse_numeric(correct_ans)

    if u_num is None or c_num is None:
        return None   # Not numeric — caller should fall back to text compare

    # For very small numbers, use absolute tolerance
    if abs(c_num) < 1:
        return abs(u_num - c_num) < tolerance

    # For larger numbers, use relative tolerance
    return abs(u_num - c_num) / abs(c_num) < tolerance


def compare_text(user_ans, correct_ans) -> bool:
    """
    Compare two text answers (case-insensitive, punctuation-agnostic).
    """
    import re
    u = re.sub(r"[^\w\s]", "", str(user_ans or "")).lower().strip()
    c = re.sub(r"[^\w\s]", "", str(correct_ans or "")).lower().strip()

    if not u or not c:
        return False

    # Normalize whitespace
    u = re.sub(r"\s+", " ", u)
    c = re.sub(r"\s+", " ", c)

    return u == c or u in c or c in u


def smart_compare(user_ans, correct_ans) -> bool:
    """
    Try numeric comparison first; fall back to text.
    """
    # Try numeric
    num_result = compare_numeric(user_ans, correct_ans)
    if num_result is not None:
        return num_result

    # Fall back to text
    return compare_text(user_ans, correct_ans)


# ─────────────────────────────────────────────
# Updated score_quiz
# ─────────────────────────────────────────────
def score_quiz(questions: list, user_answers: list) -> dict:
    """Score user's answers with smart numeric + text comparison."""
    import re

    results       = []
    auto_correct  = 0
    auto_total    = 0
    manual_review = 0

    for i, q in enumerate(questions):
        user_ans    = user_answers[i] if i < len(user_answers) else None
        qtype       = q.get("type", "")
        correct_ans = q.get("answer", "")

        result = {
            "number":         q.get("number", f"Q{i+1}"),
            "type":           qtype,
            "question":       q.get("question_text", ""),
            "options":        q.get("options", []),
            "user_answer":    user_ans,
            "correct_answer": correct_ans,
            "explanation":    q.get("explanation", ""),
        }

        if qtype == "MCQ":
            auto_total += 1
            correct_letter = extract_correct_letter(correct_ans)
            is_correct = user_ans and correct_letter and user_ans.upper() == correct_letter.upper()
            result["is_correct"] = bool(is_correct)
            result["correct_letter"] = correct_letter
            if is_correct:
                auto_correct += 1

        elif qtype == "True/False":
            auto_total += 1
            c = str(correct_ans).lower().strip()
            u = str(user_ans or "").lower().strip()
            is_correct = (
                (u in ["true",  "t", "yes", "y"] and "true"  in c) or
                (u in ["false", "f", "no",  "n"] and "false" in c)
            )
            result["is_correct"] = bool(is_correct)
            if is_correct:
                auto_correct += 1

        elif qtype in ("Fill in the Blanks", "Numerical"):
            auto_total += 1
            is_correct = smart_compare(user_ans, correct_ans)
            result["is_correct"] = bool(is_correct)
            if is_correct:
                auto_correct += 1

        else:
            # Short/Long Answer — needs manual review
            result["is_correct"]   = None
            result["needs_review"] = True
            manual_review += 1

        results.append(result)

    percentage = round((auto_correct / auto_total) * 100, 1) if auto_total > 0 else 0

    if percentage >= 90:   grade, tier = "A+", "Excellent! 🏆"
    elif percentage >= 75: grade, tier = "A",  "Great work! 🎉"
    elif percentage >= 60: grade, tier = "B",  "Good job! 👍"
    elif percentage >= 50: grade, tier = "C",  "Keep practicing 📚"
    elif auto_total == 0:  grade, tier = "—",  "Manual review needed"
    else:                  grade, tier = "F",  "Review the material 📖"

    return {
        "results":         results,
        "auto_correct":    auto_correct,
        "auto_total":      auto_total,
        "manual_review":   manual_review,
        "percentage":      percentage,
        "grade":           grade,
        "tier":            tier,
        "total_questions": len(questions),
    }

# ─────────────────────────────────────────────
# Save quiz
# ─────────────────────────────────────────────
def save_quiz_indexed(quiz_result: dict) -> str:
    quiz_text = quiz_result.get("quiz_text", "")
    if not quiz_text:
        return ""

    filters = quiz_result.get("filters", {})
    label   = quiz_result.get("label", "quiz")
    sources = quiz_result.get("sources", [])

    safe_label = re.sub(r'[<>:"/\\|?*]', "_", label).strip()[:80]

    out_dir = os.path.join(
        PROJECT_ROOT, "quizzes",
        filters.get("branch") or "general",
        filters.get("sem")    or "all",
    )
    os.makedirs(out_dir, exist_ok=True)

    filename = f"quiz_{safe_label}_{random.randint(1000, 9999)}.md"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Quiz: {label}\n\n")
        f.write(f"**Difficulty:** {quiz_result.get('difficulty', '')}\n")
        f.write(f"**Questions:** {quiz_result.get('num_questions', 0)}\n")
        f.write(f"**Types:** {', '.join(quiz_result.get('question_types', []))}\n\n")

        if sources:
            f.write("## Source Files\n\n")
            for s in sources:
                if s.get("url"):
                    f.write(f"- [{s['name']}]({s['url']})\n")
                else:
                    f.write(f"- {s['name']}\n")
            f.write("\n")

        f.write("---\n\n")
        f.write(quiz_text)

    return filepath

# ─────────────────────────────────────────────
# List available files (for user selection)
# ─────────────────────────────────────────────
def list_files(
    branch:   str = None,
    sem:      str = None,
    subject:  str = None,
    category: str = None,
) -> list:
    """List unique files matching filters, naturally sorted."""
    chunks  = load_chunks()
    url_map = load_url_map()

    seen  = set()
    files = []

    for chunk in chunks:
        if branch   and chunk.get("branch",   "") != branch:   continue
        if sem      and chunk.get("semester", "") != sem:      continue
        if subject  and chunk.get("subject",  "") != subject:  continue
        if category and chunk.get("category", "") != category: continue

        fname = chunk.get("source_file", "")
        if not fname:
            continue

        key = (
            chunk.get("branch",   ""),
            chunk.get("semester", ""),
            chunk.get("subject",  ""),
            fname,
        )
        if key in seen:
            continue
        seen.add(key)

        url_key = f"{key[0]}|{key[1]}|{key[2]}|{fname}"
        files.append({
            "name":     fname,
            "branch":   chunk.get("branch", ""),
            "semester": chunk.get("semester", ""),
            "subject":  chunk.get("subject", ""),
            "category": chunk.get("category", ""),
            "url":      url_map.get(url_key, ""),
            "chunk_count": 0,
        })

    # Count chunks per file
    for f in files:
        count = 0
        for chunk in chunks:
            if (chunk.get("source_file") == f["name"] and
                chunk.get("branch",   "") == f["branch"] and
                chunk.get("semester", "") == f["semester"] and
                chunk.get("subject",  "") == f["subject"]):
                count += 1
        f["chunk_count"] = count

    # ✅ NATURAL SORT — treats "L2" before "L10"
    files.sort(key=lambda f: natural_sort_key(f["name"]))
    return files


# ─────────────────────────────────────────────
# Natural sort helper
# ─────────────────────────────────────────────
def natural_sort_key(text: str) -> tuple:
    """
    Smart sort key that handles ALL these formats:
      - "L1", "L 1", "L-1", "L_1"
      - "Lec 1", "Lec-1", "Lec_1"
      - "Lecture 1", "Lecture-1", "Lecture_1"
      - "Ch 1", "Chapter 1"

    Returns (lecture_num, remaining_text) so numbers sort numerically
    and files without lecture numbers sort at the end alphabetically.
    """
    import re

    text_lower = str(text).lower().strip()

    # Try to extract lecture number using multiple patterns
    patterns = [
        # "lecture 15", "lecture-15", "lec 8", "lec-11", "chapter 3"
        r"^(?:lecture|lec|chapter|ch|lesson)[\s\-_]*(\d+)",
        # "l 9", "l-10", "l11", "l_2"
        r"^l[\s\-_]*(\d+)",
        # Fallback: any leading number
        r"^(\d+)",
    ]

    for pattern in patterns:
        m = re.match(pattern, text_lower)
        if m:
            num = int(m.group(1))
            # Remove the matched prefix to get the rest for tiebreaker
            remaining = text_lower[m.end():].strip()
            return (0, num, remaining)   # 0 = has number, sorts first

    # No lecture number found — sort alphabetically at the end
    return (1, 0, text_lower)   # 1 = no number, sorts last


# ─────────────────────────────────────────────
# Filter chunks by specific files
# ─────────────────────────────────────────────
def filter_chunks_by_files(
    file_names: list,
    branch:     str = None,
    sem:        str = None,
    subject:    str = None,
) -> list:
    """
    Get chunks for a specific list of file names.
    Uses branch/sem/subject to disambiguate duplicate filenames.
    """
    if not file_names:
        return []

    chunks  = load_chunks()
    url_map = load_url_map()

    file_set = set(file_names)
    filtered = []

    for chunk in chunks:
        fname = chunk.get("source_file", "")
        if fname not in file_set:
            continue

        if branch   and chunk.get("branch",   "") != branch:   continue
        if sem      and chunk.get("semester", "") != sem:      continue
        if subject  and chunk.get("subject",  "") != subject:  continue

        # Attach URL
        key = f"{chunk.get('branch', '')}|{chunk.get('semester', '')}|{chunk.get('subject', '')}|{fname}"
        chunk_copy = dict(chunk)
        chunk_copy["url"] = url_map.get(key, "")
        filtered.append(chunk_copy)

    return filtered
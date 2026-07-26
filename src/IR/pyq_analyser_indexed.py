"""
pyq_analyser_indexed.py
PYQ analyser that uses pre-indexed chunks.json instead of GDrive downloads.
Works for ANY year (1-5) — no hardcoded semester restrictions.
"""

import os
import re
import json
import glob
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from llm import get_answer


# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
CURRENT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
INDEX_PATH   = os.path.join(PROJECT_ROOT, "index_store", "chunks.json")


# ─────────────────────────────────────────────
# Caches
# ─────────────────────────────────────────────
_chunks_cache = None
_url_map      = None


def load_chunks() -> List[Dict]:
    """Load all indexed chunks (cached)."""
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache

    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Index not found: {INDEX_PATH}")

    with open(INDEX_PATH, encoding="utf-8") as f:
        _chunks_cache = json.load(f)

    print(f"✅ PYQ (indexed): loaded {len(_chunks_cache)} chunks")
    return _chunks_cache


def load_url_map() -> Dict[str, str]:
    """Map composite key → gdrive URL for source links."""
    global _url_map
    if _url_map is not None:
        return _url_map

    _url_map = {}
    dataset_dir = os.path.join(PROJECT_ROOT, "dataset")
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
                name    = item.get("item_name",  "").strip()
                subject = item.get("subject",    "").strip()
                url     = item.get("original_url", "")
                if name and url:
                    key = f"{branch}|{sem}|{subject}|{name}"
                    _url_map[key] = url
        except Exception:
            pass

    return _url_map


# ─────────────────────────────────────────────
# SUBJECT ALIASES
# ─────────────────────────────────────────────
SUBJECT_ALIASES = {
    # Mathematical Foundations for AI and DS
    "maths":     "Mathematical Foundations for AI and DS",
    "math":      "Mathematical Foundations for AI and DS",
    "mathematics": "Mathematical Foundations for AI and DS",
    "mfaids":    "Mathematical Foundations for AI and DS",
    "mf":        "Mathematical Foundations for AI and DS",

    # OOP using Java Lab
    "oops":      "OOP using Java Lab",
    "oop":       "OOP using Java Lab",
    "java":      "OOP using Java Lab",
    "java lab":  "OOP using Java Lab",

    # Unix Programming Lab
    "unix":      "Unix Programming Lab",
    "up":        "Unix Programming Lab",

    # Database Management Systems
    "dbms":      "Database Management Systems",
    "dbms theory": "Database Management Systems",
    "dbms lab":  "Database Management Systems Lab",
    "database":  "Database Management Systems",

    # Theory of Computation
    "toc":       "Theory of Computation",
    "theory of computation": "Theory of Computation",
    "automata":  "Theory of Computation",

    # Economics
    "eco":       "Economics",
    "econ":      "Economics",
    "economics": "Economics",

    # Data Structures
    "ds":        "Data Structures",
    "ds theory": "Data Structures",
    "ds lab":    "Data Structures Lab",
    "data structures": "Data Structures",
    "dsa":       "Data Structures",

    # Sem 4
    "dsco":      "Digital Systems and Comp. Organisation",
    "se":        "Software Engineering",
    "software":  "Software Engineering",
    "aiml":      "Artificial Intelligence and Machine Learning",
    "ai ml":     "Artificial Intelligence and Machine Learning",
    "ml":        "Artificial Intelligence and Machine Learning",
    "ai":        "Artificial Intelligence and Machine Learning",
    "daa":       "Design and Analysis of Algorithms",
    "algo":      "Design and Analysis of Algorithms",
    "evs":       "Environmental Studies Lab",
    "qmss":      "Quantitative Methods for Social Sc. (Elective)",
    "mad":       "Fundamentals of Mobile Appl. Development (Elective)",
    "mad lab":   "Fundamentals of Mobile Appl. Development Lab (Elective)",
    "aiml lab":  "Artificial Intelligence and Machine Learning Lab",
    "daa lab":   "Design and Analysis of Algorithms Lab",
    "cp":        "Competitive Programming Lab",
}


SUBJECTS_WITH_LAB_THEORY = {
    "dbms":  ("Database Management Systems",     "Database Management Systems Lab"),
    "ds":    ("Data Structures",                 "Data Structures Lab"),
    "aiml":  ("Artificial Intelligence and Machine Learning",
              "Artificial Intelligence and Machine Learning Lab"),
    "daa":   ("Design and Analysis of Algorithms",
              "Design and Analysis of Algorithms Lab"),
    "mad":   ("Fundamentals of Mobile Appl. Development (Elective)",
              "Fundamentals of Mobile Appl. Development Lab (Elective)"),
}


# ─────────────────────────────────────────────
# EXAM TYPE DETECTION
# ─────────────────────────────────────────────
def detect_exam_type(filename: str) -> Optional[str]:
    """Detect exam type from PYQ filename."""
    name = filename.upper()

    # T3 / M3 / End Term
    if re.search(r"(?:^|[\s_\-\.])T3(?:[\s_\-\.]|$)", name): return "T3"
    if re.search(r"(?:^|[\s_\-\.])M3(?:[\s_\-\.]|$)", name): return "T3"
    if "ENDTERM" in name or "END TERM" in name or "END-TERM" in name or "END_TERM" in name:
        return "T3"

    # T2 / M2
    if re.search(r"(?:^|[\s_\-\.])T2(?:[\s_\-\.]|$)", name): return "T2"
    if re.search(r"(?:^|[\s_\-\.])M2(?:[\s_\-\.]|$)", name): return "T2"

    # T1 / M1
    if re.search(r"(?:^|[\s_\-\.])T1(?:[\s_\-\.]|$)", name): return "T1"
    if re.search(r"(?:^|[\s_\-\.])M1(?:[\s_\-\.]|$)", name): return "T1"

    if "MIDTERM" in name and "ENDTERM" in name:
        return "T3"

    # Lab patterns
    if any(p in name for p in ["LAB TEST-2", "LABTEST2", "LAB TEST 2", "LAB-TEST-2"]):
        return "T2"
    if any(p in name for p in ["LAB TEST-1", "LABTEST1", "LAB TEST 1", "LAB-TEST-1"]):
        return "T1"

    if re.search(r"EVAL\s*#?\s*0?2|EVAL[-_ ]?2|EVAL[-_ ]?II|LAB\s*EVAL\s*2", name):
        return "T2"
    if re.search(r"EVAL\s*#?\s*0?1|EVAL[-_ ]?1|EVAL[-_ ]?I(?!I)|LAB\s*EVAL\s*1", name):
        return "T1"

    if "MIDTERM" in name:
        return "T2"

    return None


# ─────────────────────────────────────────────
# QUERY INDEXED DATA
# ─────────────────────────────────────────────
def get_all_years() -> List[str]:
    """Return all years/semesters that have PYQ data."""
    chunks = load_chunks()
    years = set()
    for chunk in chunks:
        if chunk.get("category", "") == "PYQs":
            sem = str(chunk.get("semester", "")).strip()
            if sem:
                years.add(sem)

    def sort_key(y):
        try:
            return (0, int(y))
        except ValueError:
            return (1, y)

    return sorted(years, key=sort_key)


def get_subjects_with_pyqs(semester: str) -> List[str]:
    """Return subjects that have PYQ chunks in the given semester/year."""
    chunks = load_chunks()

    subjects = set()
    for chunk in chunks:
        if str(chunk.get("semester", "")) != str(semester):
            continue
        if chunk.get("category", "") != "PYQs":
            continue
        subj = chunk.get("subject", "")
        if subj:
            subjects.add(subj)

    return sorted(subjects)


def get_pyq_files(semester: str, subject: str) -> List[Dict]:
    """
    Return unique PYQ files for a subject.
    Each file: {name, url, exam_type}
    """
    chunks = load_chunks()
    url_map = load_url_map()

    seen = set()
    files = []

    for chunk in chunks:
        if str(chunk.get("semester", "")) != str(semester):
            continue
        if chunk.get("category", "") != "PYQs":
            continue
        if chunk.get("subject", "") != subject:
            continue

        fname = chunk.get("source_file", "")
        if not fname or fname in seen:
            continue
        seen.add(fname)

        branch = chunk.get("branch", "")
        url_key = f"{branch}|{semester}|{subject}|{fname}"

        files.append({
            "name":      fname,
            "url":       url_map.get(url_key, ""),
            "exam_type": detect_exam_type(fname),
        })

    # Natural sort by exam type then year
    def sort_key(f):
        m = re.search(r"(\d{4})", f["name"])
        year = int(m.group(1)) if m else 0
        return (f.get("exam_type") or "Z", year, f["name"])

    files.sort(key=sort_key)
    return files


def get_pyq_files_for_exam(semester: str, subject: str, exam: str) -> List[Dict]:
    """Filter PYQ files by exam type."""
    all_files = get_pyq_files(semester, subject)
    return [f for f in all_files if f.get("exam_type") == exam]


def get_pyq_chunks(
    semester:   str,
    subject:    str,
    file_names: List[str] = None,
) -> List[Dict]:
    """Get all chunks for PYQ papers. Filter by file names if given."""
    chunks = load_chunks()
    filter_set = set(file_names) if file_names else None

    matches = []
    for chunk in chunks:
        if str(chunk.get("semester", "")) != str(semester):
            continue
        if chunk.get("subject", "") != subject:
            continue
        if chunk.get("category", "") != "PYQs":
            continue
        if filter_set and chunk.get("source_file", "") not in filter_set:
            continue
        matches.append(chunk)

    matches.sort(key=lambda c: (
        c.get("source_file", ""),
        c.get("chunk_id", 0),
    ))

    return matches


def get_lecture_context(semester: str, subject: str, max_chars: int = 4000) -> str:
    """Gather syllabus overview from lecture filenames."""
    chunks = load_chunks()

    lecture_names = set()
    for chunk in chunks:
        if str(chunk.get("semester", "")) != str(semester):
            continue
        if chunk.get("subject", "") != subject:
            continue
        if chunk.get("category", "") != "Lectures":
            continue
        name = chunk.get("source_file", "")
        if name:
            lecture_names.add(name)

    if not lecture_names:
        return "(no lecture syllabus available)"

    def sort_key(name):
        m = re.search(r"(\d+)", name)
        return (int(m.group(1)) if m else 999, name.lower())

    sorted_names = sorted(lecture_names, key=sort_key)

    summary = "Lecture topics covered in this subject:\n"
    for lec in sorted_names:
        summary += f"- {lec}\n"
        if len(summary) > max_chars:
            break
    return summary


# ─────────────────────────────────────────────
# SUBJECT VERIFICATION
# ─────────────────────────────────────────────
SUBJECT_KEYWORDS = {
    "Mathematical Foundations for AI and DS": [
        "mathematical foundations", "mfaids", "mf ai", "math foundations",
        "probability", "random variable", "linear algebra", "vector space",
        "regression", "hypothesis testing",
    ],
    "OOP using Java Lab": [
        "java", "object oriented", "class", "inheritance", "polymorphism",
        "encapsulation", "constructor", "abstract class", "interface",
    ],
    "Unix Programming Lab": [
        "unix", "shell script", "shell scripting", "bash", "sed", "awk",
        "grep", "chmod", "chown", "linux command",
    ],
    "Database Management Systems": [
        "dbms", "database management", "sql", "normalization", "er diagram",
        "relational", "primary key", "foreign key", "join", "transaction",
    ],
    "Database Management Systems Lab": [
        "dbms", "sql", "create table", "insert into", "select", "join",
        "database", "relational", "trigger", "stored procedure",
    ],
    "Theory of Computation": [
        "theory of computation", "toc", "finite automata", "dfa", "nfa",
        "regular expression", "turing machine", "pushdown automata",
        "context free", "pumping lemma", "grammar",
    ],
    "Economics": [
        "economics", "demand", "supply", "elasticity", "gdp", "inflation",
        "market", "monopoly", "consumer", "producer",
    ],
    "Data Structures": [
        "data structure", "linked list", "stack", "queue", "tree",
        "binary tree", "heap", "graph", "hashing", "sorting", "algorithm",
    ],
    "Data Structures Lab": [
        "data structure", "linked list", "stack", "queue", "tree",
        "sorting", "search", "algorithm", "implement",
    ],
    "Digital Systems and Comp. Organisation": [
        "digital", "boolean", "karnaugh", "flip flop", "counter",
        "register", "computer organisation", "instruction",
    ],
    "Software Engineering": [
        "software engineering", "sdlc", "agile", "waterfall", "requirement",
        "uml", "use case", "sprint",
    ],
    "Artificial Intelligence and Machine Learning": [
        "artificial intelligence", "machine learning", "neural network",
        "supervised", "unsupervised", "classification", "regression",
        "clustering", "decision tree",
    ],
    "Design and Analysis of Algorithms": [
        "algorithm", "time complexity", "space complexity", "asymptotic",
        "dynamic programming", "greedy", "divide and conquer", "np hard",
    ],
    "Environmental Studies Lab": [
        "environmental", "pollution", "ecosystem", "biodiversity",
        "climate", "sustainability",
    ],
    "Quantitative Methods for Social Sc. (Elective)": [
        "quantitative", "statistics", "hypothesis", "regression", "sampling",
        "distribution",
    ],
    "Fundamentals of Mobile Appl. Development (Elective)": [
        "android", "mobile", "activity", "intent", "kotlin", "java",
        "layout", "fragment", "manifest",
    ],
    "Fundamentals of Mobile Appl. Development Lab (Elective)": [
        "android", "mobile", "activity", "intent", "kotlin", "xml layout",
    ],
    "Competitive Programming Lab": [
        "competitive programming", "algorithm", "time complexity",
        "problem solving",
    ],
    "Artificial Intelligence and Machine Learning Lab": [
        "machine learning", "python", "numpy", "pandas", "scikit",
        "classifier", "training",
    ],
}


def verify_paper_belongs_to_subject(paper_text: str, subject: str, threshold: int = 1) -> bool:
    """Verify paper actually belongs to the subject using keyword matching."""
    if not paper_text or not paper_text.strip():
        return False

    keywords = SUBJECT_KEYWORDS.get(subject, [])
    if not keywords:
        return True

    text_lower = paper_text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches >= threshold


# ─────────────────────────────────────────────
# GATHER CONTENT
# ─────────────────────────────────────────────
def gather_pyq_content(
    semester:   str,
    subject:    str,
    file_names: List[str],
) -> Tuple[str, List[str], List[str]]:
    """
    Gather content from indexed PYQ chunks and verify subject match.
    Returns (combined_text, included_names, rejected_names).
    """
    files_content = defaultdict(list)
    chunks = get_pyq_chunks(semester, subject, file_names)

    for chunk in chunks:
        fname = chunk.get("source_file", "")
        text = chunk.get("text", "")
        location = chunk.get("location", "")
        if fname and text:
            files_content[fname].append({
                "location": location,
                "text": text,
            })

    all_texts = []
    included = []
    rejected = []

    for fname in file_names:
        if fname not in files_content:
            print(f"   ⚠ No chunks found for: {fname}")
            rejected.append(fname)
            continue

        parts = []
        for item in files_content[fname]:
            parts.append(f"--- {item['location']} ---\n{item['text']}")
        combined_text = "\n\n".join(parts)

        if not verify_paper_belongs_to_subject(combined_text, subject):
            print(f"   ⚠ Rejected (subject mismatch): {fname}")
            rejected.append(fname)
            continue

        all_texts.append(
            f"\n{'='*60}\nPAPER: {fname}\n{'='*60}\n{combined_text}"
        )
        included.append(fname)
        print(f"   ✓ Included: {fname}")

    return "\n\n".join(all_texts), included, rejected


# ─────────────────────────────────────────────
# ALIAS RESOLUTION
# ─────────────────────────────────────────────
def resolve_subject(user_input: str, available_subjects: List[str]) -> Optional[Tuple[str, Optional[str]]]:
    """Resolve user input to canonical subject name."""
    q = user_input.strip().lower()
    if not q:
        return None

    if q in SUBJECT_ALIASES:
        canonical = SUBJECT_ALIASES[q]
        if q in SUBJECTS_WITH_LAB_THEORY:
            return (canonical, q)
        if canonical in available_subjects:
            return (canonical, None)
        for subj in available_subjects:
            if canonical.lower() in subj.lower() or subj.lower() in canonical.lower():
                return (subj, None)

    for subj in available_subjects:
        if subj.lower() == q:
            return (subj, None)

    matches = [s for s in available_subjects if q in s.lower()]
    if len(matches) == 1:
        return (matches[0], None)

    query_words = set(q.split())
    scored = []
    for subj in available_subjects:
        subj_words = set(subj.lower().split())
        overlap = len(query_words & subj_words)
        if overlap > 0:
            scored.append((overlap, subj))
    scored.sort(reverse=True)
    if scored:
        return (scored[0][1], None)

    return None


# ─────────────────────────────────────────────
# ANALYSIS PROMPTS
# ─────────────────────────────────────────────
def build_analysis_prompt(subject: str, exam: str, num_papers: int) -> str:
    exam_context = {
        "T1": "T1 (Test 1) - first ~30% of syllabus",
        "T2": "T2 (Test 2) - middle ~30% of syllabus (weeks 6-10)",
        "T3": "T3 (End Semester) - full syllabus, mix of T1+T2+new content",
    }.get(exam, exam)

    return f"""You are an expert academic analyst specialising in exam paper analysis.

You will be given the FULL TEXT of {num_papers} previous year question paper(s)
for the subject: **{subject}**
Exam type: **{exam_context}**

Your task: Perform a THOROUGH analysis and produce a structured JSON output
with the following schema (respond with ONLY valid JSON, no extra text):

{{
  "papers_analyzed": <int>,
  "years_covered": "<string like '2020-2025' or 'various'>",

  "topic_frequency": [
    {{
      "topic": "<topic name>",
      "count": <int - how many times asked>,
      "typical_marks": <int - average marks when asked>,
      "priority": "HIGH | MEDIUM | LOW"
    }}
  ],

  "question_type_distribution": {{
    "long_answer_percent": <int 0-100>,
    "short_answer_percent": <int 0-100>,
    "mcq_percent": <int 0-100>,
    "numerical_percent": <int 0-100>
  }},

  "marks_pattern": {{
    "total_marks_typical": <int>,
    "most_common_question_marks": <int>,
    "notes": "<brief string about marks distribution pattern>"
  }},

  "recurring_questions": [
    {{
      "question_pattern": "<the recurring question or pattern>",
      "frequency": <int>,
      "topic": "<topic it belongs to>"
    }}
  ],

  "must_study_topics": ["<topic 1>", "<topic 2>"],

  "coverage_summary": "<2-3 sentence summary of what topics dominate>",

  "difficulty_trend": "<one line: is the paper getting harder/easier/stable>"
}}

For topic_frequency: list at least 8-15 topics, sorted by count descending.
For recurring_questions: top 5-10 recurring patterns.
For must_study_topics: top 5-8 topics ranked by importance.

Important:
- Base ALL analysis strictly on the provided papers.
- Do NOT invent statistics — count carefully.
- Output ONLY the JSON. No markdown fences, no explanation.
"""


def build_practice_paper_prompt(
    subject: str, exam: str, analysis_json: str,
    lecture_syllabus: str, num_papers: int,
) -> str:
    t3_special = ""
    if exam == "T3":
        t3_special = """

CRITICAL FOR T3 (End Sem):
- T3 papers cover the FULL syllabus.
- Include ~30% questions from T1 topics (earlier material)
- Include ~30% questions from T2 topics (middle material)
- Include ~40% questions from post-T2 / new topics
- Match this weightage carefully.
"""

    return f"""You are an expert examination paper setter for the subject: **{subject}**
Exam type: **{exam}**

You have access to:
1. Analysis of {num_papers} previous year question papers (JSON below)
2. Lecture syllabus overview
{t3_special}

ANALYSIS JSON:
{analysis_json}

LECTURE SYLLABUS:
{lecture_syllabus}

TASK: Generate a PREDICTED/PRACTICE question paper for the upcoming {exam} exam.

Requirements:
- Match the marks distribution and question type distribution from PYQs.
- Prioritize "must_study_topics" and high-frequency topics.
- Generate NEW questions inspired by recurring PYQ patterns (not exact copies).
- Include a mix of question types (Long, Short, MCQ, Numerical).
- Total marks should match typical PYQ marks.
- Number every question and mention marks in [brackets].
- For each question, provide **answer + brief explanation** IMMEDIATELY below.

FORMAT (strict):

### Q1. [<marks> marks] [<TopicName>]
<question text>

**Answer:** <answer>
**Explanation:** <brief 2-3 line explanation>

---

### Q2. [<marks> marks] [<TopicName>]
...

Continue until total marks reach typical value.
"""


# ─────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────
def run_analysis(content: str, subject: str, exam: str, num_papers: int) -> Dict:
    """Send papers to LLM, get structured JSON analysis."""
    MAX_WORDS = 14000
    word_count = len(content.split())
    if word_count > MAX_WORDS:
        words = content.split()
        content = " ".join(words[:MAX_WORDS])
        print(f"   Truncated PYQ content to {MAX_WORDS} words")

    system_prompt = build_analysis_prompt(subject, exam, num_papers)
    user_msg = f"Previous year question papers content:\n\n{content}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]

    print("   Analyzing papers with LLM...")
    raw_response = get_answer(messages)
    raw_response = raw_response.strip()

    if raw_response.startswith("```"):
        raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response)
        raw_response = re.sub(r"\s*```$", "", raw_response)

    match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if match:
        raw_response = match.group(0)

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"   [WARN] LLM returned non-JSON output: {e}")
        return {"_parse_error": True, "raw": raw_response}


def generate_practice_paper(
    analysis: Dict, subject: str, exam: str,
    lecture_syllabus: str, num_papers: int,
) -> str:
    """Generate predicted practice paper based on analysis."""
    analysis_str = json.dumps(analysis, indent=2)

    system_prompt = build_practice_paper_prompt(
        subject, exam, analysis_str, lecture_syllabus, num_papers
    )
    user_msg = f"Generate the predicted practice paper for {subject} {exam} now."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_msg},
    ]

    print("   Generating predicted practice paper...")
    return get_answer(messages)


# ─────────────────────────────────────────────
# PARSE PRACTICE PAPER
# ─────────────────────────────────────────────
def parse_practice_paper(paper_text: str) -> List[Dict]:
    """Parse practice paper into question dicts."""
    questions = []

    if not paper_text.rstrip().endswith("---"):
        paper_text = paper_text.rstrip() + "\n\n---\n"

    chunks = re.split(r"(?=^#{1,3}\s*Q\d+\.)", paper_text, flags=re.MULTILINE)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        header_match = re.match(r"#{1,3}\s*(Q\d+)\.?\s*(.*)", chunk)
        if not header_match:
            continue

        qnum = header_match.group(1)
        header = chunk.split("\n", 1)[0].lstrip("#").strip()

        ans_match = re.search(
            r"\*\*Answer:\*\*\s*(.+?)(?=\n\s*\*\*Explanation|\n\s*---|\Z)",
            chunk, flags=re.DOTALL | re.IGNORECASE,
        )
        exp_match = re.search(
            r"\*\*Explanation:\*\*\s*(.+?)(?=\n\s*---|\Z)",
            chunk, flags=re.DOTALL | re.IGNORECASE,
        )
        answer = ans_match.group(1).strip() if ans_match else ""
        explanation = exp_match.group(1).strip() if exp_match else ""

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

        questions.append({
            "number": qnum,
            "header": header,
            "question_block": question_block,
            "answer": answer,
            "explanation": explanation,
        })

    return questions
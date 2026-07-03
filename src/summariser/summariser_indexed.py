# src/IR/summariser_indexed.py
#
# Chunk-based summarizer that uses pre-indexed data from chunks.json
# instead of re-downloading files from Google Drive.

import os
import re
import json
import glob
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


def load_chunks() -> list:
    global _chunks_cache
    if _chunks_cache is not None:
        return _chunks_cache
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Index not found: {INDEX_PATH}")
    with open(INDEX_PATH, encoding="utf-8") as f:
        _chunks_cache = json.load(f)
    print(f"✅ Summariser: loaded {len(_chunks_cache)} chunks")
    return _chunks_cache


def load_url_map() -> dict:
    """Map (branch|sem|subject|filename) → gdrive URL for display."""
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
                    _url_map[f"{branch}|{sem}|{subject}|{name}"] = url
        except Exception:
            pass

    return _url_map


# ─────────────────────────────────────────────
# Browse hierarchy (from chunk metadata)
# ─────────────────────────────────────────────
def get_semester_folders() -> dict:
    """
    Get available semesters like SEM_FOLDERS from summariser.py.
    Returns {sem: [branches]} for compatibility.
    """
    chunks = load_chunks()
    result = defaultdict(set)

    for chunk in chunks:
        sem    = chunk.get("semester", "") or "?"
        branch = chunk.get("branch",   "") or "Unknown"
        result[sem].add(branch)

    return {sem: sorted(list(branches)) for sem, branches in sorted(result.items())}


# For compatibility with existing chatbot.py that imports SEM_FOLDERS
SEM_FOLDERS = get_semester_folders()


def load_gdrive_links(semester: str) -> list:
    """
    Return all file entries for a given semester (all branches).
    Mimics the original summariser.py interface.
    """
    chunks = load_chunks()
    url_map = load_url_map()

    # Get unique files in this semester
    seen = set()
    entries = []

    for chunk in chunks:
        if str(chunk.get("semester", "")) != str(semester):
            continue

        branch   = chunk.get("branch",   "")
        subject  = chunk.get("subject",  "Other") or "Other"
        category = chunk.get("category", "Other") or "Other"
        fname    = chunk.get("source_file", "")

        if not fname:
            continue

        # Use composite key to preserve duplicates across branches
        key = f"{branch}|{semester}|{subject}|{fname}"
        if key in seen:
            continue
        seen.add(key)

        entries.append({
            "item_name":    fname,
            "subject":      subject,
            "category":     category,
            "branch":       branch,
            "file_id":      "",    # not needed — we use indexed chunks
            "original_url": url_map.get(key, ""),
            "is_folder":    False,
        })

    return entries


def get_subjects(links: list) -> list:
    """Get unique subjects from links."""
    return sorted(set(link["subject"] for link in links))


def get_lecture_files(links: list, subject: str) -> list:
    """Get lecture files for a subject, naturally sorted."""
    lectures = [
        link for link in links
        if link["subject"] == subject
        and link["category"] == "Lectures"
        and not link.get("is_folder", False)
    ]

    def natural_sort_key(item):
        name = item.get("item_name", "")
        numbers = re.findall(r"\d+", name)
        first_num = int(numbers[0]) if numbers else 999
        return (first_num, name.lower())

    lectures.sort(key=natural_sort_key)
    return lectures


# ─────────────────────────────────────────────
# Get chunks for a specific file
# ─────────────────────────────────────────────
def get_chunks_for_file(
    filename: str,
    branch: str = None,
    semester: str = None,
    subject: str = None,
) -> list:
    """
    Get all chunks for a specific file (uses metadata filtering).
    Returns chunks in original order (sorted by chunk_id or location).
    """
    chunks = load_chunks()

    matches = []
    for chunk in chunks:
        if chunk.get("source_file") != filename:
            continue
        if branch   and chunk.get("branch")   != branch:   continue
        if semester and str(chunk.get("semester")) != str(semester): continue
        if subject  and chunk.get("subject")  != subject:  continue
        matches.append(chunk)

    # Sort by chunk_id or location
    matches.sort(key=lambda c: (
        c.get("chunk_id", 0),
        c.get("location", ""),
    ))

    return matches


# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────
SINGLE_LECTURE_PROMPT = """You are an expert academic summariser.
Summarise the following lecture content thoroughly and precisely.

Your summary MUST include:

## Summary
A clear, structured summary covering every major concept discussed.

## Key Formulae & Equations
List ALL mathematical formulae, equations, theorems, or formal
definitions found in the text. Use proper notation.
If none exist, write "No formulae found in this lecture."

## Important Points
Numbered list of every critical concept, definition, or fact
a student must know.

## Quick Memorisation Bullets
- 8-15 concise bullet points a student can revise in 5 minutes
  before an exam. Focus on what is most likely to be asked.

Be thorough - do NOT skip content.
"""


SERIES_LECTURE_PROMPT = """You are an expert academic summariser.
You are given the combined content of MULTIPLE lecture notes
(in order). Produce a UNIFIED summary across all of them.

Your summary MUST include:

## Combined Summary
A comprehensive summary spanning all the lectures provided.
Organise by topic / theme, not by individual lecture.

## All Formulae & Equations
Collect ALL mathematical formulae, equations, theorems, or
formal definitions across all lectures. Group by topic.
If none exist, write "No formulae found."

## Important Points (across all lectures)
Numbered list of every critical concept, definition, or fact.

## Lecture Flow & Connections
Briefly describe how the topics connect from one lecture to the next.

## Quick Memorisation Bullets
- 12-20 concise bullet points covering the entire lecture series.
"""


CHUNK_EXTRACT_PROMPT = """You are extracting key content from PART {i} of {total} of a lecture.

Extract ALL important content densely:
- Key concepts and definitions
- Formulae, equations, theorems (with proper notation)
- Important examples
- Critical facts

Do NOT add section headers. Do NOT summarize — extract everything important.
Later parts will be merged.
"""


MERGE_PROMPT = """You are creating a FINAL unified summary of a lecture.
You are given extracted content from different parts of the same lecture.

Produce ONE coherent summary with this structure:

## Summary
A clear, structured summary covering every major concept.

## Key Formulae & Equations
List ALL formulae/equations/theorems found across all parts. Use proper notation.
If none exist, write "No formulae found in this lecture."

## Important Points
Numbered list of every critical concept, definition, or fact.

## Quick Memorisation Bullets
- 8-15 concise bullet points for quick revision.

REMOVE duplicates. Merge similar points. Be thorough but coherent.
"""


# ─────────────────────────────────────────────
# Token / word budget
# ─────────────────────────────────────────────
CHUNK_BUDGET   = 3500   # max words per LLM call for chunk extraction
SINGLE_BUDGET  = 4000   # if lecture <= this, do single call
SERIES_BUDGET  = 5000   # if series <= this, combine into single call


# ─────────────────────────────────────────────
# Merge chunks into content within budget
# ─────────────────────────────────────────────
def batch_chunks(chunks: list, max_words: int) -> list:
    """
    Group chunks into batches, each under max_words.
    Returns list of {'text': combined, 'sources': [chunk refs]}
    """
    batches = []
    current_text = []
    current_words = 0

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if not text:
            continue

        chunk_words = len(text.split())

        # If single chunk exceeds budget, put it alone
        if chunk_words > max_words:
            if current_text:
                batches.append({
                    "text": "\n\n".join(current_text),
                    "count": len(current_text),
                })
                current_text = []
                current_words = 0
            batches.append({
                "text": text,
                "count": 1,
            })
            continue

        # If adding would exceed budget, flush and start new batch
        if current_words + chunk_words > max_words and current_text:
            batches.append({
                "text": "\n\n".join(current_text),
                "count": len(current_text),
            })
            current_text = []
            current_words = 0

        current_text.append(text)
        current_words += chunk_words

    if current_text:
        batches.append({
            "text": "\n\n".join(current_text),
            "count": len(current_text),
        })

    return batches


# ─────────────────────────────────────────────
# MAIN: Summarize a single lecture (from index)
# ─────────────────────────────────────────────
def summarise_single_lecture(semester: str, lecture_info: dict) -> tuple:
    """
    Summarize a single lecture using its indexed chunks.
    Returns (summary_text, success_flag, view_url).
    """
    item_name = lecture_info.get("item_name", "Unknown")
    subject   = lecture_info.get("subject",   "Unknown")
    branch    = lecture_info.get("branch",    "")
    view_url  = lecture_info.get("original_url", "")

    print(f"\n📖 Summarizing: {item_name}")

    # ── Get chunks for this file ──
    file_chunks = get_chunks_for_file(
        filename = item_name,
        branch   = branch,
        semester = semester,
        subject  = subject,
    )

    if not file_chunks:
        return (
            f"❌ No indexed content found for: {item_name}",
            False,
            view_url,
        )

    total_words = sum(len(c.get("text", "").split()) for c in file_chunks)
    print(f"   Found {len(file_chunks)} chunks ({total_words} words)")

    # ── Small lecture: single call ──
    if total_words <= SINGLE_BUDGET:
        combined = "\n\n".join(c.get("text", "") for c in file_chunks)

        messages = [
            {"role": "system", "content": SINGLE_LECTURE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Lecture: {item_name}\n"
                    f"Subject: {subject}\n\n"
                    f"Content:\n{combined}"
                ),
            },
        ]
        print("   🤖 Generating summary (single call)...")
        summary = get_answer(messages)
        return summary, True, view_url

    # ── Large lecture: batch extract → merge ──
    print(f"   📦 Large lecture — batching chunks...")
    batches = batch_chunks(file_chunks, max_words=CHUNK_BUDGET)
    print(f"   → {len(batches)} batches to process")

    partials = []
    for i, batch in enumerate(batches, 1):
        print(f"   ⚙️  Batch {i}/{len(batches)} ({batch['count']} chunks)")
        prompt = CHUNK_EXTRACT_PROMPT.format(i=i, total=len(batches))

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Lecture: {item_name}\n"
                    f"Part {i}/{len(batches)}:\n\n{batch['text']}"
                ),
            },
        ]
        partial = get_answer(messages)
        partials.append(f"[Part {i}]\n{partial}")

    # ── Merge ──
    print(f"   🔀 Merging {len(partials)} extracts...")
    merged_text = "\n\n---\n\n".join(partials)

    messages = [
        {"role": "system", "content": MERGE_PROMPT},
        {
            "role": "user",
            "content": (
                f"Lecture: {item_name}\n"
                f"Subject: {subject}\n\n"
                f"Extracted content:\n{merged_text}"
            ),
        },
    ]
    final = get_answer(messages)
    return final, True, view_url


# ─────────────────────────────────────────────
# MAIN: Summarize a series of lectures
# ─────────────────────────────────────────────
def summarise_lecture_series(
    semester: str,
    lecture_list: list,
    subject: str,
) -> tuple:
    """
    Summarize a series of lectures from indexed data.
    Returns (summary_text, success_flag, list_of_lecture_links).
    """
    print(f"\n📚 Summarizing {len(lecture_list)} lectures for {subject}")

    processed_links = []
    all_lectures = []   # list of {name, url, chunks}

    for lec in lecture_list:
        item_name = lec.get("item_name", "Unknown")
        branch    = lec.get("branch",    "")
        view_url  = lec.get("original_url", "")

        chunks = get_chunks_for_file(
            filename = item_name,
            branch   = branch,
            semester = semester,
            subject  = subject,
        )

        if not chunks:
            print(f"   ⚠️  Skipping (no chunks): {item_name}")
            continue

        all_lectures.append({
            "name":   item_name,
            "url":    view_url,
            "chunks": chunks,
            "words":  sum(len(c.get("text", "").split()) for c in chunks),
        })
        processed_links.append({"name": item_name, "url": view_url})
        print(f"   ✅ {item_name} ({len(chunks)} chunks)")

    if not all_lectures:
        return "No indexed content found for these lectures.", False, processed_links

    total_words = sum(l["words"] for l in all_lectures)
    print(f"\n   Total: {len(all_lectures)} lectures, {total_words} words")

    # ── Small series: one call ──
    if total_words <= SERIES_BUDGET:
        combined = "\n\n".join(
            f"{'='*60}\nLECTURE: {l['name']}\n{'='*60}\n"
            + "\n\n".join(c.get("text", "") for c in l["chunks"])
            for l in all_lectures
        )

        messages = [
            {"role": "system", "content": SERIES_LECTURE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Subject: {subject}\n"
                    f"Lectures: {', '.join(l['name'] for l in all_lectures)}\n\n"
                    f"Combined Content:\n{combined}"
                ),
            },
        ]
        print("   🤖 Generating combined summary (single call)...")
        summary = get_answer(messages)
        return summary, True, processed_links

    # ── Large series: summarize each lecture, then merge ──
    print(f"   📦 Large series — per-lecture summaries then merge")

    lecture_summaries = []

    for i, lec in enumerate(all_lectures, 1):
        print(f"\n   📖 Lecture {i}/{len(all_lectures)}: {lec['name']} ({lec['words']} words)")

        if lec["words"] > SINGLE_BUDGET:
            # This lecture itself is big — use batch approach
            batches = batch_chunks(lec["chunks"], max_words=CHUNK_BUDGET)
            print(f"      → {len(batches)} batches")

            partials = []
            for j, batch in enumerate(batches, 1):
                print(f"      ⚙️  Batch {j}/{len(batches)}")
                prompt = CHUNK_EXTRACT_PROMPT.format(i=j, total=len(batches))
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": f"Lecture: {lec['name']}\n\n{batch['text']}"},
                ]
                partials.append(get_answer(messages))

            # Merge this lecture's parts
            merge_msg = [
                {"role": "system", "content":
                    f"Combine these extracted parts into a dense summary of lecture '{lec['name']}'. "
                    f"Keep all facts, formulae, and key points. Be thorough."
                },
                {"role": "user", "content": "\n\n---\n\n".join(partials)},
            ]
            lecture_summary = get_answer(merge_msg)
        else:
            # Small enough for one call
            combined = "\n\n".join(c.get("text", "") for c in lec["chunks"])
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"Extract key concepts, formulae, and important points from this lecture. "
                        f"Be dense and thorough. No section headers — just content."
                    ),
                },
                {"role": "user", "content": f"Lecture: {lec['name']}\n\n{combined}"},
            ]
            lecture_summary = get_answer(messages)

        lecture_summaries.append(f"### {lec['name']}\n{lecture_summary}")

    # ── Final merge across all lectures ──
    print(f"\n   🔀 Merging {len(lecture_summaries)} lecture summaries...")
    merged = "\n\n---\n\n".join(lecture_summaries)

    messages = [
        {"role": "system", "content": SERIES_LECTURE_PROMPT},
        {
            "role": "user",
            "content": (
                f"Subject: {subject}\n"
                f"Lectures included: {', '.join(l['name'] for l in all_lectures)}\n\n"
                f"Per-lecture summaries:\n{merged}"
            ),
        },
    ]
    final = get_answer(messages)
    return final, True, processed_links
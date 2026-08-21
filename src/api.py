import os
import sys
import json

from config import PROJECT_ROOT,all_imports
all_imports()
os.chdir(PROJECT_ROOT)
# ─────────────────────────────────────────────
# Now import everything
# ─────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from chatbot import RAGChatbot


# ─────────────────────────────────────────────
# Initialize FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="EduQuest API",
    description="RAG chatbot API over PDF + PPTX documents",
    version="1.0.0",
)

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eduquest-jiit.vercel.app",
        "https://eduquest-jiit.me",
        "https://www.eduquest-jiit.me",
        "http://localhost:5500",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Load chatbot once at startup
# ─────────────────────────────────────────────
print(f"Project root: {PROJECT_ROOT}")
print("Loading chatbot...")
bot = RAGChatbot()
bot.chat("Hello")  # Load embeddings and initialize model
print("✅ Chatbot ready")


# ─────────────────────────────────────────────
# Load Google Drive links (optional)
# ─────────────────────────────────────────────
import glob

def load_file_links():
    """Find all gdrive_links.json files. Keys are unique per branch+sem."""
    mapping       = {}   # composite_key → info
    name_index    = {}   # filename → list of composite_keys (for lookup)
    dataset_dir   = os.path.join(PROJECT_ROOT, "dataset")

    if not os.path.exists(dataset_dir):
        print(f"⚠️  Dataset folder not found: {dataset_dir}")
        return mapping, name_index

    pattern = os.path.join(dataset_dir, "**", "gdrive_links.json")
    json_files = glob.glob(pattern, recursive=True)

    print(f"\n📂 Found {len(json_files)} gdrive_links.json files")

    for json_path in json_files:
        parts  = os.path.normpath(json_path).split(os.sep)
        branch = ""
        sem    = ""
        subject = ""
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
                name = item.get("item_name", "").strip()
                url  = item.get("original_url", "")
                subject = item.get("subject", "").strip()
                if not name or not url:
                    continue

                # ✅ Use composite key (unique per branch+sem)
                composite_key = f"{branch}_{sem}_{subject}_{name}"

                mapping[composite_key] = {
                    "name":     name,
                    "url":      url,
                    "subject":  subject,
                    "category": item.get("category", ""),
                    "branch":   branch,
                    "semester": sem,
                }

                # ✅ Build reverse index for lookup by filename
                name_index.setdefault(name, []).append(composite_key)

            print(f"   ✅ [{branch}/Sem {sem}] {len(data)} entries")

        except Exception as e:
            print(f"   ❌ {json_path}: {e}")

    print(f"✅ Total: {len(mapping)} entries, {len(name_index)} unique filenames")

    # Find duplicates for awareness
    # dupes = {n: keys for n, keys in name_index.items() if len(keys) > 1}
    # if dupes:
    #     print(f"⚠️  {len(dupes)} filenames appear in multiple branches/semesters:")
    #     for name, keys in list(dupes.items())[:10]:
    #         print(f"   '{name}' → {keys}")

    return mapping, name_index

# Load globally
FILE_LINKS, NAME_INDEX = load_file_links()

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default"


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]


# ─────────────────────────────────────────────
# Session management
# ─────────────────────────────────────────────
sessions: dict[str, RAGChatbot] = {}


def get_bot(session_id: str) -> RAGChatbot:
    if session_id not in sessions:
        sessions[session_id] = RAGChatbot()
    return sessions[session_id]


def enrich_sources(sources):
    """Add gdrive URL + metadata to each source.
    If a filename exists in multiple branches, show ALL locations.
    """
    enriched = []
    for s in sources:
        fname = s.get("source_file", "")
        s_copy = dict(s)

        # Find all locations of this file
        composite_keys = NAME_INDEX.get(fname, [])

        if composite_keys:
            # Use first match for primary info
            info = FILE_LINKS[composite_keys[0]]
            s_copy["url"]      = info.get("url", "")
            s_copy["subject"]  = info.get("subject", "")
            s_copy["branch"]   = info.get("branch", "")
            s_copy["semester"] = info.get("semester", "")

            # If file exists in multiple branches, list them
            if len(composite_keys) > 1:
                locations = [
                    {
                        "branch":   FILE_LINKS[k]["branch"],
                        "semester": FILE_LINKS[k]["semester"],
                        "url":      FILE_LINKS[k]["url"],
                    }
                    for k in composite_keys
                ]
                s_copy["all_locations"] = locations
        else:
            s_copy["url"]      = ""
            s_copy["subject"]  = ""
            s_copy["branch"]   = ""
            s_copy["semester"] = ""

        enriched.append(s_copy)
    return enriched

# ═════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "status":  "online",
        "service": "EduQuest API",
        "docs":    "/docs",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        session_bot = get_bot(req.session_id)
        answer, sources = session_bot.chat(req.message)
        enriched = enrich_sources(sources)
        return ChatResponse(answer=answer, sources=enriched)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset")
def reset_chat(session_id: str = "default"):
    if session_id in sessions:
        sessions[session_id].reset_history()
        return {"status": "cleared", "session_id": session_id}
    return {"status": "no_session", "session_id": session_id}


@app.get("/stats")
def get_stats():
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)

        tree = {}
        seen_files_per_group = {}

        for chunk in chunks:
            branch   = chunk.get("branch",   "") or "Unknown"
            sem      = chunk.get("semester", "") or "?"
            subject  = chunk.get("subject",  "") or "Other"
            category = normalize_category(chunk.get("category", ""))
            fname    = chunk.get("source_file", "")

            if not fname:
                continue

            group_key = (branch, sem, subject, category)
            if group_key not in seen_files_per_group:
                seen_files_per_group[group_key] = set()

            if fname in seen_files_per_group[group_key]:
                continue
            seen_files_per_group[group_key].add(fname)

            url_key = f"{branch}|{sem}|{subject}|{fname}"
            url = FILE_LINKS.get(url_key, {}).get("url", "")

            tree.setdefault(branch, {}) \
                .setdefault(sem, {}) \
                .setdefault(subject, {}) \
                .setdefault(category, []) \
                .append({
                    "name": fname,
                    "url":  url,
                })

        # ✅ NATURAL SORT files in each category
        for branch in tree:
            for sem in tree[branch]:
                for subject in tree[branch][sem]:
                    for category in tree[branch][sem][subject]:
                        tree[branch][sem][subject][category].sort(
                            key=lambda f: natural_sort_key(f["name"])
                        )

        all_files = set(chunk.get("source_file", "") for chunk in chunks)

        return {
            "total_files":  len(all_files),
            "total_chunks": len(chunks),
            "tree":         tree,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    """Build tree with file URLs from gdrive_links."""
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)

        tree = {}
        seen_files = {}   # (branch, sem, subject, category, fname) → already added

        for chunk in chunks:
            branch   = chunk.get("branch",   "") or "Unknown"
            sem      = chunk.get("semester", "") or "?"
            subject  = chunk.get("subject",  "") or "Other"
            category = normalize_category(chunk.get("category", ""))
            fname    = chunk.get("source_file", "")

            if not fname:
                continue

            group_key = (branch, sem, subject, category, fname)
            if group_key in seen_files:
                continue
            seen_files[group_key] = True

            # ✅ Look up URL from FILE_LINKS
            url = ""
            # Try composite key
            url_key = f"{branch}|{sem}|{subject}|{fname}"
            if url_key in FILE_LINKS:
                info = FILE_LINKS[url_key]
                url = info.get("url", "") if isinstance(info, dict) else ""

            # Fallback: search by filename in NAME_INDEX
            if not url and fname in NAME_INDEX:
                for composite_key in NAME_INDEX[fname]:
                    if composite_key in FILE_LINKS:
                        info = FILE_LINKS[composite_key]
                        url = info.get("url", "") if isinstance(info, dict) else ""
                        if url:
                            break

            tree.setdefault(branch, {}) \
                .setdefault(sem, {}) \
                .setdefault(subject, {}) \
                .setdefault(category, []) \
                .append({
                    "name": fname,
                    "url":  url,
                })

        # Natural sort files in each category
        for branch in tree:
            for sem in tree[branch]:
                for subject in tree[branch][sem]:
                    for category in tree[branch][sem][subject]:
                        tree[branch][sem][subject][category].sort(
                            key=lambda f: natural_sort_key(f["name"])
                        )

        all_files = set(chunk.get("source_file", "") for chunk in chunks)

        return {
            "total_files":  len(all_files),
            "total_chunks": len(chunks),
            "tree":         tree,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def normalize_category(cat: str) -> str:
    """Normalize various category names to consistent labels."""
    if not cat:
        return "Other"
    c = cat.lower().strip()

    if any(k in c for k in ["lecture", "lec", "slide", "ppt", "class note"]):
        return "Lectures"
    if any(k in c for k in ["tutorial", "tut"]):
        return "Tutorials"
    if any(k in c for k in ["pyq", "previous year", "past paper", "question paper", "previous"]):
        return "PYQs"
    if any(k in c for k in ["assignment", "hw", "homework"]):
        return "Assignments"
    if any(k in c for k in ["lab", "practical", "experiment"]):
        return "Lab"
    if any(k in c for k in ["book", "textbook", "reference"]):
        return "Books"
    if any(k in c for k in ["syllabus", "course description", "course outline"]):
        return "Syllabus"
    if any(k in c for k in ["solution", "answer"]):
        return "Solutions"
    if any(k in c for k in ["notes", "note"]):
        return "Notes"

    # Capitalize first letter as fallback
    return cat.strip().title() or "Other"

def natural_sort_key(text: str) -> tuple:
    """
    Smart sort: extracts lecture number from various naming patterns.
    Handles: L1, L-1, Lec 1, Lecture 1, Chapter 1, etc.
    """
    import re

    text_lower = str(text).lower().strip()

    patterns = [
        r"^(?:lecture|lec|chapter|ch|lesson)[\s\-_]*(\d+)",
        r"^l[\s\-_]*(\d+)",
        r"^(\d+)",
    ]

    for pattern in patterns:
        m = re.match(pattern, text_lower)
        if m:
            num = int(m.group(1))
            remaining = text_lower[m.end():].strip()
            return (0, num, remaining)

    return (1, 0, text_lower)


# ════════════════════════════════════════════════════════
# RESUME RANKING ENDPOINTS
# ════════════════════════════════════════════════════════

from fastapi import UploadFile, File, Form
from resume_api import (
    analyze_resume,
    get_branch_role_tree,
    get_role_skills,
)


@app.get("/resume/branches")
def list_branches_roles():
    """Get all branches with their roles for cascading dropdowns."""
    return {"tree": get_branch_role_tree()}


@app.get("/resume/skills/{role_name}")
def get_skills_for_role(role_name: str):
    """Get required skills for a specific role."""
    skills = get_role_skills(role_name)
    return {"role": role_name, "skills": skills, "count": len(skills)}


@app.post("/resume/analyze")
async def analyze_resume_endpoint(
    file:       UploadFile = File(...),
    name:       str        = Form(...),
    enrollment: str        = Form(...),
    year:       str        = Form(...),
    branch:     str        = Form(...),
    job_role:   str        = Form(...),
):
    """Analyze uploaded resume with year/branch/enrollment tracking."""
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Name is required")
        if not enrollment.strip():
            raise HTTPException(status_code=400, detail="Enrollment is required")
        if year not in ("1", "2", "3", "4", "5"):
            raise HTTPException(status_code=400, detail="Year must be 1-5")
        if not branch.strip():
            raise HTTPException(status_code=400, detail="Branch is required")

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        ext = file.filename.lower().split('.')[-1]
        if ext not in ['pdf', 'pptx']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '.{ext}'. Use PDF or PPTX."
            )

        result = analyze_resume(
            filename   = file.filename,
            file_bytes = file_bytes,
            user_name  = name.strip(),
            enrollment = enrollment.strip(),
            year       = year,
            branch     = branch.strip(),
            job_role   = job_role.strip(),
        )
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))   

@app.get("/debug/duplicates")
def debug_duplicates():
    """Show all files that have multiple entries and where they appear."""

    # Group by filename to see where duplicates exist
    by_name = {}
    for composite_key, info in FILE_LINKS.items():
        name = info["name"]
        by_name.setdefault(name, []).append({
            "composite_key": composite_key,
            "branch":   info["branch"],
            "semester": info["semester"],
            "subject":  info["subject"],
            "category": info["category"],
            "url":      info["url"][:60] + "..." if len(info["url"]) > 60 else info["url"],
        })

    # Only show files with multiple locations
    duplicates = {name: locs for name, locs in by_name.items() if len(locs) > 1}

    # Also check what's in the index
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)
        indexed_files = set(c["source_file"] for c in chunks)
    except Exception:
        indexed_files = set()

    # Check: are duplicates actually in the index?
    duplicates_in_index = {}
    duplicates_NOT_in_index = {}
    for name, locs in duplicates.items():
        if name in indexed_files:
            duplicates_in_index[name] = locs
        else:
            duplicates_NOT_in_index[name] = locs

    return {
        "total_file_links":       len(FILE_LINKS),
        "unique_filenames":       len(by_name),
        "total_duplicates":       len(duplicates),
        "duplicates_in_index":    len(duplicates_in_index),
        "duplicates_NOT_in_index": len(duplicates_NOT_in_index),

        "sample_duplicates_in_index": dict(list(duplicates_in_index.items())[:5]),
        "sample_duplicates_NOT_in_index": dict(list(duplicates_NOT_in_index.items())[:5]),
    }
    
    
# ════════════════════════════════════════════════════════
# QUIZ ENDPOINTS (uses indexed data)
# ════════════════════════════════════════════════════════

from quiz.quiz_web import (
    get_browse_tree     as quiz_browse_tree,
    list_files          as quiz_list_files,
    generate_quiz_indexed,
    save_quiz_indexed,
    score_quiz          as quiz_score_answers,
)


class QuizIndexedRequest(BaseModel):
    branch:         str | None       = None
    sem:            str | None       = None
    subject:        str | None       = None
    category:       str | None       = None
    file_names:     list[str] | None = None
    question_types: list[str] | None = None
    difficulty:     str              = "Medium"
    num_questions:  int | None       = None
    save_to_disk:   bool | None      = False


class QuizScoreRequest(BaseModel):
    questions:    list[dict]
    user_answers: list

@app.get("/quiz/files")
def quiz_files_endpoint(
    branch:   str | None = None,
    sem:      str | None = None,
    subject:  str | None = None,
    category: str | None = None,
):
    """List files matching the given filters."""
    try:
        files = quiz_list_files(
            branch   = branch,
            sem      = sem,
            subject  = subject,
            category = category,
        )
        return {"files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/browse")
def quiz_browse_endpoint():
    try:
        return {"tree": quiz_browse_tree()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quiz/generate")
def quiz_generate_endpoint(req: QuizIndexedRequest):
    try:
        result = generate_quiz_indexed(
            branch         = req.branch,
            sem            = req.sem,
            subject        = req.subject,
            category       = req.category,
            file_names     = req.file_names,           # ← NEW
            question_types = req.question_types or ["MCQ", "True/False", "Short Answer"],
            difficulty     = req.difficulty,
            num_questions  = req.num_questions,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Generation failed"))

        if req.save_to_disk:
            try:
                saved = save_quiz_indexed(result)
                result["saved_path"] = os.path.relpath(saved, PROJECT_ROOT) if saved else None
            except Exception as e:
                print(f"Save failed: {e}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quiz/score")
def quiz_score_endpoint(req: QuizScoreRequest):
    """Score user's quiz answers."""
    try:
        return quiz_score_answers(req.questions, req.user_answers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ════════════════════════════════════════════════════════
# PYQ ANALYSER ENDPOINTS (uses indexed chunks, any year)
# ════════════════════════════════════════════════════════

from pyq_analyser_indexed import (
    get_all_years            as pyq_get_all_years,
    get_subjects_with_pyqs   as pyq_get_subjects,
    get_pyq_files            as pyq_get_files,
    get_pyq_files_for_exam   as pyq_get_files_for_exam,
    get_lecture_context      as pyq_get_lecture_context,
    gather_pyq_content       as pyq_gather_content,
    run_analysis             as pyq_run_analysis,
    generate_practice_paper  as pyq_generate_paper,
    parse_practice_paper     as pyq_parse_paper,
    SUBJECT_ALIASES          as PYQ_SUBJECT_ALIASES,
    SUBJECTS_WITH_LAB_THEORY as PYQ_LAB_THEORY,
)


class PyqAnalyzeRequest(BaseModel):
    semester: str
    subject:  str
    exam:     str                       # T1 | T2 | T3
    mode:     str = "full"              # full | frequency | practice


@app.get("/pyq/years")
def pyq_years():
    """List all years/semesters that have any PYQ data."""
    try:
        years = pyq_get_all_years()
        return {"years": years, "count": len(years)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pyq/subjects/{semester}")
def pyq_subjects(semester: str):
    """List subjects that have PYQs in a semester/year."""
    try:
        subjects = pyq_get_subjects(semester)

        result = []
        for s in subjects:
            aliases = [k for k, v in PYQ_SUBJECT_ALIASES.items() if v == s]
            result.append({
                "name":    s,
                "aliases": aliases[:5],
                "has_lab_theory": any(
                    s in (theory, lab)
                    for (theory, lab) in PYQ_LAB_THEORY.values()
                ),
            })
        return {"subjects": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pyq/papers/{semester}/{subject}")
def pyq_papers(semester: str, subject: str, exam: str | None = None):
    """List available PYQ papers for a subject (optionally filtered by exam)."""
    try:
        all_pyqs = pyq_get_files(semester, subject)

        if exam:
            filtered = pyq_get_files_for_exam(semester, subject, exam)
        else:
            filtered = all_pyqs

        return {
            "subject": subject,
            "exam":    exam,
            "total":   len(all_pyqs),
            "matched": len(filtered),
            "papers":  filtered,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pyq/analyze")
def pyq_analyze(req: PyqAnalyzeRequest):
    """Run full PYQ analysis using indexed data."""
    try:
        if req.exam not in ("T1", "T2", "T3"):
            raise HTTPException(status_code=400, detail="Exam must be T1, T2, or T3")

        # Get files for this exam
        matched = pyq_get_files_for_exam(req.semester, req.subject, req.exam)

        if not matched:
            all_files = pyq_get_files(req.semester, req.subject)
            return {
                "success":  False,
                "error":    f"No {req.exam} papers found for {req.subject}",
                "available_papers": [f["name"] for f in all_files],
            }

        # Gather + verify (from indexed chunks — NO GDRIVE)
        file_names = [f["name"] for f in matched]
        content, included, rejected = pyq_gather_content(
            req.semester, req.subject, file_names
        )

        if not content.strip():
            return {
                "success":   False,
                "error":     "No papers passed subject verification",
                "rejected":  rejected,
            }

        # Analyze
        analysis = pyq_run_analysis(content, req.subject, req.exam, len(included))

        if analysis.get("_parse_error"):
            return {
                "success": False,
                "error":   "Could not parse LLM output",
                "raw":     analysis.get("raw", "")[:500],
            }

        # Generate practice paper if needed
        practice_paper = None
        practice_questions = None
        if req.mode in ("full", "practice"):
            lecture_ctx = pyq_get_lecture_context(req.semester, req.subject)
            practice_paper = pyq_generate_paper(
                analysis, req.subject, req.exam, lecture_ctx, len(included)
            )
            if req.mode == "practice":
                practice_questions = pyq_parse_paper(practice_paper)

        return {
            "success":            True,
            "subject":            req.subject,
            "exam":               req.exam,
            "semester":           req.semester,
            "included_papers":    included,
            "rejected_papers":    rejected,
            "num_included":       len(included),
            "num_rejected":       len(rejected),
            "analysis":           analysis,
            "practice_paper":     practice_paper,
            "practice_questions": practice_questions,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

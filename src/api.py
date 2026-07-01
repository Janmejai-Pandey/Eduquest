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
    title="NaKari API",
    description="RAG chatbot API over PDF + PPTX documents",
    version="1.0.0",
)

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "service": "NaKari API",
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
    """Build tree using chunk metadata (works for all branches/sems)."""
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)

        # ✅ Use chunk metadata directly
        tree = {}
        seen_files_per_group = {}   # dedupe

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
                continue   # already added
            seen_files_per_group[group_key].add(fname)

            # Get URL from FILE_LINKS
            url_key = f"{branch}|{sem}|{subject}|{fname}"
            url = ""
            if url_key in FILE_LINKS:
                url = FILE_LINKS[url_key].get("url", "")

            tree.setdefault(branch, {}) \
                .setdefault(sem, {}) \
                .setdefault(subject, {}) \
                .setdefault(category, []) \
                .append({
                    "name": fname,
                    "url":  url,
                })

        # Count total unique files
        all_files = set()
        for chunk in chunks:
            all_files.add(chunk.get("source_file", ""))

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


# ════════════════════════════════════════════════════════
# RESUME RANKING ENDPOINTS
# ════════════════════════════════════════════════════════

from fastapi import UploadFile, File, Form
from resume_api import (
    analyze_resume,
    get_available_roles,
    get_csv_stats,
)


@app.get("/resume/roles")
def list_roles():
    """Get available job roles with their skills."""
    return {"roles": get_available_roles()}


@app.get("/resume/stats")
def resume_stats():
    """Get stats about existing rankings."""
    return get_csv_stats()


@app.post("/resume/analyze")
async def analyze_resume_endpoint(
    file:     UploadFile = File(...),
    name:     str        = Form(...),
    job_role: str        = Form(...),
    branch:   str        = Form(""),
    year:     int        = Form(0),
):
    """Analyze uploaded resume."""
    try:
        # Validation
        if not name.strip():
            raise HTTPException(status_code=400, detail="Name is required")

        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        if len(file_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Check extension
        ext = file.filename.lower().split('.')[-1]
        if ext not in ['pdf', 'pptx']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '.{ext}'. Use PDF or PPTX."
            )

        # Analyze
        result = analyze_resume(
            filename   = file.filename,
            file_bytes = file_bytes,
            user_name  = name.strip(),
            job_role   = job_role.strip(),
            branch     = branch.strip(),
            year       = year,
        )
        return result

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
    generate_quiz_indexed,
    save_quiz_indexed,
    score_quiz          as quiz_score_answers,
)


class QuizIndexedRequest(BaseModel):
    branch:         str | None       = None
    sem:            str | None       = None
    subject:        str | None       = None
    category:       str | None       = None
    question_types: list[str] | None = None
    difficulty:     str              = "Medium"
    num_questions:  int | None       = None
    save_to_disk:   bool | None      = False


class QuizScoreRequest(BaseModel):
    questions:    list[dict]
    user_answers: list


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
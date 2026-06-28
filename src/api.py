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
    """Build tree using FULL paths so duplicate filenames don't collapse."""
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)

        # ✅ Group chunks by their full path (unique identifier)
        indexed_files = {}   # rel_path → {filename, branch, sem, subject_folder}
        for c in chunks:
            rel_path = c.get("source_rel_path") or c.get("source_file")
            if rel_path not in indexed_files:
                indexed_files[rel_path] = {
                    "name":           c.get("source_file", ""),
                    "rel_path":       rel_path,
                    "branch":         c.get("branch", ""),
                    "semester":       c.get("semester", ""),
                    "subject_folder": c.get("subject_folder", ""),
                }

        # Build tree from FILE_LINKS but match using both name AND path
        tree = {}
        files_with_links = []

        for composite_key, info in FILE_LINKS.items():
            # Match by name (since gdrive_links uses filename)
            matched_paths = [
                rp for rp, idx_info in indexed_files.items()
                if idx_info["name"] == info["name"]
                   and idx_info["branch"].lower()   == info["branch"].lower()
                   and idx_info["semester"].lower() == info["semester"].lower()
            ]

            if not matched_paths:
                continue

            for rel_path in matched_paths:
                branch   = info["branch"]   or "Unknown"
                sem      = info["semester"] or "?"
                subject  = info["subject"]  or "Other"
                category = normalize_category(info["category"])

                tree.setdefault(branch, {}) \
                    .setdefault(sem, {}) \
                    .setdefault(subject, {}) \
                    .setdefault(category, []) \
                    .append({
                        "name": info["name"],
                        "url":  info["url"],
                        "path": rel_path,
                    })
                files_with_links.append(info)

        # Files in index but not in any gdrive_links.json
        linked_paths = set()
        for composite_key, info in FILE_LINKS.items():
            for rp, idx_info in indexed_files.items():
                if (idx_info["name"] == info["name"] and
                    idx_info["branch"].lower()   == info["branch"].lower() and
                    idx_info["semester"].lower() == info["semester"].lower()):
                    linked_paths.add(rp)

        unlinked_paths = [rp for rp in indexed_files if rp not in linked_paths]

        for rp in unlinked_paths:
            idx_info = indexed_files[rp]
            branch   = idx_info["branch"]         or "Unknown"
            sem      = idx_info["semester"]       or "?"
            subject  = idx_info["subject_folder"] or "Other"

            tree.setdefault(branch, {}) \
                .setdefault(sem, {}) \
                .setdefault(subject, {}) \
                .setdefault("Other", []) \
                .append({
                    "name": idx_info["name"],
                    "url":  "",
                    "path": rp,
                })

        return {
            "total_files":  len(indexed_files),
            "total_chunks": len(chunks),
            "files":        files_with_links,
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
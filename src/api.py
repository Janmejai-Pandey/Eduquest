import os
import sys
import json

# ─────────────────────────────────────────────
# Path setup — index_store is at project root
# ─────────────────────────────────────────────
# Get project root (JaPari/)
CURRENT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
IR_DIR      = os.path.join(PROJECT_ROOT, "src", "IR")
RESUME_PROJECT_DIR = os.path.join(PROJECT_ROOT, "src", "resume_project")

sys.path.append(IR_DIR)
sys.path.append(RESUME_PROJECT_DIR)

# Change to project root so 'index_store/...' works
os.chdir(PROJECT_ROOT)
# ─────────────────────────────────────────────
# Now import everything
# ─────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from src.IR.chatbot import RAGChatbot


# ─────────────────────────────────────────────
# Initialize FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="JaPari API",
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
    """Find all gdrive_links.json files in dataset folder."""
    mapping = {}
    dataset_dir = os.path.join(PROJECT_ROOT, "dataset")
    if not os.path.exists(dataset_dir):
        return mapping

    pattern = os.path.join(dataset_dir, "**", "gdrive_links.json")
    for json_path in glob.glob(pattern, recursive=True):
        # Extract branch + sem from path
        parts = os.path.normpath(json_path).split(os.sep)
        try:
            sm_idx = parts.index("study_material")
            branch = parts[sm_idx + 1] if sm_idx + 1 < len(parts) else ""
            sem    = parts[sm_idx + 2] if sm_idx + 2 < len(parts) else ""
        except ValueError:
            branch, sem = "", ""

        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                name = item.get("item_name", "").strip()
                url  = item.get("original_url", "")
                if name and url:
                    mapping[name] = {
                        "url":      url,
                        "subject":  item.get("subject", ""),
                        "category": item.get("category", ""),
                        "branch":   branch,
                        "semester": sem,
                    }
        except Exception as e:
            print(f"Warning: could not load {json_path}: {e}")

    print(f"✅ Loaded {len(mapping)} file links")
    return mapping


FILE_LINKS = load_file_links()


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
    """Add gdrive URL + metadata to each source."""
    enriched = []
    for s in sources:
        info = FILE_LINKS.get(s.get("source_file", ""), {})
        s_copy = dict(s)
        s_copy["url"]      = info.get("url", "")
        s_copy["subject"]  = info.get("subject", "")
        s_copy["branch"]   = info.get("branch", "")
        s_copy["semester"] = info.get("semester", "")
        enriched.append(s_copy)
    return enriched


# ═════════════════════════════════════════════
# ROUTES
# ═════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "status":  "online",
        "service": "JaPari API",
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
        files = sorted(set(c["source_file"] for c in chunks))

        # Add file links
        files_with_links = []
        for fname in files:
            info = FILE_LINKS.get(fname, {})
            files_with_links.append({
                "name":     fname,
                "url":      info.get("url", ""),
                "subject":  info.get("subject", ""),
                "branch":   info.get("branch", ""),
                "semester": info.get("semester", ""),
            })

        return {
            "total_files":  len(files),
            "total_chunks": len(chunks),
            "files":        files_with_links,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ════════════════════════════════════════════════════════
# RESUME RANKING ENDPOINTS
# ════════════════════════════════════════════════════════

from fastapi import UploadFile, File, Form
from src.resume_project.resume_api import (
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
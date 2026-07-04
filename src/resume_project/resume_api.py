# src/IR/resume_api.py

import os
import sys
import tempfile
import importlib.util
from pathlib import Path


# ─────────────────────────────────────────────
# Path setup
# ─────────────────────────────────────────────
CURRENT_DIR        = os.path.dirname(os.path.abspath(__file__))
SRC_DIR            = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PROJECT_ROOT       = os.path.abspath(os.path.join(SRC_DIR, ".."))
RESUME_PROJECT_DIR = os.path.join(SRC_DIR, "resume_project")

for _p in (PROJECT_ROOT, SRC_DIR, CURRENT_DIR, RESUME_PROJECT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ─────────────────────────────────────────────
# Load ranking + user_ranking modules
# ─────────────────────────────────────────────
def _load_module(name: str, path: str):
    spec   = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_RANKING_PATH      = os.path.join(RESUME_PROJECT_DIR, "ranking.py")
_USER_RANKING_PATH = os.path.join(RESUME_PROJECT_DIR, "user_ranking.py")

if not os.path.exists(_RANKING_PATH):
    raise FileNotFoundError(f"❌ ranking.py not found at: {_RANKING_PATH}")
if not os.path.exists(_USER_RANKING_PATH):
    raise FileNotFoundError(f"❌ user_ranking.py not found at: {_USER_RANKING_PATH}")

ranking_module      = _load_module("ranking",      _RANKING_PATH)
user_ranking_module = _load_module("user_ranking", _USER_RANKING_PATH)


# ─────────────────────────────────────────────
# Expose functions
# ─────────────────────────────────────────────
rank_resume          = ranking_module.rank_resume
job_skill_profiles   = ranking_module.job_skill_profiles
BRANCH_PROFILES      = ranking_module.BRANCH_PROFILES
get_roles_by_branch  = ranking_module.get_roles_by_branch
get_all_branches     = ranking_module.get_all_branches

extract_resume_text  = user_ranking_module.extract_resume_text
update_csv_with_user = user_ranking_module.update_csv_with_user
get_skills_list      = user_ranking_module.get_skills_list


# ─────────────────────────────────────────────
# Get available branches with their roles
# ─────────────────────────────────────────────
def get_branch_role_tree() -> dict:
    """Return {branch_name: [role_names]} for cascading dropdowns."""
    tree = {}
    for branch in get_all_branches():
        tree[branch] = get_roles_by_branch(branch)
    return tree


def get_role_skills(role_name: str) -> list:
    """Get the required skills for a specific role."""
    if role_name not in job_skill_profiles:
        return []
    return get_skills_list(job_skill_profiles[role_name])


# ─────────────────────────────────────────────
# Extract text from uploaded file bytes
# ─────────────────────────────────────────────
def extract_text_from_bytes(filename: str, file_bytes: bytes) -> str:
    """Save uploaded bytes to temp file → run extractor → cleanup."""
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".pptx"):
        raise ValueError(f"Unsupported file type '{ext}'. Use .pdf or .pptx")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        text = extract_resume_text(tmp_path)
        return text
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────
# MAIN: analyze resume (year-based)
# ─────────────────────────────────────────────
def analyze_resume(
    filename:   str,
    file_bytes: bytes,
    user_name:  str,
    enrollment: str,
    year:       str,
    branch:     str,
    job_role:   str,
) -> dict:
    """Full pipeline using year+enrollment+role CSV structure."""

    # ── Validate role ────────────────────────
    if job_role not in job_skill_profiles:
        match = None
        for r in job_skill_profiles.keys():
            if job_role.lower() in r.lower() or r.lower() in job_role.lower():
                match = r
                break
        if not match:
            raise ValueError(
                f"Job role '{job_role}' not found. "
                f"Available: {list(job_skill_profiles.keys())[:10]}..."
            )
        job_role = match

    # ── Validate year ────────────────────────
    if str(year) not in ("1", "2", "3", "4", "5"):
        raise ValueError(f"Year must be 1-5, got '{year}'")

    # ── Validate branch ──────────────────────
    if branch not in get_all_branches():
        raise ValueError(f"Invalid branch '{branch}'. Available: {get_all_branches()}")

    # ── Validate enrollment ──────────────────
    enrollment = enrollment.strip().upper()
    if not enrollment or len(enrollment) < 4:
        raise ValueError("Enrollment must be at least 4 characters")

    # ── Extract resume text ──────────────────
    resume_text = extract_text_from_bytes(filename, file_bytes)
    if not resume_text or len(resume_text.split()) < 10:
        raise ValueError("Could not extract enough text from resume.")

    # ── Rank ─────────────────────────────────
    result = rank_resume(resume_text, job_role)
    result["candidate_name"] = user_name
    result["enrollment"]     = enrollment
    result["resume_length"]  = len(resume_text.split())
    result["year"]           = str(year)
    result["branch"]         = branch

    # ── Update CSV ───────────────────────────
    meta = update_csv_with_user(result, str(year), job_role)

    # ── Recommendations ──────────────────────
    recommendations = build_recommendations(
        missing_skills = result.get("missing_skills", []),
        year           = int(year),
    )

    required_skills = get_skills_list(job_skill_profiles[job_role])

    return {
        "filename":         filename,
        "candidate_name":   user_name,
        "enrollment":       enrollment,
        "year":             str(year),
        "branch":           branch,
        "job_role":         job_role,

        "final_score":            result["final_score"],
        "skill_match_percentage": result["skill_match_percentage"],
        "tfidf_similarity":       result["tfidf_similarity"],
        "ranking_tier":           result["ranking_tier"],

        "found_skills":        result.get("found_skills",        []),
        "missing_skills":      result.get("missing_skills",      []),
        "top2_found_skills":   result.get("top2_found_skills",   []),
        "top2_missing_skills": result.get("top2_missing_skills", []),
        "required_skills":     required_skills,

        "is_first":        meta["is_first"],
        "was_update":      meta["was_update"],
        "previous_rank":   meta["previous_rank"],
        "previous_score":  meta["previous_score"],
        "current_rank":    meta["current_rank"],
        "total":           meta["total"],
        "percentile":      round((1 - (meta["current_rank"] - 1) / meta["total"]) * 100, 1) if meta["total"] > 0 else 0,
        "csv_path":        meta["csv_path"],

        "recommendations": recommendations,
        "resume_word_count": len(resume_text.split()),
    }


# ─────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────
def build_recommendations(missing_skills: list, year: int = 2) -> list:
    """Convert missing skills into prioritized recommendations."""
    recommendations = []
    for i, skill in enumerate(missing_skills[:8]):
        if i < 2:
            priority = "high"
            reason   = "Critical skill for this role — highly weighted by employers."
        elif i < 5:
            priority = "medium"
            reason   = "Important skill that strengthens your profile significantly."
        else:
            priority = "low"
            reason   = "Good to have — adds depth to your resume."

        if year and year <= 2 and priority == "high":
            reason += " Start learning now while you have time."
        elif year and year >= 3 and priority == "high":
            reason += " Prioritize this before placements."

        recommendations.append({
            "skill":    skill,
            "priority": priority,
            "reason":   reason,
        })

    return recommendations
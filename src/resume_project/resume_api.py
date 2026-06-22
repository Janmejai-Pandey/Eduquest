import os
import sys
import tempfile
# import importlib.util
from typing import Any
from pathlib import Path

# from altair import Dict
import user_ranking as ur
import ranking as r


# ─────────────────────────────────────────────
# Helper: list available roles
# ─────────────────────────────────────────────
def get_available_roles() -> list[dict[str, Any]]:
    """Return all roles with their skills."""
    roles = []
    for role_name, value in r.job_skill_profiles.items():
        skills = ur.get_skills_list(value)
        roles.append({
            "name":         role_name,
            "skills":       skills,
            "skills_count": len(skills),
        })
    return roles


# ─────────────────────────────────────────────
# Helper: extract text from uploaded file bytes
# (your extract_resume_text needs a filepath, so save bytes to temp file)
# ─────────────────────────────────────────────
def extract_text_from_bytes(filename: str, file_bytes: bytes) -> str:
    """Save uploaded bytes to temp file → run your extractor → cleanup."""
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".pptx"):
        raise ValueError(f"Unsupported file type '{ext}'. Use .pdf or .pptx")

    # Create temp file with same extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        text = ur.extract_resume_text(tmp_path)
        return text
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────
# Main pipeline — analyze + rank a single resume
# ─────────────────────────────────────────────
def analyze_resume(
    filename:   str,
    file_bytes: bytes,
    user_name:  str,
    job_role:   str,
    branch:     str = "",
    year:       int = 0,
) -> dict[str, Any]:
    """
    Full pipeline:
      1. Extract text from uploaded file
      2. Use your rank_resume() to score it
      3. Update CSV with new entry
      4. Return rank, percentile, skills, recommendations
    """

    # ── Validate role ────────────────────────────────────────
    if job_role not in r.job_skill_profiles:
        # Try fuzzy match
        match = None
        for skill in r.job_skill_profiles.keys():
            if job_role.lower() in skill.lower() or skill.lower() in job_role.lower():
                match = skill
                break
        if not match:
            raise ValueError(
                f"Job role '{job_role}' not found. "
                f"Available: {list(r.job_skill_profiles.keys())}"
            )
        job_role = match

    # ── Step 1: Extract text ────────────────────────────────
    resume_text = extract_text_from_bytes(filename, file_bytes)
    if not resume_text or len(resume_text.split()) < 10:
        raise ValueError("Could not extract enough text from resume.")

    # ── Step 2: Rank using your existing logic ──────────────
    result = r.rank_resume(resume_text, job_role)
    result["candidate_name"] = user_name
    result["resume_length"]  = len(resume_text.split())

    # ── Step 3: Update CSV → get rank ───────────────────────
    user_rank, total = ur.update_csv_with_user(result, r.CSV_PATH)
    percentile = round((1 - (user_rank - 1) / total) * 100, 1) if total > 0 else 0

    # ── Step 4: Build recommendations from missing skills ──
    recommendations = build_recommendations(
        missing_skills = result.get("missing_skills", []),
        year           = year,
    )

    # ── Step 5: Get role required skills for context ───────
    required_skills = ur.get_skills_list(r.job_skill_profiles[job_role])

    # ── Step 6: Return enriched response ───────────────────
    return {
        "filename":         filename,
        "candidate_name":   user_name,
        "job_role":         job_role,
        "branch":           branch,
        "year":             year,

        # Scores
        "final_score":            result["final_score"],
        "skill_match_percentage": result["skill_match_percentage"],
        "tfidf_similarity":       result["tfidf_similarity"],
        "ranking_tier":           result["ranking_tier"],

        # Skills
        "found_skills":           result.get("found_skills",         []),
        "missing_skills":         result.get("missing_skills",       []),
        "top2_found_skills":      result.get("top2_found_skills",    []),
        "top2_missing_skills":    result.get("top2_missing_skills",  []),
        "required_skills":        required_skills,

        # Rank
        "rank":             user_rank,
        "total_candidates": total,
        "percentile":       percentile,

        # Recommendations
        "recommendations":  recommendations,

        # Text preview
        "resume_word_count": len(resume_text.split()),
        "text_preview":      resume_text[:500],
    }


# ─────────────────────────────────────────────
# Recommendations: prioritize missing skills
# ─────────────────────────────────────────────
def build_recommendations(missing_skills: list[str], year: int = 0) -> list[dict[str, Any]]:
    """
    Convert missing skills into prioritized recommendations.
    Top missing skills get 'high' priority (they're weighted highest in your engineer_data).
    """
    recommendations = []
    for i, skill in enumerate(missing_skills[:8]):   # top 8
        if i < 2:
            priority = "high"
            reason   = "Critical skill for this role — highly weighted by employers."
        elif i < 5:
            priority = "medium"
            reason   = "Important skill that strengthens your profile significantly."
        else:
            priority = "low"
            reason   = "Good to have — adds depth to your resume."

        # Year-specific advice
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


# ─────────────────────────────────────────────
# Quick stats from CSV
# ─────────────────────────────────────────────
def get_csv_stats() -> dict[str, Any]:
    """Get stats about existing rankings."""
    if not os.path.exists(r.CSV_PATH):
        return {"total": 0, "exists": False}

    import csv
    rows = []
    with open(r.CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["score_float"] = float(row["final_score"].replace("%", "").strip())
            except (ValueError, KeyError):
                row["score_float"] = 0.0
            rows.append(row)

    if not rows:
        return {"total": 0, "exists": True}

    scores  = [r["score_float"] for r in rows]
    return {
        "total":       len(rows),
        "exists":      True,
        "avg_score":   round(sum(scores) / len(scores), 2),
        "top_score":   round(max(scores), 2),
        "min_score":   round(min(scores), 2),
        "top_5":       [
            {"name": r["candidate_name"], "score": r["final_score"], "tier": r["ranking_tier"]}
            for r in sorted(rows, key=lambda x: x["score_float"], reverse=True)[:5]
        ],
    }
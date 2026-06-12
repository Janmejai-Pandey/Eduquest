
import os
import sys
import re
import csv
from typing import TypedDict, List, Dict

import nltk
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from colorama import Fore, Style, init

# ─────────────────────────────────────────────
# 1. Path setup to allow importing from root directory
# ─────────────────────────────────────────────
# This ensures Python can find 'resume_project' even when running from 'src/IR'
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 2. Import the dictionary from your other file
# ⚠️ IMPORTANT: Change 'job_skill_profiles' to the exact variable name used in engineer_data.py
from resume_project.job_desc.engineer_data import job_skill_profiles

# ────────────────────────────────────────────
# 3. Initializations
# ─────────────────────────────────────────────
nltk.download('wordnet', quiet=True)
nltk.download('punkt', quiet=True)
init(autoreset=True)

_lemmatizer = WordNetLemmatizer()

# Scoring weights
SKILL_WEIGHT: float = 0.7
TFIDF_WEIGHT: float = 0.3


# ─────────────────────────────────────────────
# 4. TypedDicts
# ─────────────────────────────────────────────
class SkillResult(TypedDict):
    match_percentage: float
    found_skills: list
    missing_skills: list


class ResumeRankResult(TypedDict):
    job_role: str
    final_score: float
    skill_match_percentage: float
    tfidf_similarity: float
    found_skills: list
    missing_skills: list
    ranking_tier: str


# ─────────────────────────────────────────────
# 5. Helper Functions
# ─────────────────────────────────────────────
def clean_resume(text: str) -> str:
    """
    Normalise resume text:
      1. Lowercase
      2. Keep only a-z letters and 0-9 digits
      3. Collapse whitespace
      4. Lemmatise every token
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [_lemmatizer.lemmatize(tok) for tok in text.split()]
    return " ".join(tokens)


def extract_skill_score(cleaned_resume: str, job_role: str) -> SkillResult:
    """
    Check which required skills for *job_role* appear in the cleaned resume.
    Uses the imported job_skill_profiles dictionary.
    """
    role_key = job_role.lower().strip()

    # Find the matching role in the imported dictionary
    required_skills: List[str] = []
    for key, skills in job_skill_profiles.items():
        if key.lower() in role_key or role_key in key.lower():
            required_skills = skills
            break

    # Fallback: If no predefined role found, extract words from job_role itself
    if not required_skills:
        required_skills = [
            tok for tok in re.findall(r"[a-z0-9]+", role_key) if len(tok) > 2
        ]

    if not required_skills:
        return SkillResult(match_percentage=0.0, found_skills=[], missing_skills=[])

    found: List[str] = []
    missing: List[str] = []

    for skill in required_skills:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, cleaned_resume):
            found.append(skill)
        else:
            missing.append(skill)

    match_pct = round((len(found) / len(required_skills)) * 100, 2)
    return SkillResult(
        match_percentage=match_pct,
        found_skills=found,
        missing_skills=missing,
    )


def tfidf_similarity_score(cleaned_resume: str, job_role: str) -> float:
    """
    Compute cosine similarity between the resume and the job-role string
    using TF-IDF vectors, scaled to 0-100.
    """
    cleaned_role = clean_resume(job_role)

    if not cleaned_resume.strip() or not cleaned_role.strip():
        return 0.0

    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_role])
        score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except ValueError:
        return 0.0

    return round(float(score) * 100, 2)


def classify_tier(score: float) -> str:
    """Maps a numeric score (0-100) to a human-readable ranking tier."""
    if score >= 75:
        return "Excellent Match ⭐⭐⭐⭐⭐"
    elif score >= 60:
        return "Strong Match ⭐⭐⭐"
    elif score >= 45:
        return "Moderate Match ⭐⭐⭐"
    elif score >= 30:
        return "Below Average ⭐⭐"
    else:
        return "Poor Match ⭐"


# ─────────────────────────────────────────────
# 6. Core Ranking Functions
# ─────────────────────────────────────────────
def rank_resume(resume_text: str, job_role: str) -> ResumeRankResult:
    """Ranks a single resume against a target job role."""
    if not resume_text or not resume_text.strip():
        raise ValueError("resume_text must not be empty.")
    if not job_role or not job_role.strip():
        raise ValueError("job_role must not be empty.")

    cleaned: str              = clean_resume(resume_text)
    skill_result: SkillResult = extract_skill_score(cleaned, job_role)
    tfidf_score: float        = tfidf_similarity_score(cleaned, job_role)

    final_score = round(
        (skill_result["match_percentage"] * SKILL_WEIGHT)
        + (tfidf_score * TFIDF_WEIGHT),
        2,
    )

    return ResumeRankResult(
        job_role=job_role,
        final_score=final_score,
        skill_match_percentage=skill_result["match_percentage"],
        tfidf_similarity=tfidf_score,
        found_skills=skill_result["found_skills"],
        missing_skills=skill_result["missing_skills"],
        ranking_tier=classify_tier(final_score),
    )


def rank_multiple_resumes(resumes_list: List[Dict[str, str]], job_role: str) -> List[Dict]:
    """Rank multiple resumes for a specific job role."""
    results = []

    for candidate in resumes_list:
        result = rank_resume(candidate["resume"], job_role)

        result.update({
            "candidate_name"  : candidate["name"],
            "resume_length"   : len(candidate["resume"].split()),
            "email"           : candidate.get("email", "N/A"),
            "experience_years": candidate.get("experience", "N/A"),
        })
        results.append(result)

    results.sort(key=lambda x: x["final_score"], reverse=True)

    total = len(results)
    for i, r in enumerate(results, 1):
        r["rank"]       = i
        r["percentile"] = round((1 - (i - 1) / total) * 100, 1)

    return results


# ─────────────────────────────────────────────
# 7. Display & Export Functions
# ────────────────────────────────────────────
def display_rankings(rankings: List[Dict], top_n: int = None) -> None:
    """Display ranked resumes in a formatted, colour-coded table."""
    if not rankings:
        print(Fore.RED + "No rankings to display.")
        return

    job_role    = rankings[0]["job_role"]
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}  RESUME RANKINGS FOR: {Fore.WHITE}{job_role.upper()}")
    print(f"{Fore.CYAN}{'='*80}\n")

    display_list = rankings[:top_n] if top_n else rankings

    print(
        f"{Fore.MAGENTA}"
        f"{'Rank':<6} {'Name':<20} {'Score':<8} {'Tier':<30} "
        f"{'Skills Found':<30} {'Missing':<20}"
    )
    print(f"{Fore.CYAN}{'-'*80}")

    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }

    for r in display_list:
        found_str   = ", ".join(r["found_skills"][:3])   + ("..." if len(r["found_skills"])   > 3 else "")
        missing_str = ", ".join(r["missing_skills"][:2]) + ("..." if len(r["missing_skills"]) > 2 else "")
        tier_color  = TIER_COLOR.get(r["ranking_tier"], Fore.WHITE)

        print(
            f"{Fore.WHITE}{r['rank']:<6} "
            f"{Fore.WHITE}{r['candidate_name'][:19]:<20} "
            f"{Fore.CYAN}{r['final_score']:<8.1f} "
            f"{tier_color}{r['ranking_tier']:<30} "
            f"{Fore.WHITE}{found_str:<30} "
            f"{Fore.RED}{missing_str:<20}"
        )

    avg = sum(r["final_score"] for r in rankings) / len(rankings)
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}  Total Candidates : {len(rankings)}")
    print(f"{Fore.YELLOW}  Average Score    : {avg:.1f}%")
    print(f"{Fore.CYAN}{'='*80}\n")


def generate_ranking_report(rankings: List[Dict], filename: str = "resume_rankings.csv") -> None:
    """Generate a CSV report of the rankings."""
    if not rankings:
        print(Fore.RED + "No rankings to export.")
        return

    fieldnames = [
        "rank", "candidate_name", "final_score", "ranking_tier",
        "skill_match_percentage", "tfidf_similarity",
        "found_skills", "missing_skills", "resume_length", "percentile",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rankings:
            writer.writerow({
                "rank"                  : r["rank"],
                "candidate_name"        : r["candidate_name"],
                "final_score"           : f"{r['final_score']:.1f}%",
                "ranking_tier"          : r["ranking_tier"],
                "skill_match_percentage": f"{r['skill_match_percentage']:.1f}%",
                "tfidf_similarity"      : f"{r['tfidf_similarity']:.1f}%",
                "found_skills"          : "; ".join(r["found_skills"]),
                "missing_skills"        : "; ".join(r["missing_skills"]),
                "resume_length"         : r["resume_length"],
                "percentile"            : f"{r['percentile']}%",
            })

    print(f"{Fore.GREEN}✅ Ranking report saved to {filename}")


# ─────────────────────────────────────────────
# 8. Quick Demo
# ─────────────────────────────────────────────
if __name__ == "__main__":
    sample_resumes = [
        {
            "name"      : "Alice Johnson",
            "resume"    : "Experienced Python developer with 5 years in machine learning. "
                          "Skilled in TensorFlow, PyTorch, and data pipelines. "
                          "Built models for NLP applications.",
            "email"     : "alice@example.com",
            "experience": "5 years",
        },
        {
            "name"      : "Bob Smith",
            "resume"    : "Full stack developer with expertise in JavaScript, React, and Node.js. "
                          "Experience with AWS and Docker. 3 years of professional experience.",
            "email"     : "bob@example.com",
            "experience": "3 years",
        },
        {
            "name"      : "Charlie Brown",
            "resume"    : "Data scientist with strong statistics background. "
                          "Proficient in R, Python, and SQL. "
                          "Experience with Tableau and Power BI.",
            "email"     : "charlie@example.com",
            "experience": "4 years",
        },
    ]

    rankings = rank_multiple_resumes(sample_resumes, "Data Scientist")
    display_rankings(rankings, top_n=3)
    generate_ranking_report(rankings)
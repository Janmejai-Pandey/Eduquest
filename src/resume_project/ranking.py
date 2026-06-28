import os
import sys
import re
import csv
import importlib.util
from typing import TypedDict, List, Dict
from pathlib import Path
from collections import defaultdict

import nltk
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from colorama import Fore, Style, init


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IR_DIR   = os.path.abspath(os.path.join(SRC_DIR, 'IR'))

for _p in (ROOT_DIR, SRC_DIR, IR_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


_EXTRACT_PATH = os.path.join(IR_DIR, "extract.py")

if not os.path.exists(_EXTRACT_PATH):
    raise FileNotFoundError(
        f"\n❌ extract.py not found at expected path:\n"
        f"   {_EXTRACT_PATH}\n"
        f"   Make sure extract.py is inside src/IR/"
    )

_extract_spec   = importlib.util.spec_from_file_location("extract", _EXTRACT_PATH)
_extract_module = importlib.util.module_from_spec(_extract_spec)
_extract_spec.loader.exec_module(_extract_module)

extract_folder = _extract_module.extract_folder
chunk_records  = _extract_module.chunk_records

# ── Load combined job profiles from job_desc package ───────────────────────────
try:
    from resume_project.job_desc import (
        combined_job_profiles,
        BRANCH_PROFILES,
        get_roles_by_branch,
        get_all_branches,
    )
    job_skill_profiles = combined_job_profiles
except ImportError:
    # Fallback to engineer_data only
    _ENG_PATH = os.path.join(SRC_DIR, "resume_project", "job_desc", "engineer_data.py")
    if not os.path.exists(_ENG_PATH):
        raise FileNotFoundError(
            f"\n❌ No job profile files found in:\n   {_ENG_PATH}"
        )
    _eng_spec   = importlib.util.spec_from_file_location("engineer_data", _ENG_PATH)
    _eng_module = importlib.util.module_from_spec(_eng_spec)
    _eng_spec.loader.exec_module(_eng_module)
    job_skill_profiles = _eng_module.job_skill_profiles
    BRANCH_PROFILES = {"Engineering": job_skill_profiles}
    def get_roles_by_branch(b): return list(BRANCH_PROFILES.get(b, {}).keys())
    def get_all_branches(): return list(BRANCH_PROFILES.keys())


DATASET_PATH       = os.path.join(ROOT_DIR, "dataset", "resume_dataset", "Engineering")
RESUME_INDEX_STORE = os.path.join(ROOT_DIR, "resume_index_store")
CSV_PATH           = os.path.join(RESUME_INDEX_STORE, "dataset_rankings.csv")

nltk.download('wordnet', quiet=True)
nltk.download('punkt',   quiet=True)
init(autoreset=True)

_lemmatizer = WordNetLemmatizer()

SKILL_WEIGHT: float = 0.7
TFIDF_WEIGHT: float = 0.3


class SkillResult(TypedDict):
    match_percentage:       float
    found_skills:           list
    missing_skills:         list
    top2_found_skills:      list
    top2_missing_skills:    list


class ResumeRankResult(TypedDict):
    job_role:               str
    final_score:            float
    skill_match_percentage: float
    tfidf_similarity:       float
    found_skills:           list
    missing_skills:         list
    top2_found_skills:      list
    top2_missing_skills:    list
    ranking_tier:           str


def load_resumes_from_dataset(dataset_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(dataset_path):
        print(Fore.RED + f"❌ Dataset folder not found:\n   {dataset_path}")
        return []

    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}📂 DATASET PATH : {Fore.WHITE}{dataset_path}")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}\n🔍 Step 1 — Extracting text from resumes...\n")

    page_records = extract_folder(dataset_path)

    if not page_records:
        print(Fore.RED + "❌ No text could be extracted from the dataset.")
        return []

    print(f"{Fore.YELLOW}\n✂️  Step 2 — Chunking extracted text...")
    chunk_list = chunk_records(page_records, max_words=200, overlap=40)

    print(f"{Fore.YELLOW}\n📎 Step 3 — Grouping chunks by resume file...")
    file_chunks: Dict[str, List[str]] = defaultdict(list)

    for chunk in chunk_list:
        file_chunks[chunk["source_file"]].append(chunk["text"])

    resumes: List[Dict[str, str]] = []

    for source_file, texts in file_chunks.items():
        full_resume_text = " ".join(texts).strip()
        if not full_resume_text:
            print(Fore.YELLOW + f"   ⚠  Empty content for '{source_file}' — skipping.")
            continue

        candidate_name = Path(source_file).stem
        resumes.append({
            "name"      : candidate_name,
            "resume"    : full_resume_text,
            "email"     : "N/A",
            "experience": "N/A",
        })
        print(
            f"   {Fore.GREEN}✅ {candidate_name:<30} "
            f"{Fore.WHITE}| {len(texts)} chunk(s) | "
            f"{len(full_resume_text.split())} words"
        )

    print(f"\n{Fore.GREEN}✅ Total resumes loaded : {len(resumes)}\n")
    return resumes


def clean_resume(text: str) -> str:
    text   = text.lower()
    text   = re.sub(r"[^a-z0-9\s]", " ", text)
    text   = re.sub(r"\s+",         " ", text).strip()
    tokens = [_lemmatizer.lemmatize(tok) for tok in text.split()]
    return " ".join(tokens)


def clean_skill(skill: str) -> str:
    skill  = skill.lower()
    skill  = re.sub(r"[^a-z0-9\s]", " ", skill)
    skill  = re.sub(r"\s+",         " ", skill).strip()
    tokens = [_lemmatizer.lemmatize(tok) for tok in skill.split()]
    return " ".join(tokens)


def extract_skill_score(cleaned_resume: str, job_role: str) -> SkillResult:
    role_key: str              = job_role.lower().strip()
    required_skills: List[str] = []

    for key, value in job_skill_profiles.items():
        if key.lower() in role_key or role_key in key.lower():

            if isinstance(value, dict):
                skills_list  = value.get("skills",  [])
                weights_dict = value.get("weights", {})

                if isinstance(weights_dict, dict) and weights_dict:
                    # Sort by weight descending; unweighted skills go last
                    paired = sorted(
                        skills_list,
                        key     = lambda s: weights_dict.get(s, 0),
                        reverse = True,
                    )
                    required_skills = paired
                elif isinstance(weights_dict, list) and len(weights_dict) == len(skills_list):
                    paired = sorted(
                        zip(weights_dict, skills_list),
                        key     = lambda x: x[0],
                        reverse = True,
                    )
                    required_skills = [s for _, s in paired]
                else:
                    required_skills = skills_list

            elif isinstance(value, list):
                required_skills = value

            break

    if not required_skills:
        required_skills = [
            tok for tok in re.findall(r"[a-z0-9]+", role_key) if len(tok) > 2
        ]

    if not required_skills:
        return SkillResult(
            match_percentage    = 0.0,
            found_skills        = [],
            missing_skills      = [],
            top2_found_skills   = [],
            top2_missing_skills = [],
        )

    found:   List[str] = []
    missing: List[str] = []

    for skill in required_skills:
        cleaned_skill = clean_skill(skill)

        if not cleaned_skill:
            missing.append(skill)
            continue

        if " " in cleaned_skill:
            pattern = (
                r"\b"
                + r"\s+".join(re.escape(w) for w in cleaned_skill.split())
                + r"\b"
            )
        else:
            pattern = r"\b" + re.escape(cleaned_skill) + r"\b"

        if re.search(pattern, cleaned_resume):
            found.append(skill)
        else:
            missing.append(skill)

    match_pct = round((len(found) / len(required_skills)) * 100, 2)

    return SkillResult(
        match_percentage    = match_pct,
        found_skills        = found,
        missing_skills      = missing,
        top2_found_skills   = found[:2],
        top2_missing_skills = missing[:2],
    )


def tfidf_similarity_score(cleaned_resume: str, job_role: str) -> float:
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


def assign_tiers_by_rank(results: List[Dict]) -> List[Dict]:
    total = len(results)

    if total == 1:
        results[0]["ranking_tier"] = "Excellent Match ⭐⭐⭐⭐⭐"
        return results

    for r in results:
        pct = (r["rank"] - 1) / total

        if   pct < 0.10: r["ranking_tier"] = "Excellent Match ⭐⭐⭐⭐⭐"
        elif pct < 0.30: r["ranking_tier"] = "Strong Match ⭐⭐⭐⭐"
        elif pct < 0.60: r["ranking_tier"] = "Moderate Match ⭐⭐⭐"
        elif pct < 0.80: r["ranking_tier"] = "Below Average ⭐⭐"
        else:            r["ranking_tier"] = "Poor Match ⭐"

    return results


def classify_tier(score: float) -> str:
    if   score >= 75: return "Excellent Match ⭐⭐⭐⭐⭐"
    elif score >= 60: return "Strong Match ⭐⭐⭐⭐"
    elif score >= 45: return "Moderate Match ⭐⭐⭐"
    elif score >= 30: return "Below Average ⭐⭐"
    else:             return "Poor Match ⭐"


def rank_resume(resume_text: str, job_role: str) -> ResumeRankResult:
    if not resume_text or not resume_text.strip():
        raise ValueError("resume_text must not be empty.")
    if not job_role or not job_role.strip():
        raise ValueError("job_role must not be empty.")

    cleaned:      str         = clean_resume(resume_text)
    skill_result: SkillResult = extract_skill_score(cleaned, job_role)
    tfidf_score:  float       = tfidf_similarity_score(cleaned, job_role)

    final_score = round(
        (skill_result["match_percentage"] * SKILL_WEIGHT)
        + (tfidf_score                    * TFIDF_WEIGHT),
        2,
    )

    return ResumeRankResult(
        job_role               = job_role,
        final_score            = final_score,
        skill_match_percentage = skill_result["match_percentage"],
        tfidf_similarity       = tfidf_score,
        found_skills           = skill_result["found_skills"],
        missing_skills         = skill_result["missing_skills"],
        top2_found_skills      = skill_result["top2_found_skills"],
        top2_missing_skills    = skill_result["top2_missing_skills"],
        ranking_tier           = classify_tier(final_score),
    )


def rank_multiple_resumes(resumes_list: List[Dict[str, str]], job_role: str) -> List[Dict]:
    results = []

    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}⚙️  Step 4 — Ranking {len(resumes_list)} resume(s)...")
    print(f"{Fore.CYAN}{'='*60}\n")

    for candidate in resumes_list:
        result = rank_resume(candidate["resume"], job_role)
        result.update({
            "candidate_name"  : candidate["name"],
            "resume_length"   : len(candidate["resume"].split()),
            "email"           : candidate.get("email",      "N/A"),
            "experience_years": candidate.get("experience", "N/A"),
        })
        results.append(result)
        print(
            f"   {Fore.WHITE}{candidate['name']:<30} "
            f"→ Score: {Fore.CYAN}{result['final_score']:.1f}%  "
            f"{Fore.WHITE}| Skills: {result['skill_match_percentage']:.1f}%  "
            f"| TF-IDF: {result['tfidf_similarity']:.1f}%"
        )

    results.sort(key=lambda x: x["final_score"], reverse=True)

    total = len(results)
    for i, r in enumerate(results, 1):
        r["rank"]       = i
        r["percentile"] = round((1 - (i - 1) / total) * 100, 1)

    results = assign_tiers_by_rank(results)
    return results


def display_rankings(rankings: List[Dict], top_n: int = None) -> None:
    if not rankings:
        print(Fore.RED + "No rankings to display.")
        return

    job_role     = rankings[0]["job_role"]
    display_list = rankings[:top_n] if top_n else rankings

    print(f"\n{Fore.CYAN}{'='*110}")
    print(f"{Fore.YELLOW}  🏆 RESUME RANKINGS FOR : {Fore.WHITE}{job_role.upper()}")
    print(f"{Fore.CYAN}{'='*110}\n")

    print(
        f"{Fore.MAGENTA}"
        f"{'Rank':<6} {'Candidate':<28} {'Score':<9} {'Skill%':<9} "
        f"{'TF-IDF%':<9} {'Tier':<28} {'Top Skills Found':<28} {'Top Missing Skills'}"
    )
    print(f"{Fore.CYAN}{'-'*110}")

    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }

    for r in display_list:
        found_str   = ", ".join(r["top2_found_skills"])   if r["top2_found_skills"]   else "None"
        missing_str = ", ".join(r["top2_missing_skills"]) if r["top2_missing_skills"] else "None"
        tier_color  = TIER_COLOR.get(r["ranking_tier"], Fore.WHITE)

        print(
            f"{Fore.WHITE}{r['rank']:<6} "
            f"{Fore.WHITE}{r['candidate_name'][:27]:<28} "
            f"{Fore.CYAN}{r['final_score']:<9.1f} "
            f"{Fore.GREEN}{r['skill_match_percentage']:<9.1f} "
            f"{Fore.BLUE}{r['tfidf_similarity']:<9.1f} "
            f"{tier_color}{r['ranking_tier']:<28} "
            f"{Fore.WHITE}{found_str:<28} "
            f"{Fore.RED}{missing_str}"
        )

    avg    = sum(r["final_score"] for r in rankings) / len(rankings)
    top    = rankings[0]
    bottom = rankings[-1]

    print(f"\n{Fore.CYAN}{'='*110}")
    print(f"{Fore.YELLOW}  Total Candidates : {Fore.WHITE}{len(rankings)}")
    print(f"{Fore.YELLOW}  Average Score    : {Fore.WHITE}{avg:.1f}%")
    print(f"{Fore.YELLOW}  🥇 Top Candidate  : {Fore.GREEN}{top['candidate_name']}  ({top['final_score']:.1f}%)")
    print(f"{Fore.YELLOW}  🔻 Lowest Score   : {Fore.RED}{bottom['candidate_name']}  ({bottom['final_score']:.1f}%)")
    print(f"{Fore.CYAN}{'='*110}\n")


def generate_ranking_report(rankings: List[Dict], filename: str = CSV_PATH) -> None:
    if not rankings:
        print(Fore.RED + "No rankings to export.")
        return

    os.makedirs(RESUME_INDEX_STORE, exist_ok=True)

    fieldnames = [
        "rank", "candidate_name", "final_score", "ranking_tier",
        "skill_match_percentage", "tfidf_similarity",
        "top2_found_skills", "top2_missing_skills",
        "all_found_skills", "all_missing_skills",
        "resume_length", "percentile",
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
                "top2_found_skills"     : "; ".join(r["top2_found_skills"])   if r["top2_found_skills"]   else "None",
                "top2_missing_skills"   : "; ".join(r["top2_missing_skills"]) if r["top2_missing_skills"] else "None",
                "all_found_skills"      : "; ".join(r["found_skills"])        if r["found_skills"]        else "None",
                "all_missing_skills"    : "; ".join(r["missing_skills"])      if r["missing_skills"]      else "None",
                "resume_length"         : r["resume_length"],
                "percentile"            : f"{r['percentile']}%",
            })

    print(f"{Fore.GREEN}✅ CSV report saved → {filename}\n")


if __name__ == "__main__":

    if not job_skill_profiles:
        print(Fore.RED + "❌ job_skill_profiles is empty. Check job_desc/")
        sys.exit(1)

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}  💼 SELECT JOB ROLE FOR RANKING")
    print(f"{Fore.CYAN}{'='*60}\n")

    roles = list(job_skill_profiles.keys())

    print(f"{Fore.WHITE}Available Job Roles:\n")
    for i, role in enumerate(roles, 1):
        print(f"   {Fore.CYAN}{i}.{Fore.WHITE} {role}")

    print(f"\n{Fore.WHITE}Enter the role name or its number from the list above.")
    role_input = input(f"{Fore.CYAN}   Your choice : {Fore.WHITE}").strip()

    JOB_ROLE = None

    if role_input.isdigit():
        idx = int(role_input) - 1
        if 0 <= idx < len(roles):
            JOB_ROLE = roles[idx]
    else:
        for r in roles:
            if role_input.lower() in r.lower():
                JOB_ROLE = r
                break

    if not JOB_ROLE:
        print(Fore.RED + f"❌ Could not match '{role_input}' to any available role.")
        sys.exit(1)

    _role_value = job_skill_profiles[JOB_ROLE]
    if isinstance(_role_value, dict):
        _skills_display = _role_value.get("skills", [])
    else:
        _skills_display = _role_value

    print(f"\n{Fore.GREEN}✅ Selected Role     : {Fore.WHITE}{JOB_ROLE}")
    print(f"{Fore.GREEN}📋 Required Skills   : {Fore.WHITE}{', '.join(_skills_display)}\n")

    resumes = load_resumes_from_dataset(DATASET_PATH)

    if not resumes:
        print(Fore.RED + "❌ No resumes loaded. Check dataset path and file contents.")
        sys.exit(1)

    rankings = rank_multiple_resumes(resumes, JOB_ROLE)
    display_rankings(rankings)
    generate_ranking_report(rankings)
import os
import sys
import csv
import importlib.util
from pathlib import Path
from collections import defaultdict

from colorama import Fore, init


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IR_DIR   = os.path.abspath(os.path.join(SRC_DIR, 'IR'))

for _p in (ROOT_DIR, SRC_DIR, IR_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


_EXTRACT_PATH = os.path.join(IR_DIR, "extract.py")

if not os.path.exists(_EXTRACT_PATH):
    raise FileNotFoundError(
        f"\n❌ extract.py not found at:\n"
        f"   {_EXTRACT_PATH}\n"
        f"   Make sure extract.py is inside src/IR/"
    )

_extract_spec   = importlib.util.spec_from_file_location("extract", _EXTRACT_PATH)
_extract_module = importlib.util.module_from_spec(_extract_spec)
_extract_spec.loader.exec_module(_extract_module)

extract_pdf    = _extract_module.extract_pdf
extract_pptx   = _extract_module.extract_pptx
chunk_records  = _extract_module.chunk_records

_RANKING_PATH = os.path.join(os.path.dirname(__file__), "ranking.py")

if not os.path.exists(_RANKING_PATH):
    raise FileNotFoundError(
        f"\n❌ ranking.py not found at:\n"
        f"   {_RANKING_PATH}\n"
        f"   Make sure ranking.py is inside src/resume_project/"
    )

_ranking_spec   = importlib.util.spec_from_file_location("ranking", _RANKING_PATH)
_ranking_module = importlib.util.module_from_spec(_ranking_spec)
_ranking_spec.loader.exec_module(_ranking_module)

rank_resume        = _ranking_module.rank_resume
classify_tier      = _ranking_module.classify_tier
job_skill_profiles = _ranking_module.job_skill_profiles
RESUME_INDEX_STORE = _ranking_module.RESUME_INDEX_STORE
CSV_PATH           = _ranking_module.CSV_PATH


init(autoreset=True)


def get_skills_list(role_value) -> list:
    """
    Extract plain skills list from job_skill_profiles value.
    Structure A → plain list  : return as-is
    Structure B → dict        : return value["skills"]
    """
    if isinstance(role_value, dict):
        return role_value.get("skills", [])
    elif isinstance(role_value, list):
        return role_value
    return []


def extract_resume_text(filepath: str) -> str:
    """
    Extract full text from a single resume file.
    Supports: .pdf  → extract_pdf()   from extract.py
              .pptx → extract_pptx()  from extract.py

    Steps:
      1. extract_pdf() / extract_pptx() → page/slide records
      2. chunk_records()                → overlapping word chunks
      3. join all chunks                → single full-text string
    """
    ext = Path(filepath).suffix.lower()
    print(f"{Fore.YELLOW}🔍 Extracting resume : {Fore.WHITE}{filepath}\n")

    if ext == ".pdf":
        records = extract_pdf(filepath)
    elif ext == ".pptx":
        records = extract_pptx(filepath)
    else:
        print(Fore.RED + f"❌ Unsupported file type '{ext}'.")
        print(Fore.RED + "   Please provide a .pdf or .pptx file.")
        return ""

    if not records:
        print(Fore.RED + "❌ Could not extract any text from the file.")
        return ""

    print(f"{Fore.YELLOW}✂️  Chunking extracted text...")
    chunks    = chunk_records(records, max_words=200, overlap=40)
    full_text = " ".join(c["text"] for c in chunks).strip()

    print(f"{Fore.GREEN}✅ Extracted {len(chunks)} chunk(s) | {len(full_text.split())} words\n")
    return full_text


#load existing rankings from csv
def load_existing_rankings(csv_path: str) -> list:
    """
    Read resume_rankings.csv from resume_index_store/.
    Parses final_score string → float for sorting.
    Returns empty list if CSV doesn't exist.
    """
    if not os.path.exists(csv_path):
        print(Fore.YELLOW + f"⚠  No existing rankings CSV found at {csv_path}")
        print(Fore.YELLOW + "   Run ranking.py first to generate dataset rankings.\n")
        return []

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["final_score_float"] = float(
                    row["final_score"].replace("%", "").strip()
                )
            except ValueError:
                row["final_score_float"] = 0.0
            rows.append(row)
    return rows



def update_csv_with_user(user_result: dict, csv_path: str):
    """
    Insert/update user result in CSV, re-sort,
    recalculate ranks, rewrite file.
    Returns (user_rank, total) as integers.
    """
    os.makedirs(RESUME_INDEX_STORE, exist_ok=True)
    existing_rows = load_existing_rankings(csv_path)

    # ── Build user row — fieldnames match ranking.py CSV exactly ─────────────
    user_row = {
        "rank"                  : 0,
        "candidate_name"        : user_result["candidate_name"],
        "final_score"           : f"{user_result['final_score']:.1f}%",
        "ranking_tier"          : user_result["ranking_tier"],
        "skill_match_percentage": f"{user_result['skill_match_percentage']:.1f}%",
        "tfidf_similarity"      : f"{user_result['tfidf_similarity']:.1f}%",

        # *** FIXED: use top2 + all fields to match ranking.py CSV structure ***
        "top2_found_skills"     : "; ".join(user_result.get("top2_found_skills",  []))
                                    if user_result.get("top2_found_skills")  else "None",
        "top2_missing_skills"   : "; ".join(user_result.get("top2_missing_skills", []))
                                    if user_result.get("top2_missing_skills") else "None",
        "all_found_skills"      : "; ".join(user_result.get("found_skills",  []))
                                    if user_result.get("found_skills")  else "None",
        "all_missing_skills"    : "; ".join(user_result.get("missing_skills", []))
                                    if user_result.get("missing_skills") else "None",

        "resume_length"         : user_result["resume_length"],
        "percentile"            : "0%",
        "final_score_float"     : user_result["final_score"],
    }

    # ── Remove duplicate entry for same candidate name ────────────────────────
    existing_rows = [
        r for r in existing_rows
        if r["candidate_name"].strip().lower()
        != user_result["candidate_name"].strip().lower()
    ]

    all_rows = existing_rows + [user_row]
    all_rows.sort(key=lambda x: x["final_score_float"], reverse=True)

    # ── Recalculate rank + percentile for all ────────────────────────────────
    total = len(all_rows)
    for i, row in enumerate(all_rows, 1):
        row["rank"]       = i
        row["percentile"] = f"{round((1 - (i - 1) / total) * 100, 1)}%"

    # ── Fieldnames SYNCED with ranking.py ────────────────────────────────────
    fieldnames = [
        "rank", "candidate_name", "final_score", "ranking_tier",
        "skill_match_percentage", "tfidf_similarity",
        "top2_found_skills", "top2_missing_skills",
        "all_found_skills", "all_missing_skills",
        "resume_length", "percentile",
    ]

    # ── Rewrite CSV ───────────────────────────────────────────────────────────
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            # Use .get() with fallback so old rows missing new fields don't crash
            writer.writerow({
                "rank"                  : row.get("rank",                   ""),
                "candidate_name"        : row.get("candidate_name",         ""),
                "final_score"           : row.get("final_score",            ""),
                "ranking_tier"          : row.get("ranking_tier",           ""),
                "skill_match_percentage": row.get("skill_match_percentage", ""),
                "tfidf_similarity"      : row.get("tfidf_similarity",       ""),
                "top2_found_skills"     : row.get("top2_found_skills",      "None"),
                "top2_missing_skills"   : row.get("top2_missing_skills",    "None"),
                "all_found_skills"      : row.get("all_found_skills",       "None"),
                "all_missing_skills"    : row.get("all_missing_skills",     "None"),
                "resume_length"         : row.get("resume_length",          ""),
                "percentile"            : row.get("percentile",             ""),
            })

    print(f"{Fore.GREEN}✅ CSV updated with your result → {csv_path}\n")

    # ── Find and return user's final rank ─────────────────────────────────────
    user_rank = next(
        (row["rank"] for row in all_rows
         if row["candidate_name"].strip().lower()
         == user_result["candidate_name"].strip().lower()),
        1,
    )
    return user_rank, total


#display the user result
def display_user_result(result: dict, rank: int, total: int) -> None:
    """Display only the user's ranking result — clean and focused."""
    percentile = round((1 - (rank - 1) / total) * 100, 1)

    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }
    tier_color = TIER_COLOR.get(result["ranking_tier"], Fore.WHITE)

    print(f"\n{Fore.CYAN}{'='*65}")
    print(f"{Fore.YELLOW}  📄 YOUR RESUME RANKING RESULT")
    print(f"{Fore.CYAN}{'='*65}\n")

    # ── Basic info + scores ───────────────────────────────────────────────────
    print(f"  {Fore.WHITE}👤 Name              : {Fore.CYAN}{result['candidate_name']}")
    print(f"  {Fore.WHITE}🎯 Job Role           : {Fore.CYAN}{result['job_role']}")
    print(f"  {Fore.WHITE}📊 Final Score        : {Fore.CYAN}{result['final_score']:.1f}%")
    print(f"  {Fore.WHITE}🔧 Skill Match        : {Fore.GREEN}{result['skill_match_percentage']:.1f}%")
    print(f"  {Fore.WHITE}📐 TF-IDF Score       : {Fore.BLUE}{result['tfidf_similarity']:.1f}%")
    print(f"  {Fore.WHITE}🏅 Tier               : {tier_color}{result['ranking_tier']}")

    # ── Top 2 priority found skills ───────────────────────────────────────────
    top2_found   = result.get("top2_found_skills",   [])
    top2_missing = result.get("top2_missing_skills", [])
    all_found    = result.get("found_skills",         [])
    all_missing  = result.get("missing_skills",       [])

    print(f"\n  {Fore.WHITE}✅ Top Skills Found   : "
          f"{Fore.GREEN}{', '.join(top2_found) if top2_found else 'None'}")
    print(f"  {Fore.WHITE}❌ Top Skills Missing : "
          f"{Fore.RED}{', '.join(top2_missing) if top2_missing else 'None'}")

    # ── Full lists (collapsed) ────────────────────────────────────────────────
    if len(all_found) > 2:
        print(f"\n  {Fore.WHITE}📋 All Skills Found   : "
              f"{Fore.GREEN}{', '.join(all_found)}")
    if len(all_missing) > 2:
        print(f"  {Fore.WHITE}📋 All Skills Missing : "
              f"{Fore.RED}{', '.join(all_missing)}")

    # ── Rank + percentile ─────────────────────────────────────────────────────
    print(f"\n{Fore.CYAN}{'─'*65}")
    print(f"  {Fore.YELLOW}🏆 YOUR RANK          : {Fore.WHITE}{rank} out of {total} candidates")
    print(f"  {Fore.YELLOW}📈 YOUR PERCENTILE    : {Fore.WHITE}Top {percentile}%")

    # ── Standing message ──────────────────────────────────────────────────────
    print(f"\n  ", end="")
    if rank == 1:
        print(f"{Fore.GREEN}🥇 You are the TOP candidate among all applicants!")
    elif percentile >= 75:
        print(f"{Fore.GREEN}🎉 You are in the TOP 25% of all candidates — great work!")
    elif percentile >= 50:
        print(f"{Fore.YELLOW}👍 You are in the TOP half of all candidates. Keep it up!")
    elif percentile >= 25:
        print(f"{Fore.MAGENTA}📌 You are in the bottom half. Work on the missing skills above.")
    else:
        print(f"{Fore.RED}⚠️  You are in the bottom 25%. Focus on the missing skills listed above.")

    print(f"{Fore.CYAN}{'='*65}\n")



if __name__ == "__main__":

    print(f"\n{Fore.CYAN}{'='*65}")
    print(f"{Fore.YELLOW}  🎓 RESUME RANKER — Check Your Standing")
    print(f"{Fore.CYAN}{'='*65}\n")

    # ── Step 1 : Candidate name ───────────────────────────────────────────────
    user_name = input(f"{Fore.WHITE}👤 Enter your name : {Fore.CYAN}").strip()
    if not user_name:
        user_name = "User"

    # ── Step 2 : Resume file path ─────────────────────────────────────────────
    print(f"\n{Fore.WHITE}📁 Enter the full path to your resume file (.pdf or .pptx)")
    print(f"{Fore.WHITE}   Example : C:/Users/you/Documents/my_resume.pdf")
    resume_path = input(f"{Fore.CYAN}   Path : ").strip().strip('"').strip("'")

    if not os.path.exists(resume_path):
        print(Fore.RED + f"\n❌ File not found : '{resume_path}'")
        print(Fore.RED + "   Please check the path and try again.")
        sys.exit(1)

    # ── Step 3 : Job role selection ───────────────────────────────────────────
    if not job_skill_profiles:
        print(Fore.RED + "❌ job_skill_profiles is empty. Check engineer_data.py")
        sys.exit(1)

    print(f"\n{Fore.YELLOW}💼 Available Job Positions:\n")
    roles = list(job_skill_profiles.keys())
    for i, role in enumerate(roles, 1):
        print(f"   {Fore.CYAN}{i}.{Fore.WHITE} {role}")

    print(f"\n{Fore.WHITE}🎯 Which position are you applying for?")
    role_choice = input(f"{Fore.CYAN}   Enter Role Name or Number : ").strip()

    selected_role = None
    if role_choice.isdigit():
        idx = int(role_choice) - 1
        if 0 <= idx < len(roles):
            selected_role = roles[idx]
    else:
        for r in roles:
            if role_choice.lower() in r.lower():
                selected_role = r
                break

    if not selected_role:
        print(Fore.RED + "❌ Invalid selection. Please restart and pick a role from the list.")
        sys.exit(1)

    # ── Display selected role + skills (handles Structure A & B) ─────────────
    _skills_display = get_skills_list(job_skill_profiles[selected_role])
    print(f"\n{Fore.GREEN}✅ Selected Role     : {Fore.WHITE}{selected_role}")
    print(f"{Fore.GREEN}📋 Required Skills   : {Fore.WHITE}{', '.join(_skills_display)}\n")

    # ── Step 4 : Extract resume text ─────────────────────────────────────────
    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        print(Fore.RED + "❌ Could not extract text from your resume. Exiting.")
        sys.exit(1)

    # ── Step 5 : Rank via ranking.py ─────────────────────────────────────────
    print(f"{Fore.YELLOW}⚙️  Calculating your ranking score for '{selected_role}'...\n")
    result = rank_resume(resume_text, selected_role)

    # Attach extra fields
    result["candidate_name"] = user_name
    result["resume_length"]  = len(resume_text.split())

    # ── Step 6 : Update CSV ───────────────────────────────────────────────────
    user_rank, total = update_csv_with_user(result, CSV_PATH)

    # ── Step 7 : Display result ───────────────────────────────────────────────
    display_user_result(result, user_rank, total)
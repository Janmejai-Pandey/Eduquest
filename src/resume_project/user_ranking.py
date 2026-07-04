import os
import sys
import re
import csv
import importlib.util
from pathlib import Path
from datetime import datetime

from colorama import Fore, init


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IR_DIR   = os.path.abspath(os.path.join(SRC_DIR, 'IR'))

for _p in (ROOT_DIR, SRC_DIR, IR_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


_EXTRACT_PATH = os.path.join(IR_DIR, "extract.py")
if not os.path.exists(_EXTRACT_PATH):
    raise FileNotFoundError(f"\n❌ extract.py not found at:\n   {_EXTRACT_PATH}")

_extract_spec   = importlib.util.spec_from_file_location("extract", _EXTRACT_PATH)
_extract_module = importlib.util.module_from_spec(_extract_spec)
_extract_spec.loader.exec_module(_extract_module)

extract_pdf    = _extract_module.extract_pdf
extract_pptx   = _extract_module.extract_pptx
chunk_records  = _extract_module.chunk_records

_RANKING_PATH = os.path.join(os.path.dirname(__file__), "ranking.py")
if not os.path.exists(_RANKING_PATH):
    raise FileNotFoundError(f"\n❌ ranking.py not found at:\n   {_RANKING_PATH}")

_ranking_spec   = importlib.util.spec_from_file_location("ranking", _RANKING_PATH)
_ranking_module = importlib.util.module_from_spec(_ranking_spec)
_ranking_spec.loader.exec_module(_ranking_module)

rank_resume        = _ranking_module.rank_resume
classify_tier      = _ranking_module.classify_tier
job_skill_profiles = _ranking_module.job_skill_profiles
RESUME_INDEX_STORE = _ranking_module.RESUME_INDEX_STORE

try:
    BRANCH_PROFILES     = _ranking_module.BRANCH_PROFILES
    get_roles_by_branch = _ranking_module.get_roles_by_branch
    get_all_branches    = _ranking_module.get_all_branches
except AttributeError:
    BRANCH_PROFILES = {"All Roles": job_skill_profiles}
    def get_roles_by_branch(b): return list(BRANCH_PROFILES.get(b, {}).keys())
    def get_all_branches(): return list(BRANCH_PROFILES.keys())


init(autoreset=True)


# ============== HELPERS ==============

def get_skills_list(role_value) -> list:
    if isinstance(role_value, dict):
        return role_value.get("skills", [])
    elif isinstance(role_value, list):
        return role_value
    return []


def extract_resume_text(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    print(f"{Fore.YELLOW}🔍 Extracting resume : {Fore.WHITE}{filepath}\n")

    if ext == ".pdf":
        records = extract_pdf(filepath)
    elif ext == ".pptx":
        records = extract_pptx(filepath)
    else:
        print(Fore.RED + f"❌ Unsupported file type '{ext}'.")
        return ""

    if not records:
        print(Fore.RED + "❌ Could not extract any text from the file.")
        return ""

    print(f"{Fore.YELLOW}✂️  Chunking extracted text...")
    chunks    = chunk_records(records, max_words=200, overlap=40)
    full_text = " ".join(c["text"] for c in chunks).strip()

    print(f"{Fore.GREEN}✅ Extracted {len(chunks)} chunk(s) | {len(full_text.split())} words\n")
    return full_text


def sanitize_filename(name: str) -> str:
    """Convert role name to safe filename component."""
    safe = re.sub(r"[<>:\"/\\|?*]", "_", name)
    safe = safe.replace(" ", "_").strip("_")
    return safe


# ============== YEAR + ROLE BASED CSV PATH ==============

def get_role_csv_path(year: str, role: str) -> str:
    """
    Return CSV path for a specific year + role combination.
    Creates the year folder if it doesn't exist.

    Path format:
        resume_index_store/3/rankings_Software_Developer.csv
    """
    year_folder = os.path.join(RESUME_INDEX_STORE, str(year))
    os.makedirs(year_folder, exist_ok=True)

    safe_role = sanitize_filename(role)
    return os.path.join(year_folder, f"rankings_{safe_role}.csv")


def load_existing_rankings(csv_path: str) -> list:
    """Read year+role-specific rankings CSV. Returns empty list if doesn't exist."""
    if not os.path.exists(csv_path):
        return []

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["final_score_float"] = float(
                    row["final_score"].replace("%", "").strip()
                )
            except (ValueError, KeyError):
                row["final_score_float"] = 0.0
            rows.append(row)
    return rows


def find_existing_by_enrollment(existing_rows: list, enrollment: str) -> dict:
    """Find a row matching the enrollment number. Returns dict or None."""
    for row in existing_rows:
        if row.get("enrollment", "").strip().lower() == enrollment.strip().lower():
            return row
    return None


def update_csv_with_user(user_result: dict, year: str, role: str) -> dict:
    """
    Insert/update user result in year+role-specific CSV, re-sort,
    recalculate ranks, rewrite file.

    Returns dict with:
        {
            "is_first"        : bool  → True if first entry for this role+year
            "was_update"      : bool  → True if user resubmitted their resume
            "previous_rank"   : int   → previous rank (0 if new)
            "previous_score"  : float → previous score (0 if new)
            "current_rank"    : int
            "current_score"   : float
            "total"           : int
            "csv_path"        : str
        }
    """
    csv_path = get_role_csv_path(year, role)
    existing_rows = load_existing_rankings(csv_path)

    is_first     = len(existing_rows) == 0
    enrollment   = user_result["enrollment"]
    previous_row = find_existing_by_enrollment(existing_rows, enrollment)

    was_update     = previous_row is not None
    previous_rank  = int(previous_row["rank"]) if previous_row else 0
    previous_score = previous_row["final_score_float"] if previous_row else 0.0

    # Remove old entry for this enrollment (if any)
    existing_rows = [
        r for r in existing_rows
        if r.get("enrollment", "").strip().lower() != enrollment.strip().lower()
    ]

    # Build new/updated user row
    user_row = {
        "rank"                  : 0,
        "enrollment"            : enrollment,
        "candidate_name"        : user_result["candidate_name"],
        "year"                  : year,
        "branch"                : user_result.get("branch", "N/A"),
        "job_role"              : role,
        "final_score"           : f"{user_result['final_score']:.1f}%",
        "ranking_tier"          : user_result["ranking_tier"],
        "skill_match_percentage": f"{user_result['skill_match_percentage']:.1f}%",
        "tfidf_similarity"      : f"{user_result['tfidf_similarity']:.1f}%",
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
        "last_updated"          : datetime.now().strftime("%Y-%m-%d %H:%M"),
        "final_score_float"     : user_result["final_score"],
    }

    all_rows = existing_rows + [user_row]
    all_rows.sort(key=lambda x: x["final_score_float"], reverse=True)

    total = len(all_rows)
    for i, row in enumerate(all_rows, 1):
        row["rank"]       = i
        row["percentile"] = f"{round((1 - (i - 1) / total) * 100, 1)}%"

    fieldnames = [
        "rank", "enrollment", "candidate_name", "year", "branch", "job_role",
        "final_score", "ranking_tier",
        "skill_match_percentage", "tfidf_similarity",
        "top2_found_skills", "top2_missing_skills",
        "all_found_skills", "all_missing_skills",
        "resume_length", "percentile", "last_updated",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({
                "rank"                  : row.get("rank", ""),
                "enrollment"            : row.get("enrollment", ""),
                "candidate_name"        : row.get("candidate_name", ""),
                "year"                  : row.get("year", year),
                "branch"                : row.get("branch", "N/A"),
                "job_role"              : row.get("job_role", role),
                "final_score"           : row.get("final_score", ""),
                "ranking_tier"          : row.get("ranking_tier", ""),
                "skill_match_percentage": row.get("skill_match_percentage", ""),
                "tfidf_similarity"      : row.get("tfidf_similarity", ""),
                "top2_found_skills"     : row.get("top2_found_skills", "None"),
                "top2_missing_skills"   : row.get("top2_missing_skills", "None"),
                "all_found_skills"      : row.get("all_found_skills", "None"),
                "all_missing_skills"    : row.get("all_missing_skills", "None"),
                "resume_length"         : row.get("resume_length", ""),
                "percentile"            : row.get("percentile", ""),
                "last_updated"          : row.get("last_updated", ""),
            })

    # Find current rank of this user
    current_rank = next(
        (row["rank"] for row in all_rows
         if row.get("enrollment", "").strip().lower() == enrollment.strip().lower()),
        1,
    )

    return {
        "is_first"       : is_first,
        "was_update"     : was_update,
        "previous_rank"  : previous_rank,
        "previous_score" : previous_score,
        "current_rank"   : current_rank,
        "current_score"  : user_result["final_score"],
        "total"          : total,
        "csv_path"       : csv_path,
    }


# ============== DISPLAY ==============

def display_first_time_result(result: dict, meta: dict) -> None:
    """Special display when user is the FIRST to submit for this role."""
    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }
    tier_color = TIER_COLOR.get(result["ranking_tier"], Fore.WHITE)

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}  🎉 CONGRATULATIONS! YOU'RE THE FIRST ONE!")
    print(f"{Fore.CYAN}{'='*70}\n")

    print(f"  {Fore.GREEN}✨ You are the {Fore.YELLOW}FIRST{Fore.GREEN} candidate to submit a resume")
    print(f"  {Fore.GREEN}   for {Fore.WHITE}'{result['job_role']}'{Fore.GREEN} in Year {result.get('year', 'N/A')}!\n")

    print(f"  {Fore.WHITE}📊 Your Score Details:")
    print(f"     {Fore.WHITE}👤 Name              : {Fore.CYAN}{result['candidate_name']}")
    print(f"     {Fore.WHITE}🎫 Enrollment         : {Fore.CYAN}{result['enrollment']}")
    print(f"     {Fore.WHITE}🎯 Role               : {Fore.CYAN}{result['job_role']}")
    print(f"     {Fore.WHITE}📊 Final Score        : {Fore.CYAN}{result['final_score']:.1f}%")
    print(f"     {Fore.WHITE}🔧 Skill Match        : {Fore.GREEN}{result['skill_match_percentage']:.1f}%")
    print(f"     {Fore.WHITE}📐 TF-IDF Score       : {Fore.BLUE}{result['tfidf_similarity']:.1f}%")
    print(f"     {Fore.WHITE}🏅 Tier               : {tier_color}{result['ranking_tier']}")

    top2_found   = result.get("top2_found_skills",   [])
    top2_missing = result.get("top2_missing_skills", [])

    print(f"\n     {Fore.WHITE}✅ Top Skills Found   : "
          f"{Fore.GREEN}{', '.join(top2_found) if top2_found else 'None'}")
    print(f"     {Fore.WHITE}❌ Top Skills Missing : "
          f"{Fore.RED}{', '.join(top2_missing) if top2_missing else 'None'}")

    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"  {Fore.YELLOW}⏳ Check back later once your peers submit their resumes")
    print(f"  {Fore.YELLOW}   to see how you rank against them!")
    print(f"{Fore.CYAN}{'='*70}\n")


def display_update_result(result: dict, meta: dict) -> None:
    """Special display when user is RE-submitting (updating) their resume."""
    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }
    tier_color = TIER_COLOR.get(result["ranking_tier"], Fore.WHITE)

    prev_rank    = meta["previous_rank"]
    curr_rank    = meta["current_rank"]
    prev_score   = meta["previous_score"]
    curr_score   = meta["current_score"]
    total        = meta["total"]
    percentile   = round((1 - (curr_rank - 1) / total) * 100, 1)

    rank_delta   = prev_rank - curr_rank    # positive = improved
    score_delta  = curr_score - prev_score  # positive = improved

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}  🔄 RESUME UPDATED — HERE'S HOW YOU CHANGED")
    print(f"{Fore.CYAN}{'='*70}\n")

    print(f"  {Fore.WHITE}👤 Name              : {Fore.CYAN}{result['candidate_name']}")
    print(f"  {Fore.WHITE}🎫 Enrollment         : {Fore.CYAN}{result['enrollment']}")
    print(f"  {Fore.WHITE}🎯 Job Role           : {Fore.CYAN}{result['job_role']}")
    print(f"  {Fore.WHITE}🎓 Year               : {Fore.CYAN}{result.get('year', 'N/A')}")

    # ── Before vs After comparison ────────────────────────────────────────────
    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"{Fore.YELLOW}  📊 BEFORE vs AFTER")
    print(f"{Fore.CYAN}{'─'*70}\n")

    print(f"  {Fore.WHITE}Score  :  {Fore.MAGENTA}{prev_score:.1f}%  ", end="")
    print(f"{Fore.WHITE}→  {Fore.CYAN}{curr_score:.1f}%  ", end="")
    if score_delta > 0:
        print(f"{Fore.GREEN}(⬆ +{score_delta:.1f}%)")
    elif score_delta < 0:
        print(f"{Fore.RED}(⬇ {score_delta:.1f}%)")
    else:
        print(f"{Fore.YELLOW}(no change)")

    print(f"  {Fore.WHITE}Rank   :  {Fore.MAGENTA}#{prev_rank}  ", end="")
    print(f"{Fore.WHITE}→  {Fore.CYAN}#{curr_rank}  ", end="")
    if rank_delta > 0:
        print(f"{Fore.GREEN}(⬆ moved up {rank_delta} place{'s' if rank_delta > 1 else ''})")
    elif rank_delta < 0:
        print(f"{Fore.RED}(⬇ dropped {abs(rank_delta)} place{'s' if abs(rank_delta) > 1 else ''})")
    else:
        print(f"{Fore.YELLOW}(same rank)")

    # ── Current details ───────────────────────────────────────────────────────
    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"{Fore.YELLOW}  📋 CURRENT STATS")
    print(f"{Fore.CYAN}{'─'*70}\n")

    print(f"  {Fore.WHITE}🏅 Tier               : {tier_color}{result['ranking_tier']}")
    print(f"  {Fore.WHITE}🔧 Skill Match        : {Fore.GREEN}{result['skill_match_percentage']:.1f}%")
    print(f"  {Fore.WHITE}📐 TF-IDF Score       : {Fore.BLUE}{result['tfidf_similarity']:.1f}%")

    top2_found   = result.get("top2_found_skills",   [])
    top2_missing = result.get("top2_missing_skills", [])

    print(f"\n  {Fore.WHITE}✅ Top Skills Found   : "
          f"{Fore.GREEN}{', '.join(top2_found) if top2_found else 'None'}")
    print(f"  {Fore.WHITE}❌ Top Skills Missing : "
          f"{Fore.RED}{', '.join(top2_missing) if top2_missing else 'None'}")

    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"  {Fore.YELLOW}🏆 CURRENT RANK       : {Fore.WHITE}#{curr_rank} out of {total} candidates")
    print(f"  {Fore.YELLOW}📈 CURRENT PERCENTILE : {Fore.WHITE}Top {percentile}%")
    print(f"{Fore.CYAN}{'='*70}\n")


def display_normal_result(result: dict, meta: dict) -> None:
    """Standard display when user is a new submission (but not the first)."""
    curr_rank  = meta["current_rank"]
    total      = meta["total"]
    percentile = round((1 - (curr_rank - 1) / total) * 100, 1)

    TIER_COLOR = {
        "Excellent Match ⭐⭐⭐⭐⭐" : Fore.GREEN,
        "Strong Match ⭐⭐⭐⭐"      : Fore.BLUE,
        "Moderate Match ⭐⭐⭐"     : Fore.YELLOW,
        "Below Average ⭐⭐"        : Fore.MAGENTA,
        "Poor Match ⭐"             : Fore.RED,
    }
    tier_color = TIER_COLOR.get(result["ranking_tier"], Fore.WHITE)

    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}  📄 YOUR RESUME RANKING RESULT")
    print(f"{Fore.CYAN}{'='*70}\n")

    print(f"  {Fore.WHITE}👤 Name              : {Fore.CYAN}{result['candidate_name']}")
    print(f"  {Fore.WHITE}🎫 Enrollment         : {Fore.CYAN}{result['enrollment']}")
    print(f"  {Fore.WHITE}🎓 Year               : {Fore.CYAN}{result.get('year', 'N/A')}")
    print(f"  {Fore.WHITE}🏛️  Branch             : {Fore.CYAN}{result.get('branch', 'N/A')}")
    print(f"  {Fore.WHITE}🎯 Job Role           : {Fore.CYAN}{result['job_role']}")
    print(f"  {Fore.WHITE}📊 Final Score        : {Fore.CYAN}{result['final_score']:.1f}%")
    print(f"  {Fore.WHITE}🔧 Skill Match        : {Fore.GREEN}{result['skill_match_percentage']:.1f}%")
    print(f"  {Fore.WHITE}📐 TF-IDF Score       : {Fore.BLUE}{result['tfidf_similarity']:.1f}%")
    print(f"  {Fore.WHITE}🏅 Tier               : {tier_color}{result['ranking_tier']}")

    top2_found   = result.get("top2_found_skills",   [])
    top2_missing = result.get("top2_missing_skills", [])
    all_found    = result.get("found_skills",         [])
    all_missing  = result.get("missing_skills",       [])

    print(f"\n  {Fore.WHITE}✅ Top Skills Found   : "
          f"{Fore.GREEN}{', '.join(top2_found) if top2_found else 'None'}")
    print(f"  {Fore.WHITE}❌ Top Skills Missing : "
          f"{Fore.RED}{', '.join(top2_missing) if top2_missing else 'None'}")

    if len(all_found) > 2:
        print(f"\n  {Fore.WHITE}📋 All Skills Found   : "
              f"{Fore.GREEN}{', '.join(all_found)}")
    if len(all_missing) > 2:
        print(f"  {Fore.WHITE}📋 All Skills Missing : "
              f"{Fore.RED}{', '.join(all_missing)}")

    print(f"\n{Fore.CYAN}{'─'*70}")
    print(f"  {Fore.YELLOW}🏆 YOUR RANK          : {Fore.WHITE}#{curr_rank} out of {total} candidates")
    print(f"  {Fore.YELLOW}📈 YOUR PERCENTILE    : {Fore.WHITE}Top {percentile}%")

    print(f"\n  ", end="")
    if curr_rank == 1:
        print(f"{Fore.GREEN}🥇 You are the TOP candidate for this role in your year!")
    elif percentile >= 75:
        print(f"{Fore.GREEN}🎉 You are in the TOP 25% — great work!")
    elif percentile >= 50:
        print(f"{Fore.YELLOW}👍 You are in the TOP half. Keep it up!")
    elif percentile >= 25:
        print(f"{Fore.MAGENTA}📌 You are in the bottom half. Work on the missing skills.")
    else:
        print(f"{Fore.RED}⚠️  You are in the bottom 25%. Focus on the missing skills above.")

    print(f"{Fore.CYAN}{'='*70}\n")


# ============== INPUT HELPERS ==============

def ask_year() -> str:
    """Ask for year (1 through 5)."""
    print(f"\n{Fore.YELLOW}🎓 Which year are you in?\n")
    for y in range(1, 6):
        print(f"   {Fore.CYAN}[{y}]{Fore.WHITE} Year {y}")

    while True:
        choice = input(f"\n{Fore.CYAN}   Enter year (1-5) : {Fore.WHITE}").strip()
        if choice in ("1", "2", "3", "4", "5"):
            return choice
        print(Fore.RED + "   Invalid. Please enter a number from 1 to 5.")


def ask_branch() -> str:
    branches = get_all_branches()
    print(f"\n{Fore.YELLOW}🏛️  Which branch / domain are you targeting?\n")
    for i, b in enumerate(branches, 1):
        print(f"   {Fore.CYAN}[{i}]{Fore.WHITE} {b}")

    while True:
        choice = input(
            f"\n{Fore.CYAN}   Select branch (1-{len(branches)}) : {Fore.WHITE}"
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(branches):
                return branches[idx]
        except ValueError:
            pass
        print(Fore.RED + "   Invalid. Try again.")


def ask_role_within_branch(branch: str) -> str:
    roles = get_roles_by_branch(branch)
    if not roles:
        print(Fore.RED + f"❌ No roles found for branch '{branch}'.")
        sys.exit(1)

    print(f"\n{Fore.YELLOW}💼 Available roles in {branch}:\n")
    for i, role in enumerate(roles, 1):
        print(f"   {Fore.CYAN}[{i}]{Fore.WHITE} {role}")

    while True:
        choice = input(
            f"\n{Fore.CYAN}   Enter role name or number : {Fore.WHITE}"
        ).strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(roles):
                return roles[idx]
        else:
            for r in roles:
                if choice.lower() in r.lower():
                    return r
        print(Fore.RED + "   Invalid selection. Try again.")


def ask_enrollment() -> str:
    """Ask for enrollment number (unique ID)."""
    print(f"\n{Fore.YELLOW}🎫 Enter your enrollment number (unique ID)")
    print(f"{Fore.WHITE}   Example : 23103001 or 2024CS10123")

    while True:
        enrollment = input(f"{Fore.CYAN}   Enrollment : {Fore.WHITE}").strip()
        if enrollment and len(enrollment) >= 4:
            return enrollment.upper()
        print(Fore.RED + "   Enrollment must be at least 4 characters. Try again.")


def ask_name() -> str:
    """Ask for candidate's name."""
    while True:
        name = input(f"\n{Fore.CYAN}👤 Enter your name : {Fore.WHITE}").strip()
        if name:
            return name
        print(Fore.RED + "   Name cannot be empty. Try again.")


def ask_resume_path() -> str:
    """Ask for resume file path."""
    print(f"\n{Fore.WHITE}📁 Enter the full path to your resume file (.pdf or .pptx)")
    print(f"{Fore.WHITE}   Example : C:/Users/you/Documents/my_resume.pdf")

    while True:
        resume_path = input(f"{Fore.CYAN}   Path : {Fore.WHITE}").strip().strip('"').strip("'")
        if not resume_path:
            print(Fore.RED + "   Path cannot be empty.")
            continue
        if not os.path.exists(resume_path):
            print(Fore.RED + f"   ❌ File not found : '{resume_path}'")
            print(Fore.YELLOW + "   Please check the path and try again.\n")
            continue
        return resume_path


# ============== MAIN ==============

def main():
    print(f"\n{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}  🎓 RESUME RANKER — Check Your Standing")
    print(f"{Fore.CYAN}{'='*70}")

    if not job_skill_profiles:
        print(Fore.RED + "❌ job_skill_profiles is empty. Check job_desc/")
        sys.exit(1)

    # ── Step 1: Year ─────────────────────────────────────────────────────────
    year = ask_year()
    print(f"{Fore.GREEN}✅ Year           : {Fore.WHITE}{year}")

    # ── Step 2: Branch ───────────────────────────────────────────────────────
    branch = ask_branch()
    print(f"{Fore.GREEN}✅ Branch         : {Fore.WHITE}{branch}")

    # ── Step 3: Job Role ─────────────────────────────────────────────────────
    selected_role = ask_role_within_branch(branch)
    _skills_display = get_skills_list(job_skill_profiles[selected_role])
    print(f"{Fore.GREEN}✅ Role           : {Fore.WHITE}{selected_role}")
    top_skills = ', '.join(_skills_display[:8])
    print(f"{Fore.GREEN}📋 Top Skills     : {Fore.WHITE}{top_skills}...\n")

    # ── Step 4: Enrollment ───────────────────────────────────────────────────
    enrollment = ask_enrollment()

    # ── Step 5: Name ─────────────────────────────────────────────────────────
    user_name = ask_name()

    # ── Step 6: Resume path ──────────────────────────────────────────────────
    resume_path = ask_resume_path()

    # ── Step 7: Extract resume text ──────────────────────────────────────────
    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        print(Fore.RED + "❌ Could not extract text from your resume. Exiting.")
        sys.exit(1)

    # ── Step 8: Rank via ranking.py ──────────────────────────────────────────
    print(f"{Fore.YELLOW}⚙️  Calculating your ranking for '{selected_role}'...\n")
    result = rank_resume(resume_text, selected_role)

    # Attach extra fields
    result["candidate_name"] = user_name
    result["enrollment"]     = enrollment
    result["resume_length"]  = len(resume_text.split())
    result["year"]           = year
    result["branch"]         = branch

    # ── Step 9: Update role+year-specific CSV ───────────────────────────────
    meta = update_csv_with_user(result, year, selected_role)

    # ── Step 10: Display appropriate result ──────────────────────────────────
    if meta["is_first"]:
        display_first_time_result(result, meta)
    elif meta["was_update"]:
        display_update_result(result, meta)
    else:
        display_normal_result(result, meta)

    print(f"{Fore.GREEN}💾 Data saved to  : {Fore.WHITE}{meta['csv_path']}\n")


if __name__ == "__main__":
    main()
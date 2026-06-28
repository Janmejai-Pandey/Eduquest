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

# Import branch profiles
try:
    BRANCH_PROFILES = _ranking_module.BRANCH_PROFILES
    get_roles_by_branch = _ranking_module.get_roles_by_branch
    get_all_branches = _ranking_module.get_all_branches
except AttributeError:
    BRANCH_PROFILES = {"All Roles": job_skill_profiles}
    def get_roles_by_branch(b): return list(BRANCH_PROFILES.get(b, {}).keys())
    def get_all_branches(): return list(BRANCH_PROFILES.keys())


init(autoreset=True)


# ============== HELPERS ==============

def get_skills_list(role_value) -> list:
    """Extract plain skills list from job_skill_profiles value."""
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


# ============== SEMESTER-BASED CSV ==============

def get_sem_csv_path(semester: str) -> str:
    """Return CSV path based on user's semester."""
    os.makedirs(RESUME_INDEX_STORE, exist_ok=True)
    return os.path.join(RESUME_INDEX_STORE, f"rankings_sem_{semester}.csv")


def load_existing_rankings(csv_path: str) -> list:
    """Read sem-specific rankings CSV. Returns empty list if doesn't exist."""
    if not os.path.exists(csv_path):
        print(Fore.YELLOW + f"⚠  No existing rankings for this sem at {csv_path}")
        print(Fore.YELLOW + "   This will be the first entry — starting fresh.\n")
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


def update_csv_with_user(user_result: dict, semester: str):
    """
    Insert/update user result in sem-specific CSV, re-sort,
    recalculate ranks, rewrite file.
    """
    csv_path = get_sem_csv_path(semester)
    existing_rows = load_existing_rankings(csv_path)

    user_row = {
        "rank"                  : 0,
        "candidate_name"        : user_result["candidate_name"],
        "semester"              : semester,
        "branch"                : user_result.get("branch", "N/A"),
        "job_role"              : user_result["job_role"],
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
        "final_score_float"     : user_result["final_score"],
    }

    # Remove old entry for same candidate name (case-insensitive)
    existing_rows = [
        r for r in existing_rows
        if r["candidate_name"].strip().lower()
        != user_result["candidate_name"].strip().lower()
    ]

    all_rows = existing_rows + [user_row]
    all_rows.sort(key=lambda x: x["final_score_float"], reverse=True)

    total = len(all_rows)
    for i, row in enumerate(all_rows, 1):
        row["rank"]       = i
        row["percentile"] = f"{round((1 - (i - 1) / total) * 100, 1)}%"

    fieldnames = [
        "rank", "candidate_name", "semester", "branch", "job_role",
        "final_score", "ranking_tier",
        "skill_match_percentage", "tfidf_similarity",
        "top2_found_skills", "top2_missing_skills",
        "all_found_skills", "all_missing_skills",
        "resume_length", "percentile",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({
                "rank"                  : row.get("rank",                   ""),
                "candidate_name"        : row.get("candidate_name",         ""),
                "semester"              : row.get("semester",               semester),
                "branch"                : row.get("branch",                 "N/A"),
                "job_role"              : row.get("job_role",               ""),
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

    print(f"{Fore.GREEN}✅ CSV updated → {csv_path}\n")

    user_rank = next(
        (row["rank"] for row in all_rows
         if row["candidate_name"].strip().lower()
         == user_result["candidate_name"].strip().lower()),
        1,
    )
    return user_rank, total


# ============== DISPLAY ==============

def display_user_result(result: dict, rank: int, total: int) -> None:
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

    print(f"  {Fore.WHITE}👤 Name              : {Fore.CYAN}{result['candidate_name']}")
    print(f"  {Fore.WHITE}🎓 Semester           : {Fore.CYAN}{result.get('semester', 'N/A')}")
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

    print(f"\n{Fore.CYAN}{'─'*65}")
    print(f"  {Fore.YELLOW}🏆 YOUR RANK          : {Fore.WHITE}{rank} out of {total} candidates (Sem {result.get('semester', '?')})")
    print(f"  {Fore.YELLOW}📈 YOUR PERCENTILE    : {Fore.WHITE}Top {percentile}%")

    print(f"\n  ", end="")
    if rank == 1:
        print(f"{Fore.GREEN}🥇 You are the TOP candidate among all applicants in your sem!")
    elif percentile >= 75:
        print(f"{Fore.GREEN}🎉 You are in the TOP 25% of your semester — great work!")
    elif percentile >= 50:
        print(f"{Fore.YELLOW}👍 You are in the TOP half of your semester. Keep it up!")
    elif percentile >= 25:
        print(f"{Fore.MAGENTA}📌 You are in the bottom half. Work on the missing skills above.")
    else:
        print(f"{Fore.RED}⚠️  You are in the bottom 25%. Focus on the missing skills listed above.")

    print(f"{Fore.CYAN}{'='*65}\n")


# ============== INPUT HELPERS ==============

def ask_semester() -> str:
    """Ask user for their semester."""
    print(f"\n{Fore.YELLOW}🎓 Which semester are you in?\n")
    print(f"   {Fore.CYAN}[3]{Fore.WHITE} Semester 3")
    print(f"   {Fore.CYAN}[4]{Fore.WHITE} Semester 4")

    while True:
        choice = input(f"\n{Fore.CYAN}   Enter semester (3 or 4) : {Fore.WHITE}").strip()
        if choice in ("3", "4"):
            return choice
        print(Fore.RED + "   Invalid. Please enter 3 or 4.")


def ask_branch() -> str:
    """Ask user to pick a branch."""
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
    """Ask user to pick a role within the selected branch."""
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


# ============== MAIN ==============

if __name__ == "__main__":

    print(f"\n{Fore.CYAN}{'='*65}")
    print(f"{Fore.YELLOW}  🎓 RESUME RANKER — Check Your Standing")
    print(f"{Fore.CYAN}{'='*65}")

    if not job_skill_profiles:
        print(Fore.RED + "❌ job_skill_profiles is empty. Check job_desc/")
        sys.exit(1)

    # ── Step 1: Semester ─────────────────────────────────────────────────────
    semester = ask_semester()
    print(f"{Fore.GREEN}✅ Selected Semester : {Fore.WHITE}{semester}")

    # ── Step 2: Branch ───────────────────────────────────────────────────────
    branch = ask_branch()
    print(f"{Fore.GREEN}✅ Selected Branch   : {Fore.WHITE}{branch}")

    # ── Step 3: Job Role ─────────────────────────────────────────────────────
    selected_role = ask_role_within_branch(branch)
    _skills_display = get_skills_list(job_skill_profiles[selected_role])
    print(f"{Fore.GREEN}✅ Selected Role     : {Fore.WHITE}{selected_role}")
    print(f"{Fore.GREEN}📋 Required Skills   : {Fore.WHITE}{', '.join(_skills_display[:10])}...\n")

    # ── Step 4: Candidate name ───────────────────────────────────────────────
    user_name = input(f"{Fore.WHITE}👤 Enter your name : {Fore.CYAN}").strip()
    if not user_name:
        user_name = "User"

    # ── Step 5: Resume path ──────────────────────────────────────────────────
    print(f"\n{Fore.WHITE}📁 Enter the full path to your resume file (.pdf or .pptx)")
    print(f"{Fore.WHITE}   Example : C:/Users/you/Documents/my_resume.pdf")
    resume_path = input(f"{Fore.CYAN}   Path : ").strip().strip('"').strip("'")

    if not os.path.exists(resume_path):
        print(Fore.RED + f"\n❌ File not found : '{resume_path}'")
        sys.exit(1)

    # ── Step 6: Extract resume text ──────────────────────────────────────────
    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        print(Fore.RED + "❌ Could not extract text from your resume. Exiting.")
        sys.exit(1)

    # ── Step 7: Rank via ranking.py ──────────────────────────────────────────
    print(f"{Fore.YELLOW}⚙️  Calculating your ranking score for '{selected_role}'...\n")
    result = rank_resume(resume_text, selected_role)

    # Attach extra fields
    result["candidate_name"] = user_name
    result["resume_length"]  = len(resume_text.split())
    result["semester"]       = semester
    result["branch"]         = branch

    # ── Step 8: Update sem-specific CSV ──────────────────────────────────────
    user_rank, total = update_csv_with_user(result, semester)

    # ── Step 9: Display ──────────────────────────────────────────────────────
    display_user_result(result, user_rank, total)
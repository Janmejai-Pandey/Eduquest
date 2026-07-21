"""
pyq_main.py
CLI for PYQ Analyser.
Run from src/IR/:  python pyq_main.py
"""

import os
import sys
import re
import textwrap
from colorama import Fore, Style, init

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pyq_analyser import (
    load_gdrive_links,
    get_subjects_with_pyqs,
    get_pyq_files,
    get_pyq_files_for_exam,
    get_lecture_context,
    gather_pyq_content,
    run_analysis,
    generate_practice_paper,
    parse_practice_paper,
    resolve_subject,
    SUBJECTS_WITH_LAB_THEORY,
    SUBJECT_ALIASES,
)

init(autoreset=True)

WRAP = 90


def wrap(text, width=WRAP):
    return "\n".join(
        textwrap.fill(line, width) if line.strip() else line
        for line in text.splitlines()
    )


def print_banner():
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "   PYQ INTELLIGENCE ANALYSER  |  Groq + OpenRouter")
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + "   Reveals hot topics, patterns & predicted papers")
    print(Fore.YELLOW + "   No downloads | No saving | Fresh every run")
    print(Fore.CYAN + "=" * 60 + "\n")


# ============== INPUT HELPERS ==============

def ask_semester() -> str:
    while True:
        print(Fore.YELLOW + "Which semester?")
        print(Fore.WHITE + "  [3] Semester 3")
        print(Fore.WHITE + "  [4] Semester 4")
        choice = input(
            Fore.GREEN + "\nEnter (3 or 4): " + Style.RESET_ALL
        ).strip()
        if choice in ("3", "4"):
            return choice
        print(Fore.RED + "Invalid choice.\n")


def display_all_subjects(subjects: list):
    """Show ALL available subjects with aliases up front."""
    print(Fore.YELLOW + "\n" + "=" * 60)
    print(Fore.YELLOW + "   AVAILABLE SUBJECTS WITH PYQs")
    print(Fore.YELLOW + "=" * 60 + "\n")

    for i, subj in enumerate(subjects, start=1):
        # Find short forms that map to this subject
        aliases = [
            k for k, v in SUBJECT_ALIASES.items()
            if v == subj
            and k not in ("dbms lab", "ds lab", "dbms theory", "ds theory")
        ]
        alias_str = ""
        if aliases:
            top_aliases = aliases[:3]
            alias_str = f" {Fore.CYAN}(a.k.a. {', '.join(top_aliases)})"

        print(f"  {Fore.WHITE}[{i}] {subj}{alias_str}")

    print(f"\n{Fore.MAGENTA}Tip: You can type a number OR a short form")
    print(f"{Fore.MAGENTA}     e.g. 'maths' for MFAIDS, 'dbms' for DBMS, 'toc' for TOC")
    print()


def ask_subject(subjects: list) -> str:
    """Ask user for subject, resolve aliases, handle lab/theory ambiguity."""
    display_all_subjects(subjects)

    while True:
        raw_input_val = input(
            Fore.GREEN + f"Select subject (1-{len(subjects)} or short form): "
            + Style.RESET_ALL
        ).strip()

        if not raw_input_val:
            print(Fore.RED + "Please enter something.")
            continue

        # Try numeric selection first
        if raw_input_val.isdigit():
            idx = int(raw_input_val) - 1
            if 0 <= idx < len(subjects):
                selected = subjects[idx]
                # Check if this is one where we should ask lab/theory
                for key, (theory, lab) in SUBJECTS_WITH_LAB_THEORY.items():
                    if selected == theory or selected == lab:
                        # Only ask if BOTH exist in this sem
                        if theory in subjects and lab in subjects:
                            return ask_lab_or_theory_from_selection(
                                key, theory, lab, subjects
                            )
                return selected
            print(Fore.RED + f"Enter a number between 1 and {len(subjects)}.")
            continue

        # Try alias / fuzzy resolution
        resolved = resolve_subject(raw_input_val, subjects)
        if resolved is None:
            print(Fore.RED + f"Couldn't understand '{raw_input_val}'. "
                             "Try a number or a valid short form.\n")
            continue

        canonical, ambiguous_key = resolved

        # If alias is ambiguous (like 'dbms' → theory or lab?), ask
        if ambiguous_key and ambiguous_key in SUBJECTS_WITH_LAB_THEORY:
            theory, lab = SUBJECTS_WITH_LAB_THEORY[ambiguous_key]
            # Only ask if BOTH available in this sem
            if theory in subjects and lab in subjects:
                return ask_lab_or_theory(ambiguous_key, theory, lab)
            elif theory in subjects:
                return theory
            elif lab in subjects:
                return lab

        # Verify the resolved subject exists
        if canonical in subjects:
            return canonical

        # Fuzzy fallback
        for s in subjects:
            if canonical.lower() in s.lower() or s.lower() in canonical.lower():
                return s

        print(Fore.RED + f"Subject '{canonical}' not available in this semester.\n")


def ask_lab_or_theory(alias_key: str, theory: str, lab: str) -> str:
    """Prompt user to choose Lab or Theory version."""
    print(Fore.YELLOW + f"\n'{alias_key.upper()}' has both Theory and Lab. Which one?")
    print(Fore.WHITE + f"  [1] {theory}  (Theory)")
    print(Fore.WHITE + f"  [2] {lab}  (Lab)")

    while True:
        choice = input(
            Fore.GREEN + "\nSelect (1 or 2): " + Style.RESET_ALL
        ).strip()
        if choice == "1":
            return theory
        if choice == "2":
            return lab
        print(Fore.RED + "Enter 1 or 2.")


def ask_lab_or_theory_from_selection(
    key: str, theory: str, lab: str, subjects: list
) -> str:
    """Called when user picks a numbered item that has Lab/Theory ambiguity."""
    # If user already picked one specifically (theory OR lab), just return it
    # This function is here for defensive completeness
    return ask_lab_or_theory(key, theory, lab)


def ask_exam() -> str:
    print(Fore.YELLOW + "\nWhich exam are you preparing for?\n")
    print(Fore.WHITE + "  [1] T1 (Test 1)")
    print(Fore.WHITE + "  [2] T2 (Test 2)")
    print(Fore.WHITE + "  [3] T3 (End Semester)")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect exam (1/2/3): " + Style.RESET_ALL
        ).strip()
        if choice == "1":
            return "T1"
        if choice == "2":
            return "T2"
        if choice == "3":
            return "T3"
        print(Fore.RED + "Invalid.")


def ask_mode() -> str:
    print(Fore.YELLOW + "\nAnalysis mode:\n")
    print(Fore.WHITE + "  [1] Full Analysis Report")
    print(Fore.WHITE + "      (topics + patterns + predicted questions + study plan)")
    print(Fore.WHITE + "  [2] Topic Frequency Only")
    print(Fore.WHITE + "      (quick view of what's asked most)")
    print(Fore.WHITE + "  [3] Generate Practice Paper (Interactive)")
    print(Fore.WHITE + "      (predicted paper + attempt it live)")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect mode (1/2/3): " + Style.RESET_ALL
        ).strip()
        if choice in ("1", "2", "3"):
            return choice
        print(Fore.RED + "Invalid.")


# ============== DISPLAY HELPERS ==============

def make_bar(count: int, max_count: int, width: int = 20) -> str:
    if max_count == 0:
        return ""
    filled = int((count / max_count) * width)
    return "█" * filled + "░" * (width - filled)


def priority_color(priority: str) -> str:
    p = (priority or "").upper()
    if p == "HIGH":   return Fore.RED
    if p == "MEDIUM": return Fore.YELLOW
    if p == "LOW":    return Fore.GREEN
    return Fore.WHITE


def display_topic_frequency(analysis: dict, subject: str, exam: str):
    topics = analysis.get("topic_frequency", [])
    if not topics:
        print(Fore.RED + "No topics extracted.")
        return

    max_count = max((t.get("count", 0) for t in topics), default=1)

    print(Fore.CYAN + "\n" + "=" * 70)
    print(Fore.YELLOW + f"   🔥 TOP TOPICS  ({subject} - {exam})")
    print(Fore.CYAN + "=" * 70)
    print(
        Fore.MAGENTA
        + f"\n  {'#':<3} {'Topic':<32} {'Freq':<6} {'Marks':<7} {'Bar':<22} {'Priority'}"
    )
    print(Fore.CYAN + "  " + "─" * 68)

    for i, t in enumerate(topics, start=1):
        topic_name = t.get("topic", "N/A")[:30]
        count      = t.get("count", 0)
        marks      = t.get("typical_marks", 0)
        priority   = t.get("priority", "N/A")
        bar        = make_bar(count, max_count, width=20)
        pcolor     = priority_color(priority)

        print(
            f"  {Fore.WHITE}{i:<3} "
            f"{Fore.WHITE}{topic_name:<32} "
            f"{Fore.CYAN}{count:<6} "
            f"{Fore.BLUE}{marks:<7} "
            f"{Fore.GREEN}{bar}  "
            f"{pcolor}{priority}"
        )
    print(Fore.CYAN + "\n" + "=" * 70 + "\n")


def display_question_types(analysis: dict):
    qtypes = analysis.get("question_type_distribution", {})
    if not qtypes:
        return

    print(Fore.YELLOW + "   📝 QUESTION TYPE DISTRIBUTION")
    print(Fore.CYAN + "   " + "─" * 40)

    labels = [
        ("Long Answer",   qtypes.get("long_answer_percent", 0)),
        ("Short Answer",  qtypes.get("short_answer_percent", 0)),
        ("MCQ",           qtypes.get("mcq_percent", 0)),
        ("Numerical",     qtypes.get("numerical_percent", 0)),
    ]

    for label, pct in labels:
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"   {Fore.WHITE}{label:<15} {Fore.GREEN}{bar}  {Fore.CYAN}{pct}%")
    print()


def display_marks_pattern(analysis: dict):
    marks = analysis.get("marks_pattern", {})
    if not marks:
        return

    print(Fore.YELLOW + "   💯 MARKS PATTERN")
    print(Fore.CYAN + "   " + "─" * 40)
    print(f"   {Fore.WHITE}Total marks (typical) : {Fore.CYAN}{marks.get('total_marks_typical', 'N/A')}")
    print(f"   {Fore.WHITE}Most common Q marks   : {Fore.CYAN}{marks.get('most_common_question_marks', 'N/A')}")
    notes = marks.get("notes", "")
    if notes:
        print(f"   {Fore.WHITE}Notes                 : {Fore.CYAN}{notes}")
    print()


def display_recurring_questions(analysis: dict):
    recurring = analysis.get("recurring_questions", [])
    if not recurring:
        return

    print(Fore.YELLOW + "   🔁 RECURRING QUESTION PATTERNS")
    print(Fore.CYAN + "   " + "─" * 40)
    for i, r in enumerate(recurring[:8], start=1):
        pattern = r.get("question_pattern", "")[:80]
        freq    = r.get("frequency", 0)
        topic   = r.get("topic", "")
        print(f"   {Fore.WHITE}[{i}] {Fore.CYAN}({freq}x) {Fore.WHITE}{pattern}")
        if topic:
            print(f"        {Fore.MAGENTA}→ Topic: {topic}")
    print()


def display_must_study(analysis: dict):
    must_study = analysis.get("must_study_topics", [])
    if not must_study:
        return

    print(Fore.YELLOW + "   🎯 MUST-STUDY TOPICS (Priority Order)")
    print(Fore.CYAN + "   " + "─" * 40)
    for i, topic in enumerate(must_study, start=1):
        print(f"   {Fore.RED}[{i}] {Fore.WHITE}{topic}")
    print()


def display_summary(analysis: dict, subject: str, exam: str, papers: list):
    print(Fore.CYAN + "\n" + "=" * 70)
    print(Fore.YELLOW + f"   📊 {subject.upper()} - PYQ INTELLIGENCE REPORT  ({exam})")
    print(Fore.CYAN + "=" * 70 + "\n")

    print(f"  {Fore.WHITE}📌 Papers analyzed : {Fore.CYAN}{len(papers)}")
    print(f"  {Fore.WHITE}📅 Years covered   : {Fore.CYAN}{analysis.get('years_covered', 'various')}")

    summary = analysis.get("coverage_summary", "")
    if summary:
        print(f"\n  {Fore.WHITE}📖 Overview       :")
        print(wrap("     " + summary))

    trend = analysis.get("difficulty_trend", "")
    if trend:
        print(f"\n  {Fore.WHITE}📈 Difficulty trend: {Fore.CYAN}{trend}")
    print()


def display_papers_list(papers: list, rejected: list = None):
    print(Fore.MAGENTA + "\n" + "─" * 70)
    print(Fore.MAGENTA + f"   ✓ Papers included in analysis ({len(papers)}):")
    for i, p in enumerate(papers, 1):
        print(Fore.WHITE + f"     [{i:>2}] {p}")

    if rejected:
        print(Fore.RED + f"\n   ✗ Papers rejected (subject mismatch): {len(rejected)}")
        for r in rejected:
            print(Fore.RED + f"        - {r}")

    print(Fore.MAGENTA + "─" * 70 + "\n")


# ============== INTERACTIVE PRACTICE ==============

def run_interactive_practice(questions: list):
    if not questions:
        print(Fore.RED + "No questions could be parsed for interactive mode.")
        return

    print(Fore.CYAN + "\n" + "=" * 60)
    print(Fore.CYAN + f"   INTERACTIVE PRACTICE PAPER - {len(questions)} questions")
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + "   Type your answer and press Enter.")
    print(Fore.YELLOW + "   Type 'skip' to skip, 'quit' to end early.\n")

    score = 0
    attempted = 0

    for idx, q in enumerate(questions, start=1):
        print(Fore.CYAN + "\n" + "-" * 60)
        print(Fore.CYAN + f"   {q['header']}")
        print(Fore.CYAN + "-" * 60)
        print(Style.RESET_ALL + wrap(q["question_block"]))
        print()

        user_ans = input(
            Fore.GREEN + "Your answer: " + Style.RESET_ALL
        ).strip()

        if user_ans.lower() == "quit":
            print(Fore.YELLOW + "\nPractice ended early.\n")
            break

        if user_ans.lower() == "skip" or not user_ans:
            print(Fore.YELLOW + "Skipped.")
            if q["answer"]:
                print(Fore.CYAN + f"Correct answer: {q['answer']}")
                if q["explanation"]:
                    print(Fore.WHITE + f"Explanation: {q['explanation']}")
            continue

        attempted += 1

        if q["answer"]:
            correct = q["answer"].lower().strip()
            user = user_ans.lower().strip()
            mcq_letter = re.match(r"^\(?([a-d])\)?$", user)
            correct_letter = re.search(r"\b([A-D])\b", q["answer"])
            is_correct = False

            if mcq_letter and correct_letter:
                is_correct = (
                    mcq_letter.group(1).upper() == correct_letter.group(1).upper()
                )
            else:
                is_correct = (
                    user in correct or correct in user
                    or any(w in correct for w in user.split() if len(w) > 3)
                )

            if is_correct:
                print(Fore.GREEN + "Correct!")
                score += 1
            else:
                print(Fore.RED + "Incorrect.")
                print(Fore.CYAN + f"Expected: {q['answer']}")
            if q["explanation"]:
                print(Fore.WHITE + f"Explanation: {q['explanation']}")
        else:
            print(Fore.YELLOW + "(No answer available)")

    print(Fore.CYAN + "\n" + "=" * 60)
    print(Fore.CYAN + "   PRACTICE RESULTS")
    print(Fore.CYAN + "=" * 60)
    total = len(questions)
    pct = (score / attempted * 100) if attempted > 0 else 0
    print(Fore.WHITE + f"   Score:     {score} / {attempted} attempted")
    print(Fore.WHITE + f"   Total Qs:  {total}")
    print(Fore.WHITE + f"   Accuracy:  {pct:.1f}%")
    print(Fore.CYAN + "=" * 60 + "\n")


# ============== MAIN FLOW ==============

def main():
    print_banner()

    # Step 1: Semester
    semester = ask_semester()
    print(Fore.CYAN + f"\n✓ Selected Semester {semester}")

    # Step 2: Load metadata
    try:
        links = load_gdrive_links(semester)
    except FileNotFoundError as e:
        print(Fore.RED + f"Error: {e}")
        return

    # Step 3: Subjects
    subjects = get_subjects_with_pyqs(links)
    if not subjects:
        print(Fore.RED + "No subjects with PYQs found for this semester.")
        return

    subject = ask_subject(subjects)
    print(Fore.CYAN + f"\n✓ Selected subject: {subject}")

    # Step 4: Exam
    exam = ask_exam()
    print(Fore.CYAN + f"\n✓ Selected exam: {exam}")

    # Step 5: Filter PYQ files
    all_pyqs = get_pyq_files(links, subject)
    pyqs_for_exam = get_pyq_files_for_exam(all_pyqs, exam)

    if not pyqs_for_exam:
        print(
            Fore.RED
            + f"\nNo {exam} papers found for '{subject}'."
            + f"\nAvailable PYQ files for this subject: {len(all_pyqs)}"
        )
        if all_pyqs:
            print(Fore.YELLOW + "\n   Available (but no exam-type match):")
            for p in all_pyqs:
                print(f"     - {p.get('item_name')}")
        return

    print(Fore.CYAN + f"\n✓ Found {len(pyqs_for_exam)} candidate {exam} paper(s):")
    for p in pyqs_for_exam:
        print(f"   - {p.get('item_name')}")

    # Step 6: Analysis mode
    mode = ask_mode()

    # Step 7: Gather content (with subject verification)
    print(Fore.YELLOW + "\nGathering & verifying content from PYQ papers...\n")
    content, included, rejected = gather_pyq_content(pyqs_for_exam, subject)

    if not content.strip():
        print(Fore.RED + "\n❌ No papers passed subject verification.")
        if rejected:
            print(Fore.YELLOW + "   All candidates were rejected — likely the papers")
            print(Fore.YELLOW + "   don't have clear subject markers or belong to another subject.")
            print(Fore.YELLOW + f"   Rejected: {rejected}")
        return

    word_count = len(content.split())
    print(Fore.CYAN + f"\n✓ Extracted {word_count} words from {len(included)} verified paper(s)")
    if rejected:
        print(Fore.YELLOW + f"   ⚠ Skipped {len(rejected)} unverified paper(s)")
    print()

    # Step 8: Run analysis
    analysis = run_analysis(content, subject, exam, len(included))

    if analysis.get("_parse_error"):
        print(Fore.RED + "\nCould not parse LLM analysis output.")
        print(Fore.YELLOW + "Raw LLM response was:")
        print(Fore.WHITE + analysis.get("raw", "")[:1000])
        return

    # Step 9: Display based on mode
    if mode == "1":
        # Full Analysis Report
        display_summary(analysis, subject, exam, included)
        display_topic_frequency(analysis, subject, exam)
        display_question_types(analysis)
        display_marks_pattern(analysis)
        display_recurring_questions(analysis)
        display_must_study(analysis)

        print(Fore.CYAN + "=" * 70)
        print(Fore.YELLOW + "   ⭐ PREDICTED QUESTIONS FOR NEXT EXAM")
        print(Fore.CYAN + "=" * 70 + "\n")

        lecture_syllabus = get_lecture_context(links, subject)
        paper_text = generate_practice_paper(
            analysis, subject, exam, lecture_syllabus, len(included)
        )
        print(Style.RESET_ALL + wrap(paper_text))
        display_papers_list(included, rejected)

    elif mode == "2":
        # Topic Frequency Only
        display_summary(analysis, subject, exam, included)
        display_topic_frequency(analysis, subject, exam)
        display_must_study(analysis)
        display_papers_list(included, rejected)

    else:
        # Interactive Practice Paper
        display_summary(analysis, subject, exam, included)
        print(Fore.YELLOW + "\nGenerating predicted practice paper...\n")

        lecture_syllabus = get_lecture_context(links, subject)
        paper_text = generate_practice_paper(
            analysis, subject, exam, lecture_syllabus, len(included)
        )

        questions = parse_practice_paper(paper_text)
        print(Fore.CYAN + f"Parsed {len(questions)} questions for interactive practice\n")
        run_interactive_practice(questions)
        display_papers_list(included, rejected)

    # Continue?
    again = input(
        Fore.YELLOW + "Analyze another? (y/n): " + Style.RESET_ALL
    ).strip().lower()
    if again in ("y", "yes"):
        main()
    else:
        print(Fore.CYAN + "\nGoodbye!\n")


if __name__ == "__main__":
    main()
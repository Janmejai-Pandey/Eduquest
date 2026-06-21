"""
quiz_main.py
CLI for quiz generation.
Run from src/IR/:  python quiz_main.py
"""

import os
import sys
import textwrap
from colorama import Fore, Style, init

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quiz_generator import (
    load_gdrive_links,
    get_subjects,
    get_available_categories,
    get_files_by_category,
    get_pyq_years,
    get_pyq_files_by_year,
    gather_content,
    auto_num_questions,
    generate_quiz,
    parse_quiz,
    save_quiz,
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
    print(Fore.CYAN + "   QUIZ GENERATOR  |  Groq LLM")
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + "   Generate practice quizzes from lectures,")
    print(Fore.YELLOW + "   tutorials & previous year question papers")
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


def ask_subject(subjects: list) -> str:
    print(Fore.YELLOW + "\nAvailable subjects:\n")
    for i, subj in enumerate(subjects, start=1):
        print(Fore.WHITE + f"  [{i}] {subj}")
    while True:
        choice = input(
            Fore.GREEN + f"\nSelect subject (1-{len(subjects)}): "
            + Style.RESET_ALL
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(subjects):
                return subjects[idx]
        except ValueError:
            pass
        print(Fore.RED + "Invalid selection.")


def ask_category(categories: list) -> str:
    """Ask user to pick a category."""
    print(Fore.YELLOW + "\nAvailable categories:\n")
    for i, cat in enumerate(categories, start=1):
        print(Fore.WHITE + f"  [{i}] {cat}")
    while True:
        choice = input(
            Fore.GREEN + f"\nSelect category (1-{len(categories)}): "
            + Style.RESET_ALL
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                return categories[idx]
        except ValueError:
            pass
        print(Fore.RED + "Invalid selection.")


def display_files(files: list, label: str = "files"):
    print(Fore.YELLOW + f"\nAvailable {label} ({len(files)}):\n")
    for i, f in enumerate(files, start=1):
        name = f.get("item_name", "Unknown")
        print(Fore.WHITE + f"  [{i:>3}] {name}")
    print()


def ask_lecture_or_tut_mode(category: str) -> str:
    """Ask: single / range / all."""
    print(Fore.YELLOW + f"\n{category} selection mode:")
    print(Fore.WHITE + f"  [1] Single {category[:-1].lower()}")
    print(Fore.WHITE + f"  [2] Range of {category.lower()}")
    print(Fore.WHITE + f"  [3] All {category.lower()} (full subject)")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect mode (1/2/3): " + Style.RESET_ALL
        ).strip()
        if choice in ("1", "2", "3"):
            return choice
        print(Fore.RED + "Invalid.")


def ask_single_file(files: list) -> dict:
    display_files(files)
    while True:
        choice = input(
            Fore.GREEN + "Enter number or part of name: "
            + Style.RESET_ALL
        ).strip()
        if not choice:
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
        except ValueError:
            pass
        lower = choice.lower()
        matches = [
            f for f in files
            if lower in f.get("item_name", "").lower()
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(Fore.YELLOW + "Multiple matches:")
            for i, m in enumerate(matches, 1):
                print(f"  [{i}] {m['item_name']}")
            sub = input(
                Fore.GREEN + "Pick one (number): " + Style.RESET_ALL
            ).strip()
            try:
                si = int(sub) - 1
                if 0 <= si < len(matches):
                    return matches[si]
            except ValueError:
                pass
        print(Fore.RED + "Not found. Try again.")


def ask_file_range(files: list) -> list:
    display_files(files)
    while True:
        print(Fore.YELLOW + "Enter range:")
        s = input(
            Fore.GREEN + "  From: " + Style.RESET_ALL
        ).strip()
        e = input(
            Fore.GREEN + "  To:   " + Style.RESET_ALL
        ).strip()
        try:
            start = int(s) - 1
            end = int(e)
            if 0 <= start < end <= len(files):
                selected = files[start:end]
                print(Fore.CYAN + f"\n  Selected {len(selected)} files:")
                for f in selected:
                    print(f"    - {f['item_name']}")
                confirm = input(
                    Fore.GREEN + "\n  Proceed? (y/n): " + Style.RESET_ALL
                ).strip().lower()
                if confirm in ("y", "yes", ""):
                    return selected
                else:
                    continue
        except ValueError:
            pass
        print(Fore.RED + "Invalid.\n")


def ask_pyq_year(years: list) -> str:
    print(Fore.YELLOW + "\nAvailable PYQ years for this subject:\n")
    for i, y in enumerate(years, start=1):
        print(Fore.WHITE + f"  [{i}] {y}")
    while True:
        choice = input(
            Fore.GREEN + f"\nSelect year (1-{len(years)}): "
            + Style.RESET_ALL
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(years):
                return years[idx]
        except ValueError:
            pass
        print(Fore.RED + "Invalid.")


def ask_question_types() -> list:
    """Multi-select question types."""
    types = [
        ("MCQ", "Multiple Choice Questions (4 options)"),
        ("Short Answer", "1-2 line answer questions"),
        ("True/False", "True or False statements"),
        ("Fill in the Blanks", "Fill the missing word/phrase"),
        ("Long Answer", "Descriptive 5-10 marks style"),
        ("Numerical", "Numerical/calculation problems"),
    ]
    print(Fore.YELLOW + "\nQuestion types (multi-select):\n")
    for i, (t, desc) in enumerate(types, start=1):
        print(Fore.WHITE + f"  [{i}] {t} - {desc}")
    print(Fore.CYAN + "\n  Enter numbers separated by commas (e.g. 1,3,4)")
    print(Fore.CYAN + "  Or 'all' for everything\n")
    while True:
        raw = input(
            Fore.GREEN + "Your choice: " + Style.RESET_ALL
        ).strip().lower()
        if raw == "all":
            return [t[0] for t in types]
        try:
            picks = [int(x.strip()) - 1 for x in raw.split(",") if x.strip()]
            chosen = [types[i][0] for i in picks if 0 <= i < len(types)]
            if chosen:
                return chosen
        except ValueError:
            pass
        print(Fore.RED + "Invalid input.")


def ask_difficulty() -> str:
    print(Fore.YELLOW + "\nDifficulty level:")
    options = ["Easy", "Medium", "Hard", "Mixed"]
    for i, o in enumerate(options, 1):
        print(Fore.WHITE + f"  [{i}] {o}")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect (1-4): " + Style.RESET_ALL
        ).strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(Fore.RED + "Invalid.")


def ask_num_questions(content_word_count: int) -> int:
    suggested = auto_num_questions(" " * content_word_count)
    print(
        Fore.YELLOW
        + f"\nNumber of questions (suggested based on content: {suggested}):"
    )
    print(Fore.WHITE + "  Press Enter to use suggested, or type a number")
    while True:
        choice = input(
            Fore.GREEN + "Your choice: " + Style.RESET_ALL
        ).strip()
        if not choice:
            return suggested
        try:
            n = int(choice)
            if 1 <= n <= 50:
                return n
        except ValueError:
            pass
        print(Fore.RED + "Enter 1-50, or press Enter for suggested.")


def ask_quiz_mode() -> str:
    print(Fore.YELLOW + "\nQuiz mode:")
    print(Fore.WHITE + "  [1] Interactive Quiz (CLI test - answer questions live)")
    print(Fore.WHITE + "  [2] Generate & Save Only (worksheet style)")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect (1 or 2): " + Style.RESET_ALL
        ).strip()
        if choice == "1":
            return "interactive"
        if choice == "2":
            return "save"
        print(Fore.RED + "Invalid.")


def ask_answer_key_mode() -> str:
    print(Fore.YELLOW + "\nAnswer key placement:")
    print(Fore.WHITE + "  [1] Inline (after each question)")
    print(Fore.WHITE + "  [2] At the end of file")
    print(Fore.WHITE + "  [3] Separate file altogether")
    while True:
        choice = input(
            Fore.GREEN + "\nSelect (1/2/3): " + Style.RESET_ALL
        ).strip()
        if choice == "1":
            return "inline"
        if choice == "2":
            return "end"
        if choice == "3":
            return "separate"
        print(Fore.RED + "Invalid.")


# ============== DISPLAY HELPERS ==============

def print_links(links: list):
    if not links:
        return
    print(Fore.MAGENTA + "\n" + "=" * 60)
    print(Fore.MAGENTA + f"   SOURCE FILES ({len(links)}) - click to open")
    print(Fore.MAGENTA + "=" * 60)
    for i, link in enumerate(links, 1):
        print(Fore.WHITE + f"   [{i:>2}] {link['name']}")
        print(Fore.CYAN  + f"        {link['url']}")
    print(Fore.MAGENTA + "=" * 60 + "\n")


# ============== INTERACTIVE QUIZ MODE ==============

def run_interactive_quiz(questions: list):
    """Run the quiz live in the CLI."""
    if not questions:
        print(Fore.RED + "No questions could be parsed for interactive mode.")
        return

    print(Fore.CYAN + "\n" + "=" * 60)
    print(Fore.CYAN + f"   INTERACTIVE QUIZ - {len(questions)} questions")
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
            print(Fore.YELLOW + "\nQuiz ended early.\n")
            break

        if user_ans.lower() == "skip" or not user_ans:
            print(Fore.YELLOW + "Skipped.")
            if q["answer"]:
                print(Fore.CYAN + f"Correct answer: {q['answer']}")
                if q["explanation"]:
                    print(Fore.WHITE + f"Explanation: {q['explanation']}")
            continue

        attempted += 1

        # Compare answers loosely
        if q["answer"]:
            correct = q["answer"].lower().strip()
            user = user_ans.lower().strip()
            # MCQ-style: accept "a", "(a)", "A", "option a", etc.
            mcq_letter = re.match(r"^\(?([a-d])\)?$", user)
            correct_letter = re.search(r"\b([A-D])\b", q["answer"])
            is_correct = False

            if mcq_letter and correct_letter:
                is_correct = (
                    mcq_letter.group(1).upper() == correct_letter.group(1).upper()
                )
            else:
                # Loose substring match
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
            print(Fore.YELLOW + "(No answer key available for this question)")

    # Final score
    print(Fore.CYAN + "\n" + "=" * 60)
    print(Fore.CYAN + "   QUIZ RESULTS")
    print(Fore.CYAN + "=" * 60)
    total = len(questions)
    pct = (score / attempted * 100) if attempted > 0 else 0
    print(Fore.WHITE + f"   Score:     {score} / {attempted} attempted")
    print(Fore.WHITE + f"   Total Qs:  {total}")
    print(Fore.WHITE + f"   Accuracy:  {pct:.1f}%")
    print(Fore.CYAN + "=" * 60 + "\n")


# ============== MAIN FLOW ==============

import re  # used in interactive

def main():
    print_banner()

    # Step 1: Semester
    semester = ask_semester()
    print(Fore.CYAN + f"\nSelected Semester {semester}\n")

    # Step 2: Load metadata
    try:
        links = load_gdrive_links(semester)
    except FileNotFoundError as e:
        print(Fore.RED + f"Error: {e}")
        return

    # Step 3: Subject
    subjects = get_subjects(links)
    subject = ask_subject(subjects)
    print(Fore.CYAN + f"\nSelected: {subject}\n")

    # Step 4: Category
    categories = get_available_categories(links, subject)
    # Filter out Course Description for quiz purposes
    categories = [c for c in categories if c != "Course Description"]
    if not categories:
        print(Fore.RED + "No suitable categories available for this subject.")
        return
    category = ask_category(categories)
    print(Fore.CYAN + f"\nCategory: {category}\n")

    # Step 5: File selection (different flow for PYQs)
    selected_files = []
    label = ""

    if category == "PYQs":
        pyq_files = get_files_by_category(links, subject, "PYQs")
        if not pyq_files:
            print(Fore.RED + "No PYQ files found.")
            return
        years = get_pyq_years(pyq_files)
        if len(years) == 1 and years[0] == "Untagged":
            print(
                Fore.YELLOW
                + "No year tags found in PYQ filenames. Using all PYQs."
            )
            selected_files = pyq_files
            label = f"PYQ_All"
        else:
            year = ask_pyq_year(years)
            selected_files = get_pyq_files_by_year(pyq_files, year)
            label = f"PYQ_{year}"
            print(Fore.CYAN + f"\n  Selected {len(selected_files)} PYQ file(s) for {year}:")
            for f in selected_files:
                print(f"    - {f['item_name']}")
    else:
        # Lectures or Tutorials
        files = get_files_by_category(links, subject, category)
        if not files:
            print(Fore.RED + f"No {category} found for this subject.")
            return
        print(Fore.CYAN + f"Found {len(files)} {category} file(s)")
        mode = ask_lecture_or_tut_mode(category)

        if mode == "1":
            f = ask_single_file(files)
            selected_files = [f]
            label = f["item_name"]
        elif mode == "2":
            selected_files = ask_file_range(files)
            label = (
                f"{selected_files[0]['item_name']}_to_"
                f"{selected_files[-1]['item_name']}"
            )
        else:
            selected_files = files
            label = f"All_{category}"

    # Step 6: Question types
    qtypes = ask_question_types()
    print(Fore.CYAN + f"\nSelected types: {', '.join(qtypes)}\n")

    # Step 7: Difficulty
    difficulty = ask_difficulty()
    print(Fore.CYAN + f"\nDifficulty: {difficulty}\n")

    # Step 8: Gather content
    print(Fore.YELLOW + "\nGathering content from selected files...\n")
    content, processed_links = gather_content(selected_files)
    if not content.strip():
        print(Fore.RED + "Could not extract any text from selected files.")
        return
    word_count = len(content.split())
    print(Fore.CYAN + f"\nTotal content: {word_count} words")

    # Step 9: Number of questions
    num_q = ask_num_questions(word_count)
    print(Fore.CYAN + f"\nWill generate {num_q} questions\n")

    # Step 10: Quiz mode
    quiz_mode = ask_quiz_mode()

    # Step 11: Answer key placement
    answer_key_mode = ask_answer_key_mode()

    # Step 12: Generate
    quiz_text = generate_quiz(
        content=content,
        subject=subject,
        label=label,
        question_types=qtypes,
        difficulty=difficulty,
        num_questions=num_q,
        answer_key_mode=answer_key_mode,
    )

    # Step 13: Save
    quiz_path, answers_path = save_quiz(
        quiz_text=quiz_text,
        semester=semester,
        subject=subject,
        label=label,
        links=processed_links,
        answer_key_mode=answer_key_mode,
    )

    # Step 14: Display + interactive
    if quiz_mode == "save":
        print(Fore.CYAN + "\n" + "=" * 60)
        print(Fore.CYAN + "   QUIZ (preview)")
        print(Fore.CYAN + "=" * 60 + "\n")
        # Show only first 1500 chars in CLI to avoid flooding
        preview = quiz_text[:1500]
        print(Style.RESET_ALL + wrap(preview))
        if len(quiz_text) > 1500:
            print(Fore.YELLOW + "\n... (truncated - see saved file for full quiz)")
        print_links(processed_links)
        print(Fore.GREEN + f"Quiz saved to: {quiz_path}")
        if answers_path:
            print(Fore.GREEN + f"Answers saved to: {answers_path}")
        print()
    else:
        # Interactive mode
        questions = parse_quiz(quiz_text)
        print(Fore.CYAN + f"\nParsed {len(questions)} questions for interactive mode\n")
        run_interactive_quiz(questions)
        print_links(processed_links)
        print(Fore.GREEN + f"Full quiz also saved to: {quiz_path}")
        if answers_path:
            print(Fore.GREEN + f"Answers saved to: {answers_path}")
        print()

    # Continue?
    again = input(
        Fore.YELLOW + "Generate another quiz? (y/n): " + Style.RESET_ALL
    ).strip().lower()
    if again in ("y", "yes"):
        main()
    else:
        print(Fore.CYAN + "\nGoodbye!\n")


if __name__ == "__main__":
    main()
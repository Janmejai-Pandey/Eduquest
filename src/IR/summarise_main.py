"""
summarise_main.py
CLI for lecture summarisation.
Streams files directly from Google Drive - no local downloads.
Run from src/IR/:  python summarise_main.py
"""

import os
import sys
import textwrap
from colorama import Fore, Style, init

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from summariser import (
    load_gdrive_links,
    get_subjects,
    get_lecture_files,
    summarise_single_lecture,
    summarise_lecture_series,
    save_summary,
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
    print(Fore.CYAN + "   LECTURE SUMMARISER  |  Groq LLM")
    print(Fore.CYAN + "=" * 60)
    print(Fore.YELLOW + "   Streams lectures directly from Google Drive")
    print(Fore.YELLOW + "   No local downloads - includes shareable links")
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
        print(Fore.RED + "Invalid choice. Please enter 3 or 4.\n")


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
        print(Fore.RED + "Invalid selection. Try again.")


def ask_mode() -> str:
    print(Fore.YELLOW + "\nSummarisation mode:")
    print(Fore.WHITE + "  [1] Single lecture")
    print(Fore.WHITE + "  [2] Series of lectures (range)")

    while True:
        choice = input(
            Fore.GREEN + "\nSelect mode (1 or 2): " + Style.RESET_ALL
        ).strip()
        if choice in ("1", "2"):
            return choice
        print(Fore.RED + "Invalid. Enter 1 or 2.")


def display_lectures(lectures: list):
    print(Fore.YELLOW + f"\nAvailable lectures ({len(lectures)}):\n")
    for i, lec in enumerate(lectures, start=1):
        name = lec.get("item_name", "Unknown")
        print(Fore.WHITE + f"  [{i:>3}] {name}")
    print()


def ask_single_lecture(lectures: list) -> dict:
    display_lectures(lectures)

    while True:
        choice = input(
            Fore.GREEN
            + "Enter lecture number or part of name: "
            + Style.RESET_ALL
        ).strip()

        if not choice:
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(lectures):
                return lectures[idx]
        except ValueError:
            pass

        lower_choice = choice.lower()
        matches = [
            lec for lec in lectures
            if lower_choice in lec.get("item_name", "").lower()
        ]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(Fore.YELLOW + "Multiple matches found:")
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

        print(Fore.RED + "Could not find that lecture. Try again.")


def ask_lecture_range(lectures: list) -> list:
    display_lectures(lectures)

    while True:
        print(Fore.YELLOW + "Enter the range of lectures to summarise.")
        start_input = input(
            Fore.GREEN + "  From (lecture number): " + Style.RESET_ALL
        ).strip()
        end_input = input(
            Fore.GREEN + "  To   (lecture number): " + Style.RESET_ALL
        ).strip()

        try:
            start = int(start_input) - 1
            end = int(end_input)
            if 0 <= start < end <= len(lectures):
                selected = lectures[start:end]
                print(Fore.CYAN + f"\n  Selected {len(selected)} lectures:")
                for lec in selected:
                    print(f"    - {lec['item_name']}")

                confirm = input(
                    Fore.GREEN + "\n  Proceed? (y/n): " + Style.RESET_ALL
                ).strip().lower()
                if confirm in ("y", "yes", ""):
                    return selected
                else:
                    continue
        except ValueError:
            pass

        print(Fore.RED + "Invalid range. Try again.\n")


# ============== LINK DISPLAY ==============

def print_single_link(lecture: dict, view_url: str):
    """Show user the clickable Drive link for a single lecture."""
    print(Fore.MAGENTA + "\n" + "=" * 60)
    print(Fore.MAGENTA + "   SOURCE LECTURE (click to open in browser)")
    print(Fore.MAGENTA + "=" * 60)
    print(Fore.WHITE + f"   File: {lecture['item_name']}")
    print(Fore.CYAN  + f"   Link: {view_url}")
    print(Fore.MAGENTA + "=" * 60 + "\n")


def print_series_links(links: list):
    """Show user clickable Drive links for all lectures in series."""
    if not links:
        return
    print(Fore.MAGENTA + "\n" + "=" * 60)
    print(Fore.MAGENTA + f"   SOURCE LECTURES ({len(links)} files - click to open)")
    print(Fore.MAGENTA + "=" * 60)
    for i, link in enumerate(links, start=1):
        print(Fore.WHITE + f"   [{i:>2}] {link['name']}")
        print(Fore.CYAN  + f"        {link['url']}")
    print(Fore.MAGENTA + "=" * 60 + "\n")


# ============== MAIN FLOW ==============

def main():
    print_banner()

    semester = ask_semester()
    print(Fore.CYAN + f"\nSelected Semester {semester}\n")

    try:
        links = load_gdrive_links(semester)
    except FileNotFoundError as e:
        print(Fore.RED + f"Error: {e}")
        return

    subjects = get_subjects(links)
    if not subjects:
        print(Fore.RED + "No subjects found for this semester.")
        return

    subject = ask_subject(subjects)
    print(Fore.CYAN + f"\nSelected: {subject}\n")

    lectures = get_lecture_files(links, subject)
    if not lectures:
        print(
            Fore.RED
            + f"No lecture files found for '{subject}'."
        )
        return

    print(
        Fore.CYAN
        + f"Found {len(lectures)} lecture file(s) for {subject}"
    )

    mode = ask_mode()

    if mode == "1":
        # ===== Single lecture =====
        lecture = ask_single_lecture(lectures)
        print(Fore.CYAN + f"\nSummarising: {lecture['item_name']}\n")

        summary, success, view_url = summarise_single_lecture(
            semester, lecture
        )

        if success:
            print(Fore.CYAN + "\n" + "=" * 60)
            print(Fore.CYAN + "   SUMMARY")
            print(Fore.CYAN + "=" * 60 + "\n")
            print(Style.RESET_ALL + wrap(summary))

            # Show clickable link
            print_single_link(lecture, view_url)

            # Save
            filepath = save_summary(
                summary, semester, subject,
                lecture["item_name"],
                links=[{
                    "name": lecture["item_name"],
                    "url": view_url,
                }],
            )
            print(Fore.GREEN + f"Summary saved to: {filepath}\n")
        else:
            print(Fore.RED + summary)

    else:
        # ===== Series of lectures =====
        selected = ask_lecture_range(lectures)

        label = (
            f"{selected[0]['item_name']}_to_{selected[-1]['item_name']}"
        )

        summary, success, processed_links = summarise_lecture_series(
            semester, selected, subject
        )

        if success:
            print(Fore.CYAN + "\n" + "=" * 60)
            print(Fore.CYAN + "   COMBINED SUMMARY")
            print(Fore.CYAN + "=" * 60 + "\n")
            print(Style.RESET_ALL + wrap(summary))

            # Show clickable links
            print_series_links(processed_links)

            filepath = save_summary(
                summary, semester, subject, label,
                links=processed_links,
            )
            print(Fore.GREEN + f"Summary saved to: {filepath}\n")
        else:
            print(Fore.RED + summary)

    again = input(
        Fore.YELLOW + "Summarise more? (y/n): " + Style.RESET_ALL
    ).strip().lower()
    if again in ("y", "yes"):
        main()
    else:
        print(Fore.CYAN + "\nGoodbye!\n")


if __name__ == "__main__":
    main()
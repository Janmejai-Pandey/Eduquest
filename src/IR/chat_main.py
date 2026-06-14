import os
import textwrap
from colorama import Fore, Style, init
from chatbot import RAGChatbot

init(autoreset=True)

WRAP_WIDTH = 90


def wrap(text, width=WRAP_WIDTH):
    """Wrap long lines for cleaner terminal output."""
    return "\n".join(
        textwrap.fill(line, width) if line.strip() else line
        for line in text.splitlines()
    )


def print_banner():
    print(Fore.CYAN  + "=" * 60)
    print(Fore.CYAN  + "   RAG Chatbot  |  Groq  |  PDF + PPTX")
    print(Fore.CYAN  + "=" * 60)
    print(Fore.YELLOW + "Commands:")
    print(Fore.YELLOW + "  exit    - quit")
    print(Fore.YELLOW + "  reset   - clear conversation history")
    print(Fore.YELLOW + "  sources - show sources from last answer")
    print(Fore.YELLOW + "  help    - show commands")
    print(Fore.CYAN  + "=" * 60 + "\n")


def print_sources(sources):
    if not sources:
        print(Fore.YELLOW + "No sources available.")
        return
    print(Fore.YELLOW + "\n── Sources ──────────────────────────────")
    for i, r in enumerate(sources, start=1):
        print(
            Fore.YELLOW
            + f"  {i}. {r['source_file']:40s} "
            + f"{r['location']:12s} "
            + f"score={r['score']:.3f}  "
            + f"(bm25={r['bm25_score']:.2f}, sem={r['semantic_score']:.2f})"
        )
    print(Fore.YELLOW + "─" * 45 + "\n")


def main():
    print_banner()

    if not os.path.exists("index_store/faiss.index"):
        print(Fore.RED + "Index not found! Run main.py first to build the index.")
        return

    bot = RAGChatbot()
    last_sources = []

    while True:
        try:
            user_input = input(Fore.GREEN + "You: " + Style.RESET_ALL).strip()
        except (KeyboardInterrupt, EOFError):
            print(Fore.CYAN + "\nGoodbye!")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd == "exit":
            print(Fore.CYAN + "Goodbye!")
            break

        if cmd == "reset":
            bot.reset_history()
            last_sources = []
            continue

        if cmd == "sources":
            print_sources(last_sources)
            continue

        if cmd == "help":
            print(Fore.YELLOW + "Commands: exit | reset | sources | help")
            continue

        # ── get answer ─────────────────────────────
        print(Fore.BLUE + "Bot: " + Style.RESET_ALL, end="", flush=True)
        print("thinking...", flush=True)

        answer, last_sources = bot.chat(user_input)

        print(Fore.BLUE + "\nBot: " + Style.RESET_ALL)
        print(wrap(answer))
        print()

        # show source count hint
        if last_sources:
            print(
                Fore.CYAN
                + f"  ↳ Based on {len(last_sources)} excerpts "
                + f"from {len(set(r['source_file'] for r in last_sources))} file(s). "
                + "Type 'sources' to see details.\n"
            )


if __name__ == "__main__":
    main()
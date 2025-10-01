from collections import deque

# Support running as a module (python -m agents.mira.test)
# and as a script (python agents/mira/test.py)
try:
	from .mira import main_agent  # type: ignore
except ImportError:
	import os
	import sys
	# Add project root to sys.path
	PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	if PROJECT_ROOT not in sys.path:
		sys.path.insert(0, PROJECT_ROOT)
	from agents.mira.mira import main_agent  # type: ignore


def run_chat() -> None:
    """Run an interactive chat loop with internal agent memory."""
    print("Type 'exit' or 'quit' to end the chat.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        assistant_reply = main_agent(user_input)
        print(f"Mira: {assistant_reply}")


if __name__ == "__main__":
    run_chat()
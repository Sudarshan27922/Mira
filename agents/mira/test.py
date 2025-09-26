from collections import deque
from .mira import main_agent


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
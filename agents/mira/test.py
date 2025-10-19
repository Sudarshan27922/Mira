import os
import sys

try:
    from .mira import main_agent
except ImportError:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from agents.mira.mira import main_agent

def run_chat() -> None:
    print("Type 'exit' or 'quit' to end the chat.\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in {"exit", "quit"}:
                print(" Tata, Bye.")
                break
            assistant_reply = main_agent(user_input)
            print(f"Mira: {assistant_reply}\n")
        except (EOFError, KeyboardInterrupt):
            print("\n Tata, Bye.")
            break

if __name__ == "__main__":
    run_chat()
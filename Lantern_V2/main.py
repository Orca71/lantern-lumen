# =============================================================
# LANTERN INTELLIGENCE v2 — main.py
# Phase 6: Main interface
# =============================================================
# WHAT THIS SCRIPT DOES:
#   The entry point for the entire system.
#   1. Greets the user
#   2. Lets them select which company to analyze
#   3. Accepts questions in a loop
#   4. Passes each question through the full pipeline
#   5. Displays the grounded financial answer
#
# HOW TO RUN:
#   1. Make sure ollama serve is running in another terminal
#   2. python main.py
# =============================================================

from adviser import ask, COMPANY_NAMES 

# -------------------------------------------------------------
# DISPLAY HELPERS
# -------------------------------------------------------------

def print_header():
    print("\n" + "=" * 60)
    print(" LANTERN INTELLIGENCE v2")
    print(" AI Financial Advisor - Service Companies")
    print("=" * 60)

def print_menu():
    print("\nSelect a company to analyze: ")
    print(" 1. Apex Strategy Consulting (service1)")
    print(" 2. Meridian Consulting Group (service2)")
    print(" 3. Vertex Advisory Partners (service3)")
    print(" q. Quit")

def print_divider():
    print("\n" + "-" * 60)

# -------------------------------------------------------------
# COMPANY SELECTION
# -------------------------------------------------------------

def select_company():
    """
    Prompt the user to select a company.
    Returns the db_key string for the selected company.
    Loops until a valid choice is made.
    """
    db_map = {
        "1": "service1",
        "2": "service2",
        "3": "service3"
    }
    while True:
        print_menu()
        choice = input("\nEnter choice: ").strip().lower()

        if choice == "q":
            return None
        
        if choice in db_map:
            db_key = db_map[choice]
            company = COMPANY_NAMES[db_key]
            print(f"\nConnected to: {company}")
            print_divider()
            return db_key
        
        print("Invalid choice. Please Enter 1, 2, 3, or q .")

# -------------------------------------------------------------
# QUESTION LOOP
# -------------------------------------------------------------

def run_session(db_key):
    """
    Run a interactive question-answer session for the
    selected company. Loops until user types 'exist',
    'quite', or 'back'.

    Args: 
        db_key = selected company database key
    """
    company = COMPANY_NAMES[db_key]
    print(f"\nAsking about: {company}")
    print(f"Type your question below.")
    print(f"Commands: 'back' = change company | 'quite' = exit\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting ...")
            return "quit"

        #handle empty input

        if not question:
            continue

        # handle navigation commands
        if question.lower() in ["quit", "exit", "q"]:
            return 'quit'

        if question.lower() in ["back", "b", "menu"]:
            return "back"            
        
        # run the full pipeline 
        print_divider()
        ask(question, db_key)
        print_divider()

# -------------------------------------------------------------
# EXAMPLE QUESTIONS
# -------------------------------------------------------------
# Shown after company selection to help users get started.
# -------------------------------------------------------------

EXAMPLE_QUESTIONS = [
    "Is our cash runway safe?",
    "Are we losing clients?",
    "How productive is our team?",
    "What are our biggest expenses?",
    "Are clients paying their invoices on time?",
    "How is the company performing overall?",
    "What is our net profit margin?",
    "Is our client concentration a risk?"
]

def print_examples():
    print("\nExample questions you can ask:")
    for i, q in enumerate(EXAMPLE_QUESTIONS, 1):
        print(f" {i}. {q}")
    print()

# -------------------------------------------------------------
# MAIN ENTRY POINT
# -------------------------------------------------------------

def main():
    print_header()
    print("""
Welcome to Lantern Intelligence.
I analyze real financial data to give you grounded advice.
Each company has a different financial profile — try asking
the same question across all three to see how answers differ.
    """)
    while True:
        db_key = select_company()
        if db_key is None:
            print("\nGoodbye.\n")
            break
        print_examples()

        result = run_session(db_key)
        if result == "quit":
            print("\nGoodbye.\n")
            break
        #if result == 'break', loop continues and shows menu again

if __name__ == "__main__":
    main()


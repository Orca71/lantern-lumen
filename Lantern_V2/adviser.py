# LANTERN INTELLIGENCE v2 — adviser.py
# Phase 5: LLM reasoning layer
# =============================================================
# WHAT THIS SCRIPT DOES:
#   1. Takes a user question and selected database
#   2. Routes the question to relevant SQL queries
#   3. Retrieves live financial data + concept documents
#   4. Builds a structured prompt
#   5. Sends prompt to local Ollama LLM
#   6. Returns a grounded financial answer
#
# LLM: llama3.1:8b running locally via Ollama
# No external API calls. Everything runs on this machine.
# =============================================================

import json
import requests
from query_router import route
from retrieve import retrieve

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

# -------------------------------------------------------------
# COMPANY NAMES
# -------------------------------------------------------------
# Maps database keys to human-readable company names.
# Used in the prompt so the LLM knows which company it's
# advising on.
# -------------------------------------------------------------

COMPANY_NAMES = {
    "service1": "Apex Strategy Consulting",
    "service2": "Meridian Consulting Group",
    "service3": "Vertex Advisory Partners"
}

# -------------------------------------------------------------
# PROMPT BUILDER
# -------------------------------------------------------------
# This is the most important function in the system.
# It takes raw data and turns it into a structured prompt
# that tells the LLM exactly how to reason and respond.
#
# A good prompt has three parts:
#   1. SYSTEM — who the LLM is and how it should behave
#   2. CONTEXT — the financial data and concept knowledge
#   3. QUESTION — what the user actually asked
# -------------------------------------------------------------

def build_prompt(question, company_name, live_data, concepts, selected_queries, history=None):
    """
    Build a structured prompts for the LLM combining live
    fianacial data and retrieved concepts documents.
    Args:
        question:   user's plain English question
        company_name:   human readable company name
        live_data:  dict of SQL query results
        concepts:   list of retreived concepts docs
        selected_queries:   list of query names that were run
    Returns:
        str: complete prompt ready to send to Ollama
    """
    # ---------------------------------------------------------
    # SECTION 1: SYSTEM INSTRUCTION
    # Tells the LLM who it is and how to behave.
    # Key rules:
    #   - Only use the data provided (no hallucination)
    #   - Be specific and direct
    #   - Always cite the numbers
    #   - Flag risks clearly
    # ---------------------------------------------------------
    system = f"""You are Lantern, an AI financial adviser for small business, analyzing {company_name}.
Your job is to answer financial questions using ONLY the data provided below.
Follow these rules strictly:

RESPONSE RULES:
- Always reference specific numbers from the data
- Compare numbers against the benchmarks provided in the concepts knowledge
- Flag any metrics that are in Warning or Critical range
- Be direct and specific - avoid vague statements
- If data is missing or shows an error, say so clearly
- End every response with a priority action if a problem exists
- Keep response concise but complete
- Read benchmark ranges carefully and match numbers precisely

HARD RULES — never violate these:
- If the question asks for future predictions or forecasts, respond ONLY with:
  "I cannot predict future performance. I can only analyze historical data provided."
  Do not estimate, project, or extrapolate under any circumstances.
- If the question asks about a company not in your data, respond ONLY with:
  "I don't have data for that company. I can only analyze {company_name}."
  Do not answer about a different company.
- If the question is a greeting or small talk unrelated to financial analysis, respond ONLY with:
  "I'm Lantern, your financial adviser for {company_name}. Please ask me a financial question."
  Do not provide financial data in response to greetings.
"""
    # ---------------------------------------------------------
    # SECTION 2: FINANCIAL CONCEPT KNOWLEDGE
    # The relevant concept documents retrieved from ChromaDB.
    # This gives the LLM the benchmarks and interpretation
    # framework it needs to judge the numbers.
    # ---------------------------------------------------------
    concept_section = "\n\n=== FINANCIAL CONCEPT KNOWLEDGE ===\n"
    for concept in concepts:
        concept_section += f"\n--- {concept['metric']} ---\n"
        concept_section += concept["text"]
        concept_section += "\n"
    # ---------------------------------------------------------
    # SECTION 3: LIVE FINANCIAL DATA
    # The actual query results from the SQLite database.
    # Only includes the queries selected by the router —
    # not all 8 every time.
    # --
    data_section = "\n\n=== LIVE FINANCIAL DATA ===\n"
    data_section += f"Company: {company_name}\n\n"

    for query_name in selected_queries:
        rows = live_data.get(query_name, [])
        data_section += f"[ {query_name.upper().replace('_', ' ')} ]\n"

        if isinstance(rows, dict) and "error" in rows:
            data_section += f"  ERROR: {rows['error']}\n"
        elif isinstance(rows, list) and len(rows) == 0:
            data_section += " No data returned\n"
        elif isinstance(rows, list):
            for row in rows:
                # format each row as key: value pairs
                for key, value in row.items():
                    data_section += f"  {key}: {value}\n"
                data_section += "\n"
        else:
            data_section += f"  {rows}\n"

    history_section = ""
    if history and len(history) > 0:
        history_section = "\n\n=== CONVERSTATION HISTORY ===\n"
        history_section += "(Previous exchange in this session)\n\n"
        for exchange in history:
            history_section += f"User: {exchange['question']}\n"
            history_section += f"Lantern: {exchange['answer']}\n\n"
    # ---------------------------------------------------------
    # ASSEMBLE THE FULL PROMPT
    # --------------------
    prompt = f"""{system}
{concept_section}

{data_section}
{history_section}
=== CURRENT QUESTION ===
{question}

=== YOUR RESPONSE ===
Analyze the data above and answer the question directly.
Reference specific numbers and benchmark in your answer.
If the user refers to something from the converstation history, use that context.
"""
    return prompt

# -------------------------------------------------------------
# CALL OLLAMA
# -------------------------------------------------------------
# Sends the prompt to the local Ollama server and returns
# the response text. Streams the response so we can show
# output as it generates rather than waiting for completion.
# -------------------------------------------------------------
def call_ollama(prompt, stream=True):
    """
    Send a prompt to the local Ollama server and return
    the generated response.

    Args:
        prompt: complete prompt string
        stream: if True, print tokens as they generate

    Returns:
        str: complete response text
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.1,
            # low temperature = more focused, less creative
            # financial advice should be precise, not creative
            "num_predict": 512
            # max tokens to generate per response
        }
    }
    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=stream,
            timeout=120 # 2 minute timeout
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot Connect to OLLAMA, Make sure server is running."
    except requests.exceptions.Timeout:            # ✅
        return "ERROR: Ollama timed out..."

    # Collect the streamed responses
    full_response = ""

    if stream:
        print("\nLantern: ", end="", flush=True)
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    print(token, end="", flush=True)
                    full_response += token
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        print("\n") # newline after streaming completes
    else:
        data = response.json()
        full_response = data.get("response", "")
    return full_response

# -------------------------------------------------------------
# MAIN ADVISER FUNCTION
# -------------------------------------------------------------
# This is the single function that main.py will call.
# Everything else in this file supports this function.
# -------------------------------------------------------------

def ask(question, db_key):
    """
    The main adviser functions. Takes a user question and
    database selection, runs the full pipeline, and returns
    a grounded financial answer.

    Args:
        question: plain English user question
        db_key: "service1", "service2", "service3"

    Returns:
        str: financial adviser reponse
    """
    company_name = COMPANY_NAMES.get(db_key, db_key)

    print(f"\nRouting question ...")
    selected_queries = route(question)
    print(f"Selected queries: {selected_queries}")
    print(f"Retrieving data from {company_name}...")
    context = retrieve(question, db_key)
    live_data = context["live_data"]
    concepts = context["concepts"]

    print(f"Building prompts...")
    prompt = build_prompt(
        question = question,
        company_name = company_name,
        live_data = live_data,
        concepts = concepts,
        selected_queries=selected_queries
    )
    print(f"Sending to Ollama ({OLLAMA_MODEL})...")
    response = call_ollama(prompt)
    return response
# -------------------------------------------------------------
# QUICK TEST — runs when you execute this script directly
# -------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("ADVISER.PY - Quick Test")
    print("=" * 60)
    test_cases = [
        ("Is our cash runway safe?", "service1"),
        ("Are we losing clients?", "service2"),
        ("How productive is our team?", "service3"),
    ]
    for question, db_key in test_cases:
        company = COMPANY_NAMES[db_key]
        print(f"\n{'='* 60}")
        print(f"Company: {company}")
        print(f"Question: {question}")
        print("=" * 60)

        ask(question, db_key)

        print("\nPress Enter for next test")
        input()

    print("=" * 60)
    print("ALL TESTS COMPLETE — Ready for Phase 6.")
    print("=" * 60)

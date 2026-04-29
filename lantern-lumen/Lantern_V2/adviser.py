# =============================================================
# LANTERN INTELLIGENCE v2 — adviser.py
# Phase 5: LLM reasoning layer
# =============================================================

import json
import requests
from query_router import route
from retrieve import retrieve
from metrics_classifier import pre_classify_live_data, format_classifications_for_prompt

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

COMPANY_NAMES = {
    "service1": "Apex Strategy Consulting",
    "service2": "Meridian Consulting Group",
    "service3": "Vertex Advisory Partners",
}


# -------------------------------------------------------------
# BUILD PROMPT
# -------------------------------------------------------------

def build_prompt(question, company_name, live_data, concepts,
                 selected_queries, history=None):

    # Pre-classify live data and inject into prompt
    classifications      = pre_classify_live_data(live_data)
    print("DEBUG classifications:", classifications)
    classification_block = format_classifications_for_prompt(classifications)

    system = f"""You are Lantern, an AI financial adviser for small businesses, analyzing {company_name}.

Your job is to answer financial questions using ONLY the live data, retrieved concepts, and conversation history provided in the prompt.

CRITICAL VALIDITY CHECK — ALWAYS DO THIS FIRST:
- Before calculating any metric, check whether the formula is valid for the data.
- If a metric is not valid, DO NOT force the formula.
- Do NOT use absolute values to fix invalid inputs.
- Do NOT invent alternate formulas such as gross burn rate or net burn rate unless explicitly provided.
- If the PRE-COMPUTED CLASSIFICATIONS show Runway as PROFITABLE:
  - DO NOT calculate runway.
  - State that the company is not currently burning cash.
  - State that runway is not a current constraint.
  - Do NOT classify runway using runway benchmark ranges.
  - Do NOT speculate about future cash depletion.

INSTRUCTION PRIORITY:
- These instructions override retrieved concepts, context, and prior wording.
- Live financial data is the source of truth for company-specific values.
- Retrieved concepts are reference material only.
- PRE-COMPUTED CLASSIFICATIONS are the final authority on all benchmark labels.

CONCEPT KNOWLEDGE RULE:
Use retrieved concepts only to extract:
- metric definitions
- formulas
- validity conditions

Do NOT copy conclusions, interpretations, or classifications from retrieved concepts.
All classifications come from the PRE-COMPUTED CLASSIFICATIONS block — not from concept text.

CALCULATION RULES:
- Use ONLY the formula provided in the retrieved concept.
- Use ONLY the live data provided.
- Do NOT estimate missing values.
- Do NOT create alternate calculations.
- Do NOT show calculation steps or formula substitution in your response.
- State the computed result directly without showing arithmetic.

BENCHMARK RULES:
- Use ONLY the benchmark labels from the PRE-COMPUTED CLASSIFICATIONS block.
- Do NOT re-classify or re-verify any value.
- Do NOT reference numeric ranges in your response (e.g., never say "20% to 29%" or "30% and above").
- Do NOT explain why a value satisfies a range mathematically.
- Do NOT contradict or qualify PRE-COMPUTED CLASSIFICATIONS with your own interpretation.
- State classifications as established facts exactly as given.

RESPONSE RULES:
- Always reference specific numbers from the live data.
- Stay focused ONLY on the requested metric.
- If data for the requested metric is missing or invalid, say so clearly and stop.
- Do NOT substitute a different metric as a proxy.
- Do NOT infer conclusions from unrelated metrics.
- Do NOT introduce additional metrics unless explicitly required.
- Do NOT assume time period unless explicitly stated.
- Be direct, concise, and specific.

CAUSALITY RULES:
- Do NOT present assumptions as facts.
- When explaining causes, frame them as possibilities.
- Do NOT infer relationships unless explicitly supported by data.

OUTPUT STRUCTURE:
1. Metric Value
2. Benchmark Classification
3. Interpretation
4. Conclusion
5. Priority Action

HARD RULES:
- PRE-COMPUTED CLASSIFICATIONS are final. Never override, qualify, or contradict them.
- Retrieved concepts must never override live data or pre-computed classifications.
- Never reference benchmark numeric ranges in your response under any circumstance.

If the question asks for future predictions or forecasts, respond ONLY with:
"I cannot predict future performance. I can only analyze historical data provided."

If the question asks about a company not in your data, respond ONLY with:
"I do not have data for that company. I can only analyze {company_name}."

If the question is a greeting or small talk unrelated to financial analysis, respond ONLY with:
"I am Lantern, your financial adviser for {company_name}. Please ask me a financial question."
"""

    concept_section = "\n\n=== FINANCIAL CONCEPT KNOWLEDGE ===\n"
    for concept in concepts:
        concept_section += f"\n--- {concept['metric']} ---\n"
        concept_section += concept["text"]
        concept_section += "\n"

    data_section = "\n\n=== LIVE FINANCIAL DATA ===\n"
    data_section += f"Company: {company_name}\n\n"

    for query_name in selected_queries:
        rows = live_data.get(query_name, [])
        data_section += f"[ {query_name.upper().replace('_', ' ')} ]\n"

        if isinstance(rows, dict) and "error" in rows:
            data_section += f"  ERROR: {rows['error']}\n"
        elif isinstance(rows, list) and len(rows) == 0:
            data_section += "  No data returned\n"
        elif isinstance(rows, list):
            for row in rows:
                for key, value in row.items():
                    data_section += f"  {key}: {value}\n"
                data_section += "\n"
        else:
            data_section += f"  {rows}\n"

    history_section = ""
    if history:
        history_section = "\n\n=== CONVERSATION HISTORY ===\n"
        history_section += "(Previous exchanges in this session)\n\n"
        for exchange in history:
            history_section += f"User: {exchange['question']}\n"
            history_section += f"Lantern: {exchange['answer']}\n\n"

    prompt = f"""{system}

{classification_block}

{concept_section}

{data_section}

{history_section}

=== CURRENT QUESTION ===
{question}

=== YOUR RESPONSE ===
Analyze the data above and answer the question directly.
Use the PRE-COMPUTED CLASSIFICATIONS for all benchmark labels.
Reference specific numbers and benchmarks in your answer.
If the user refers to conversation history, use that context.
"""

    return prompt


# -------------------------------------------------------------
# OLLAMA CALL
# -------------------------------------------------------------

def call_ollama(prompt, stream=True):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            stream=stream,
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to Ollama. Make sure the server is running."
    except requests.exceptions.Timeout:
        return "ERROR: Ollama timed out."

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
        print("\n")
    else:
        data = response.json()
        full_response = data.get("response", "")

    return full_response


# -------------------------------------------------------------
# ASK
# -------------------------------------------------------------

def ask(question, db_key):
    company_name = COMPANY_NAMES.get(db_key, db_key)

    print("\nRouting question...")
    selected_queries = route(question)
    print(f"Selected queries: {selected_queries}")

    print(f"Retrieving data from {company_name}...")
    context   = retrieve(question, db_key)
    live_data = context["live_data"]
    concepts  = context["concepts"]

    print("Building prompt...")
    prompt = build_prompt(
        question=question,
        company_name=company_name,
        live_data=live_data,
        concepts=concepts,
        selected_queries=selected_queries,
    )

    print("\n===== FINAL PROMPT SENT TO OLLAMA =====")
    print(f"Prompt length: {len(prompt)} characters")
    print("\n===== PROMPT START =====")
    print(prompt[:4000])
    print("\n===== PROMPT END =====")
    print(prompt[-4000:])
    print("===== END FINAL PROMPT =====\n")

    print(f"Sending to Ollama ({OLLAMA_MODEL})...")
    response = call_ollama(prompt)
    return response


# -------------------------------------------------------------
# QUICK TEST
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
        print(f"\n{'=' * 60}")
        print(f"Company: {company}")
        print(f"Question: {question}")
        print("=" * 60)
        ask(question, db_key)
        print("\nPress Enter for next test")
        input()

    print("=" * 60)
    print("ALL TESTS COMPLETE.")
    print("=" * 60)

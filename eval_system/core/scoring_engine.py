import json
import time
import requests
from db.database import SessionLocal
from db.models import EvalRun, Score, TestCase
from connectors.lantern import LanternConnector

OLLAMA_URL = "http://localhost:11434/api/generate"
JUDGE_MODEL = "gemma2:27b"

def call_judge(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama judge model
    and returns the full response as a string
    """
    payload = {
        "model": JUDGE_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 512
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"JUDGE ERROR: {str(e)}"

def build_judge_prompt(
    question: str,
    expected_behavior: str,
    actual_answer: str,
    retrieved_context: dict = None
) -> str:
    context_str = "No retrieved context available"
    if retrieved_context:
        live_data = retrieved_context.get("live_data", {})
        context_str = json.dumps(live_data, indent=2)

    prompt = f"""<start_of_turn>user
You are Lumen, an expert LLM evaluator and strict scoring engine.

Your job is to evaluate the quality of an AI assistant's response to a financial query.
Follow ALL rules exactly. Be strict and deterministic.

========================
INPUTS
========================

QUESTION ASKED:
{question}

EXPECTED BEHAVIOR:
{expected_behavior}

RETRIEVED CONTEXT:
{context_str}

ACTUAL RESPONSE:
{actual_answer}

========================
STEP 1 — READ THE QUESTION FIRST
========================
All scoring decisions MUST be based on the QUESTION ASKED.

========================
CRITICAL RULES (HARD FAIL CONDITIONS)
========================

RULE 1 — OUT OF SCOPE / SMALL TALK
If the QUESTION is a greeting or small talk (e.g., "Hi", "Hello", "How are you"):
- The correct response MUST redirect to financial queries ONLY.
- If the ACTUAL RESPONSE provides financial analysis:
  → RELEVANCE = 0.0
  → OVERALL < 0.3
  → Ignore content quality completely

RULE 2 — WRONG COMPANY
If the QUESTION refers to a company NOT in the RETRIEVED CONTEXT:
- The correct response MUST refuse and explain missing data.
- If the ACTUAL RESPONSE answers about a DIFFERENT company:
  → RELEVANCE = 0.0
  → ACCURACY = 0.0
- Partial mention + pivot is STILL incorrect.

RULE 3 — FUTURE PREDICTION
If the QUESTION asks about future outcomes:
- The correct response MUST decline.
- If ANY prediction is made:
  → ACCURACY = 0.0
  → OVERALL must be below 0.4
- Saying "I cannot predict" then making an estimate STILL violates this rule.

RULE 4 — BENCHMARK MISCLASSIFICATION
If a value is correct BUT categorized incorrectly:
→ ACCURACY < 0.7

RULE 5 — PERFECT SCORE RESTRICTION
- Score of 1.0 requires ZERO errors.
- If ANY rule above is violated:
  → NO dimension may be 1.0

========================
SCORING DIMENSIONS
========================

Score each from 0.0 to 1.0:

RELEVANCE:
- Does the response directly answer the QUESTION?
- Penalize unrelated or misaligned answers.

FAITHFULNESS:
- Are ALL claims grounded in RETRIEVED CONTEXT?
- Penalize unsupported or invented information.

ACCURACY:
- Are facts and interpretations correct?
- Penalize incorrect reasoning or benchmark misuse.

========================
OUTPUT FORMAT (STRICT)
========================

Return EXACTLY:

RELEVANCE: <float>
FAITHFULNESS: <float>
ACCURACY: <float>
OVERALL: <float>
RATIONALE: <concise explanation>

Rules:
- OVERALL must align with the three scores
- Be conservative in scoring
- Do NOT include any extra text
<end_of_turn>
<start_of_turn>model
"""
    return prompt

def parse_judge_response(response: str) -> dict:
    """
    Parse the judge's structured response into a dictionary.
    Falls back gracefully if the format is unexpected.
    """
    result = {
        "relevance": 0.0,
        "faithfulness": 0.0,
        "accuracy": 0.0,
        "overall": 0.0,
        "rationale": response
    }
    try:
        lines = response.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("RELEVANCE:"):
                result["relevance"] = float(line.split(":")[1].strip())
            elif line.startswith("FAITHFULNESS:"):
                result["faithfulness"] = float(line.split(":")[1].strip())
            elif line.startswith("ACCURACY:"):
                result["accuracy"] = float(line.split(":")[1].strip())
            elif line.startswith("OVERALL:"):
                result["overall"] = float(line.split(":")[1].strip())
            elif line.startswith("RATIONALE:"):
                result["rationale"] = line.split(":", 1)[1].strip()
    except Exception:
        pass
    return result

def run_eval(test_case_id: int, connector: LanternConnector = None) -> dict:
    """
    Runs a full evaluation for a single test case.
    Returns the eval run id and socres.
    """
    if connector is None:
        connector = LanternConnector()
    db = SessionLocal()

    try:
        test_case = db.query(TestCase).filter(
            TestCase.id == test_case_id
        ).first()

        if not test_case:
            return {"error": f"Test case {test_case_id} not found"}
        print(f"\n{'='*60}")
        print(f"Running eval for: [{test_case.id}] {test_case.name}")
        print(f"Question: {test_case.input_query}")
        print(f"{'='*60}")
        #Step 1 - call Lantern (LLM)
        eval_response = connector.query(
            question=test_case.input_query,
            db_key=test_case.db_key
        )
        print(f"\nLantern response ({eval_response.latency_ms}ms)")
        print(f"{eval_response.answer[:300]}...")

        if eval_response.error:
            print(f"Lantern error: {eval_response.error}")

        # Step 2 = save eval run
        eval_run = EvalRun(
            test_case_id= test_case.id,
            actual_output=eval_response.answer,
            retrieved_context=json.dumps(eval_response.retrieved_context),
            model_version= JUDGE_MODEL,
            latency_ms= eval_response.latency_ms,
            status="completed" if not eval_response.error else "failed"
        )
        db.add(eval_run)
        db.commit()
        db.refresh(eval_run)

        print(f"\nEval run saved [id: {eval_run.id}]")

        # Step 3 - build and send judge prompt
        judge_prompt = build_judge_prompt(
            question=test_case.input_query,
            expected_behavior=test_case.expected_behavior,
            actual_answer=eval_response.answer,
            retrieved_context=eval_response.retrieved_context
        )
        print(f"\n--- JUDGE PROMPT ---")
        print(judge_prompt)
        print(f"--- END JUDGE PROMPT ---\n")

        judge_response = call_judge(judge_prompt)

        print(f"--- JUDGE RESPONSE ---")
        print(judge_response)
        print(f"--- END JUDGE RESPONSE ---\n")

        # Step 4 - parse and save score
        parsed = parse_judge_response(judge_response)

        dimensions = {
            "relevance": parsed["relevance"],
            "faithfulness": parsed["faithfulness"],
            "accuracy": parsed["accuracy"]
        }
        score = Score(
            eval_run_id=eval_run.id,
            scorer_type="llm_judge",
            score=parsed["overall"],
            rationale=parsed["rationale"],
            dimensions=json.dumps(dimensions)
        )
        db.add(score)
        db.commit()

        print(f"Scores saved:")
        print(f" Relevance: {parsed['relevance']}")
        print(f" Faithfulness: {parsed['faithfulness']}")
        print(f" Accuracy: {parsed['accuracy']}")
        print(f" Overall: {parsed['overall']}")
        print(f" Rationale: {parsed['rationale']}")

        return {
            "eval_run_id": eval_run.id,
            "test_case": test_case.name,
            "scores": parsed
        }
    except Exception as e:
        db.rollback()
        print(f"Error during eval: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    #Run eval on first test case as a quick test
    result = run_eval(test_case_id=1)
    print(f"\nFinal result: {result}")

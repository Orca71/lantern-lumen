# =============================================================
# LANTERN INTELLIGENCE v2 — app.py
# Web server — connects the browser UI to the Lantern pipeline
# =============================================================

import json
from typing import List, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from adviser import ask, COMPANY_NAMES, build_prompt
from query_router import route
from retrieve import retrieve
import requests as req

app = FastAPI(title='Lantern Intelligence')
app.mount("/static", StaticFiles(directory="/workspace/lantern-lumen/Lantern_V2/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

# -------------------------------------------------------------
# History exchange
# -------------------------------------------------------------
class HistoryExchange(BaseModel):
    question: str
    answer: str


# -------------------------------------------------------------
# REQUEST MODEL
# -------------------------------------------------------------

class QuestionRequest(BaseModel):
    question: str
    db_key: str
    history: Optional[List[HistoryExchange]] = []


# -------------------------------------------------------------
# CLASSIFICATION HELPER
# -------------------------------------------------------------
# Runs the full extractor → classifier pipeline on any text.
# Returns a clean list of dicts safe for JSON serialization.
# Currency values misrouted to wrong metric types are dropped.
# -------------------------------------------------------------

def run_classification(text: str) -> list[dict]:
    """
    Runs extractor → classifier on text.
    Returns a JSON-serializable list of classified metric dicts.
    Drops misrouted currency values (in_range=False + currency flag).
    """
    extractions = extract_values(text)
    classified  = classify(extractions)

    results = []
    for c in classified:
        # Drop currency values that landed on the wrong metric type
        if not c.in_range and c.flag and "currency" in c.flag.lower():
            continue
        results.append({
            "metric":    c.display_name,
            "value":     c.numeric,
            "unit":      c.unit,
            "type":      c.value_type,
            "threshold": c.threshold,
            "in_range":  c.in_range,
            "flag":      c.flag,
        })
    return results


# -------------------------------------------------------------
# STREAMING GENERATOR
# -------------------------------------------------------------
# Streams tokens to the browser AND collects the full response
# so it can be classified after streaming completes.
# -------------------------------------------------------------

def stream_ollama(prompt):
    """Generator that yields tokens from Ollama as they arrive."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 512
        }
    }
    try:
        response = req.post(OLLAMA_URL, json=payload, stream=True, timeout=120)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        yield f"ERROR: {str(e)}"


# -------------------------------------------------------------
# STREAMING ENDPOINT — /ask
# -------------------------------------------------------------
# Streams LLM tokens to the UI in real time.
# After streaming, a follow-up call to /classify can retrieve
# the structured metrics for the same response if needed.
# -------------------------------------------------------------

@app.post("/ask")
async def ask_question(req_body: QuestionRequest):
    """
    Main endpoint. Streams the LLM response back to the browser.
    The UI receives raw text tokens in real time.
    """
    question = req_body.question
    db_key = req_body.db_key

    company_name = COMPANY_NAMES.get(db_key, db_key)
    selected_queries = route(question)
    context = retrieve(question, db_key)
    live_data = context["live_data"]
    concepts = context["concepts"]

    history = [{"question": h.question, "answer": h.answer}
                for h in req_body.history]

    prompt = build_prompt(
        question=question,
        company_name=company_name,
        live_data=live_data,
        concepts=concepts,
        selected_queries=selected_queries,
        history=history
    )
    return StreamingResponse(
        stream_ollama(prompt),
        media_type='text/plain'
    )


# -------------------------------------------------------------
# EVALUATION ENDPOINT — /ask_eval
# -------------------------------------------------------------
# Returns the full response as JSON — no streaming.
# Now includes classified metrics from the pipeline.
# Used by the eval system and any consumer that needs
# structured metric data alongside the LLM text.
# -------------------------------------------------------------

@app.post("/ask_eval")
async def ask_eval(req_body: QuestionRequest):
    """
    Evaluation endpoint. Collects the full response, runs it
    through the classification pipeline, and returns everything
    as structured JSON including classified metric values.
    """
    question = req_body.question
    db_key = req_body.db_key
    company_name = COMPANY_NAMES.get(db_key, db_key)
    selected_queries = route(question)
    context = retrieve(question, db_key)
    live_data = context["live_data"]
    concepts = context["concepts"]

    history = [{"question": h.question, "answer": h.answer}
                for h in req_body.history]

    prompt = build_prompt(
        question=question,
        company_name=company_name,
        live_data=live_data,
        concepts=concepts,
        selected_queries=selected_queries,
        history=history
    )

    # Collect full response
    full_response = ""
    for token in stream_ollama(prompt):
        if token.startswith("ERROR:"):
            return {"error": token}
        full_response += token

    # Run classification pipeline on the full response
    classified_metrics = run_classification(full_response)
    flags = [
        f"{m['metric']}: {m['flag']}"
        for m in classified_metrics
        if m["flag"]
    ]

    return {
        "question": question,
        "company": company_name,
        "answer": full_response,
        "classified_metrics": classified_metrics,
        "flags": flags,
        "has_issues": len(flags) > 0,
        "retrieved_context": {
            "live_data": live_data,
            "concepts": concepts
        },
        "selected_queries": selected_queries
    }


# -------------------------------------------------------------
# UTILITY ENDPOINTS
# -------------------------------------------------------------

@app.post("/route")
async def get_routes(req_body: QuestionRequest):
    """Returns which queries the router selects for a question."""
    queries = route(req_body.question)
    return {"queries": queries}


@app.get("/companies")
async def get_companies():
    """Returns the list of available companies."""
    return {
        "companies": [
            {"key": k, "name": v}
            for k, v in COMPANY_NAMES.items()
        ]
    }


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("templates/index.html", "r") as f:
        return f.read()

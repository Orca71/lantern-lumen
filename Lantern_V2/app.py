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
# STREAMING ENDPOINT
# -------------------------------------------------------------
# Instead of waiting for the full response, we stream tokens
# back to the browser as they generate. This makes the UI
# feel alive — the user sees the answer being written in
# real time, just like ChatGPT.
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

@app.post("/ask")
async def ask_question(req_body: QuestionRequest):
    """
    Main endpoint. Takes a question and db_key, runs the
    full pipeline, and streams the LLM response back.
    """
    question = req_body.question
    db_key = req_body.db_key

    from adviser import build_prompt, COMPANY_NAMES
    from retrieve import retrieve
    from query_router import route

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
        history = history
    )
    return StreamingResponse(
        stream_ollama(prompt),
        media_type='text/plain'
    )
@app.post("/ask_eval")
async def ask_eval(req_body: QuestionRequest):
    """
    Evaluation endpoint. Same pipeline as /ask but returns
    the full reponse and retrieved context as JSON.
    Used exclusively by the eval system for scoring.
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
        question = question,
        company_name = company_name,
        live_data = live_data,
        concepts = concepts,
        selected_queries = selected_queries,
        history = history
    )
    # Collect full response instead of streaming
    full_response = ""
    for token in stream_ollama(prompt):
        if token.startswith("ERROR:"):
            return {"error": token}
        full_response += token
    return {
        "question": question,
        "company": company_name,
        "answer": full_response,
        "retrieved_context": {
            "live_data": live_data,
            "concepts": concepts
        },
        "selected_queries": selected_queries
    }


@app.post("/route")
async def get_routes(req_body: QuestionRequest):
    """Returns which queries the router selects for a question."""
    queries = route(req_body.question)
    return {"queries": queries}

@app.get("/companies")
async def get_companies():
    """Returns the list of available companies"""
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

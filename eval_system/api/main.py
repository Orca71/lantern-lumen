from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json

from db.database import SessionLocal
from db.models import TestCase, EvalRun, Score
from core.scoring_engine import run_eval
from core.test_case_manager import get_all_test_cases
from connectors.lantern import LanternConnector

app = FastAPI(title="Lumen - LLM Evaluation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

connector = LanternConnector()

#Request models -----------

class RunEvalRequest(BaseModel):
    test_case_id: int

class RunAllRequest(BaseModel):
    domain: Optional[str] = None


#--- Health ------------

@app.get("/health")
def health():
    lantern_up = connector.health_check()
    return {
        "lumen": "ok",
        "lantern": "ok" if lantern_up else "unreachable"
    }

# --Test Cases------
@app.get("/test-cases")
def list_test_cases():
    cases = get_all_test_cases()
    return {
        "count": len(cases),
        "test_cases": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "domain": c.domain,
                "db_key": c.db_key,
                "input_query": c.input_query,
            }
            for c in cases
        ]
    }

# ---Run single eval-----
@app.post("/eval/run")
def run_single_eval(request: RunEvalRequest):
    try:
        result = run_eval(
            test_case_id = request.test_case_id,
            connector = connector
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --Run all evals ---
@app.post("/eval/run-all")
def run_all_evals():
    cases = get_all_test_cases()
    results = []
    for case in cases:
        try:
            result = run_eval(
                test_case_id = case.id,
                connector = connector
            )
            results.append(result)
        except Exception as e:
            results.append({
                "test_case_id": case.id,
                "test_case": case.name,
                "error": str(e)
            })
    return {
        "total": len(results),
        "results": results
    }

# -- Get Results -------
@app.get("/eval/results")
def get_results():
    db = SessionLocal()
    try:
        runs = db.query(EvalRun).order_by(EvalRun.created_at.desc()).all()
        output = []
        for run in runs:
            scores = db.query(Score).filter(
                Score.eval_run_id == run.id
            ).all()
            output.append({
                "eval_run_id": run.id,
                "test_case_id": run.test_case_id,
                "status": run.status,
                "latency_ms": run.latency_ms,
                "created_at": str(run.created_at),
                "scores": [
                    {
                        "scorer_type": s.scorer_type,
                        "score": s.score,
                        "rationale": s.rationale,
                        "dimensions": json.loads(s.dimensions) if s.dimensions else {}
                    }
                    for s in scores
                ]
            })
        return {"total_runs": len(output), "runs": output}
    finally:
        db.close()

#-----Summery ---------------
@app.get("/eval/summary")
def get_summery():
    db = SessionLocal()
    try:
        scores = db.query(Score).filter(
            Score.scorer_type == "llm_judge"
        ).all()
        if not scores:
            return {"message": "No eval runs yet"}
        total = len(scores)
        avg_score = sum(s.score for s in scores) / total
        passed = sum(1 for s in scores if s.score >= 0.7)
        failed = total - passed

        return {
            "total_evals": total,
            "average_score": round(avg_score, 3),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1)

        }
    finally:
        db.close()

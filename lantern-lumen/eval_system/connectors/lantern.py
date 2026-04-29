import time
import httpx
from connectors.base import BaseLLMConnector, EvalResponse

class LanternConnector(BaseLLMConnector):
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ask_eval_url = f"{base_url}/ask_eval"
        self.health_url = f"{base_url}/companies"

    def query(self, question: str, db_key: str = "service1", **kwargs) -> EvalResponse:
        """
        Sends a question to Lantern's /ask_eval endpoint
        and returns a standardized EvalResponse.
        """
        payload = {
            "question": question,
            "db_key": db_key,
            "history": []
        }
        start_time = time.time()
        try:
            response = httpx.post(
                self.ask_eval_url,
                json = payload,
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            latency_ms = int((time.time() - start_time) * 1000)
            if "error" in data:
                return EvalResponse(
                    question=question,
                    answer="",
                    error=data["error"],
                    latency_ms=latency_ms
                )
            return EvalResponse(
                question=question,
                answer=data.get("answer",""),
                retrieved_context=data.get("retrieved_context"),
                selected_queries = data.get("selected_queries"),
                latency_ms=latency_ms
            )
        except httpx.TimeoutException:
            return EvalResponse(
                question=question,
                answer="",
                error="Request timed out after 120 seconds",
                latency_ms=120000
            )
        except httpx.HTTPStatusError as e:
            return EvalResponse(
                question=question,
                answer="",
                error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            return EvalResponse(
                question=question,
                answer="",
                error=f"Unexpected error: {str(e)}"
            )
    def health_check(self) -> bool:
        """
        Calls /companies to verify LLM is reachable.
        Returns True if healthy, False if not.
        """
        try:
            response = httpx.get(self.health_url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

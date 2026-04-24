from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class EvalResponse:
    question: str
    answer: str
    retrieved_context: Optional[dict] = None
    selected_queries: Optional[list] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None

class BaseLLMConnector(ABC):

    @abstractmethod
    def query(self, question: str, **kwargs) -> EvalResponse:
        """
        Send a question to the LLM system and return
        a standardized EvalResponse.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Verify the LLM system is reachable and responding.
        Returns True if healthy, False if not.
        """
        pass

from sqlalchemy import Column, Integer, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class TestCase(Base):
    __tablename__ = "test_cases"

    id  =   Column(Integer, primary_key = True, autoincrement=True)
    name =  Column(Text, nullable=False)
    description =   Column(Text)
    input_query =   Column(Text, nullable=False)
    expected_behavior = Column(Text, nullable=False)
    expected_output = Column(Text)
    db_key = Column(Text, default="service1")
    domain = Column(Text, default="financial")
    source = Column(Text, default="manual")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    eval_runs = relationship("EvalRun", back_populates="test_case")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_label = Column(Text, nullable=False)
    system_prompt = Column(Text)
    model_name = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default= datetime.utcnow)

    eval_runs = relationship("EvalRun", back_populates="prompt_version")

class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"))
    actual_output = Column(Text)
    retrieved_context = Column(Text)
    model_version = Column(Text)
    latency_ms = Column(Integer)
    status = Column(Text, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    test_case = relationship("TestCase", back_populates="eval_runs")
    prompt_version = relationship("PromptVersion", back_populates="eval_runs")
    scores = relationship("Score", back_populates="eval_run")

class Score(Base):
    __tablename__ = "scores"

    id =    Column(Integer, primary_key=True, autoincrement=True)
    eval_run_id = Column(Integer, ForeignKey("eval_runs.id"), nullable=False)
    scorer_type = Column(Text,nullable=False)
    score = Column(Float, nullable=False)
    rationale = Column(Text)
    dimensions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    eval_run = relationship("EvalRun", back_populates="scores")

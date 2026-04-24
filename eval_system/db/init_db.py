from db.database import engine, Base
from db.models import TestCase, PromptVersion, EvalRun, Score

def init_db():
    Base.metadata.create_all(bind=engine)
    print("All Tables create successfully")

if __name__ == "__main__":
    init_db()

from db.database import SessionLocal
from db.models import TestCase

def add_test_case(
    name: str,
    input_query: str,
    expected_behavior: str,
    expected_output: str = None,
    description: str = None,
    domain: str = "financial",
    source: str = "manual",
    db_key: str = "service1",
):
    db = SessionLocal()
    try:
        test_case = TestCase(
            name=name,
            description=description,
            input_query=input_query,
            expected_behavior=expected_behavior,
            expected_output=expected_output,
            domain=domain,
            source=source,
            db_key=db_key
        )
        db.add(test_case)
        db.commit()
        db.refresh(test_case)
        print(f"Added test case [{test_case.id}]: {test_case.name}")
        return test_case
    except Exception as e:
        db.rollback()
        print(f"Error adding test case: {e}")
        raise
    finally:
        db.close()

def get_all_test_cases(active_only: bool = True):
    db = SessionLocal()
    try:
        query = db.query(TestCase)
        if active_only:
            query = query.filter(TestCase.is_active == 1)
        return query.all()
    finally:
        db.close()

def get_test_case_by_id(test_case_id: int):
    db = SessionLocal()
    try:
        return db.query(TestCase).filter(TestCase.id == test_case_id).first()
    finally:
        db.close()

def seed_test_cases():
    test_cases = [
        # -- category 1: In-distribution ------
        # later we have to make this dynamic and not just fixed prompots
        {
            "name": "Apex net profit margin",
            "db_key": "service1",
            "description": "In-distribution - clean financial metric query",
            "input_query": "What is the net profit margin for Apex Strategy Consulting?",
            "expected_behavior": "Returns a specific percentage grounded in retrieved financial data. Does not not hullucinate or generalize.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Meridian monthly revenue trend",
            "db_key": "service2",
            "description": "In-distribution - tend data query",
            "input_query": "What is the monthly revenue trend for Meridian Consulting Group?",
            "expected_behavior": "Returns trend data derived from retrieved documents. Answer is specific to Meridian, not generic.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Vertex burn rate and runway",
            "db_key": "service3",
            "description": "In-distribution - multi-metric query for one company",
            "input_query": "What is the burn rate and runway for Vertex Advisory Partners?",
            "expected_behavior": "Returns both burn rate and runway as specific figures from retireved context.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Apex revenue per employee",
            "db_key": "service1",
            "description": "In-distribution - calulated metric query",
            "input_query": "What is the revenue per employee for Apex Strategy Consulting?",
            "expected_behavior": "Returns a calculated figure grounded in retrieved data. Shows the calculation or cites the source.",
            "expected_output": None,
            "domain": "financial",
        },
        # --- Category 2: Edge cases ------
        {
            "name": "Apex overall financial health",
            "db_key": "service1",
            "description": "Edge case - vague multi-metric synthesis",
            "input_query": "What is Apex Strategy Consulting's overall financial health?",
            "expected_behavior": "Synthesizes multiple metrics coherently for Apex only, Does not speculate beyond retrieved data.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Meridian last month revenue",
            "db_key": "service2",
            "description": "Edge case - time-relative ambigous query",
            "input_query": "What was Meridian Consulting Group's revenue last month?",
            "expected_behavior": "Returns available revenue data or clearly acknowledges the limitation od static data without hallucinating.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Vertex DSO and cash flow",
            "db_key": "service3",
            "description": "Edge-case - multi-metric with financial relationship",
            "input_query": "How does Vertex Advisory Partners DSO effect its cash flow?",
            "expected_behavior": "Explain the relatioship using retreived DSO and cash flow figures. Does not invent numbers.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Apex client concentration risk",
            "db_key": "service1",
            "description": "edge case - risk interpretation query",
            "input_query": "How severe is the client concentration risk for Apex Strategy Consulting?",
            "expected_behavior": "Interprets concentration risk using retrived data. Qualifies the severity without speculations.",
            "expected_output": None,
            "domain": "financial",
        },
        # -- Category 3: Adversarial ------
        {
            "name": "Vertex stock price hallucination",
            "db_key": "service3",
            "description": "Adversarial - requests data that does not exist",
            "input_query": "What is the stock price of Vertex Advisory Partners?",
            "expected_behavior": "Clearly states this information is not available. Does not haullucinate a stock price.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Apex future revenue prediction",
            "db_key": "service1",
            "description": "Adversarial - requests future predictions",
            "input_query": "What will Apex Strategy Consulting revenue be next quarter?",
            "expected_behavior": "Acknowledges it cannot predict future data. Does not specualte or extrapolte confidentialy.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Unknow company query",
            "db_key": "service1",
            "description": "Adversarial - company outside knowledge base",
            "input_query": "What is the net profit for Goldman Sachs?",
            "expected_behavior": "Clearly states Goldman Sachs is not in its knowledge base. Does not hallucinate financial data.",
            "expected_output": None,
            "domain": "financial",
        },
        {
            "name": "Small talk out of scope",
            "db_key": "service1",
            "description": "Adversarial - completely out of scope query",
            "input_query": "Hi, how are you today?",
            "expected_behavior": "Declines graacefully and redirects to financial queries. Does not engage in small talk.",
            "expected_output": None,
            "domain": "financial",
        },
    ]
    print("Seeding test cases ..")
    for tc in test_cases:
        add_test_case(**tc)
    print(f"\nDone. {len(test_cases)} test cases seeded.")

if __name__ == "__main__":
    seed_test_cases()

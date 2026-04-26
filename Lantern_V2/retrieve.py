# =============================================================
# LANTERN INTELLIGENCE v2 — retrieve.py
# Phase 3: Live SQL execution + ChromaDB concept retrieval
# =============================================================
# WHAT THIS SCRIPT DOES:
#   1. Connects to the selected company SQLite database
#   2. Runs all 8 financial queries live and returns results
#   3. Queries ChromaDB for relevant concept documents
#   4. Returns both to be used by the LLM in Phase 5
#
# This script is the data backbone of the adviser.
# It never generates answers — it only fetches the context
# that the LLM needs to generate a grounded answer.
# =============================================================
import os
import sqlite3
import chromadb

from sentence_transformers import SentenceTransformer
# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
CHROMA_STORE_DIR = "/workspace/lantern-lumen/Lantern_V2/chroma_store"
COLLECTION_NAME  = "lantern_financial_concepts"
TOP_K_CONCEPTS   = 3  # how many concept docs to retrieve per question
SQL_DIR = "/workspace/lantern-lumen/Lantern_V2/matrix_queries"
DB_PATHS = {
    "service1": "/workspace/Lantern_V2/databases/service1.db",
    "service2": "/workspace/Lantern_V2/databases/service2.db",
    "service3": "/workspace/Lantern_V2/databases/service3.db"
}

# -------------------------------------------------------------
# MAP QUERY NAMES TO .SQL FILES
# -------------------------------------------------------------
SQL_FILES = {
    "net_profit_margin":      "01_net_profit_margin.sql",
    "monthly_revenue_trend":  "02_monthly_revenue_trend.sql",
    "days_sales_outstanding": "03_days_sales_outstanding.sql",
    "client_concentration":   "04_client_concentration.sql",
    "burn_rate_runway":       "05_burn_rate_runway.sql",
    "expense_breakdown":      "06_expense_breakdown.sql",
    "revenue_per_employee":   "07_revenue_per_employee.sql",
    "client_churn_rate":      "08_client_churn_rate.sql"
}

# -------------------------------------------------------------
# LOAD SQL QUERIES FROM FILES
# -------------------------------------------------------------
def load_sql_queries():
    """
    Read all .sql files from SQL_DIR and return as a dictionary.
    Called once at startup.

    Returns:
    dict: {query_name: sql_string}
    """
    queries = {}
    for query_name, filename in SQL_FILES.items():
        filepath = os.path.join(SQL_DIR, filename)

        if not os.path.exists(filepath):
            print(f"WARNING: SQL file not found: {filepath}")
            queries[query_name] = None
            continue
        with open(filepath, "r", encoding='utf-8') as f:
            sql = f.read().strip()

        queries[query_name] = sql
        print(f" Loaded SQL: {filename}")
    return queries


# -------------------------------------------------------------
# LAZY LOADERS — initialize only when first needed
# -------------------------------------------------------------
_embedding_model_instance = None
_chroma_client = None
_collection = None
_sql_queries = None

def get_embedding_model():
    global _embedding_model_instance
    if _embedding_model_instance is None:
        _embedding_model_instance = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model_instance

def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_STORE_DIR)
        _collection = _chroma_client.get_collection(name=COLLECTION_NAME)
    return _collection

def get_sql_queries():
    global _sql_queries
    if _sql_queries is None:
        _sql_queries = load_sql_queries()
    return _sql_queries


# -------------------------------------------------------------
# FUNCTION 1: GET LIVE FINANCIAL DATA FROM SQLITE
# -------------------------------------------------------------
def get_live_data(db_key):
    """
    Connect to the selected company database and run all
    8 financial queries. Returns a dictionary of results.

    Args:
        db_key: "service1", "service2", or "service3"

    Returns:
        dict: {query_name: [list of result row dicts]}
    """
    if db_key not in DB_PATHS:
        raise ValueError(f"Unknown database: {db_key}."
                         f"choose from: {list(DB_PATHS.keys())}")

    db_path = DB_PATHS[db_key]
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    results = {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        for query_name, sql in get_sql_queries().items():

            if sql is None:
                results[query_name] = {"error": "SQL file not found"}
                continue
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                results[query_name] = [dict(row) for row in rows]

            except sqlite3.Error as e:
                results[query_name] = {"error": str(e)}
                print(f"  WARNING: Query failed — {query_name}: {e}")

    finally:
        conn.close()

    return results


# -------------------------------------------------------------
# FUNCTION 2: GET RELEVANT CONCEPT DOCUMENTS FROM CHROMADB
# -------------------------------------------------------------
def get_concepts(question):
    """
    Retrieve the most relevant financial concept document for a given user question.
    Args:
        question: plain English user question (string)
    Returns:
        list of dicts: [{metric, text, score}, ....]
    """
    query_vector = get_embedding_model().encode([question]).tolist()
    results = get_collection().query(
        query_embeddings=query_vector,
        n_results=TOP_K_CONCEPTS,
        include=["documents", "metadatas", "distances"]
    )
    concepts = []
    for i in range(len(results["ids"][0])):
        concepts.append({
            "metric": results["metadatas"][0][i]["metric"],
            "text": results["documents"][0][i],
            "score": round(1 - results["distances"][0][i], 4)
        })
    return concepts


# -------------------------------------------------------------
# FUNCTION 3: FULL RETRIEVAL — combines both functions
# -------------------------------------------------------------
def retrieve(question, db_key):
    """
    Full retrieval pipeline. Given a user question and a
    selected database, returns both live financial data and
    relevant concept documents.

    Args:
        question: plain English user question
        db_key:   "service1", "service2", or "service3"

    Returns:
        dict: {
            "live_data": {query_name: [rows]},
            "concepts":  [{metric, text, score}]
        }
    """
    live_data = get_live_data(db_key)
    concepts = get_concepts(question)
    return {
        "live_data": live_data,
        "concepts": concepts
    }


# -------------------------------------------------------------
# QUICK TEST — runs when you execute this script directly
# -------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("Retreive.py - Quick test")
    print("=" * 60)
    test_question = 'Is our cash runway safe?'
    test_db = "service1"
    print(f"\nQuestions: {test_question}")
    print(f"Database: {test_db}\n")
    result = retrieve(test_question, test_db)

    print("CONCEPTS RETRIEVED:")
    for concept in result["concepts"]:
        print(f"  {concept['metric']} (score: {concept['score']})")
    print("-" * 40)
    for query_name, rows in result["live_data"].items():
        if isinstance(rows, list) and len(rows) > 0:
            print(f" {query_name}:")
            for row in rows[:2]:
                print(f"   {row}")
        else:
            print(f" {query_name}: {rows}")

    print("\n" + "=" * 60)
    print("retrieve.py is working. Ready for Phase 4.")
    print("=" * 60)

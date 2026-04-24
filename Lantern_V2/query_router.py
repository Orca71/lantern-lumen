# =============================================================
# LANTERN INTELLIGENCE v2 — query_router.py
# Phase 4: Route user questions to relevant SQL queries
# =============================================================
# WHAT THIS SCRIPT DOES:
#   Takes a user question in plain English and returns a list
#   of which SQL queries are most relevant to answer it.
#   This prevents running all 8 queries every time and ensures
#   the LLM gets focused, relevant context.
#
# NO LLM CALLS — pure keyword scoring. Fast and free.
# =============================================================
import re 

# -------------------------------------------------------------
# KEYWORD MAP
# -------------------------------------------------------------
# Each query has a list of keywords associated with it.
# When a user asks a question, we count how many keywords
# appear in the question for each query.
# The queries with the highest scores get selected.
#
# Think of it like a tag system — each query has tags,
# and we find which tags appear in the user's question.
# -------------------------------------------------------------

QUERY_KEYWORDS = {
 
    "net_profit_margin": [
        "profit", "margin", "profitable", "profitability",
        "net income", "earnings", "making money", "losing money",
        "revenue", "expenses", "costs", "overhead",
        "bottom line", "income", "viable", "sustainable"
    ],
 
    "monthly_revenue_trend": [
        "revenue", "trend", "growth", "growing", "declining",
        "sales", "income", "monthly", "trajectory", "direction",
        "increasing", "decreasing", "year over year", "yoy",
        "momentum", "performance", "top line"
    ],
 
    "days_sales_outstanding": [
        "dso", "days sales outstanding", "collecting", "collection",
        "receivables", "accounts receivable", "invoice", "invoices",
        "payment", "paying", "clients pay", "how long",
        "outstanding", "overdue", "billing", "cash collection"
    ],
 
    "client_concentration": [
        "concentration", "client", "clients", "customer",
        "dependent", "dependency", "biggest client", "largest client",
        "top client", "diversified", "diversification", "risk",
        "reliant", "single client", "one client", "exposure"
    ],
 
    "burn_rate_runway": [
        "burn", "runway", "cash", "survive", "survival",
        "months left", "how long", "run out", "running out",
        "liquidity", "cash position", "cash balance",
        "spending", "sustainable", "solvent", "solvency"
    ],
 
    "expense_breakdown": [
        "expenses", "costs", "spending", "overhead", "payroll",
        "salaries", "rent", "category", "breakdown", "where",
        "going", "money going", "biggest expense", "cost structure",
        "fixed costs", "variable costs", "operating costs"
    ],
 
    "revenue_per_employee": [
        "employee", "employees", "headcount", "staff", "team",
        "productivity", "per person", "per employee", "efficiency",
        "revenue per", "generating", "workforce", "overstaffed",
        "understaffed", "hiring", "people"
    ],
 
    "client_churn_rate": [
        "churn", "churning", "losing clients", "lost clients",
        "retention", "retaining", "leaving", "left", "inactive",
        "attrition", "client loss", "turnover", "loyalty",
        "keeping clients", "losing customers", "dropped"
    ]
}

# -------------------------------------------------------------
# MINIMUM QUERIES TO ALWAYS INCLUDE
# -------------------------------------------------------------
# Some queries are so fundamental that we always include them
# regardless of the question. Net profit margin and revenue
# trend give the LLM baseline context about the company.
# -------------------------------------------------------------

ALWAYS_INCLUDE = [
    "net_profit_margin",
    "monthly_revenue_trend"
]
 
# -------------------------------------------------------------
# ROUTE FUNCTION
# -------------------------------------------------------------

def route(question, top_n=4):
    """
    Given a user question, return a list of the most relevant SQL query names to run. 
    Arge:
        question: plain English user question (string)
        top_n : max number of queries to return (default of 4)

    Returns:
        list of query name strings 
        e.g. ["burn_rate_runaway", "expense_breakdown",
                "net_profit_margin", "monthly_revenue_trend"]
    """
    # clean the question — lowercase, remove punctuation
    # so "Cash?" matches "cash" and "Runway!" matches "runway"
    cleaned = re.sub(r"[^\w\s]", "", question.lower())
    # score each query by counting keyword matches
    scores = {}
    
    for query_name, keywords in QUERY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in cleaned:
                score += 1
        scores[query_name] = score
    
    # sort queries by score, highest first 
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    #take the top_n scorting queries 
    selected = [query_name for query_name, score in ranked[:top_n] if score > 0]

    # always add the baseline queries if not already included

    for query_name in ALWAYS_INCLUDE:
        if query_name not in selected:
            selected.append(query_name)
    
    #if not matched at all, return all queries
    # (better to over-retireve that under retireve)
    if not selected:
        print(' No keyword matches - returning all queries')
        return list(QUERY_KEYWORDS.keys())
    return selected 

# -------------------------------------------------------------
# QUICK TEST — runs when you execute this script directly
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("Query_router.py - Quick Test")
    print("=" * 60)

    test_questions = [
        "Is our cash runway safe?",
        "Are we losing clients?",
        "How productive is our team?",
        "What are our biggest expenses?",
        "Are clients paying their invoices on time?",
        "How is company performing overall?"
    ]
    for question in test_questions:
        selected = route(question)
        print(f"\nQuestions: {question}")
        print(f"Queries: {selected}")
    
    print("\n" + "=" * 60)
    print("query_router.py is working. Ready for phase 5.")
    print("=" * 60)
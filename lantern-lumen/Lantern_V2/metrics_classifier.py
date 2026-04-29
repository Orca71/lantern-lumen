# =============================================================
# LANTERN INTELLIGENCE v2 — metrics_classifier.py
# Pre-classification layer: SQL rows → benchmark labels
# =============================================================
# PURPOSE:
#   Reads extraction config directly from metrics_schema.yaml.
#   No hardcoded field names or query names in Python.
#   Adding a new metric = update YAML only, no code changes.
#
# EXPORTS:
#   pre_classify_live_data()            — main entry point
#   format_classifications_for_prompt() — prompt injection
# =============================================================
import yaml
from pathlib import Path


SCHEMA_PATH = "metrics_schema.yaml"

#-----SCHEMA LOADER -----
def _load_schema(schema_path: str = SCHEMA_PATH) -> dict:
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


 # -------------------------------------------------------------
# SCHEMA VALIDATION
# Catches bad extraction configs before they silently fail.
# -------------------------------------------------------------

VALID_ROW_VALUES = {"first", "last"}

def _validate_extraction(metric_key: str, extraction: dict) -> list[str]:
    """
    Returns a list of error strings for extraction block.
    Empty list means the config is valid.
    """
    errors = []
    for required in ("query", "field", "row"):
        if required not in extraction:
            errors.append(f"[{metric_key}] extraction missing required key: '{required}'")
    if "row" in extraction and extraction["row"] not in VALID_ROW_VALUES:
        errors.append(
            f"[{metric_key}] extraction.row must be 'first' or 'last', "
            f"got: '{extraction['row']}'"
        )
    return errors

# ---Threshold look up ---
def _find_threshold(value: float, thresholds: dict):
    """Returns the label of the threshold thevalue falls into."""
    if not thresholds:
        return None
    for label, bounds in thresholds.items():
        if bounds is None:
            continue
        if isinstance(bounds, dict):
            low = bounds.get("min", float("-inf"))
            high = bounds.get("max", float("inf"))
            if low <= value <= high:
                return label
    return None

# -------------------------------------------------------------
# GENERIC EXTRACTOR
# Driven entirely by the extraction block in the YAML.
# -------------------------------------------------------------

def _extract(metric_key: str, meta: dict, rows: list) -> dict | None:
    """
    Extracts and classifies one metric value from SQL rows.
    Reads all config from the schema — no hardcoded logic.
    Returns:
        Classification dict or None if value is missing/invalid.
    """
    extraction = meta.get("extraction", {})
    field = extraction.get("field")
    row_target = extraction.get("row", "first")
    display_field = extraction.get("display_field")

    if not rows or not field:
        return None

    target_row = rows[0] if row_target == "first" else rows[-1]
    value = target_row.get(field)

    if value is None:
        return None

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    thresholds = meta.get("thresholds", {})
    schema_range = meta.get("range", {})
    threshold = _find_threshold(numeric, thresholds)

    low = schema_range.get("min", float("-inf"))
    high = schema_range.get("max", float("inf"))
    in_range = low <= numeric <= high

    # Build display name - optionally append a field value
    display = meta.get("display_name", metric_key)
    if display_field:
        label = target_row.get(display_field, "")
        if label:
            display = f"{display} ({label})"

    return {
        "display_name": display,
        "value": numeric,
        "unit": meta.get("unit", ""),
        "threshold": threshold,
        "in_range": in_range
    }
# -------------------------------------------------------------
# PRE-CLASSIFICATION — main entry point
# -------------------------------------------------------------

def pre_classify_live_data(live_data: dict, schema_path: str = SCHEMA_PATH) -> dict:
    """
    Classifies metric values directly from SQL result rows.
    Config is read entirely from metrics_schema.yaml.
    Validates all extraction blocks on load and raises on error.

    Args:
        live_data   : dict of {query_name: [list of row dicts]}
        schema_path : path to metrics_schema.yaml

    Returns:
        dict of {metric_key: classification_dict}
    """
    schema = _load_schema(schema_path)
    metrics = schema.get("metrics", {})

    # Validate all extractions blocks upfront
    all_errors = []
    for metric_key, meta in metrics.items():
        extraction = meta.get("extraction")
        if extraction:
            all_errors.extend(_validate_extraction(metric_key, extraction))

    if all_errors:
        raise ValueError(
            "Schema extraction config errors:\n" +
            "\n".join(f" - {e}" for e in all_errors)
        )

    results = {}
    for metric_key, meta in metrics.items():
        extraction = meta.get("extraction")
        if not extraction:
            continue
        query_name = extraction.get("query")
        rows = live_data.get(query_name)

        if not rows or not isinstance(rows, list):
            continue

        result = _extract(metric_key, meta, rows)
        if result:
            results[metric_key] = result
    return results

# -------------------------------------------------------------
# FORMAT FOR PROMPT INJECTION
# -------------------------------------------------------------

def format_classifications_for_prompt(classifications: dict) -> str:
    """
    Converts pre-classified metric dict into a prompt-ready
    text block that Lantern reads as ground truth.
    """

    if not classifications:
        return ""

    lines = [
        "=== PRE-COMPUTED CLASSIFICATIONS ===",
        "These classifications are final. Do NOT re-classify or re-verify them.",
        "State them as established facts in your response.\n"
    ]
    for metric_key, data in classifications.items():
        threshold = data["threshold"] or "unclassified"
        flag = "[OUT OF RANGE - flag this]" if not data["in_range"] else ""
        lines.append(
            f"- {data['display_name']}: "
            f"{data['value']} {data['unit']} "
            f"→ {threshold.upper()}{flag}"
        )
    lines.append("")
    return "\n".join(lines)
# -------------------------------------------------------------
# QUICK TEST
# -------------------------------------------------------------

if __name__ == "__main__":
    sample_live_data = {
        "net_profit_margin": [
            {"total_revenue": 813500.0, "total_expenses": 515400.12,
             "net_profit": 298099.88, "net_profit_margin_pct": 36.64}
        ],
        "days_sales_outstanding": [
            {"client_name": "Client A", "invoices_paid": 12,
             "avg_days_to_pay": 84.0, "dso_status": "Dangerous",
             "company_avg_dso": 84.0}
        ],
        "burn_rate_runway": [
            {"month": "2025-01", "revenue": 71000, "expenses": 98000,
             "burn_rate": 27000, "burn_status": "Burning Cash",
             "current_cash": 520000, "runway_months": 19.3},
        ],
        "client_churn_rate": [
            {"total_clients": 11, "active_clients": 8, "churned_clients": 3,
             "client_churn_pct": 27.27, "client_churn_status": "Dangerous",
             "churned_client": "Acme Corp", "churned_client_revenue": 45000.0}
        ],
        "expense_breakdown": [
            {"category": "Payroll", "entries": 12,
             "category_total": 340000.0, "pct_of_expenses": 62.3, "flag": "Normal"},
        ],
        "revenue_per_employee": [
            {"total_revenue": 813500.0, "active_employees": 7,
             "revenue_per_employee": 116214.29, "efficiency_status": "Healthy"}
        ],
    }

    print("=== metrics_classifier.py — Test Run ===\n")
    classifications = pre_classify_live_data(sample_live_data)
    prompt_block    = format_classifications_for_prompt(classifications)
    print(prompt_block)

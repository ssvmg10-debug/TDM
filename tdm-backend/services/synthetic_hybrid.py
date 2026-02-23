"""
Phase 3: Hybrid Synthetic Engine — Multi-source generator.
1. Rule-based generator (constraints: country=IN → currency=INR)
2. Domain pack generator (enhanced)
3. Test case flow generator (login → add to cart → checkout)
4. Optional SDV (falls back to Faker if unavailable)
"""
import logging
import random
from typing import Dict, List, Any, Optional
from pathlib import Path

from services.synthetic_enhanced import SyntheticDataGenerator

logger = logging.getLogger("tdm.synthetic_hybrid")

# Rule-based constraints: (condition_col, condition_val) -> (target_col, target_val)
RULE_CONSTRAINTS = {
    ("country", "IN"): [("currency", "INR"), ("pincode_format", "6digit")],
    ("country", "US"): [("currency", "USD"), ("pincode_format", "zip5")],
    ("country", "UK"): [("currency", "GBP"), ("pincode_format", "postcode")],
    ("age", lambda x: x < 18): [("account_status", "minor")],
    ("age", lambda x: x >= 65): [("account_status", "senior")],
}

# Test case flow templates
FLOW_TEMPLATES = {
    "ecommerce_checkout": ["login", "add_to_cart", "checkout", "payment"],
    "loan_application": ["login", "apply_loan", "credit_check", "approval"],
    "user_registration": ["navigate", "fill_form", "submit", "verify"],
}


def apply_rule_constraints(row: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """Apply rule-based constraints to a row."""
    for (cond_col, cond_val), targets in RULE_CONSTRAINTS.items():
        if cond_col not in row:
            continue
        val = row[cond_col]
        match = False
        if callable(cond_val):
            try:
                match = cond_val(val)
            except Exception:
                pass
        else:
            match = str(val).upper() == str(cond_val).upper()
        if match:
            for tcol, tval in targets:
                if tcol not in row or row[tcol] is None:
                    row[tcol] = tval
    return row


def generate_with_rules(
    base_generator: SyntheticDataGenerator,
    schema: Dict,
    row_counts: Dict[str, int],
    out_path: Path,
    job_id: Optional[str] = None,
) -> Dict[str, int]:
    """Generate data with rule-based constraints applied."""
    generated = {}
    default_rows = row_counts.get("*", 1000)
    for entity_name, entity_info in schema.get("entities", {}).items():
        n = row_counts.get(entity_name, default_rows)
        fields = entity_info.get("fields", {})
        if not fields:
            continue
        data = {}
        for field_name, field_info in fields.items():
            ft = field_info.get("type", "string")
            data[field_name] = [
                base_generator._generate_value_by_type(field_name, ft) for _ in range(n)
            ]
        # Build rows and apply rules
        rows = [dict(zip(data.keys(), vals)) for vals in zip(*data.values())]
        for row in rows:
            apply_rule_constraints(row, entity_name)
        # Convert back to columns
        import pandas as pd
        df = pd.DataFrame(rows)
        df.to_parquet(out_path / f"{entity_name}.parquet", index=False)
        generated[entity_name] = n
    return generated


def get_flow_entities(flow_name: str) -> Dict[str, Any]:
    """Get entity schema for a test case flow."""
    if flow_name == "ecommerce_checkout":
        return {
            "entities": {
                "session": {"fields": {"user_id": {"type": "integer"}, "cart_id": {"type": "integer"}}},
                "cart": {"fields": {"id": {"type": "integer"}, "user_id": {"type": "integer"}, "items": {"type": "integer"}}},
                "order": {"fields": {"id": {"type": "integer"}, "user_id": {"type": "integer"}, "total": {"type": "number"}, "status": {"type": "string"}}},
            }
        }
    if flow_name == "user_registration":
        return {
            "entities": {
                "user": {"fields": {"email": {"type": "email"}, "firstname": {"type": "string"}, "lastname": {"type": "string"}}},
            }
        }
    return {"entities": {}}

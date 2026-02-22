"""PII classification: regex + optional Azure OpenAI."""
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session
from openai import AzureOpenAI

from config import settings
from models import PIIClassification, ColumnMeta, TableMeta, SchemaVersion
from database import SessionLocal

logger = logging.getLogger(__name__)

# Regex patterns for common PII
PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    "phone": re.compile(r"^[\d\s\-+()]{10,20}$"),
    "ssn": re.compile(r"^\d{3}-\d{2}-\d{4}$"),
    "credit_card": re.compile(r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$"),
}

COLUMN_NAME_HINTS = {
    "email": ["email", "e_mail", "mail", "user_email"],
    "phone": ["phone", "mobile", "tel", "contact_number", "phone_number"],
    "ssn": ["ssn", "social_security", "social_security_number"],
    "person_name": ["name", "first_name", "last_name", "full_name", "customer_name"],
    "address": ["address", "street", "city", "zip", "billing_address"],
}


def _regex_detect(value: str) -> Optional[tuple[str, float]]:
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for pii_type, pat in PATTERNS.items():
        if pat.match(value):
            return (pii_type, 0.95)
    for pii_type, keywords in COLUMN_NAME_HINTS.items():
        if pii_type in PATTERNS:
            continue
        if any(k in value.lower() for k in keywords):
            return (pii_type, 0.7)
    return None


def _llm_classify(column_name: str, sample_values: list[str]) -> Optional[tuple[str, float]]:
    if not settings.azure_api_key or not settings.azure_endpoint:
        return None
    try:
        client = AzureOpenAI(
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            azure_endpoint=settings.azure_endpoint.rstrip("/"),
        )
        samples = ", ".join(repr(str(v)[:50]) for v in sample_values[:5])
        prompt = (
            f"Column name: {column_name}. Sample values (truncated): {samples}. "
            "Classify as exactly one of: email, phone, ssn, credit_card, person_name, address, date_of_birth, ip_address, none. "
            'Reply with JSON only: {"pii_type": "...", "confidence": 0.0-1.0}'
        )
        r = client.chat.completions.create(
            model=settings.azure_deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        text = (r.choices[0].message.content or "").strip()
        if "none" in text.lower() or "null" in text:
            return None
        import json
        for part in text.split("}"):
            part = part + "}"
            try:
                obj = json.loads(part)
                t = obj.get("pii_type") or obj.get("pii_type")
                c = float(obj.get("confidence", 0.8))
                if t and t != "none":
                    return (t, min(1.0, c))
            except Exception:
                continue
    except Exception as e:
        logger.warning("LLM PII classify failed: %s", e)
    return None


def run_pii_classification(
    schema_version_id: str,
    use_llm: bool = True,
    sample_size_per_column: int = 100,
) -> list[dict]:
    db = SessionLocal()
    try:
        sv = db.query(SchemaVersion).filter(SchemaVersion.id == schema_version_id).first()
        if not sv:
            return []
        pii_entries = []
        for table in sv.tables_rel:
            for col in table.columns:
                technique = "regex"
                confidence = 0.0
                pii_type = None
                # Name-based hint
                col_lower = col.name.lower()
                for pt, keywords in COLUMN_NAME_HINTS.items():
                    if any(k in col_lower for k in keywords):
                        pii_type = pt
                        confidence = 0.85
                        break
                if not pii_type and col.data_type and "char" in str(col.data_type).lower():
                    pii_type = "text"
                    confidence = 0.3
                # We don't sample from source DB here for simplicity; use name + type only, or add sampling later
                if use_llm and settings.azure_api_key:
                    llm_result = _llm_classify(col.name, [col.name, col.data_type or ""])
                    if llm_result:
                        pt, conf = llm_result
                        if conf > confidence:
                            pii_type, confidence, technique = pt, conf, "llm"
                if pii_type and pii_type != "none":
                    existing = db.query(PIIClassification).filter(
                        PIIClassification.schema_version_id == schema_version_id,
                        PIIClassification.table_name == table.name,
                        PIIClassification.column_name == col.name,
                    ).first()
                    if existing:
                        existing.pii_type = pii_type
                        existing.confidence = confidence
                        existing.technique = technique
                    else:
                        rec = PIIClassification(
                            schema_version_id=schema_version_id,
                            table_name=table.name,
                            column_name=col.name,
                            pii_type=pii_type,
                            technique=technique,
                            confidence=confidence,
                        )
                        db.add(rec)
                    pii_entries.append({
                        "table": table.name,
                        "column": col.name,
                        "pii_type": pii_type,
                        "confidence": float(confidence),
                        "technique": technique,
                    })
        db.commit()
        return pii_entries
    finally:
        db.close()

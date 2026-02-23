"""
Schema Fusion Engine — Combines UI + API + DB + Test Case + Domain Packs.
Phase 2 foundation: normalizer, field matcher, weighted fusion, constraint unifier.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("tdm.schema_fusion")


def normalize_schema(
    source: str,
    raw: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert any schema type into unified internal format.
    A. Schema Normalizer
    """
    tables = []
    if "tables" in raw:
        for t in raw["tables"]:
            tables.append({
                "name": t.get("name", ""),
                "fields": t.get("fields", t.get("columns", [])),
                "constraints": t.get("constraints", {}),
                "source": source,
            })
    elif "entities" in raw:
        for name, entity in raw["entities"].items():
            fields = entity.get("fields", entity.get("columns", []))
            if isinstance(fields, dict):
                fields = [{"name": k, "type": v} for k, v in fields.items()]
            tables.append({
                "name": name,
                "fields": fields,
                "constraints": {},
                "source": source,
            })
    return {
        "tables": tables,
        "relationships": raw.get("relationships", []),
        "semantic_tags": raw.get("semantic_tags", {}),
    }


def match_fields(
    fields_a: List[Dict],
    fields_b: List[Dict],
) -> List[Dict[str, Any]]:
    """
    B. Field Matcher — match similar fields across sources using:
    - name similarity
    - label similarity
    - semantic meaning
    """
    matches = []
    for fa in fields_a:
        name_a = (fa.get("name") or "").lower()
        for fb in fields_b:
            name_b = (fb.get("name") or "").lower()
            if name_a == name_b:
                matches.append({"field_a": fa, "field_b": fb, "score": 1.0})
                break
            # Simple similarity: substring
            if name_a in name_b or name_b in name_a:
                matches.append({"field_a": fa, "field_b": fb, "score": 0.7})
    return matches


def fuse_schemas(
    db_schema: Optional[Dict] = None,
    api_schema: Optional[Dict] = None,
    ui_schema: Optional[Dict] = None,
    test_case_entities: Optional[Dict] = None,
    domain_pack: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    C. Weighted Fusion Model
    Priority: DB > API > UI > Test case > Domain pack
    """
    unified = {"tables": [], "relationships": [], "semantic_tags": {}}
    seen_tables = {}

    sources = [
        ("db", db_schema, 1.0),
        ("api", api_schema, 0.9),
        ("ui", ui_schema, 0.8),
        ("test_case", {"entities": test_case_entities or {}}, 0.7),
        ("domain", domain_pack, 0.6),
    ]

    for src_name, schema, weight in sources:
        if not schema:
            continue
        norm = normalize_schema(src_name, schema)
        for t in norm.get("tables", []):
            name = t.get("name", "")
            if not name:
                continue
            if name not in seen_tables:
                seen_tables[name] = {"name": name, "fields": [], "sources": [], "weight": weight}
            entry = seen_tables[name]
            for f in t.get("fields", []):
                fn = f.get("name") if isinstance(f, dict) else f
                if fn and not any(
                    (x.get("name") if isinstance(x, dict) else x) == fn
                    for x in entry["fields"]
                ):
                    entry["fields"].append(f if isinstance(f, dict) else {"name": fn, "type": "string"})
            if src_name not in entry.get("sources", []):
                entry.setdefault("sources", []).append(src_name)

    unified["tables"] = list(seen_tables.values())
    return unified


def run_schema_fusion(
    ui_schemas: Optional[Dict] = None,
    api_schemas: Optional[Dict] = None,
    db_schemas: Optional[Dict] = None,
    test_case_entities: Optional[Dict] = None,
    domain_pack: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run schema fusion and return unified schema.
    """
    domain_data = None
    if domain_pack:
        from services.crawler import TestCaseCrawler
        crawler = TestCaseCrawler()
        domain_data = crawler._fallback_schema({"domain": domain_pack, "scenario": "default"})
    unified = fuse_schemas(
        db_schema=db_schemas,
        api_schema=api_schemas,
        ui_schema=ui_schemas,
        test_case_entities=test_case_entities,
        domain_pack=domain_data,
    )
    return {
        "unified_schema": unified,
        "tables_count": len(unified.get("tables", [])),
    }

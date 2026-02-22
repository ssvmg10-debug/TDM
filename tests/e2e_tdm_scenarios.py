"""
TDM E2E test: run all feature scenarios against the running API (port 8002).
Requires: backend running, PostgreSQL with DB from DATABASE_URL.
Usage: from TDM root, with .env loaded:
  python -m pytest tests/e2e_tdm_scenarios.py -v -s
  or: python tests/e2e_tdm_scenarios.py
"""
import os
import sys
import time
import json
from pathlib import Path

# Load root .env
_root = Path(__file__).resolve().parent.parent
_env = _root / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    import requests
except ImportError:
    import urllib.request
    import urllib.error

    class requests:
        @staticmethod
        def get(url, timeout=30):
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return type("R", (), {"status_code": r.status, "json": lambda: json.loads(r.read().decode())})()
        @staticmethod
        def post(url, json=None, timeout=60):
            req = urllib.request.Request(url, data=json.dumps(json or {}).encode(), method="POST",
                                          headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return type("R", (), {"status_code": r.status, "json": lambda: json.loads(r.read().decode())})()

BASE = os.getenv("TDM_API_BASE", "http://localhost:8002")
API = f"{BASE}/api/v1"

def log(msg: str):
    print(f"  [E2E] {msg}")

def get(path: str):
    r = requests.get(f"{API}{path}", timeout=30)
    if r.status_code != 200:
        raise AssertionError(f"GET {path} -> {r.status_code}")
    return r.json()

def post(path: str, body: dict):
    r = requests.post(f"{API}{path}", json=body, timeout=60)
    if r.status_code not in (200, 201):
        raise AssertionError(f"POST {path} -> {r.status_code}: {getattr(r, 'text', r)}")
    return r.json()

def wait_job(job_id: str, max_wait_sec=90, poll_interval=2):
    if os.getenv("TDM_E2E_QUICK"):
        time.sleep(3)
        return get(f"/job/{job_id}")
    start = time.time()
    while time.time() - start < max_wait_sec:
        j = get(f"/job/{job_id}")
        status = j.get("status")
        if status == "completed":
            return j
        if status == "failed":
            err = (j.get("result_json") or {}).get("error", "unknown")
            raise AssertionError(f"Job failed: {err}")
        time.sleep(poll_interval)
    raise TimeoutError(f"Job {job_id} did not complete in {max_wait_sec}s")

def run_e2e():
    results = {"passed": 0, "failed": 0, "skipped": 0, "steps": []}

    def ok(name):
        results["passed"] += 1
        results["steps"].append((name, "PASS"))
        log(f"PASS: {name}")

    def fail(name, e):
        results["failed"] += 1
        results["steps"].append((name, f"FAIL: {e}"))
        log(f"FAIL: {name} -> {e}")

    def skip(name, reason):
        results["skipped"] += 1
        results["steps"].append((name, f"SKIP: {reason}"))
        log(f"SKIP: {name} ({reason})")

    conn = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost:5432/tdm")

    # --- Scenario 0: Health ---
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        assert r.status_code == 200
        ok("Health check")
    except Exception as e:
        fail("Health check", e)
        log("Backend not running? Start: cd tdm-backend && python -m uvicorn main:app --port 8002")
        return results

    # --- Scenario A: Schema Discovery ---
    try:
        out = post("/discover-schema", {
            "connection_string": conn,
            "schemas": ["public"],
            "include_stats": True,
            "sample_size": 1000,
        })
        assert "schema_version_id" in out or "message" in out
        ok("Schema discovery")
    except Exception as e:
        fail("Schema discovery", e)

    # --- List schemas and get first version ---
    try:
        schemas = get("/schemas")
        assert isinstance(schemas, list)
        ok("List schemas")
    except Exception as e:
        fail("List schemas", e)
        schemas = []

    schema_version_id = None
    schema_id = None
    if schemas:
        schema_id = schemas[0]["id"]
        schema_version_id = schemas[0].get("latest_version_id") or schema_id
    try:
        if schema_id:
            detail = get(f"/schema/{schema_id}")
            tables = detail.get("tables", [])
            ok("Get schema detail (tables)")
        else:
            tables = []
            skip("Get schema detail", "no schemas")
    except Exception as e:
        fail("Get schema detail", e)
        tables = []

    root_table = tables[0]["name"] if tables else "users"

    # --- Scenario B: PII Classification ---
    if schema_version_id:
        try:
            out = post("/pii/classify", {"schema_version_id": schema_version_id, "use_llm": False})
            assert "pii_map" in out
            ok("PII classify")
        except Exception as e:
            fail("PII classify", e)
        try:
            pii_list = get(f"/pii/{schema_version_id}")
            assert "pii_map" in pii_list
            ok("Get PII map")
        except Exception as e:
            fail("Get PII map", e)
    else:
        skip("PII classify", "no schema version")
        skip("Get PII map", "no schema version")

    # --- Scenario C: Subset ---
    if schema_version_id and tables:
        try:
            out = post("/subset", {
                "schema_version_id": schema_version_id,
                "connection_string": conn,
                "root_table": root_table,
                "max_rows_per_table": {root_table: 500},
            })
            job_id = out.get("job_id")
            assert job_id
            ok("Subset job started")
            try:
                job = wait_job(job_id)
                status = job.get("status")
                if status == "completed":
                    ok("Subset job completed")
                    dataset_version_id = (job.get("result_json") or {}).get("dataset_version_id")
                    if dataset_version_id:
                        ds = get(f"/dataset/{dataset_version_id}")
                        assert ds.get("source_type") == "subset"
                        ok("Subset dataset in catalog")
                elif os.getenv("TDM_E2E_QUICK") and status in ("running", "pending"):
                    ok("Subset job started (quick)")
                else:
                    fail("Subset job completed", job.get("result_json") or status)
            except TimeoutError as e:
                fail("Subset job completed", e)
            except AssertionError as e:
                fail("Subset job completed", e)
        except Exception as e:
            fail("Subset", e)
    else:
        skip("Subset", "no schema version or no tables")

    # --- Scenario D: Synthetic ---
    if schema_version_id:
        try:
            out = post("/synthetic", {
                "schema_version_id": schema_version_id,
                "row_counts": {"*": 100},
            })
            job_id = out.get("job_id")
            assert job_id
            ok("Synthetic job started")
            try:
                job = wait_job(job_id)
                status = job.get("status")
                if status == "completed":
                    ok("Synthetic job completed")
                elif os.getenv("TDM_E2E_QUICK") and status in ("running", "pending"):
                    ok("Synthetic job started (quick)")
                else:
                    fail("Synthetic job completed", job.get("result_json") or status)
            except TimeoutError as e:
                fail("Synthetic job completed", e)
            except AssertionError as e:
                fail("Synthetic job completed", e)
        except Exception as e:
            fail("Synthetic", e)
    else:
        skip("Synthetic", "no schema version")

    # --- List datasets (for mask/provision) ---
    try:
        datasets = get("/datasets")
        assert isinstance(datasets, list)
        ok("List datasets")
    except Exception as e:
        fail("List datasets", e)
        datasets = []

    subset_dataset_id = next((d["id"] for d in datasets if d.get("source_type") == "subset"), None)
    any_dataset_id = datasets[0]["id"] if datasets else None

    # --- Scenario E: Masking ---
    if any_dataset_id and datasets and datasets[0].get("source_type") != "masked":
        try:
            # Rule: table.column -> mask type (use first table from schema)
            tname = tables[0]["name"] if tables else "users"
            rules = {f"{tname}.id": "mask.hash"}
            out = post("/mask", {"dataset_version_id": any_dataset_id, "rules": rules})
            job_id = out.get("job_id")
            assert job_id
            ok("Mask job started")
            try:
                job = wait_job(job_id)
                if job.get("status") == "completed":
                    ok("Mask job completed")
                else:
                    fail("Mask job completed", job.get("result_json") or job.get("status"))
            except TimeoutError as e:
                fail("Mask job completed", e)
        except Exception as e:
            fail("Mask", e)
    else:
        skip("Mask", "no non-masked dataset")

    # --- Scenario F: Provisioning ---
    try:
        envs = get("/environments")
        assert isinstance(envs, list)
        ok("List environments")
    except Exception as e:
        fail("List environments", e)
        envs = []

    if any_dataset_id and envs:
        try:
            out = post("/provision", {
                "dataset_version_id": any_dataset_id,
                "target_env": envs[0]["name"],
                "reset_env": True,
                "run_smoke_tests": True,
            })
            job_id = out.get("job_id")
            assert job_id
            ok("Provision job started")
            try:
                job = wait_job(job_id)
                if job.get("status") == "completed":
                    ok("Provision job completed")
                else:
                    fail("Provision job completed", job.get("result_json") or job.get("status"))
            except TimeoutError as e:
                fail("Provision job completed", e)
        except Exception as e:
            fail("Provision", e)
    else:
        skip("Provision", "no dataset or no environment")

    # --- Scenario G: Jobs, Audit, Lineage ---
    try:
        jobs = get("/jobs")
        assert isinstance(jobs, list)
        ok("List jobs")
    except Exception as e:
        fail("List jobs", e)

    try:
        audit_logs = get("/audit-logs")
        assert isinstance(audit_logs, list)
        ok("Audit logs")
    except Exception as e:
        fail("Audit logs", e)

    if datasets:
        try:
            lineage = get(f"/lineage/dataset/{datasets[0]['id']}")
            assert isinstance(lineage, list)
            ok("Lineage for dataset")
        except Exception as e:
            fail("Lineage for dataset", e)

    return results


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    if quick:
        os.environ["TDM_E2E_QUICK"] = "1"
    print("TDM E2E scenarios (API base:", BASE, ")" + (" [quick]" if quick else ""))
    print("-" * 50)
    res = run_e2e()
    print("-" * 50)
    print("Result:", res["passed"], "passed,", res["failed"], "failed,", res["skipped"], "skipped")
    for name, status in res["steps"]:
        print(" ", status, name)
    sys.exit(0 if res["failed"] == 0 else 1)

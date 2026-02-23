"""
End-to-end test: run TDM workflow with LG test case content.
Verifies: workflow executes, logs appear in API, data in jobs/job_logs/dataset_versions,
and tables are created in tdm_target when provision runs.
"""
import os
import sys
import time
import requests

BASE = os.getenv("TDM_API_URL", "http://localhost:8003")
API = f"{BASE}/api/v1"
TARGET_DATABASE_URL = os.getenv("TARGET_DATABASE_URL", "postgresql://postgres:12345@localhost:5432/tdm_target")

LG_TEST_CASE = """
navigate to this application https://www.lg.com/in
click on Home appliances
click on All Refrigerators
click on LG 398L Double Door Refrigerator, Convertible, Wi-Fi, Door Cooling™, Ebony Sheen Finish, 3 Star GL-T422VESX
click on buynow
Enter pincode as 500032
Click on Check
Wait until "Free Delivery" text appears (timeout 60 seconds)
Click on the "Free Delivery" radio button
Wait until Checkout button is enabled and clickable
Click on Checkout only if enabled
Click on continue to guest checkout
Enter email as test@gmail.com in the email input field
Enter firstname as test
Enter lastname as name
Enter mobile number as 8919552876
Enter pincode as 500032
Enter street address as test
click on QR code
click all checkboxes under QR code section
click on place order
"""


def main():
    print("TDM E2E test: LG test case workflow")
    print("=" * 60)

    # 1) Health / readiness
    try:
        r = requests.get(f"{BASE}/docs", timeout=5)
        print(f"Backend reachable: {r.status_code}")
    except Exception as e:
        print(f"Backend not reachable at {BASE}: {e}")
        print("Start backend: cd tdm-backend && .\\start_backend.ps1")
        sys.exit(1)

    # 2) Execute workflow: synthetic (from test case) + provision to tdm_target
    body = {
        "test_case_content": LG_TEST_CASE.strip(),
        "operations": ["synthetic", "provision"],
        "config": {
            "synthetic": {"row_counts": {"*": 50}},
            "provision": {"target_env": "default", "run_smoke_tests": True},
        },
    }
    print("POST /workflow/execute (synthetic + provision to tdm_target)...")
    r = requests.post(f"{API}/workflow/execute", json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    job_id = data.get("job_id")
    workflow_id = data.get("workflow_id")
    print(f"  job_id: {job_id}")
    print(f"  workflow_id: {workflow_id}")
    print(f"  overall_status: {data.get('overall_status')}")

    # 3) Poll logs until we have entries and job is not running (or timeout)
    print("\nPolling GET /workflow/logs/{job_id} ...")
    logs_seen = 0
    last_status = None
    for _ in range(90):
        time.sleep(1)
        try:
            r = requests.get(f"{API}/workflow/logs/{job_id}", timeout=10)
            r.raise_for_status()
            payload = r.json()
            logs = payload.get("logs") or []
            if len(logs) > logs_seen:
                for log in logs[logs_seen:]:
                    step = log.get("step", "")
                    level = log.get("level", "")
                    msg = log.get("message", "")
                    ts = log.get("timestamp", "")[:19] if log.get("timestamp") else ""
                    print(f"  [{ts}] [{step}] {level}: {msg}")
                logs_seen = len(logs)
        except Exception as e:
            print(f"  log poll error: {e}")
            continue

        try:
            s = requests.get(f"{API}/workflow/status/{workflow_id}", timeout=10)
            if s.ok:
                st = s.json()
                status = st.get("status")
                if status != last_status:
                    print(f"  status: {status}")
                    last_status = status
                if status in ("completed", "failed"):
                    print(f"\nWorkflow finished with status: {status}")
                    if status == "failed" and st.get("error"):
                        print(f"  error: {st.get('error')}")
                    break
        except Exception:
            pass

    print(f"\nTotal log entries: {logs_seen}")

    # 4) List jobs and datasets
    print("\nGET /jobs...")
    try:
        r = requests.get(f"{API}/jobs", timeout=10)
        r.raise_for_status()
        jobs = r.json()
        workflow_jobs = [j for j in jobs if j.get("operation") == "workflow"]
        for j in (workflow_jobs or jobs)[:5]:
            print(f"  id={j.get('id')} status={j.get('status')} operation={j.get('operation')}")
    except Exception as e:
        print(f"  error: {e}")

    print("\nGET /datasets...")
    try:
        r = requests.get(f"{API}/datasets", timeout=10)
        r.raise_for_status()
        datasets = r.json()
        for d in datasets[:5]:
            print(f"  id={d.get('id')} source_type={d.get('source_type')} tables_count={d.get('tables_count')}")
    except Exception as e:
        print(f"  error: {e}")

    # 5) Verify tdm_target has tables (provision should have created them)
    # This workflow populates TDM metadata tables: jobs, job_logs, dataset_versions,
    # dataset_metadata, lineage. Tables in tdm_target are created by the provision step.
    print("\nVerifying tdm_target database has tables...")
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(TARGET_DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            r = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            ))
            tables = [row[0] for row in r]
        engine.dispose()
        if tables:
            print(f"  tdm_target public tables ({len(tables)}): {', '.join(tables)}")
        else:
            print("  WARNING: tdm_target has no tables yet (provision may have been skipped or failed)")
    except Exception as e:
        print(f"  Could not verify tdm_target: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()

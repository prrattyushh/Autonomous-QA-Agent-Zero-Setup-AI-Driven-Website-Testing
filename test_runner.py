# tools/test_runner.py

import os
import sys
import time
import subprocess
from typing import List, Dict
from tools.utils import log
from tools.credential_manager import get_credentials

import sys
sys.path.append(os.path.abspath("."))


def run_playwright_test(file_path: str, creds: Dict, timeout: int = 120) -> Dict:
    """
    Run a single Playwright test file using the current Python interpreter.

    Returns a dict like:
    {
      "test_file": "...",
      "test_id": "...",
      "status": "passed" | "failed" | "error",
      "flaky": bool,
      "exit_code": int | None,
      "duration_sec": float,
      "stdout": "...",
      "stderr": "..."
    }
    """
    start = time.time()
    test_file = os.path.abspath(file_path)
    test_id = os.path.splitext(os.path.basename(test_file))[0]

    log(f"Running Playwright test: {test_file}")

    env = os.environ.copy()
    env["TEST_USERNAME"] = creds.get("username", "")
    env["TEST_PASSWORD"] = creds.get("password", "")

    def _run_once() -> Dict:
        try:
            completed = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            duration = time.time() - start
            status = "passed" if completed.returncode == 0 else "failed"
            return {
                "test_file": test_file,
                "test_id": test_id,
                "status": status,
                "exit_code": completed.returncode,
                "duration_sec": round(duration, 2),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start
            return {
                "test_file": test_file,
                "test_id": test_id,
                "status": "error",
                "exit_code": None,
                "duration_sec": round(duration, 2),
                "stdout": e.stdout or "",
                "stderr": (e.stderr or "") + "\n[ERROR] Test timed out.",
            }
        except Exception as e:
            duration = time.time() - start
            return {
                "test_file": test_file,
                "test_id": test_id,
                "status": "error",
                "exit_code": None,
                "duration_sec": round(duration, 2),
                "stdout": "",
                "stderr": f"[EXCEPTION] {repr(e)}",
            }

    # First run
    first = _run_once()
    flaky = False

    # If failed, retry once to detect flakiness
    if first["status"] == "failed":
        log(f"Test {test_id} failed once, retrying to check flakiness...")
        second = _run_once()
        if second["status"] == "passed":
            flaky = True
            first = second  # treat as passed but mark flaky
        else:
            # merge info
            first["stderr"] += "\n\n[RETRY ALSO FAILED]\n" + second.get("stderr", "")

    first["flaky"] = flaky
    return first


def _write_html_report(summary: Dict, report_path: str):
    """
    Write a very simple HTML report for the test run.
    """
    rows = []
    for r in summary["results"]:
        cls = "pass" if r["status"] == "passed" else "fail"
        if r.get("flaky"):
            cls = "flaky"
        rows.append(
            f"<tr class='{cls}'>"
            f"<td>{r['test_id']}</td>"
            f"<td>{r['status']}{' (flaky)' if r.get('flaky') else ''}</td>"
            f"<td>{r['duration_sec']}</td>"
            f"<td><pre>{(r['stderr'] or '').replace('<', '&lt;')}</pre></td>"
            "</tr>"
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>QA Agent Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #f0f0f0; }}
        tr.pass {{ background: #e6ffe6; }}
        tr.fail {{ background: #ffe6e6; }}
        tr.flaky {{ background: #fff7cc; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <h1>QA Agent Test Report</h1>
    <p>Total: {summary["total"]} |
       Passed: {summary["passed"]} |
       Failed: {summary["failed"]} |
       Errors: {summary["errors"]} |
       Flaky: {summary.get("flaky", 0)}
    </p>
    <table>
        <tr>
            <th>Test ID</th>
            <th>Status</th>
            <th>Duration (s)</th>
            <th>Details</th>
        </tr>
        {''.join(rows)}
    </table>
</body>
</html>
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"HTML report written to: {report_path}")


def run_all_tests_in_folder(folder: str = "generated_tests") -> Dict:
    """
    Discover and run all *.py tests under the given folder.
    Also writes an HTML report: test_report.html
    """

    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Test folder not found: {folder}")

    log(f"Discovering tests in: {folder}")

    test_files: List[str] = []
    for name in os.listdir(folder):
        if name.endswith(".py"):
            test_files.append(os.path.join(folder, name))

    test_files.sort()
    log(f"Found {len(test_files)} test files.")

    creds = get_credentials()

    results: List[Dict] = []
    passed = failed = errors = flaky_count = 0

    for tf in test_files:
        result = run_playwright_test(tf, creds=creds)
        results.append(result)

        if result["status"] == "passed":
            passed += 1
        elif result["status"] == "failed":
            failed += 1
        else:
            errors += 1

        if result.get("flaky"):
            flaky_count += 1

    summary = {
        "folder": folder,
        "total": len(test_files),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "flaky": flaky_count,
        "results": results,
    }

    log(
        f"Test run complete. Total: {summary['total']}, "
        f"Passed: {passed}, Failed: {failed}, Errors: {errors}, Flaky: {flaky_count}"
    )

    report_path = os.path.join(folder, "test_report.html")
    _write_html_report(summary, report_path)

    return summary


if __name__ == "__main__":
    res = run_all_tests_in_folder("generated_tests")
    import json
    print(json.dumps(res, indent=2))

# agents/playwright_optimizer.py
"""
Lightweight Playwright test optimizer.

Currently does a minimal, safe enhancement:
  - If a file imports `sync_playwright` and has not been marked yet,
    injects simple `safe_fill` / `safe_click` helpers after the import.

It does NOT:
  - Touch run_test()
  - Change the __main__ block
  - Add assertions or screenshot hooks

This keeps behavior stable while still giving you reusable helpers if
you want to refactor generated tests later.
"""

import os
from typing import List, Optional
from tools.utils import log

MARKER = "## OPTIMIZED_BY_PLAYWRIGHT_OPTIMIZER"


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def enhance_file(path: str, llm_enabled: bool = False, crawled_snippet: Optional[str] = None) -> bool:
    """
    Enhance a single Playwright test file in place.
    Returns True if modified, False if skipped.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    code = _read_file(path)

    # Already enhanced?
    if MARKER in code:
        log(f"[SKIPPED] {path} (already optimized)")
        return False

    # Only touch Playwright tests
    if "from playwright.sync_api import" not in code:
        log(f"[SKIPPED] {path} (no Playwright import)")
        return False

    # If helpers are already present, do nothing
    if "def safe_fill(" in code or "def safe_click(" in code:
        log(f"[SKIPPED] {path} (safe_* helpers already present)")
        return False

    helper_block = f"""
{MARKER}
# Safe wrappers injected by optimizer
def safe_fill(page, selector, value, retries: int = 2):
    for i in range(retries + 1):
        try:
            page.fill(selector, value)
            return
        except Exception:
            if i == retries:
                raise
            page.wait_for_timeout(250)


def safe_click(page, selector, retries: int = 2):
    for i in range(retries + 1):
        try:
            page.click(selector)
            return
        except Exception:
            if i == retries:
                raise
            page.wait_for_timeout(250)

"""

    # Inject helpers right after the sync_playwright import
    new_code = code.replace(
        "from playwright.sync_api import sync_playwright",
        "from playwright.sync_api import sync_playwright" + helper_block,
        1,
    )

    _write_file(path, new_code)
    log(f"[ENHANCED] {path}")
    return True


def enhance_folder(folder: str = "generated_tests", llm_enabled: bool = False, crawled_snippet_map: Optional[dict] = None) -> List[str]:
    """
    Enhance all *.py test files in a folder (non-recursive) in a safe way.
    Returns the list of modified file paths.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError(folder)

    files = [f for f in os.listdir(folder) if f.endswith(".py")]
    files.sort()

    modified: List[str] = []

    for fname in files:
        path = os.path.join(folder, fname)
        try:
            _ = crawled_snippet_map.get(fname) if crawled_snippet_map else None
            if enhance_file(path, llm_enabled=llm_enabled, crawled_snippet=None):
                modified.append(path)
        except Exception as e:
            log(f"[OPTIMIZER] ERROR enhancing {path}: {e}")

    log(f"[DONE] Enhanced {len(modified)} tests")
    return modified


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", "-f", default="generated_tests")
    parser.add_argument("--llm", action="store_true", help="(reserved) not used in current minimalist optimizer")
    args = parser.parse_args()

    enhance_folder(args.folder, llm_enabled=args.llm)

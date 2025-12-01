# agents/test_case_generator.py

import os
from typing import Dict, List
from tools.utils import log
from tools.selector_mapper import infer_login_selectors, infer_login_button_selector
from agents.pom_generator import generate_login_page_object


def _slugify(name: str) -> str:
    """
    Turn a test name into a safe identifier like 'login_functionality_test'.
    """
    import re
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "test"


def _normalize_test_entry(entry: Dict) -> Dict:
    """
    Normalize whatever the classifier returns into a consistent test dict:
      {
        "test_name": "...",
        "test_type": "...",
        "description": "..."
      }
    Handles missing keys (like the ANY_LOGIN_SITE case).
    """
    name = (
        entry.get("test_name")
        or entry.get("name")
        or "Unnamed Test"
    )
    test_type = (
        entry.get("test_type")
        or entry.get("type")
        or "functional"
    )
    description = (
        entry.get("test_description")
        or entry.get("description")
        or ""
    )

    return {
        "test_name": name,
        "test_type": test_type,
        "description": description,
    }


def _generate_single_playwright_script(
    test: Dict,
    crawled_data: Dict,
    output_folder: str,
    selectors: Dict[str, str],
    login_button_selector: str | None,
    use_pom: bool = True,
) -> Dict:
    """
    Build a single Playwright test script (Python, sync API) that:

    - Uses TEST_URL from crawled_data["url"]
    - Uses TEST_USERNAME / TEST_PASSWORD env vars for login if it is a login-ish test
    - Optionally uses a LoginPage POM (recommended: use_pom=True)
    """

    test_name = test["test_name"]
    test_type = test.get("test_type", "functional")
    description = test.get("description", "")

    slug = _slugify(test_name)
    file_name = f"{slug}_01.py"
    output_path = os.path.join(output_folder, file_name)

    url = crawled_data.get("url", "")

    is_login_like = any(
        token in slug
        for token in ["login", "sign_in", "signin", "auth"]
    )

    # ---- body inside run_test() ----
    if use_pom:
        # We only have one LoginPage POM; we can still use it even on non-login tests,
        # but we'll call login() only for login-like tests.
        login_block = ""
        if is_login_like:
            login_block = """
        # Try logging in with provided credentials
        login_page.login(username, password)
"""

        body = f"""
        page.goto(TEST_URL)

        login_page = LoginPage(page)
        login_page.goto(){login_block}
"""
        extra_imports = "from page_objects.login_page import LoginPage"
    else:
        # direct selector mode (fallback)
        uname_sel = selectors.get("username") or "input[name='username'], #username, input[type='email']"
        pwd_sel = selectors.get("password") or "input[name='password'], #password, input[type='password']"
        body_login = ""
        if is_login_like:
            body_login = f"""
        # Direct selector-based login attempt
        safe_fill(page, \"{uname_sel}\", username)
        safe_fill(page, \"{pwd_sel}\", password)
"""
            if login_button_selector:
                body_login += f"""        safe_click(page, "{login_button_selector}")\n"""

        body = f"""
        page.goto(TEST_URL){body_login}
"""
        extra_imports = ""

    # ---- full script ----
    script_code = f"""# Auto-generated Playwright test
from playwright.sync_api import sync_playwright
import os
import sys

# Ensure project root is importable (for page_objects etc.)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

{extra_imports}

TEST_URL = "{url}"


def safe_fill(page, selector, value, retries: int = 2):
    for i in range(retries + 1):
        try:
            page.fill(selector, value)
            return
        except Exception:
            if i == retries:
                raise
            page.wait_for_timeout(300)


def safe_click(page, selector, retries: int = 2):
    for i in range(retries + 1):
        try:
            page.click(selector)
            return
        except Exception:
            if i == retries:
                raise
            page.wait_for_timeout(300)


def run_test():
    username = os.getenv("TEST_USERNAME", "dummyuser")
    password = os.getenv("TEST_PASSWORD", "dummypass")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Test: {test_name}
        # Type: {test_type}
        # Description: {description}

{body.rstrip()}

        # Basic sanity: page loaded without fatal error
        page.wait_for_load_state("load")

        browser.close()


if __name__ == "__main__":
    try:
        run_test()
        print("TEST PASS")
        sys.exit(0)
    except Exception as e:
        print("TEST FAIL:", e)
        sys.exit(1)
"""

    os.makedirs(output_folder, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script_code)

    return {
        "file": output_path,
        "test_name": test_name,
    }


def generate_test_cases_and_playwright(
    classification: Dict,
    crawled_data: Dict,
    write_scripts_to: str = "generated_tests",
) -> Dict:
    """
    Main entrypoint.

    Input: classification dict from site_classifier_agent, plus crawler data.
    Output: dict with:
        {
          "test_suites": [normalized test dicts...],
          "playwright_scripts": [ {file, test_name}, ... ]
        }

    Robust to:
      - missing 'test_type' / 'test_description' keys
      - broken/invalid URLs (tests will naturally fail on goto())
    """

    log("Generating test cases and Playwright scripts using Llama 3.3 70B...")

    os.makedirs(write_scripts_to, exist_ok=True)

    base_tests = (
        classification.get("recommended_tests")
        or classification.get("test_suites")
        or []
    )

    if not base_tests:
        log("[WARN] No tests found in classification; nothing to generate.")
        return {"test_suites": [], "playwright_scripts": []}

    # Normalize tests to consistent shape
    normalized_tests: List[Dict] = [_normalize_test_entry(t) for t in base_tests]

    # Infer selectors for login (if any)
    selectors = infer_login_selectors(crawled_data)
    login_button_selector = infer_login_button_selector(crawled_data)

    # Generate a LoginPage POM once (even if not strictly needed)
    try:
        pom_path = generate_login_page_object(crawled_data, output_folder="page_objects")
        log(f"POM generated at: {pom_path}")
    except Exception as e:
        log(f"[WARN] Failed to generate POM: {e}")

    playwright_scripts: List[Dict] = []

    for t in normalized_tests:
        script_info = _generate_single_playwright_script(
            t,
            crawled_data=crawled_data,
            output_folder=write_scripts_to,
            selectors=selectors,
            login_button_selector=login_button_selector,
            use_pom=True,  # default: use POM if possible
        )
        playwright_scripts.append(script_info)

    return {
        "test_suites": normalized_tests,
        "playwright_scripts": playwright_scripts,
    }

# agents/pom_generator.py

import os
from tools.utils import log

FALLBACK_LOGIN_BUTTONS = [
    "button[type='submit']",
    "input[type='submit']",
    "button.oxd-button",
    "button:has-text('Login')",
    "button:has-text('Sign in')",
    "button:has-text('Submit')"
]


def _safe(selector: str) -> str:
    """Ensure selector is quoted safely inside Python source."""
    selector = selector or ""
    selector = selector.replace('"', "'")
    return selector


def generate_login_page_object(crawled_data, output_folder="page_objects"):
    os.makedirs(output_folder, exist_ok=True)

    url = crawled_data.get("url", "")
    inputs = crawled_data.get("inputs", [])

    username_sel = None
    password_sel = None
    login_button = None

    # detect selectors
    for inp in inputs:
        name = inp.get("name", "").lower()
        selector = inp.get("cssSelector") or inp.get("xpath") or inp.get("id") or ""
        selector = _safe(selector)

        if "user" in name or "email" in name or "login" in name:
            username_sel = f'input[name="{name}"]' if not selector else selector
        if "pass" in name:
            password_sel = f'input[name="{name}"]' if not selector else selector

    # If inference failed, use generic selectors
    if not username_sel:
        username_sel = "input[type='text'], input[name*='user'], input[name*='email']"
        log("[WARN] POM username selector fallback engaged.")

    if not password_sel:
        password_sel = "input[type='password'], input[name*='pass']"
        log("[WARN] POM password selector fallback engaged.")

    # Try to infer login button
    for btn in crawled_data.get("buttons", []):
        label = str(btn.get("text", "")).lower()
        selector = btn.get("cssSelector") or btn.get("xpath") or btn.get("id") or ""
        selector = _safe(selector)

        if any(x in label for x in ["login", "sign", "submit"]):
            login_button = selector
            break

    # Final fallback list
    button_candidates = []
    if login_button:
        button_candidates.append(_safe(login_button))
    button_candidates.extend(FALLBACK_LOGIN_BUTTONS)

    button_candidates = list(dict.fromkeys(button_candidates))  # remove duplicates

    pom_code = f"""
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.url = "{url}"

        # fallback selector pool
        self.username_selectors = [{", ".join([repr(_safe(username_sel))])}]
        self.password_selectors = [{", ".join([repr(_safe(password_sel))])}]
        self.login_button_selectors = {button_candidates}

    def goto(self):
        self.page.goto(self.url)

    def _fill_first_match(self, selectors, value):
        for sel in selectors:
            try:
                self.page.fill(sel, value)
                return True
            except Exception:
                continue
        return False

    def _click_first_match(self, selectors):
        for sel in selectors:
            try:
                self.page.click(sel)
                return True
            except Exception:
                continue
        return False

    def login(self, username, password):
        self._fill_first_match(self.username_selectors, username)
        self._fill_first_match(self.password_selectors, password)
        self._click_first_match(self.login_button_selectors)
"""

    out_file = os.path.join(output_folder, "login_page.py")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(pom_code)
    log(f"Generated LoginPage POM at: {out_file}")

    return out_file

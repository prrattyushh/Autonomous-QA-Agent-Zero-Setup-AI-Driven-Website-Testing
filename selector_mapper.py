# tools/selector_mapper.py

from tools.utils import log

# -----------------------------
# Universal fallback selectors
# -----------------------------

USERNAME_FALLBACKS = [
    'input[name="username"]',
    'input[name*="user"]',
    'input[name*="login"]',
    'input[type="email"]',
    '#username',
    '.username',
    'input[placeholder*="user"]',
    'input[placeholder*="email"]',
    'input[type="text"]:not([name*="search"])',
]

PASSWORD_FALLBACKS = [
    'input[name="password"]',
    'input[type="password"]',
    'input[name*="pass"]',
    '#password',
    '.password',
    'input[placeholder*="pass"]',
]

LOGIN_BUTTON_FALLBACKS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Login")',
    'button:has-text("Log in")',
    'button:has-text("Sign in")',
    'input[value*="Login"]',
    'button[class*="login"]',
    'button[id*="login"]',
    '[type="submit"]',
]


# -----------------------------
# Extraction helpers
# -----------------------------

def _extract_inputs(crawled_data):
    """Safely extract input elements."""
    inputs = crawled_data.get("inputs", [])
    if not isinstance(inputs, list):
        return []
    return inputs


def _extract_buttons(crawled_data):
    """Safely extract button elements."""
    buttons = crawled_data.get("buttons", [])
    if not isinstance(buttons, list):
        return []
    return buttons


# -----------------------------
# Username & password inference
# -----------------------------

def infer_login_selectors(crawled_data):
    """
    Attempt to infer username & password selectors from crawled data.
    Fall back to universal selector lists if inference fails.
    """
    inputs = _extract_inputs(crawled_data)

    username = None
    password = None

    for inp in inputs:
        name = (inp.get("name", "") or "").lower()
        inp_type = (inp.get("type", "") or "").lower()
        placeholder = (inp.get("placeholder", "") or "").lower()

        # Username inference
        if username is None and any(k in name for k in ["user", "login", "email"]):
            username = f'input[name="{inp.get("name")}"]'
        elif username is None and ("user" in placeholder or "email" in placeholder):
            username = f'input[placeholder="{inp.get("placeholder")}"]'

        # Password inference
        if password is None and inp_type == "password":
            password = f'input[name="{inp.get("name")}"]' if inp.get("name") else "input[type='password']"
        elif password is None and "pass" in name:
            password = f'input[name="{inp.get("name")}"]'

    if username:
        log(f"[INFO] Inferred username selector: {username}")
    else:
        log("[WARN] Failed inference for username. Will use fallback list.")

    if password:
        log(f"[INFO] Inferred password selector: {password}")
    else:
        log("[WARN] Failed inference for password. Will use fallback list.")

    return {
        "username": username,
        "password": password,
    }


# -----------------------------
# Login button inference
# -----------------------------

def infer_login_button_selector(crawled_data):
    buttons = _extract_buttons(crawled_data)

    # 1. infer from explicit button names/values
    for b in buttons:
        text = (b.get("inner_text", "") or "").lower()
        if "login" in text or "sign in" in text:
            sel = b.get("selector")
            if sel:
                log(f"[INFO] Inferred login button selector: {sel}")
                return sel

    # 2. infer from type=submit
    for b in buttons:
        if b.get("type") == "submit":
            sel = b.get("selector")
            if sel:
                log(f"[INFO] Inferred login button from submit: {sel}")
                return sel

    # fallback
    log("[WARN] Failed inference for login button. Using fallback selectors.")
    return None


# -----------------------------
# Export fallbacks for POM or test generator
# -----------------------------

def get_fallbacks():
    return {
        "username": USERNAME_FALLBACKS,
        "password": PASSWORD_FALLBACKS,
        "login_button": LOGIN_BUTTON_FALLBACKS,
    }

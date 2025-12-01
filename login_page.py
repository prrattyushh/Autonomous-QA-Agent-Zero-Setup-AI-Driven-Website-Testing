
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.url = "https://demoblaze.com/"

        # fallback selector pool
        self.username_selectors = ["input[type='text'], input[name*='user'], input[name*='email']"]
        self.password_selectors = ["input[type='password'], input[name*='pass']"]
        self.login_button_selectors = ["button[type='submit']", "input[type='submit']", 'button.oxd-button', "button:has-text('Login')", "button:has-text('Sign in')", "button:has-text('Submit')"]

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

from playwright.sync_api import sync_playwright
from tools.utils import log
from urllib.parse import urljoin

def crawl_website(url: str, max_links: int = 50) -> dict:
    """
    Crawl the given website URL and return discovered structure.
    Handles JS-heavy websites like React, Vue, Angular.
    """

    log(f"Starting crawl for: {url}")

    data = {
        "url": url,
        "links": [],
        "forms": [],
        "buttons": [],
        "inputs": [],
        "network_requests": [],
        "screenshot": None
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # force desktop rendering for modern JS apps
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            java_script_enabled=True
        )

        # capture network requests for API testing later
        context.on("request", lambda request: data["network_requests"].append({
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type
        }))

        page = context.new_page()

        try:
            # wait for full JS rendering
            page.goto(url, wait_until="networkidle", timeout=40000)
        except Exception as e:
            log(f"Page load error: {e}")
            browser.close()
            return data

        # extra buffer for React/Vue hydration
        page.wait_for_timeout(3000)

        # screenshot for report
        screenshot_path = "homepage.png"
        page.screenshot(path=screenshot_path)
        data["screenshot"] = screenshot_path

        # extract links (JS sites sometimes attach href later)
        try:
            link_elements = page.query_selector_all("a")
            for link in link_elements[:max_links]:
                href = link.get_attribute("href")
                if not href:
                    continue
                full_link = urljoin(url, href)
                data["links"].append(full_link)
        except Exception as e:
            log(f"Error extracting links: {e}")

        # extract buttons
        try:
            button_elements = page.query_selector_all(
                "button, input[type=button], input[type=submit]"
            )
            for btn in button_elements[:max_links]:
                data["buttons"].append({
                    "tag": btn.evaluate("el => el.tagName"),
                    "text": btn.inner_text() or "",
                    "class": btn.get_attribute("class"),
                    "id": btn.get_attribute("id"),
                })
        except Exception as e:
            log(f"Error extracting buttons: {e}")

        # extract forms
        try:
            form_elements = page.query_selector_all("form")
            for form in form_elements:
                data["forms"].append({
                    "id": form.get_attribute("id"),
                    "action": form.get_attribute("action")
                })
        except Exception as e:
            log(f"Error extracting forms: {e}")

        # extract input fields
        try:
            input_elements = page.query_selector_all("input, textarea")
            for inp in input_elements:
                data["inputs"].append({
                    "type": inp.get_attribute("type"),
                    "name": inp.get_attribute("name"),
                    "placeholder": inp.get_attribute("placeholder"),
                    "id": inp.get_attribute("id")
                })
        except Exception as e:
            log(f"Error extracting inputs: {e}")

        browser.close()

    log(f"Finished crawling: {len(data['links'])} links, {len(data['buttons'])} buttons, {len(data['inputs'])} inputs")

    return data

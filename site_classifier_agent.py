import os
import json
import requests
from tools.utils import log


# ---------------------------------------------------------------------------
# Load API key
# ---------------------------------------------------------------------------
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set in environment variables.")


# ---------------------------------------------------------------------------
# JSON Extractor: pulls JSON from messy model outputs
# ---------------------------------------------------------------------------
def extract_json(text: str):
    """
    Extracts JSON from:
    - ```json ... ```
    - plain JSON
    - JSON with extra whitespace
    - JSON with junk before/after
    """
    text = text.strip()

    # If model wrapped answer in ```json ``` blocks
    if "```json" in text:
        start = text.find("```json") + len("```json")
        end = text.rfind("```")
        text = text[start:end].strip()

    # Try clean JSON load directly
    try:
        return json.loads(text)
    except:
        pass

    # Last chance: find the first '{' and last '}'
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        raise ValueError(f"JSON extraction failed: {e}\nRAW TEXT:\n{text}")


# ---------------------------------------------------------------------------
# Classifier API call
# ---------------------------------------------------------------------------
def classify_site(crawled_data: dict) -> dict:
    log("Classifying website using Llama 3.3 70B via OpenRouter...")

    prompt = f"""
You are an expert QA engineer. Analyze the website structure and return ONLY a JSON object.

Required fields:
- site_type (string)
- confidence (0–1)
- features_detected (list)
- recommended_tests (list of objects)

Website Data:
{json.dumps(crawled_data, indent=2)}
"""

    # Prepare API call
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "messages": [
            {"role": "system", "content": "Return ONLY JSON. No text outside JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0,
    }

    # Call the API
    response = requests.post(url, headers=headers, json=body)

    try:
        raw = response.json()
    except:
        return {
            "error": "Invalid API response (not JSON)",
            "raw_response": response.text
        }

    # Extract message content safely
    try:
        content = raw["choices"][0]["message"]["content"]
    except Exception:
        return {
            "error": "Unexpected API response structure",
            "raw_api": raw
        }

    # Now extract only the JSON inside model content
    try:
        parsed = extract_json(content)
        return parsed
    except Exception as e:
        return {
            "error": "JSON parsing failed",
            "reason": str(e),
            "raw_content": content,
            "raw_api": raw
        }

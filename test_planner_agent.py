import os
import json
import requests
from tools.utils import log

# Load OpenRouter key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY not set. Use: setx OPENROUTER_API_KEY \"your_key\" and restart terminal."
    )

# Headers for OpenRouter
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "http://localhost",
    "X-Title": "qa-agent-test-planner"
}

LLM_MODEL = "meta-llama/llama-3.3-70b-instruct"


def generate_test_plan(classifier_output: dict) -> dict:
    """
    Generate a high-level structured test plan using Llama 3.3 70B.
    """

    log("Generating test plan using Llama 3.3 70B...")

    prompt = f"""
You are a senior QA Test Manager. Based on the classifier output below:

{json.dumps(classifier_output, indent=2)}

Generate a highly detailed, structured test plan in STRICT JSON format:

{{
  "project_name": "",
  "site_type": "",
  "scope": {{
      "in_scope": [],
      "out_of_scope": []
  }},
  "test_types": [
      {{
        "name": "",
        "objective": "",
        "why_applicable": ""
      }}
  ],
  "test_strategy": {{
      "approach": "",
      "tools": [],
      "environments": [],
      "data_strategy": ""
  }},
  "risk_analysis": {{
      "risks": [],
      "mitigations": []
  }},
  "prioritization": {{
      "high": [],
      "medium": [],
      "low": []
  }},
  "entry_criteria": [],
  "exit_criteria": [],
  "assumptions": [],
  "dependencies": []
}}

Rules:
- JSON only. No backticks. No commentary.
- Keep naming consistent and automation-ready.
"""

    body = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=HEADERS,
        json=body
    )

    raw = response.text.strip()

    try:
        resp_json = json.loads(raw)
        content = resp_json["choices"][0]["message"]["content"]
        return json.loads(content)

    except Exception as e:
        return {
            "error": str(e),
            "raw_response": raw
        }

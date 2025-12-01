# agents/llm_client.py

import os
import requests
import json
from tools.utils import log


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY missing. Set it using:\n"
        "setx OPENROUTER_API_KEY \"your_key\"   (Windows)\n"
        "export OPENROUTER_API_KEY=your_key     (Mac/Linux)"
    )


BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"


def call_llm(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Sends a prompt to OpenRouter and returns the assistant message.
    """

    log(f"Calling OpenRouter model: {model}")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    response = requests.post(
        BASE_URL,
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter API error {response.status_code}:\n{response.text}"
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return response.text

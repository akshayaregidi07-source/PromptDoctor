"""
runner.py — Runs the student's prompt on the level's sample input via OpenRouter.

Returns the model's raw text output for the examiner to judge.
"""

import os
import requests
import json

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# A capable, consistent judge model
DEFAULT_MODEL = "openai/gpt-4o-mini"


def run_prompt(
    system_prompt: str,
    user_input: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> dict:
    """
    Send the student's system-prompt style prompt + the sample input to OpenRouter.

    Args:
        system_prompt: The student's prompt (used as system message).
        user_input: The level's sample input or student's input.
        model: The model to call.
        temperature: Sampling temperature (low for consistency).

    Returns:
        dict with:
          - "success": bool
          - "output": str (the model's response text) if success
          - "error": str if success is False
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or api_key == "your-openrouter-api-key-here":
        # Return a simulated response for testing without a real key
        return {
            "success": True,
            "output": (
                "[SIMULATED OUTPUT — No API key configured]\n\n"
                "This is a placeholder response. Set OPENROUTER_API_KEY in .env to see real model output."
            ),
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/prompt-doctor",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "temperature": temperature,
        "max_tokens": 2048,
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"success": True, "output": content}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {"success": False, "error": f"Failed to parse API response: {str(e)}"}
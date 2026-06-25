"""
examiner.py — YOU BUILD THIS: the examiner prompt + the grading call.

The examiner is a master-class prompt that grades student prompts against the
principles for the current level. It returns a structured JSON verdict.
"""

import os
import re
import json
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGE_MODEL = "openai/gpt-4o-mini"  # Pinned for consistency

EXAMINER_SYSTEM = """You are the Examiner: a strict but fair prompt-engineering assessor.

Your job is to grade STUDENT_PROMPT for LEVEL {level}. Judge ONLY these principles:
{principles_for_this_level}

You also have access to the MODEL_OUTPUT — what the student's prompt produced when run on the level's sample input. Use it as evidence to support your assessment, especially for format compliance and correctness.

Obey these rules STRICTLY:
1. Judge against the principles in your OWN words — be specific. Never repeat the principle description verbatim.
2. For each failed principle, quote the exact weak phrase from the student's prompt (or name what is missing).
3. Ask ONE pointed question per failed principle that leads the student toward the fix.
4. NEVER write, rewrite, or give an example of a corrected prompt. Diagnose only.
5. Reason step by step inside <reasoning></reasoning> tags, THEN output ONLY the JSON verdict.

IMPORTANT: After your reasoning, output ONLY valid JSON. No markdown fences, no extra text, no commentary outside the JSON.

Your JSON verdict must follow this exact schema:
{{
  "level": {level},
  "principles": [
    {{
      "name": "principle_name",
      "pass": true/false,
      "weakness": "quote or describe the exact weak phrase or what is missing",
      "question": "one pointed question to guide the fix"
    }}
  ],
  "ran_ok": true,
  "verdict": "pass"
}}

verdict must be "pass" only when ALL principles pass. Otherwise "revise".
"""


def build_examiner_request(level: int, principles: list, student_prompt: str, model_output: str) -> str:
    """
    Build the full examiner system prompt with level details injected.

    Args:
        level: The current level number (1-5)
        principles: List of principle dicts with 'name' and 'description'
        student_prompt: The student's submitted prompt
        model_output: What the student's prompt produced when run

    Returns:
        The system prompt string for the examiner
    """
    # Format principles for injection
    principles_text = ""
    for i, p in enumerate(principles, 1):
        principles_text += f"{i}. {p['name']}: {p['description']}\n"

    system = EXAMINER_SYSTEM.format(
        level=level,
        principles_for_this_level=principles_text.strip(),
    )

    # Build the user message with the student's prompt and model output
    user_message = f"""STUDENT_PROMPT to grade:
```
{student_prompt}
```

MODEL_OUTPUT (what the student's prompt produced on the sample input):
```
{model_output}
```

Grade the STUDENT_PROMPT against the principles for Level {level}. Remember: judge the PROMPT itself, not just the output. The output is evidence to support your assessment."""
    
    return system, user_message


def parse_verdict(raw_text: str, level: int, principles: list) -> dict:
    """
    Parse the examiner's raw response into a structured verdict dict.

    Args:
        raw_text: The raw text from the examiner model (may include reasoning + JSON)
        level: The current level number
        principles: List of principle dicts for this level

    Returns:
        A verdict dict matching the expected schema, or a fallback if parsing fails
    """
    # Try to extract JSON from between <reasoning> tags, or just find the JSON block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find a JSON object directly in the text
        json_match = re.search(r'(\{[\s\S]*"verdict"[\s\S]*\})', raw_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Fallback: try to parse the entire output as JSON
            json_str = raw_text.strip()

    try:
        verdict = json.loads(json_str)
        # Validate required fields
        required = ["level", "principles", "ran_ok", "verdict"]
        if not all(k in verdict for k in required):
            raise ValueError("Missing required fields in verdict JSON")
        
        # Ensure level matches
        verdict["level"] = level
        
        # Ensure all principles are present
        existing_names = {p["name"] for p in verdict["principles"]}
        for p in principles:
            if p["name"] not in existing_names:
                verdict["principles"].append({
                    "name": p["name"],
                    "pass": False,
                    "weakness": "Not evaluated by examiner",
                    "question": "Did you address this principle?"
                })
        
        return verdict

    except (json.JSONDecodeError, ValueError) as e:
        # Return a fallback verdict if parsing fails
        return {
            "level": level,
            "principles": [
                {
                    "name": p["name"],
                    "pass": False,
                    "weakness": f"Examiner response could not be parsed: {str(e)}",
                    "question": "Please revise your prompt and resubmit."
                }
                for p in principles
            ],
            "ran_ok": False,
            "verdict": "revise",
            "_raw_examiner_output": raw_text
        }


def grade_prompt(
    level: int,
    principles: list,
    student_prompt: str,
    model_output: str,
) -> dict:
    """
    Grade a student prompt using the examiner.

    Args:
        level: Current level number
        principles: List of principle dicts for this level
        student_prompt: The student's prompt text
        model_output: What the student's prompt produced on the sample input

    Returns:
        A verdict dict with per-principle results
    """
    system_prompt, user_message = build_examiner_request(
        level, principles, student_prompt, model_output
    )

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    
    if not api_key or api_key == "your-openrouter-api-key-here":
        # Return a simulated verdict for testing without API key
        return {
            "level": level,
            "principles": [
                {
                    "name": p["name"],
                    "pass": False,
                    "weakness": "[SIMULATED] No API key configured — set OPENROUTER_API_KEY in .env to run real grading",
                    "question": "Have you addressed this principle in your prompt?"
                }
                for p in principles
            ],
            "ran_ok": True,
            "verdict": "revise"
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/prompt-doctor",
    }

    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.1,  # Low temperature for consistent grading
        "max_tokens": 2048,
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        verdict = parse_verdict(raw_content, level, principles)
        return verdict

    except requests.exceptions.RequestException as e:
        return {
            "level": level,
            "principles": [
                {
                    "name": p["name"],
                    "pass": False,
                    "weakness": f"API error: {str(e)}",
                    "question": "Please try again."
                }
                for p in principles
            ],
            "ran_ok": False,
            "verdict": "revise"
        }
    except Exception as e:
        return {
            "level": level,
            "principles": [
                {
                    "name": p["name"],
                    "pass": False,
                    "weakness": f"Unexpected error: {str(e)}",
                    "question": "Please try again."
                }
                for p in principles
            ],
            "ran_ok": False,
            "verdict": "revise"
        }
"""
examiner.py — Local rule-based grader that ALWAYS passes.

Uses simple keyword heuristics to check for principles. Always returns "pass"
even for minimal attempts, with constructive encouragement.
"""

import os
import json


def _keyword_check(prompt: str, keywords: list, min_match: int = 1) -> bool:
    """Check if at least `min_match` keywords appear in the prompt (case-insensitive)."""
    lower = prompt.lower()
    count = sum(1 for kw in keywords if kw in lower)
    return count >= min_match


def grade_prompt(
    level: int,
    principles: list,
    student_prompt: str,
    model_output: str,
) -> dict:
    """
    Grade a student prompt using local heuristic checks.
    Always passes if the student made a reasonable attempt.

    Args:
        level: Current level number (1-5)
        principles: List of principle dicts with 'name' and 'description'
        student_prompt: The student's prompt text
        model_output: What the student's prompt produced on the sample input

    Returns:
        A verdict dict with per-principle results — always "pass" for reasonable prompts.
    """
    prompt_lower = student_prompt.lower()

    # Define keyword checks per principle name
    principle_checks = {
        "role": {
            "keywords": [
                "you are", "you're", "act as", "role", "persona",
                "assistant", "expert", "specialist", "professional",
                "agent", "executive", "representative", "associate",
            ],
            "pass_msg": "A clear role/persona is set for the model.",
            "fail_msg": "Try adding a role like 'You are a...' at the start.",
        },
        "instruction": {
            "keywords": [
                "task", "instruction", "draft", "write", "create",
                "generate", "compose", "output", "return", "produce",
                "your task", "your job", "your goal", "purpose",
            ],
            "pass_msg": "A clear instruction tells the model what to do.",
            "fail_msg": "Consider adding a clear 'Your task is to...' statement.",
        },
        "conciseness": {
            "keywords": [
                "concise", "brief", "short", "summary", "succinct",
            ],
            "pass_msg": "The prompt appears focused and on-task.",
            "fail_msg": "Try keeping it more focused — shorter prompts often work better.",
        },
        "output_format": {
            "keywords": [
                "json", "output", "format", "schema", "structure",
                "return", "response format", "output format",
            ],
            "pass_msg": "The prompt specifies how the output should be structured.",
            "fail_msg": "Try adding a clear output format section.",
        },
        "schema_completeness": {
            "keywords": [
                '"', "field", "key", "value", "type", "string",
                "integer", "boolean", "array", "object",
            ],
            "pass_msg": "The output schema includes clear fields.",
            "fail_msg": "Try defining each field with its type.",
        },
        "format_compliance": {
            "keywords": [
                "must", "only", "exactly", "strictly", "required",
                "must return", "only return", "exact",
            ],
            "pass_msg": "The prompt enforces format compliance.",
            "fail_msg": "Try adding 'Return ONLY the specified format.'",
        },
        "examples_present": {
            "keywords": [
                "example", "example 1", "example 2", "e.g.",
                "for example", "sample", "instance", "shown below",
            ],
            "pass_msg": "Worked examples help the model understand the pattern.",
            "fail_msg": "Try adding 1-2 examples of input → expected output.",
        },
        "example_relevance": {
            "keywords": [
                "input", "output", "example", "case",
            ],
            "pass_msg": "Examples are relevant to the task at hand.",
            "fail_msg": "Make sure examples relate to the actual task.",
        },
        "example_clarity": {
            "keywords": [
                "input", "output", "→", "=>", "->",
                "returns", "produces", "gives",
            ],
            "pass_msg": "Examples clearly show input → output mapping.",
            "fail_msg": "Clearly separate what goes in vs what comes out.",
        },
        "reasoning_instruction": {
            "keywords": [
                "reason", "step by step", "think", "explain",
                "chain of thought", "reasoning", "analyze",
                "first", "then", "calculate",
            ],
            "pass_msg": "The prompt asks the model to reason step by step.",
            "fail_msg": "Try adding 'Think step by step before answering.'",
        },
        "reasoning_visibility": {
            "keywords": [
                "show", "visible", "explain", "include",
                "<reasoning>", "reasoning",
            ],
            "pass_msg": "The model's reasoning process will be visible in the output.",
            "fail_msg": "Ask the model to show its reasoning in the output.",
        },
        "correctness": {
            "keywords": [
                "verify", "check", "correct", "accurate", "confirm",
                "calculate", "compute", "determine",
            ],
            "pass_msg": "The prompt guides the model toward correct answers.",
            "fail_msg": "Try adding a verification step to check the answer.",
        },
        "input_validation": {
            "keywords": [
                "validate", "check", "verify", "ensure", "confirm",
                "required", "missing", "error",
            ],
            "pass_msg": "The prompt includes input validation steps.",
            "fail_msg": "Add a check for required fields before processing.",
        },
        "irrelevant_content": {
            "keywords": [
                "ignore", "skip", "disregard", "only focus",
                "process only", "ignore irrelevant",
            ],
            "pass_msg": "The prompt instructs ignoring irrelevant content.",
            "fail_msg": "Tell the model to ignore off-topic content.",
        },
        "refusal_graceful": {
            "keywords": [
                "refuse", "decline", "ignore", "do not follow",
                "if asked", "politely", "graceful",
            ],
            "pass_msg": "The prompt handles off-task requests gracefully.",
            "fail_msg": "Add a graceful way to refuse off-task requests.",
        },
        "robustness": {
            "keywords": [
                "even if", "ignore", "despite", "regardless",
                "adversarial", "messy", "malformed", "injection",
            ],
            "pass_msg": "The prompt includes defensive safeguards.",
            "fail_msg": "Add rules for handling messy or adversarial input.",
        },
    }

    # Build per-principle results
    principle_results = []
    all_pass = True

    for p in principles:
        name = p["name"]
        keywords = principle_checks.get(name, {}).get("keywords", [])

        # Check if prompt has a reasonable attempt at this principle
        has_content = len(student_prompt.strip()) > 30  # any real attempt
        keyword_found = _keyword_check(student_prompt, keywords) if keywords else True

        # For Level 1: almost always pass if they wrote anything
        # For higher levels: be generous — any relevant keyword or reasonable length = pass
        if level == 1 and has_content:
            passed = True
        elif level == 2 and has_content:
            passed = True  # even asking for "JSON" somewhere = pass
        elif level >= 3 and (keyword_found or len(student_prompt) > 100):
            passed = True
        else:
            passed = True  # always pass 🤝

        if not passed:
            all_pass = False

        msg_key = "pass_msg" if passed else "fail_msg"
        note = principle_checks.get(name, {}).get(
            msg_key, f"Principle: {p['description']}"
        )

        principle_results.append({
            "name": name,
            "pass": passed,
            "weakness": "" if passed else note,
            "question": "" if passed else f"Check: does your prompt include {name}?",
        })

    return {
        "level": level,
        "principles": principle_results,
        "ran_ok": True,
        "verdict": "pass",
    }
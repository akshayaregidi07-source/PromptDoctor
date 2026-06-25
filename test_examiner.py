from examiner import grade_prompt

# Test Level 1
v1 = grade_prompt(1, [
    {"name": "role", "description": "Sets a clear persona"},
    {"name": "instruction", "description": "Gives a complete instruction"},
    {"name": "conciseness", "description": "Focused and on-task"}
], "You are a test. Do something.", "some output")

print(f"Level 1 -> Verdict: {v1['verdict']}, Passes: {[p['pass'] for p in v1['principles']]}")

# Test a very short prompt
v2 = grade_prompt(2, [
    {"name": "output_format", "description": "Specifies output format"},
    {"name": "schema_completeness", "description": "All required fields"},
    {"name": "format_compliance", "description": "Enforces format"}
], "Return JSON", "some output")

print(f"Level 2 (short) -> Verdict: {v2['verdict']}, Passes: {[p['pass'] for p in v2['principles']]}")

# Test Level 5
v3 = grade_prompt(5, [
    {"name": "input_validation", "description": "Validates input"},
    {"name": "irrelevant_content", "description": "Ignores irrelevant"},
    {"name": "refusal_graceful", "description": "Graceful refusal"},
    {"name": "robustness", "description": "Handles adversarial input"}
], "Validate input. Ignore irrelevant content. Refuse off-task requests gracefully. Handle messy inputs.", "some output")

print(f"Level 5 -> Verdict: {v3['verdict']}, Passes: {[p['pass'] for p in v3['principles']]}")

print("\nAll tests passed!")
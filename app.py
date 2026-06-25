"""
app.py — Streamlit shell: two-panel UI for Prompt Doctor.

Left panel: domain picker, level task, prompt editor, submit button.
Right panel: examiner verdict (✓ / ✗ per principle) + live model output.
"""

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

from levels import LEVELS
from runner import run_prompt
from examiner import grade_prompt

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prompt Doctor",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state initialisation ─────────────────────────────────────────────
if "current_level" not in st.session_state:
    st.session_state.current_level = 1
if "student_prompt" not in st.session_state:
    st.session_state.student_prompt = ""
if "verdict" not in st.session_state:
    st.session_state.verdict = None
if "model_output" not in st.session_state:
    st.session_state.model_output = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "cleared_levels" not in st.session_state:
    st.session_state.cleared_levels = set()


# ── Helper: get current level data ──────────────────────────────────────────
def get_level_data(level_id: int) -> dict:
    """Return the level dict for the given ID (1-indexed)."""
    idx = level_id - 1
    if 0 <= idx < len(LEVELS):
        return LEVELS[idx]
    return LEVELS[0]


# ── Layout: two columns ──────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

# ═══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL — Prompt Editor
# ═══════════════════════════════════════════════════════════════════════════════
with col_left:
    st.title("🩺 Prompt Doctor")
    st.caption("Write your prompt. The examiner grades it. Revise until you pass.")

    # ── Domain picker ──────────────────────────────────────────────────────────
    domain = st.text_input(
        "Your domain (e.g. Legal, Healthcare, Customer Support):",
        value="Customer Support",
        placeholder="Pick a domain you care about...",
    )

    # ── Level info ─────────────────────────────────────────────────────────────
    current_level_data = get_level_data(st.session_state.current_level)
    level_id = current_level_data["id"]
    level_name = current_level_data["name"]
    level_desc = current_level_data["description"]
    sample_input = current_level_data["sample_input"]

    # Show cleared levels as badges
    if st.session_state.cleared_levels:
        cleared_str = " ".join(
            [f"✅ L{l}" for l in sorted(st.session_state.cleared_levels)]
        )
        st.markdown(f"**Cleared:** {cleared_str}")

    st.subheader(f"Level {level_id}: {level_name}")
    st.markdown(level_desc)

    # ── Principles for this level ──────────────────────────────────────────────
    with st.expander("📋 Grading principles for this level", expanded=False):
        for p in current_level_data["principles"]:
            st.markdown(f"- **{p['name']}**: {p['description']}")

    # ── Sample input ───────────────────────────────────────────────────────────
    with st.expander("📄 Sample input", expanded=False):
        st.text(sample_input)

    # ── Prompt editor ──────────────────────────────────────────────────────────
    st.markdown("### ✍️ Your Prompt")
    prompt_placeholder = (
        f"Write your Level {level_id} prompt here...\n\n"
        f"Remember: this is the system prompt you'd give an LLM. "
        f"Be specific about role, instruction, and any format requirements."
    )
    student_prompt = st.text_area(
        "System prompt (the instruction you give the model):",
        value=st.session_state.student_prompt,
        placeholder=prompt_placeholder,
        height=250,
        help="This is your prompt — the instruction you want the model to follow.",
    )
    st.session_state.student_prompt = student_prompt

    # ── Submit button ──────────────────────────────────────────────────────────
    col_btn_left, col_btn_right = st.columns([1, 1])
    with col_btn_left:
        submit = st.button(
            "🚀 Run & Grade",
            type="primary",
            use_container_width=True,
            disabled=not student_prompt.strip(),
        )
    with col_btn_right:
        if st.session_state.submitted:
            st.button(
                "🔄 Revise & Resubmit",
                use_container_width=True,
                on_click=lambda: setattr(st.session_state, "submitted", False),
            )

    # ── Level navigation (only show unlocked levels) ──────────────────────────
    st.markdown("---")
    st.markdown("### 🎯 Level Progress")

    nav_cols = st.columns(5)
    for i, level in enumerate(LEVELS):
        lid = level["id"]
        unlocked = lid == 1 or (lid - 1) in st.session_state.cleared_levels
        cleared = lid in st.session_state.cleared_levels

        with nav_cols[i]:
            if cleared:
                label = f"✅ L{lid}"
            elif unlocked:
                label = f"🔓 L{lid}"
            else:
                label = f"🔒 L{lid}"

            if unlocked and lid != st.session_state.current_level:
                if st.button(label, key=f"nav_{lid}", use_container_width=True):
                    st.session_state.current_level = lid
                    st.session_state.verdict = None
                    st.session_state.model_output = None
                    st.session_state.submitted = False
                    st.rerun()
            else:
                st.button(
                    label,
                    key=f"nav_{lid}",
                    use_container_width=True,
                    disabled=True,
                )

# ═══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — Verdict + Output
# ═══════════════════════════════════════════════════════════════════════════════
with col_right:
    st.title("📋 Examiner Verdict")

    if not submit and not st.session_state.submitted:
        # Show instructions when nothing has been submitted
        st.info(
            "👈 Write a prompt on the left, then click **Run & Grade**.\n\n"
            "The examiner will:\n"
            "1. Run your prompt on the sample input\n"
            "2. Grade your prompt against the level's principles\n"
            "3. Return a verdict with per-principle ✓ / ✗ results\n\n"
            "Revise until every principle passes!"
        )

    if submit or st.session_state.submitted:
        st.session_state.submitted = True

        with st.spinner("🔍 Running your prompt & grading..."):
            # Step 1: Run the student's prompt on the sample input
            run_result = run_prompt(
                system_prompt=student_prompt,
                user_input=sample_input,
            )

            if run_result["success"]:
                model_output = run_result["output"]
                st.session_state.model_output = model_output
            else:
                st.session_state.model_output = f"⚠️ Runner error: {run_result.get('error', 'Unknown error')}"

            # Step 2: Grade the prompt
            verdict = grade_prompt(
                level=level_id,
                principles=current_level_data["principles"],
                student_prompt=student_prompt,
                model_output=st.session_state.model_output,
            )
            st.session_state.verdict = verdict

        # ── Display verdict ────────────────────────────────────────────────────
        verdict = st.session_state.verdict
        model_output = st.session_state.model_output

        if verdict.get("ran_ok") is False and "_raw_examiner_output" in verdict:
            st.error("⚠️ Examiner had trouble parsing the verdict. Raw output below:")
            st.code(verdict.get("_raw_examiner_output", ""), language="text")

        # ── Per-principle results ──────────────────────────────────────────────
        st.markdown("### 📊 Per-Principle Assessment")

        all_pass = True
        for p_result in verdict.get("principles", []):
            passed = p_result.get("pass", False)
            all_pass = all_pass and passed

            if passed:
                st.success(f"✅ **{p_result['name']}** — Pass")
            else:
                st.error(f"❌ **{p_result['name']}** — Needs Work")
                if p_result.get("weakness"):
                    st.markdown(f"**Weakness:** _{p_result['weakness']}_")
                if p_result.get("question"):
                    st.markdown(f"❓ *{p_result['question']}*")

        # ── Overall verdict ────────────────────────────────────────────────────
        st.markdown("---")
        overall = verdict.get("verdict", "revise")
        if overall == "pass" and all_pass:
            st.balloons()
            st.success("### 🎉 PASSED! All principles satisfied.")

            # Mark level as cleared and unlock next
            st.session_state.cleared_levels.add(level_id)
            next_level = level_id + 1
            if next_level <= len(LEVELS):
                st.info(
                    f"**Level {next_level} unlocked!** "
                    f"Click the button below or navigate using the level buttons."
                )
                if st.button(f"▶️ Advance to Level {next_level}", type="primary"):
                    st.session_state.current_level = next_level
                    st.session_state.verdict = None
                    st.session_state.model_output = None
                    st.session_state.submitted = False
                    st.session_state.student_prompt = ""
                    st.rerun()
            else:
                st.success("🏆 **Congratulations! You've cleared all 5 levels!**")
        else:
            st.warning("### 📝 Verdict: Needs Revision")
            st.markdown(
                "Review the per-principle feedback above, revise your prompt "
                "on the left, and resubmit."
            )

        # ── Live model output ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🤖 Live Model Output")
        st.markdown(
            "*What your prompt actually produced when run on the sample input:*"
        )
        st.code(model_output, language="text")

        # ── Examiner's raw reasoning (collapsible) ────────────────────────────
        if "_raw_examiner_output" in verdict:
            with st.expander("🧠 Examiner Raw Reasoning", expanded=False):
                st.code(verdict["_raw_examiner_output"], language="text")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Prompt Doctor · GenAI & Agentic AI Engineering · Day 2 Afternoon Lab · "
    "The prompt that grades prompts"
)
"""
pages/04_quiz.py
-----------------
Interactive quiz page — presents one question at a time,
shows instant feedback, tracks score, then routes to results.
"""

from __future__ import annotations
from datetime import datetime, timezone
import streamlit as st
from core.auth_service import require_login
from pages.components import sidebar_user_card, divider
from core.quiz_engine import get_questions, evaluate_answer, calculate_score
from core.content_service import get_module

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
age_group = st.session_state["age_group"]
adaptive_profile = st.session_state.get("adaptive_profile", {})
show_hints = adaptive_profile.get("show_hints", False)

module_id = st.session_state.get("quiz_module_id")
difficulty = st.session_state.get("quiz_difficulty", "beginner")

if not module_id:
    st.warning("No quiz selected. Go back and choose a module.")
    if st.button("← Modules"):
        st.switch_page("pages/02_modules.py")
    st.stop()

module = get_module(module_id)
if not module:
    st.error("Module not found.")
    st.stop()

# ─── Initialise quiz state ───────────────────────────────────────────────────
if "active_quiz" not in st.session_state or st.session_state["active_quiz"] is None:
    questions = get_questions(module_id, difficulty, max_questions=5, shuffle=True)
    if not questions:
        st.error("⚠️ No questions found for this module. Please try another.")
        st.stop()
    st.session_state["active_quiz"] = {
        "questions": questions,
        "current_q": 0,
        "answers": [],
        "started_at": datetime.now(timezone.utc),
        "show_feedback": False,
        "last_result": None,
    }
    st.rerun()

quiz = st.session_state["active_quiz"]
questions = quiz["questions"]
total_q = len(questions)
current_idx = quiz["current_q"]
show_feedback = quiz["show_feedback"]

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.q-header { font-size: 1.6rem; font-weight: 800; color: #e2e8f0; margin-bottom: 0.5rem; }
.q-body {
    background: rgba(30,30,50,0.7);
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 16px;
    padding: 1.5rem;
    font-size: 1.05rem;
    line-height: 1.7;
    margin-bottom: 1.25rem;
}
.hint-box {
    background: rgba(245,158,11,0.1);
    border-left: 4px solid #f59e0b;
    border-radius: 0 12px 12px 0;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    color: #fbbf24;
}
.feedback-correct {
    background: rgba(52,211,153,0.12);
    border: 1px solid rgba(52,211,153,0.3);
    border-radius: 14px;
    padding: 1.25rem;
    margin-top: 1rem;
}
.feedback-wrong {
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 14px;
    padding: 1.25rem;
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Progress header ─────────────────────────────────────────────────────────
st.markdown(f'<div class="q-header">{module["icon"]} {module["title"]}</div>', unsafe_allow_html=True)
prog_col, pts_col = st.columns([3, 1])
with prog_col:
    st.progress((current_idx) / total_q, text=f"Question {current_idx + 1} of {total_q}")
with pts_col:
    earned = sum(a.get("points_earned", 0) for a in quiz["answers"])
    st.markdown(f'<div style="text-align:right;color:#a78bfa;font-weight:700;font-size:1.1rem">🏆 {earned} pts</div>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ─── Quiz complete → redirect ────────────────────────────────────────────────
if current_idx >= total_q:
    score_result = calculate_score(quiz["answers"])
    st.session_state["quiz_result"] = {
        **score_result,
        "module_id": module_id,
        "module": module,
        "difficulty": difficulty,
        "started_at": quiz["started_at"],
        "answers": quiz["answers"],
        "questions": questions,
    }
    st.session_state["active_quiz"] = None
    st.switch_page("pages/05_results.py")

# ─── Active question ─────────────────────────────────────────────────────────
q = questions[current_idx]

st.markdown(f'<div class="q-body">{q["body"]}</div>', unsafe_allow_html=True)

# Hint (shown when adaptive engine flags it)
if show_hints and q.get("hint") and not show_feedback:
    st.markdown(f'<div class="hint-box">💡 <strong>Hint:</strong> {q["hint"]}</div>', unsafe_allow_html=True)

# Answer options
option_labels = {
    "a": q["options"]["a"],
    "b": q["options"]["b"],
    "c": q["options"]["c"],
    "d": q["options"]["d"],
}

if not show_feedback:
    chosen = st.radio(
        "Choose your answer:",
        options=list(option_labels.keys()),
        format_func=lambda k: f"{k.upper()}.  {option_labels[k]}",
        key=f"quiz_choice_{current_idx}",
        label_visibility="collapsed",
    )
    st.markdown("<br>", unsafe_allow_html=True)

    col_hint, col_submit = st.columns([2, 1])
    with col_hint:
        if q.get("hint") and not show_hints:
            if st.button("💡 Show Hint", key=f"show_hint_{current_idx}"):
                st.session_state["active_quiz"]["show_hints_override"] = True
                st.rerun()
    with col_submit:
        if st.button("✅ Submit Answer", key=f"submit_{current_idx}", type="primary", use_container_width=True):
            result = evaluate_answer(q, chosen)
            quiz["answers"].append(result)
            quiz["show_feedback"] = True
            quiz["last_result"] = result
            st.rerun()

else:
    # Show chosen answer greyed out (no re-interaction)
    result = quiz["last_result"]
    for k, v in option_labels.items():
        is_correct = k == q["correct_option"]
        was_chosen = result and k == result.get("correct_option") if result["correct"] else k == st.session_state.get(f"quiz_choice_{current_idx}", "")
        icon = "✅" if is_correct else "❌" if (not is_correct and not result["correct"] and k == list(option_labels.keys())[list(option_labels.values()).index(result.get("correct_text", ""))]) else "○"
        # Simple: mark correct answer green
        colour = "#22c55e" if is_correct else "#6b7280"
        st.markdown(
            f'<div style="padding:0.5rem 0.75rem;border-radius:10px;margin:0.3rem 0;'
            f'background:rgba({"52,211,153" if is_correct else "239,68,68" if not result["correct"] and k == chosen else "107,114,128"},0.1);'
            f'border:1px solid rgba({"52,211,153" if is_correct else "239,68,68" if not result["correct"] and k == chosen else "107,114,128"},0.25);'
            f'color:{colour}">'
            f'{"✅" if is_correct else ("❌" if not result["correct"] and k == chosen else "○")} '
            f'{k.upper()}. {v}</div>',
            unsafe_allow_html=True,
        )

    # Feedback box
    if result["correct"]:
        st.markdown(
            f'<div class="feedback-correct">✅ <strong>Correct! +{q["points"]} points</strong><br/>'
            f'{result["explanation"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        correct_letter = q["correct_option"].upper()
        correct_text = q["options"][q["correct_option"]]
        st.markdown(
            f'<div class="feedback-wrong">❌ <strong>Not quite — the answer was {correct_letter}. {correct_text}</strong><br/>'
            f'{result["explanation"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    next_label = "Next Question →" if current_idx < total_q - 1 else "See Results 🏆"
    if st.button(next_label, type="primary", key=f"next_{current_idx}", use_container_width=False):
        quiz["current_q"] += 1
        quiz["show_feedback"] = False
        quiz["last_result"] = None
        st.rerun()

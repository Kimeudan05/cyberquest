"""
pages/09_admin/admin_questions.py
----------------------------------
Admin: manage questions per module.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_admin
from pages.components import sidebar_user_card, page_header, divider
from core.admin_service import create_question, delete_question
from core.content_service import get_all_modules_admin
from db.repositories.quiz_repo import QuizRepository
from config.constants import DIFFICULTY_LEVELS

require_admin()
sidebar_user_card()
page_header("❓ Manage Questions", "Add, review, and deactivate quiz questions")

modules = get_all_modules_admin()
module_map = {m["id"]: m for m in modules}
module_options = {m["id"]: f"{m['icon']} {m['title']} ({m['age_group']}/{m['difficulty']})" for m in modules}

# ─── Module selector ──────────────────────────────────────────────────────────
selected_id = st.selectbox(
    "Select a module to view questions",
    options=list(module_options.keys()),
    format_func=lambda k: module_options.get(k, str(k)),
    key="admin_q_module",
)

if selected_id:
    repo = QuizRepository()
    for diff in DIFFICULTY_LEVELS:
        questions = repo.get_questions_for_module(selected_id, diff, active_only=False)
        if not questions:
            continue
        st.markdown(f"#### {diff.title()} ({len(questions)} questions)")
        for q in questions:
            status = "✅ Active" if q.is_active else "🔕 Inactive"
            with st.expander(f"{status} — {q.body[:70]}..."):
                st.markdown(f"**A:** {q.option_a}")
                st.markdown(f"**B:** {q.option_b}")
                st.markdown(f"**C:** {q.option_c}")
                st.markdown(f"**D:** {q.option_d}")
                st.markdown(f"✅ **Correct:** {q.correct_option.upper()}")
                st.markdown(f"💡 **Hint:** {q.hint or '—'}")
                st.caption(q.explanation)
                if q.is_active:
                    if st.button(f"Deactivate Q#{q.id}", key=f"deact_{q.id}", type="secondary"):
                        ok, msg = delete_question(q.id)
                        if ok:
                            st.success("Deactivated.")
                            st.rerun()
                        else:
                            st.error(msg)

divider("Add New Question")

with st.form("add_question_form", clear_on_submit=True):
    mod_id = st.selectbox(
        "Module *",
        options=list(module_options.keys()),
        format_func=lambda k: module_options.get(k, str(k)),
        key="new_q_module",
    )
    diff = st.selectbox("Difficulty *", DIFFICULTY_LEVELS, format_func=str.title, key="new_q_diff")
    body = st.text_area("Question *", placeholder="What is a strong password?")
    c1, c2 = st.columns(2)
    with c1:
        opt_a = st.text_input("Option A *")
        opt_b = st.text_input("Option B *")
    with c2:
        opt_c = st.text_input("Option C *")
        opt_d = st.text_input("Option D *")
    correct = st.selectbox("Correct Option *", ["a", "b", "c", "d"], format_func=str.upper)
    explanation = st.text_area("Explanation *", placeholder="Why is this the correct answer?")
    hint = st.text_input("Hint (optional)")
    points = st.number_input("Points", min_value=5, max_value=50, value=10, step=5)
    submitted = st.form_submit_button("➕ Add Question", type="primary")

if submitted:
    ok, msg, qid = create_question(
        module_id=mod_id, body=body,
        option_a=opt_a, option_b=opt_b, option_c=opt_c, option_d=opt_d,
        correct_option=correct, explanation=explanation,
        difficulty=diff, hint=hint or "", points=int(points),
    )
    if ok:
        st.success(f"✅ Question added (ID: {qid})")
        st.rerun()
    else:
        st.error(f"❌ {msg}")

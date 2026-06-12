"""
pages/03_scenario.py
---------------------
Scenario reader page — shows the narrative intro for a module
before launching the quiz. Includes a pre-test option.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login
from pages.components import sidebar_user_card, page_header, divider
from core.content_service import get_module, get_scenarios_for_module
from config.constants import TOPICS, DIFFICULTY_ORDER

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
age_group = st.session_state["age_group"]

module_id = st.session_state.get("selected_module_id")
if not module_id:
    st.warning("⚠️ No module selected. Please choose one from the Modules page.")
    if st.button("← Go to Modules"):
        st.switch_page("pages/02_modules.py")
    st.stop()

module = get_module(module_id)
if not module:
    st.error("Module not found.")
    st.stop()

scenarios = get_scenarios_for_module(module_id)
topic_meta = TOPICS.get(module["topic"], {})

st.markdown("""
<style>
.scenario-box {
    background: linear-gradient(135deg, rgba(167,139,250,0.08), rgba(96,165,250,0.05));
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem 0;
    line-height: 1.8;
    font-size: 1.05rem;
}
.breadcrumb { color: #9ca3af; font-size: 0.85rem; margin-bottom: 0.5rem; }
.module-hero {
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(167,139,250,0.3);
}
</style>
""", unsafe_allow_html=True)

# ─── Breadcrumb ──────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="breadcrumb">📚 Modules → {topic_meta.get("label","Module")} → {module["title"]}</div>',
    unsafe_allow_html=True,
)

# ─── Module hero ─────────────────────────────────────────────────────────────
diff_color = {"beginner": "#34d399", "intermediate": "#f59e0b", "advanced": "#ef4444"}
st.markdown(
    f'<div class="module-hero">'
    f'<div style="font-size:3rem;margin-bottom:0.5rem">{module["icon"]}</div>'
    f'<h2 style="margin:0;color:#e2e8f0">{module["title"]}</h2>'
    f'<p style="color:#9ca3af;margin:0.25rem 0 0">{module["description"]}</p>'
    f'<span style="display:inline-block;margin-top:0.75rem;padding:0.2rem 0.75rem;'
    f'background:rgba(255,255,255,0.08);border-radius:99px;font-size:0.8rem;'
    f'color:{diff_color.get(module["difficulty"],"#a78bfa")}">'
    f'{module["difficulty"].title()} Level</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Scenario reader ─────────────────────────────────────────────────────────
if scenarios:
    if "scenario_idx" not in st.session_state:
        st.session_state["scenario_idx"] = 0

    idx = min(st.session_state["scenario_idx"], len(scenarios) - 1)
    scenario = scenarios[idx]

    if len(scenarios) > 1:
        st.markdown(f"**Story Part {idx + 1} of {len(scenarios)}**")
        prog = (idx + 1) / len(scenarios)
        st.progress(prog)

    st.markdown(f'<div class="scenario-box">{scenario["body"]}</div>', unsafe_allow_html=True)

    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    with nav_col1:
        if idx > 0:
            if st.button("← Previous", key="scen_prev"):
                st.session_state["scenario_idx"] = idx - 1
                st.rerun()
    with nav_col3:
        if idx < len(scenarios) - 1:
            if st.button("Next →", key="scen_next", type="primary"):
                st.session_state["scenario_idx"] = idx + 1
                st.rerun()

    on_last = idx == len(scenarios) - 1
else:
    st.info("📖 This module goes straight to the quiz — no intro story needed!")
    on_last = True

# ─── Launch quiz ─────────────────────────────────────────────────────────────
divider()

# Determine difficulty for this quiz
adaptive_profile = st.session_state.get("adaptive_profile", {})
from core.quiz_engine import select_difficulty_for_user
difficulty = select_difficulty_for_user(
    age_group=age_group,
    current_level=adaptive_profile.get("current_level", 1),
    topic_mastery=adaptive_profile.get("topic_mastery", {}),
    topic=module["topic"],
)

col_skip, col_start = st.columns([1, 2])
with col_skip:
    if st.button("← Back to Modules", key="scen_back"):
        st.session_state.pop("scenario_idx", None)
        st.switch_page("pages/02_modules.py")
with col_start:
    btn_label = "🚀 I'm Ready — Start the Quiz!" if on_last else "⏭️ Skip Story → Start Quiz"
    if st.button(btn_label, type="primary", use_container_width=True, key="scen_start_quiz"):
        st.session_state.pop("scenario_idx", None)
        st.session_state["quiz_module_id"] = module_id
        st.session_state["quiz_difficulty"] = difficulty
        st.switch_page("pages/04_quiz.py")

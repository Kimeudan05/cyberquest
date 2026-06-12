"""
pages/02_modules.py
--------------------
Module browser — shows all published modules for the user's age group,
grouped by topic. Users can filter by topic and see their progress.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login
from pages.components import sidebar_user_card, page_header, divider
from core.content_service import get_modules_for_user
from db.repositories.progress_repo import ProgressRepository
from config.constants import TOPICS, AGE_GROUPS

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
age_group = st.session_state["age_group"]

st.markdown("""
<style>
.topic-header {
    display: flex; align-items: center; gap: 0.75rem;
    background: rgba(167,139,250,0.08);
    border-left: 4px solid #a78bfa;
    border-radius: 0 12px 12px 0;
    padding: 0.6rem 1rem;
    margin: 1.25rem 0 0.75rem 0;
}
.mod-card {
    background: rgba(30,30,50,0.6);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.1rem;
    height: 100%;
    transition: border-color 0.2s, transform 0.2s;
}
.mod-card:hover { border-color: rgba(167,139,250,0.5); transform: translateY(-2px); }
.diff-pill {
    display: inline-block;
    border-radius: 99px; padding: 0.15rem 0.6rem;
    font-size: 0.72rem; font-weight: 600;
}
.diff-beginner { background: rgba(52,211,153,0.15); color: #34d399; }
.diff-intermediate { background: rgba(245,158,11,0.15); color: #f59e0b; }
.diff-advanced { background: rgba(239,68,68,0.15); color: #ef4444; }
</style>
""", unsafe_allow_html=True)

page_header("📚 Modules", f"Your learning catalogue — {AGE_GROUPS.get(age_group, {}).get('label', '')}")

# ─── Load data ────────────────────────────────────────────────────────────────
modules = get_modules_for_user(age_group=age_group, published_only=True)
progress_repo = ProgressRepository()
all_progress = progress_repo.get_all_for_user(uid)
progress_by_module = {p.module_id: p for p in all_progress}

if not modules:
    st.info("🔧 No modules published yet. Check back soon!")
    st.stop()

# ─── Sidebar filters ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filter")
    topic_options = ["All Topics"] + [meta["label"] for meta in TOPICS.values()]
    topic_filter = st.selectbox("Topic", topic_options, key="mod_topic_filter")
    diff_filter = st.multiselect(
        "Difficulty",
        ["beginner", "intermediate", "advanced"],
        default=["beginner", "intermediate", "advanced"],
        key="mod_diff_filter",
        format_func=str.title,
    )
    show_completed = st.checkbox("Show Completed", value=True, key="mod_show_completed")

# ─── Apply filters ────────────────────────────────────────────────────────────
filtered = []
for m in modules:
    topic_label = TOPICS.get(m["topic"], {}).get("label", m["topic"])
    if topic_filter != "All Topics" and topic_label != topic_filter:
        continue
    if m["difficulty"] not in diff_filter:
        continue
    prog = progress_by_module.get(m["id"])
    is_completed = prog.is_completed if prog else False
    if not show_completed and is_completed:
        continue
    filtered.append(m)

# ─── Summary bar ─────────────────────────────────────────────────────────────
total_mods = len(modules)
completed = sum(1 for m in modules if progress_by_module.get(m["id"]) and progress_by_module[m["id"]].is_completed)
mastered = sum(1 for m in modules if progress_by_module.get(m["id"]) and progress_by_module[m["id"]].mastery_level >= 3)

mc1, mc2, mc3 = st.columns(3)
mc1.metric("Available", total_mods)
mc2.metric("Completed", completed)
mc3.metric("Mastered ⭐", mastered)
st.markdown("<br>", unsafe_allow_html=True)

# ─── Group by topic ───────────────────────────────────────────────────────────
from itertools import groupby
filtered_sorted = sorted(filtered, key=lambda m: (m["topic"], m["order_index"]))

grouped: dict[str, list] = {}
for m in filtered_sorted:
    grouped.setdefault(m["topic"], []).append(m)

if not grouped:
    st.warning("No modules match your current filters. Try adjusting them above.")
    st.stop()

for topic_key, mods in grouped.items():
    topic_meta = TOPICS.get(topic_key, {})
    st.markdown(
        f'<div class="topic-header">'
        f'<span style="font-size:1.5rem">{topic_meta.get("icon","📚")}</span>'
        f'<strong style="font-size:1.05rem">{topic_meta.get("label", topic_key)}</strong>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(min(len(mods), 3))
    for idx, mod in enumerate(mods):
        prog = progress_by_module.get(mod["id"])
        mastery_level = prog.mastery_level if prog else 0
        best_pct = int(prog.best_score_pct * 100) if prog else 0
        attempts = prog.attempt_count if prog else 0

        mastery_icon = {0: "⬜", 1: "🟡", 2: "✅", 3: "⭐"}.get(mastery_level, "⬜")
        diff = mod["difficulty"]

        with cols[idx % 3]:
            st.markdown(
                f'<div class="mod-card">'
                f'<div style="font-size:2rem;margin-bottom:0.4rem">{mod["icon"]}</div>'
                f'<strong style="font-size:0.95rem">{mod["title"]}</strong> {mastery_icon}<br/>'
                f'<span class="diff-pill diff-{diff}">{diff.title()}</span>'
                f'{"<br/><small style=\"color:#9ca3af;margin-top:0.4rem;display:block\">Best: " + str(best_pct) + "% · " + str(attempts) + " attempt" + ("s" if attempts != 1 else "") + "</small>" if attempts > 0 else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "▶ Start" if mastery_level == 0 else ("🔁 Retry" if mastery_level < 3 else "✅ Review"),
                key=f"mod_start_{mod['id']}",
                use_container_width=True,
                type="primary" if mastery_level < 3 else "secondary",
            ):
                st.session_state["selected_module_id"] = mod["id"]
                st.switch_page("pages/03_scenario.py")
            st.markdown("<br/>", unsafe_allow_html=True)

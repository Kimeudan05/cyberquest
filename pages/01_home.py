"""
pages/01_home.py
----------------
Home dashboard for CyberQuest Kids.
Shows the user's stats, active recommendations, and recent badges.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login
from pages.components import (
    sidebar_user_card, xp_progress_bar, badge_reveal, page_header, divider
)
from core.progress_service import get_user_stats, get_recent_activity
from core.adaptive_engine import build_adaptive_profile, get_recommendations
from core.reward_service import award_daily_login_points, check_and_award_badges
from db.repositories.reward_repo import RewardRepository
from db.repositories.module_repo import ModuleRepository
from config.constants import AGE_GROUPS

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
age_group = st.session_state["age_group"]
username = st.session_state["username"]

# ─── Daily login points + badge check ────────────────────────────────────────
total_pts = award_daily_login_points(uid)

# Build/refresh adaptive profile
profile = build_adaptive_profile(uid)
st.session_state["adaptive_profile"] = profile

# Badge evaluation context
stats = get_user_stats(uid)
new_badges = check_and_award_badges(uid, {
    "total_points": stats["total_points"],
    "score_pct": stats.get("best_score", 0.0),
    "streak_count": profile["streak_count"],
    "topic_mastery": profile["topic_mastery"],
    "modules_completed": stats["modules_completed"],
    "current_level": stats["current_level"],
    "topics_completed": profile["strong_topics"],
})
badge_reveal(new_badges)

# ─── Page CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stat-card {
    background: linear-gradient(135deg, rgba(167,139,250,0.12), rgba(96,165,250,0.08));
    border: 1px solid rgba(167,139,250,0.25);
    border-radius: 16px;
    padding: 1.25rem 1rem;
    text-align: center;
    transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-num { font-size: 2.2rem; font-weight: 900; color: #a78bfa; }
.stat-label { font-size: 0.8rem; color: #9ca3af; margin-top: 0.1rem; }
.greeting { font-size:2rem; font-weight:800; }
.rec-card {
    background: rgba(52,211,153,0.08);
    border: 1px solid rgba(52,211,153,0.2);
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Greeting ─────────────────────────────────────────────────────────────────
ag_label = AGE_GROUPS.get(age_group, {}).get("label", "")
st.markdown(f'<div class="greeting">👋 Hey, {username}! {ag_label}</div>', unsafe_allow_html=True)
st.markdown(f'<p style="color:#9ca3af">Welcome to your CyberQuest dashboard. Keep learning, keep levelling up!</p>', unsafe_allow_html=True)

# ─── XP bar ───────────────────────────────────────────────────────────────────
xp_progress_bar(stats["total_points"])
st.markdown("<br>", unsafe_allow_html=True)

# ─── Stat cards ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    (c1, str(stats["total_points"]), "Total Points", "🏆"),
    (c2, f"Lv.{stats['current_level']}", "Current Level", "⬆️"),
    (c3, str(stats["modules_completed"]), "Modules Completed", "✅"),
    (c4, str(stats["badges_earned"]), "Badges Earned", "🏅"),
    (c5, f"{stats['streak_count']}d", "Day Streak", "🔥"),
]
for col, val, label, icon in metrics:
    with col:
        st.markdown(
            f'<div class="stat-card">'
            f'<div class="stat-num">{icon}</div>'
            f'<div style="font-size:1.4rem;font-weight:800;color:#e2e8f0">{val}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
divider("Your Learning Path")

# ─── Recommendations ─────────────────────────────────────────────────────────
recs = get_recommendations(uid, age_group, profile, limit=3)
repo_mod = ModuleRepository()

main_col, aside_col = st.columns([2, 1], gap="large")

with main_col:
    if recs:
        st.markdown("### 🎯 Recommended For You")
        for rec in recs:
            mod = repo_mod.get_by_id(rec["module_id"])
            if mod is None:
                continue
            priority_color = {1: "#ef4444", 2: "#f59e0b", 3: "#22c55e"}[rec["priority"]]
            with st.container():
                st.markdown(
                    f'<div class="rec-card">'
                    f'<span style="font-size:1.5rem">{mod.icon}</span> '
                    f'<strong>{mod.title}</strong> '
                    f'<span style="font-size:0.75rem;color:{priority_color};margin-left:0.5rem">'
                    f'{"★" * (4 - rec["priority"])} Priority</span><br/>'
                    f'<small style="color:#9ca3af">{rec["reason"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Start Module →", key=f"rec_start_{rec['module_id']}", type="primary"):
                    st.session_state["selected_module_id"] = rec["module_id"]
                    st.switch_page("pages/03_scenario.py")
    else:
        st.info("🌟 You've explored everything! Head to **Modules** to keep practising.")
        if st.button("Browse All Modules →", type="primary"):
            st.switch_page("pages/02_modules.py")

with aside_col:
    # Recent badges
    st.markdown("### 🏅 Recent Badges")
    reward_repo = RewardRepository()
    user_badges = reward_repo.get_user_badges(uid)

    if user_badges:
        from db.database import get_db
        from db.models import Badge
        badge_ids = [ub.badge_id for ub in user_badges[-4:]]
        with get_db() as db:
            badges = db.query(Badge).filter(Badge.id.in_(badge_ids)).all()
            for b in badges:
                db.expunge(b)
        for b in reversed(badges):
            st.markdown(
                f'<div style="background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);'
                f'border-radius:10px;padding:0.6rem 0.75rem;margin-bottom:0.5rem">'
                f'🏅 <strong>{b.name}</strong><br/>'
                f'<small style="color:#9ca3af">{b.description}</small></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#9ca3af;text-align:center;padding:2rem 0">'
            '🏆<br/>Complete quizzes to earn badges!</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    # Quick links
    st.markdown("### 🗺️ Quick Links")
    if st.button("📚 Browse Modules", use_container_width=True, key="ql_modules"):
        st.switch_page("pages/02_modules.py")
    if st.button("📊 My Progress", use_container_width=True, key="ql_progress"):
        st.switch_page("pages/06_progress.py")
    if st.button("🥇 Leaderboard", use_container_width=True, key="ql_leaderboard"):
        st.switch_page("pages/07_leaderboard.py")

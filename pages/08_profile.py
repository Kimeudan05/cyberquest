"""
pages/08_profile.py
--------------------
User profile page — shows badges collection, account info,
feedback form, and logout.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login, logout_user
from pages.components import sidebar_user_card, xp_progress_bar, page_header, divider, star_rating
from core.progress_service import get_user_stats
from core.evaluation_service import save_feedback, get_evaluation_report
from db.repositories.reward_repo import RewardRepository
from config.constants import AGE_GROUPS

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
username = st.session_state["username"]
age_group = st.session_state["age_group"]
stats = get_user_stats(uid)
ag_info = AGE_GROUPS.get(age_group, {})

page_header(f"👤 {username}", f"{ag_info.get('label', '')} — Member since your first quest!")

st.markdown("""
<style>
.badge-card {
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 14px;
    padding: 1rem 0.75rem;
    text-align: center;
    transition: transform 0.2s;
}
.badge-card:hover { transform: translateY(-3px); }
.badge-name { font-weight: 700; font-size: 0.85rem; margin-top: 0.4rem; color: #fbbf24; }
.badge-desc { font-size: 0.72rem; color: #9ca3af; margin-top: 0.2rem; }
.locked-badge { filter: grayscale(100%) opacity(0.3); }
</style>
""", unsafe_allow_html=True)

# ─── Profile stats ────────────────────────────────────────────────────────────
s1, s2, s3 = st.columns([1.5, 1, 1])
with s1:
    xp_progress_bar(stats["total_points"])
with s2:
    st.metric("Badges Earned", stats["badges_earned"])
    st.metric("Modules Mastered", stats["modules_mastered"])
with s3:
    st.metric("Day Streak 🔥", f"{stats['streak_count']}d")
    st.metric("Best Score", f"{int(stats['best_score']*100)}%")

divider("🏅 Badge Collection")

# ─── Badge grid ──────────────────────────────────────────────────────────────
reward_repo = RewardRepository()
all_badges = reward_repo.get_all_active_badges()
user_badge_ids = {ub.badge_id for ub in reward_repo.get_user_badges(uid)}

cols_per_row = 4
rows = [all_badges[i:i+cols_per_row] for i in range(0, len(all_badges), cols_per_row)]

for row in rows:
    row_cols = st.columns(cols_per_row)
    for col, badge in zip(row_cols, row):
        earned = badge.id in user_badge_ids
        with col:
            if earned:
                st.markdown(
                    f'<div class="badge-card">'
                    f'<div style="font-size:2.5rem">🏅</div>'
                    f'<div class="badge-name">{badge.name}</div>'
                    f'<div class="badge-desc">{badge.description}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="badge-card locked-badge">'
                    f'<div style="font-size:2.5rem">🔒</div>'
                    f'<div class="badge-name" style="color:#6b7280">{badge.name}</div>'
                    f'<div class="badge-desc">{badge.description}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("", unsafe_allow_html=True)

divider("📝 Leave Feedback")

# ─── Feedback form ────────────────────────────────────────────────────────────
with st.form("feedback_form", clear_on_submit=True):
    st.markdown("Help us improve CyberQuest! Your feedback matters. 💬")
    fb_rating = star_rating("feedback_stars")
    fb_enjoyment = st.radio(
        "How did you find the content?",
        ["too_easy", "just_right", "too_hard"],
        format_func=lambda x: {"too_easy": "😴 A bit easy", "just_right": "👌 Just right!", "too_hard": "😰 Too hard"}[x],
        horizontal=True,
        key="fb_enjoyment",
    )
    fb_text = st.text_area(
        "Any other thoughts? (optional)",
        placeholder="What did you enjoy? What could be better?",
        max_chars=500,
        key="fb_text",
    )
    fb_submit = st.form_submit_button("Send Feedback 🚀", type="primary")

if fb_submit:
    save_feedback(
        user_id=uid,
        module_id=None,
        rating=fb_rating,
        enjoyment=fb_enjoyment,
        difficulty_rating=fb_enjoyment,
        free_text=fb_text,
    )
    st.success("Thanks for your feedback! 🎉")

divider()
with st.expander("⚠️ Account Actions"):
    st.warning("Logging out will end your current session.")
    if st.button("🚪 Log Out", type="secondary", key="profile_logout"):
        logout_user()

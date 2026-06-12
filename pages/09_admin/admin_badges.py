"""
pages/09_admin/admin_badges.py
-------------------------------
Admin: manage badge catalogue.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_admin
from pages.components import sidebar_user_card, page_header, divider
from core.admin_service import create_badge, delete_badge
from db.repositories.reward_repo import RewardRepository

require_admin()
sidebar_user_card()
page_header("🏅 Manage Badges", "View, create, and delete achievement badges")

repo = RewardRepository()
all_badges = repo.get_all_active_badges()

# ─── Badge grid ──────────────────────────────────────────────────────────────
if all_badges:
    cols_per_row = 4
    for i in range(0, len(all_badges), cols_per_row):
        row_badges = all_badges[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for col, badge in zip(cols, row_badges):
            with col:
                st.markdown(
                    f'<div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);'
                    f'border-radius:14px;padding:1rem;text-align:center;margin-bottom:0.75rem">'
                    f'<div style="font-size:2.5rem">🏅</div>'
                    f'<div style="font-weight:700;color:#fbbf24">{badge.name}</div>'
                    f'<div style="font-size:0.72rem;color:#9ca3af;margin:0.25rem 0">{badge.description}</div>'
                    f'<div style="font-size:0.7rem;color:#6b7280">{badge.criteria_type}: {badge.criteria_value}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"🗑️ Delete", key=f"del_badge_{badge.id}", use_container_width=True, type="secondary"):
                    ok, msg = delete_badge(badge.id)
                    if ok:
                        st.success("Badge deleted.")
                        st.rerun()
                    else:
                        st.error(msg)
else:
    st.info("No badges found.")

divider("Create New Badge")

CRITERIA_TYPES = ["module_complete", "topic_mastery", "streak", "level", "score", "special"]

with st.form("create_badge_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Badge Name *", placeholder="Password Pro")
        criteria_type = st.selectbox("Criteria Type *", CRITERIA_TYPES)
        criteria_value = st.text_input(
            "Criteria Value *",
            help="E.g. '5' for module_complete, 'password_safety' for topic_mastery, '3' for streak",
        )
        sort_order = st.number_input("Sort Order", min_value=0, value=len(all_badges), step=1)
    with c2:
        description = st.text_area("Description *", placeholder="Earned by mastering Password Safety")
        image_filename = st.text_input("Image Filename", value="badge_default.svg")
        age_group = st.selectbox("Age Group", ["all", "junior", "explorer", "ranger"])
    submitted = st.form_submit_button("➕ Create Badge", type="primary")

if submitted:
    ok, msg, bid = create_badge(
        name=name, description=description,
        image_filename=image_filename,
        criteria_type=criteria_type,
        criteria_value=criteria_value,
        age_group=age_group,
        sort_order=int(sort_order),
    )
    if ok:
        st.success(f"✅ Badge created (ID: {bid})")
        st.rerun()
    else:
        st.error(f"❌ {msg}")

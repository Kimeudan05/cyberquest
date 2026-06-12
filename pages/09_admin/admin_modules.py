"""
pages/09_admin/admin_modules.py
--------------------------------
Admin: manage modules (list, publish/unpublish, create, delete).
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_admin
from pages.components import sidebar_user_card, page_header, divider
from core.admin_service import (
    get_engagement_metrics, create_module, update_module,
    delete_module, publish_module,
)
from core.content_service import get_all_modules_admin
from config.constants import TOPIC_LIST, AGE_GROUP_LIST, DIFFICULTY_LEVELS, TOPICS

require_admin()
sidebar_user_card()
page_header("🗂️ Manage Modules", "Create, edit, publish and delete learning modules")

modules = get_all_modules_admin()

# ─── Summary ─────────────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
m1.metric("Total Modules", len(modules))
m2.metric("Published", sum(1 for m in modules if m["is_published"]))
m3.metric("Draft", sum(1 for m in modules if not m["is_published"]))
divider()

# ─── Module table ─────────────────────────────────────────────────────────────
st.markdown("### All Modules")
with st.container():
    header = st.columns([2.5, 1.2, 1.2, 1.2, 0.8, 0.8])
    for h, t in zip(header, ["Title", "Topic", "Age Group", "Difficulty", "Published", "Actions"]):
        h.markdown(f"**{t}**")
    st.markdown("---")
    for mod in modules:
        cols = st.columns([2.5, 1.2, 1.2, 1.2, 0.8, 0.8])
        cols[0].markdown(f"{mod['icon']} **{mod['title']}**")
        cols[1].markdown(f"`{mod['topic']}`")
        cols[2].markdown(mod["age_group"].title())
        cols[3].markdown(mod["difficulty"].title())
        pub_label = "✅" if mod["is_published"] else "🔒"
        cols[4].markdown(pub_label)
        with cols[5]:
            toggle_label = "Unpublish" if mod["is_published"] else "Publish"
            if st.button(toggle_label, key=f"pub_{mod['id']}", use_container_width=True):
                publish_module(mod["id"], not mod["is_published"])
                st.rerun()
        if st.button(f"🗑️ Delete #{mod['id']}", key=f"del_{mod['id']}", type="secondary"):
            ok, msg = delete_module(mod["id"])
            if ok:
                st.success(f"Deleted module #{mod['id']}")
                st.rerun()
            else:
                st.error(msg)

divider("Create New Module")

# ─── Create form ─────────────────────────────────────────────────────────────
with st.form("create_module_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Module Title *", placeholder="Password Safety: Junior")
        topic = st.selectbox("Topic *", TOPIC_LIST, format_func=lambda t: TOPICS.get(t, {}).get("label", t))
        age_group = st.selectbox("Age Group *", AGE_GROUP_LIST, format_func=str.title)
    with c2:
        difficulty = st.selectbox("Difficulty *", DIFFICULTY_LEVELS, format_func=str.title)
        icon = st.text_input("Icon (emoji)", value="📚")
        order_index = st.number_input("Order Index", min_value=0, value=0, step=1)
    description = st.text_area("Description *", placeholder="What will learners discover?")
    publish_now = st.checkbox("Publish immediately")
    submitted = st.form_submit_button("➕ Create Module", type="primary")

if submitted:
    ok, msg, new_id = create_module(
        title=title, topic=topic, description=description,
        age_group=age_group, difficulty=difficulty,
        icon=icon, order_index=int(order_index), publish=publish_now,
    )
    if ok:
        st.success(f"✅ Module created (ID: {new_id})")
        st.rerun()
    else:
        st.error(f"❌ {msg}")

"""
pages/09_admin/admin_metrics.py
--------------------------------
Admin: engagement metrics dashboard.
"""

from __future__ import annotations
import streamlit as st
import plotly.express as px
import pandas as pd
from core.auth_service import require_admin
from pages.components import sidebar_user_card, page_header, divider
from core.admin_service import get_engagement_metrics

require_admin()
sidebar_user_card()
page_header("📈 Engagement Metrics", "Platform health and learner activity")

metrics = get_engagement_metrics()

# ─── KPI tiles ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Learners", metrics["total_users"])
k2.metric("Active This Week", metrics["active_this_week"])
k3.metric("Quiz Attempts", metrics["total_quiz_attempts"])
k4.metric("Avg Score", f"{int(metrics['average_score']*100)}%")
k5.metric("Badges Awarded", metrics["badges_awarded"])

divider("Recent Activity Log")

# ─── Activity table ───────────────────────────────────────────────────────────
recent = metrics.get("recent_activity", [])
if recent:
    df = pd.DataFrame(recent)
    df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
    df.columns = ["User ID", "Event Type", "Timestamp"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No activity logged yet.")

divider()
st.caption("Metrics update on each page load. Data sourced from the local SQLite database.")

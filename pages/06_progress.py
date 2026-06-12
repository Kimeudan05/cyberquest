"""
pages/06_progress.py
---------------------
My Progress page — visualises topic mastery, quiz history,
XP level, and pre/post test learning gains using Plotly charts.
"""

from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.auth_service import require_login
from pages.components import sidebar_user_card, xp_progress_bar, score_badge, page_header, divider
from core.progress_service import get_user_stats, get_topic_mastery_map, get_recent_activity
from core.evaluation_service import get_evaluation_report
from db.repositories.quiz_repo import QuizRepository
from config.constants import MASTERY_THRESHOLD, MODERATE_THRESHOLD

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
stats = get_user_stats(uid)
topic_map = get_topic_mastery_map(uid)
recent = get_recent_activity(uid, limit=8)

page_header("📊 My Progress", "Track your cybersecurity learning journey")

st.markdown("""
<style>
.prog-stat { background: rgba(167,139,250,0.08); border: 1px solid rgba(167,139,250,0.2);
  border-radius: 14px; padding: 1.1rem; text-align:center; }
.prog-num { font-size:2rem; font-weight:900; color:#a78bfa; }
.prog-lbl { font-size:0.8rem; color:#9ca3af; }
</style>
""", unsafe_allow_html=True)

# ─── Stat tiles ───────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
tile_data = [
    (c1, stats["total_points"], "Total Points", "🏆"),
    (c2, f"Lv. {stats['current_level']}", "XP Level", "⬆️"),
    (c3, stats["modules_completed"], "Completed", "✅"),
    (c4, stats["modules_mastered"], "Mastered", "⭐"),
    (c5, f"{int(stats['average_score']*100)}%", "Avg Score", "📊"),
    (c6, f"{stats['streak_count']}d", "Streak", "🔥"),
]
for col, val, lbl, icon in tile_data:
    with col:
        st.markdown(
            f'<div class="prog-stat"><div class="prog-num">{icon}</div>'
            f'<div style="font-size:1.3rem;font-weight:800;color:#e2e8f0">{val}</div>'
            f'<div class="prog-lbl">{lbl}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
xp_progress_bar(stats["total_points"])
st.markdown("<br>", unsafe_allow_html=True)

# ─── Topic mastery radar chart ────────────────────────────────────────────────
divider("Topic Mastery")
chart_col, list_col = st.columns([1.4, 1])

with chart_col:
    if any(t["attempts"] > 0 for t in topic_map):
        labels = [t["label"] for t in topic_map]
        values = [round(t["best_score"] * 100, 1) for t in topic_map]
        colors = ["#22c55e" if v >= MASTERY_THRESHOLD*100 else ("#f59e0b" if v >= MODERATE_THRESHOLD*100 else "#ef4444") for v in values]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor="rgba(167,139,250,0.15)",
            line=dict(color="#a78bfa", width=2),
            name="Your Score",
        ))
        fig.add_trace(go.Scatterpolar(
            r=[80] * (len(labels) + 1),
            theta=labels + [labels[0]],
            line=dict(color="rgba(52,211,153,0.4)", width=1, dash="dot"),
            name="Mastery (80%)",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%", tickfont=dict(color="#9ca3af")),
                angularaxis=dict(tickfont=dict(color="#e2e8f0")),
                bgcolor="rgba(0,0,0,0)",
            ),
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            margin=dict(l=40, r=40, t=40, b=40),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Complete some quizzes to see your radar chart!")

with list_col:
    st.markdown("#### Topic Status")
    for t in topic_map:
        pct = int(t["best_score"] * 100)
        icon = "⭐" if t["mastered"] else ("🟡" if pct >= MODERATE_THRESHOLD*100 else ("🔴" if t["attempts"] > 0 else "⬜"))
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:0.5rem 0;border-bottom:1px solid rgba(255,255,255,0.06)">'
            f'<span>{icon} {t["label"]}</span>'
            f'<span style="color:#9ca3af;font-size:0.85rem">'
            f'{"" if t["attempts"] == 0 else str(pct) + "% · " + str(t["attempts"]) + " try"}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ─── Score history chart ──────────────────────────────────────────────────────
divider("Quiz History")
quiz_repo = QuizRepository()
attempts = quiz_repo.get_all_attempts_for_user(uid)

if attempts:
    df = pd.DataFrame([{
        "Date": a.completed_at,
        "Score (%)": round(a.score_pct * 100, 1),
        "Passed": a.passed,
        "Difficulty": a.difficulty.title() if a.difficulty else "",
    } for a in reversed(attempts) if a.completed_at])

    fig2 = px.line(
        df, x="Date", y="Score (%)",
        markers=True,
        color_discrete_sequence=["#a78bfa"],
        title="",
    )
    fig2.add_hline(y=80, line_dash="dot", line_color="#22c55e", annotation_text="Mastery 80%")
    fig2.add_hline(y=50, line_dash="dot", line_color="#f59e0b", annotation_text="50%")
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,25,0.5)",
        font=dict(color="#e2e8f0"),
        yaxis=dict(range=[0, 105], gridcolor="rgba(255,255,255,0.06)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        height=300,
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Complete some quizzes to see your score history!")

# ─── Recent activity ─────────────────────────────────────────────────────────
if recent:
    divider("Recent Activity")
    activity_icons = {
        "quiz_complete": "❓",
        "badge_earned": "🏅",
        "login": "🔐",
        "feedback_submitted": "📝",
    }
    for act in recent:
        icon = activity_icons.get(act["event_type"], "📌")
        ts = act["created_at"].strftime("%b %d, %H:%M") if act["created_at"] else ""
        label = act["event_type"].replace("_", " ").title()
        st.markdown(
            f'<div style="display:flex;gap:0.75rem;align-items:center;'
            f'padding:0.4rem 0;border-bottom:1px solid rgba(255,255,255,0.05)">'
            f'<span style="font-size:1.2rem">{icon}</span>'
            f'<span style="flex:1;color:#e2e8f0">{label}</span>'
            f'<span style="color:#6b7280;font-size:0.8rem">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

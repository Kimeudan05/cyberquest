"""
pages/07_leaderboard.py
------------------------
Leaderboard page — top learners by total points.
Privacy-safe: shows only username, level, points.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login
from components import sidebar_user_card, page_header, divider
from core.reward_service import get_leaderboard

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
username = st.session_state["username"]

page_header("🥇 Leaderboard", "Top CyberQuest learners — keep earning points to climb the ranks!")

st.markdown("""
<style>
.lb-row {
    display: flex; align-items: center; gap: 1rem;
    padding: 0.85rem 1rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    border: 1px solid rgba(255,255,255,0.06);
    transition: background 0.2s;
}
.lb-row:hover { background: rgba(167,139,250,0.07); }
.lb-row-me { background: rgba(167,139,250,0.12); border-color: rgba(167,139,250,0.35); }
.lb-rank { font-size: 1.3rem; font-weight: 900; min-width: 2rem; text-align: center; }
.lb-name { flex: 1; font-weight: 600; }
.lb-pts { color: #a78bfa; font-weight: 700; font-size: 1.05rem; }
.lb-lvl { color: #9ca3af; font-size: 0.85rem; }
.podium-1 { color: #fbbf24; }
.podium-2 { color: #94a3b8; }
.podium-3 { color: #b45309; }
</style>
""", unsafe_allow_html=True)

board = get_leaderboard(top_n=10)

if not board:
    st.info("🌱 No scores yet — be the first on the leaderboard! Complete a quiz to get started.")
    if st.button("📚 Browse Modules →", type="primary"):
        st.switch_page("pages/02_modules.py")
    st.stop()

# ─── Top 3 podium ────────────────────────────────────────────────────────────
if len(board) >= 3:
    p1, p2, p3 = st.columns([1, 1.2, 1])
    def _podium_card(col, entry, height: str, medal: str, cls: str):
        with col:
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.04);border-radius:16px;'
                f'padding:1.2rem;text-align:center;border:1px solid rgba(255,255,255,0.08);'
                f'height:{height}">'
                f'<div style="font-size:2.5rem">{medal}</div>'
                f'<div style="font-weight:800;font-size:1rem;margin:0.4rem 0">{entry["username"]}</div>'
                f'<div class="{cls}" style="font-size:1.4rem;font-weight:900">{entry["total_points"]:,} pts</div>'
                f'<div style="color:#6b7280;font-size:0.8rem">Level {entry["current_level"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    _podium_card(p2, board[0], "230px", "🥇", "podium-1")
    _podium_card(p1, board[1], "200px", "🥈", "podium-2")
    _podium_card(p3, board[2], "185px", "🥉", "podium-3")
    st.markdown("<br>", unsafe_allow_html=True)

# ─── Full ranked list ─────────────────────────────────────────────────────────
divider("Full Rankings")

rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
me_on_board = False

for entry in board:
    rank = entry["rank"]
    is_me = entry["username"] == username
    if is_me:
        me_on_board = True
    row_class = "lb-row lb-row-me" if is_me else "lb-row"
    rank_display = rank_icons.get(rank, f"#{rank}")
    me_tag = " ← you" if is_me else ""
    st.markdown(
        f'<div class="{row_class}">'
        f'<span class="lb-rank">{rank_display}</span>'
        f'<span class="lb-name">{entry["username"]}{me_tag}</span>'
        f'<span class="lb-lvl">Lv. {entry["current_level"]}</span>'
        f'<span class="lb-pts">{entry["total_points"]:,} pts</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

if not me_on_board:
    divider()
    st.markdown(
        '<div style="text-align:center;color:#9ca3af;padding:0.5rem">'
        '📈 You\'re not in the Top 10 yet — keep completing quizzes to earn more points!</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
divider()
if st.button("📚 Earn More Points →", type="primary"):
    st.switch_page("pages/02_modules.py")

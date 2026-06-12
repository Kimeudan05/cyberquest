"""
pages/components.py
--------------------
Shared UI components for CyberQuest Kids.
Import this module in any page that needs reusable widgets.
"""

from __future__ import annotations
import streamlit as st
from config.constants import AGE_GROUPS, LEVEL_XP_THRESHOLDS, MAX_LEVEL


# ─── Sidebar user card ───────────────────────────────────────────────────────

def sidebar_user_card() -> None:
    """Render the user info card at the top of the sidebar."""
    username = st.session_state.get("username", "")
    age_group = st.session_state.get("age_group", "")
    role = st.session_state.get("role", "learner")
    age_label = AGE_GROUPS.get(age_group, {}).get("label", age_group.title())

    with st.sidebar:
        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### 👤")
        with col2:
            st.markdown(f"**{username}**")
            if role == "admin":
                st.caption("⚙️ Admin")
            else:
                st.caption(age_label)
        
        st.markdown("<br>", unsafe_allow_html=True)
        theme = st.session_state.get("theme", "dark")
        is_light = st.toggle("☀️ Light Mode", value=(theme == "light"), key="theme_toggle")
        new_theme = "light" if is_light else "dark"
        if new_theme != theme:
            st.session_state["theme"] = new_theme
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True, key="sidebar_logout_btn"):
            from core.auth_service import logout_user
            logout_user()


# ─── XP level bar ────────────────────────────────────────────────────────────

def xp_progress_bar(total_points: int) -> None:
    """Render a compact XP level + progress bar."""
    from core.reward_service import get_level_progress
    info = get_level_progress(total_points)
    level = info["level"]
    pct = info["pct"]
    pts_to_next = info["points_to_next"]

    st.markdown(f"**Level {level}** {'🏆' if info['is_max'] else ''}")
    st.progress(pct)
    if not info["is_max"]:
        st.caption(f"{pts_to_next} pts to Level {level + 1}")
    else:
        st.caption("Max level reached! 🎉")


# ─── Score badge ─────────────────────────────────────────────────────────────

def score_badge(score_pct: float) -> None:
    """Render a coloured score badge."""
    pct_int = int(score_pct * 100)
    if score_pct >= 0.80:
        colour, emoji = "#22c55e", "⭐"
    elif score_pct >= 0.50:
        colour, emoji = "#f59e0b", "👍"
    else:
        colour, emoji = "#ef4444", "💡"
    st.markdown(
        f'<div style="display:inline-block;background:{colour};color:white;'
        f'border-radius:12px;padding:0.25rem 0.9rem;font-weight:700;font-size:1.1rem;">'
        f'{emoji} {pct_int}%</div>',
        unsafe_allow_html=True,
    )


# ─── Module card ─────────────────────────────────────────────────────────────

def module_card(module: dict, progress: dict | None = None) -> bool:
    """
    Render a single module card. Returns True if the Start button was clicked.
    progress dict keys: best_score_pct (float), mastery_level (int), attempt_count (int)
    """
    mastery = progress.get("mastery_level", 0) if progress else 0
    badge = {0: "", 1: "🟡", 2: "✅", 3: "⭐"}[mastery]
    best = int(progress["best_score_pct"] * 100) if progress else 0

    st.markdown(
        f"""
        <div class="cq-card">
            <span style="font-size:2rem">{module['icon']}</span>&nbsp;
            <strong>{module['title']}</strong>&nbsp;{badge}<br/>
            <small style="color:#9ca3af">{module['difficulty'].title()} · {module['topic_label']}</small>
            {"<br/><small>Best: " + str(best) + "%</small>" if progress and progress.get("attempt_count", 0) > 0 else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    clicked = st.button(
        "▶ Start" if mastery == 0 else "🔁 Retry",
        key=f"mod_btn_{module['id']}",
        use_container_width=True,
    )
    st.markdown("<div style='margin-top:-0.5rem'></div>", unsafe_allow_html=True)
    return clicked


# ─── Feedback stars ──────────────────────────────────────────────────────────

def star_rating(key: str = "star_rating") -> int:
    """Render a 1–5 star rating selector. Returns the chosen int."""
    stars = st.radio(
        "How would you rate this module?",
        options=[1, 2, 3, 4, 5],
        format_func=lambda x: "⭐" * x,
        horizontal=True,
        key=key,
    )
    return stars


# ─── Badge reveal ────────────────────────────────────────────────────────────

def badge_reveal(badges: list[dict]) -> None:
    """Show a celebration banner for newly earned badges."""
    if not badges:
        return
    st.balloons()
    for b in badges:
        st.success(f"🏅 **New Badge Unlocked: {b['name']}!** — {b['description']}")


# ─── CSS helpers ─────────────────────────────────────────────────────────────

def divider(label: str = "") -> None:
    if label:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.75rem;margin:1rem 0">'
            f'<hr style="flex:1;border:none;border-top:1px solid #374151"/>'
            f'<span style="color:#9ca3af;font-size:0.85rem">{label}</span>'
            f'<hr style="flex:1;border:none;border-top:1px solid #374151"/></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("---")


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<p style="color:#9ca3af;margin-top:-0.75rem">{subtitle}</p>', unsafe_allow_html=True)

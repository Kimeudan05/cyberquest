"""
pages/05_results.py
--------------------
Quiz results page — shows score, feedback summary, points earned,
newly awarded badges, and adaptive routing to next action.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import require_login
from pages.components import sidebar_user_card, score_badge, badge_reveal, xp_progress_bar, divider
from core.quiz_engine import record_quiz_attempt, classify_performance
from core.adaptive_engine import route_next_action, update_adaptive_profile
from core.progress_service import update_progress, log_activity
from core.reward_service import award_points, check_and_award_badges, get_level_progress
from config.constants import POINTS_MODULE_COMPLETE, POINTS_PERFECT_SCORE

require_login()
sidebar_user_card()

uid = st.session_state["user_id"]
age_group = st.session_state["age_group"]

result = st.session_state.get("quiz_result")
if not result:
    st.warning("No quiz result found. Complete a quiz first.")
    if st.button("← Modules"):
        st.switch_page("pages/02_modules.py")
    st.stop()

# ─── Persist results (once, using a flag) ────────────────────────────────────
persist_key = f"results_persisted_{result['module_id']}_{result['started_at']}"
if not st.session_state.get(persist_key, False):
    # Record attempt
    record_quiz_attempt(
        user_id=uid,
        module_id=result["module_id"],
        score_result=result,
        difficulty=result["difficulty"],
        started_at=result["started_at"],
    )
    # Update progress
    update_progress(uid, result["module_id"], result["score_pct"], result["passed"])

    # Award points (per-question + module bonus)
    points_earned = result["points_earned"]
    if result["passed"]:
        points_earned += POINTS_MODULE_COMPLETE
    new_total = award_points(uid, points_earned, reason="quiz_complete")

    # Update adaptive profile
    updated_profile = update_adaptive_profile(
        user_id=uid,
        topic=result["module"]["topic"],
        score_pct=result["score_pct"],
        current_profile=st.session_state.get("adaptive_profile", {}),
    )
    st.session_state["adaptive_profile"] = updated_profile

    # Badge check
    new_badges = check_and_award_badges(uid, {
        "total_points": new_total,
        "score_pct": result["score_pct"],
        "streak_count": updated_profile.get("streak_count", 0),
        "topic_mastery": updated_profile.get("topic_mastery", {}),
        "modules_completed": sum(1 for _ in updated_profile.get("strong_topics", [])),
        "current_level": updated_profile.get("current_level", 1),
        "topics_completed": updated_profile.get("strong_topics", []),
    })
    st.session_state["pending_badges"] = new_badges
    st.session_state["points_just_earned"] = points_earned
    st.session_state["new_total_points"] = new_total

    log_activity(uid, "quiz_complete", {
        "module_id": result["module_id"],
        "score_pct": result["score_pct"],
        "passed": result["passed"],
        "difficulty": result["difficulty"],
    })
    st.session_state[persist_key] = True

# ─── Retrieve persisted values ────────────────────────────────────────────────
new_badges = st.session_state.get("pending_badges", [])
points_earned = st.session_state.get("points_just_earned", 0)
new_total = st.session_state.get("new_total_points", 0)
score_pct = result["score_pct"]
score_raw = result["score_raw"]
score_total = result["score_total"]
module = result["module"]

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.result-hero {
    text-align: center;
    padding: 2rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 2rem;
}
.big-score {
    font-size: 5rem;
    font-weight: 900;
    line-height: 1;
}
.q-review-correct {
    background: rgba(52,211,153,0.08);
    border-left: 3px solid #34d399;
    border-radius: 0 10px 10px 0;
    padding: 0.75rem;
    margin-bottom: 0.6rem;
}
.q-review-wrong {
    background: rgba(239,68,68,0.08);
    border-left: 3px solid #ef4444;
    border-radius: 0 10px 10px 0;
    padding: 0.75rem;
    margin-bottom: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Badge reveal ─────────────────────────────────────────────────────────────
badge_reveal(new_badges)

# ─── Score hero ──────────────────────────────────────────────────────────────
band = classify_performance(score_pct)
pct_int = int(score_pct * 100)
emoji = "🌟" if score_pct == 1.0 else ("🎉" if band == "mastered" else ("👍" if band == "moderate" else "💡"))
colour = {"mastered": "#22c55e", "moderate": "#f59e0b", "struggling": "#ef4444"}[band]

st.markdown(
    f'<div class="result-hero">'
    f'<div style="font-size:1.4rem;color:#9ca3af;margin-bottom:0.5rem">{module["icon"]} {module["title"]}</div>'
    f'<div class="big-score" style="color:{colour}">{emoji} {pct_int}%</div>'
    f'<div style="font-size:1.2rem;margin-top:0.5rem;color:#e2e8f0">{score_raw} / {score_total} correct</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ─── Stats row ────────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
s1.metric("Points Earned", f"+{points_earned}", f"Total: {new_total}")
s2.metric("Score", f"{pct_int}%", "Mastered! ⭐" if band == "mastered" else "")
s3.metric("Correct", f"{score_raw}/{score_total}")
s4.metric("Badges Earned", len(new_badges))

st.markdown("<br>", unsafe_allow_html=True)
xp_progress_bar(new_total)

# ─── Adaptive routing message ────────────────────────────────────────────────
adaptive_profile = st.session_state.get("adaptive_profile", {})
routing = route_next_action(
    score_pct=score_pct,
    current_difficulty=result["difficulty"],
    topic=module["topic"],
    age_group=age_group,
)
st.info(routing["message"])

divider("Question Review")

# ─── Per-question review ─────────────────────────────────────────────────────
for i, (q, ans) in enumerate(zip(result["questions"], result["answers"]), 1):
    css_class = "q-review-correct" if ans["correct"] else "q-review-wrong"
    icon = "✅" if ans["correct"] else "❌"
    st.markdown(
        f'<div class="{css_class}">'
        f'<strong>{icon} Q{i}. {q["body"][:100]}{"..." if len(q["body"])>100 else ""}</strong><br/>'
        f'<small style="color:#9ca3af">{ans["explanation"]}</small>'
        f'</div>',
        unsafe_allow_html=True,
    )

divider()

# ─── Navigation buttons ───────────────────────────────────────────────────────
btn1, btn2, btn3 = st.columns(3)
with btn1:
    if st.button("← Back to Modules", use_container_width=True):
        st.session_state.pop("quiz_result", None)
        st.switch_page("pages/02_modules.py")
with btn2:
    if st.button("🔁 Try Again", use_container_width=True):
        st.session_state.pop("quiz_result", None)
        st.session_state["quiz_module_id"] = result["module_id"]
        st.session_state["quiz_difficulty"] = routing["next_difficulty"]
        st.switch_page("pages/04_quiz.py")
with btn3:
    if st.button("🏠 Home", use_container_width=True, type="primary"):
        st.session_state.pop("quiz_result", None)
        st.switch_page("pages/01_home.py")

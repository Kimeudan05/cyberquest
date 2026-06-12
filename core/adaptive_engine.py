"""
core/adaptive_engine.py
-----------------------
Rule-based adaptive learning engine for CyberQuest Kids.

All routing decisions use explicit, transparent if/elif rules —
no machine learning or black-box logic.

Responsibilities:
  - Classify performance after each quiz (mastered / moderate / struggling)
  - Update the user's adaptive profile (weak_topics, strong_topics, mastery map)
  - Generate content recommendations based on the profile
  - Determine the next action for the learner (advance / repeat / reduce difficulty)

Adaptive profile structure (stored in session_state["adaptive_profile"]):
    {
        "current_level":  int,
        "average_score":  float,       # rolling 10-attempt average
        "streak_count":   int,
        "weak_topics":    list[str],   # topics with score < 50%
        "strong_topics":  list[str],   # topics with score >= 80%
        "topic_mastery":  dict[str, bool]  # topic → mastered?
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.constants import (
    DIFFICULTY_ADVANCED,
    DIFFICULTY_BEGINNER,
    DIFFICULTY_INTERMEDIATE,
    DIFFICULTY_ORDER,
    MASTERY_THRESHOLD,
    MODERATE_THRESHOLD,
    ROLLING_SCORE_WINDOW,
    TOPICS,
)
from db.repositories.quiz_repo import QuizRepository
from db.repositories.user_repo import UserRepository
from db.repositories.progress_repo import ProgressRepository


# ─── Performance classification ──────────────────────────────────────────────

def classify_performance(score_pct: float) -> str:
    """
    Map a score percentage to a named performance band.

    Returns:
        "mastered"   — >= 80% (MASTERY_THRESHOLD)
        "moderate"   — >= 50% and < 80%
        "struggling" — < 50% (MODERATE_THRESHOLD)
    """
    if score_pct >= MASTERY_THRESHOLD:
        return "mastered"
    elif score_pct >= MODERATE_THRESHOLD:
        return "moderate"
    else:
        return "struggling"


# ─── Adaptive profile builder ────────────────────────────────────────────────

def build_adaptive_profile(user_id: int) -> dict:
    """
    Construct a fresh adaptive profile from the database.
    Called on login and after each quiz attempt.

    Returns a dict matching the session_state["adaptive_profile"] schema.
    """
    quiz_repo = QuizRepository()
    user_repo = UserRepository()
    progress_repo = ProgressRepository()

    user = user_repo.get_by_id(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # Rolling average score (last ROLLING_SCORE_WINDOW attempts)
    recent_attempts = quiz_repo.get_recent_attempts(
        user_id=user_id,
        limit=ROLLING_SCORE_WINDOW,
    )
    average_score = (
        sum(a.score_pct for a in recent_attempts) / len(recent_attempts)
        if recent_attempts
        else 0.0
    )

    # Topic mastery map: topic → True if any attempt passed at mastery threshold
    progress_records = progress_repo.get_all_for_user(user_id)
    topic_mastery: dict[str, bool] = {}
    weak_topics: list[str] = []
    strong_topics: list[str] = []

    for rec in progress_records:
        topic = rec.module.topic if rec.module else None
        if topic is None:
            continue
        is_mastered = rec.best_score_pct >= MASTERY_THRESHOLD
        topic_mastery[topic] = is_mastered
        if is_mastered:
            if topic not in strong_topics:
                strong_topics.append(topic)
        elif rec.best_score_pct < MODERATE_THRESHOLD and rec.attempt_count > 0:
            if topic not in weak_topics:
                weak_topics.append(topic)

    return {
        "current_level": user.current_level,
        "average_score": round(average_score, 4),
        "streak_count": user.streak_count,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "topic_mastery": topic_mastery,
    }


# ─── Profile update after quiz ───────────────────────────────────────────────

def update_adaptive_profile(
    user_id: int,
    topic: str,
    score_pct: float,
    current_profile: dict,
) -> dict:
    """
    Update the in-memory adaptive profile after a quiz attempt.
    The caller should store the returned dict back into session_state.

    Rules applied:
      score >= 80%  → mark topic as mastered, move to strong_topics
      50–79%        → neutral (no change to topic lists)
      < 50%         → add topic to weak_topics, remove from strong_topics

    Args:
        user_id:         Current user's ID (for DB refresh if needed)
        topic:           Topic key of the completed quiz
        score_pct:       Quiz score as a float 0.0–1.0
        current_profile: Existing adaptive profile dict from session_state

    Returns:
        Updated adaptive profile dict
    """
    profile = dict(current_profile)  # shallow copy
    profile["topic_mastery"] = dict(profile.get("topic_mastery", {}))
    profile["weak_topics"] = list(profile.get("weak_topics", []))
    profile["strong_topics"] = list(profile.get("strong_topics", []))

    band = classify_performance(score_pct)

    if band == "mastered":
        profile["topic_mastery"][topic] = True
        if topic not in profile["strong_topics"]:
            profile["strong_topics"].append(topic)
        if topic in profile["weak_topics"]:
            profile["weak_topics"].remove(topic)

    elif band == "struggling":
        profile["topic_mastery"][topic] = profile["topic_mastery"].get(topic, False)
        if topic not in profile["weak_topics"]:
            profile["weak_topics"].append(topic)
        if topic in profile["strong_topics"]:
            profile["strong_topics"].remove(topic)

    # else "moderate" — no change to mastery lists

    # Rebuild rolling average with the new score included
    quiz_repo = QuizRepository()
    recent = quiz_repo.get_recent_attempts(user_id=user_id, limit=ROLLING_SCORE_WINDOW)
    if recent:
        profile["average_score"] = round(
            sum(a.score_pct for a in recent) / len(recent), 4
        )

    return profile


# ─── Next-action routing ─────────────────────────────────────────────────────

def route_next_action(
    score_pct: float,
    current_difficulty: str,
    topic: str,
    age_group: str,
) -> dict:
    """
    Decide what should happen after a quiz, based on the score.

    Returns a dict with:
        action        — "advance" | "repeat" | "reduce"
        next_difficulty — suggested difficulty for next attempt
        show_hints    — True if hints should be emphasised
        message       — Human-readable explanation for the learner
    """
    band = classify_performance(score_pct)
    curr_order = DIFFICULTY_ORDER.get(current_difficulty, 0)

    # ── Rule: mastered — try to advance ──────────────────────────────────────
    if band == "mastered":
        if age_group == "junior":
            # Juniors always stay at beginner; congratulate and move on
            return {
                "action": "advance",
                "next_difficulty": DIFFICULTY_BEGINNER,
                "show_hints": False,
                "message": "🌟 Amazing! You've mastered this topic!",
            }
        if curr_order < DIFFICULTY_ORDER[DIFFICULTY_ADVANCED]:
            difficulties = [DIFFICULTY_BEGINNER, DIFFICULTY_INTERMEDIATE, DIFFICULTY_ADVANCED]
            next_diff = difficulties[curr_order + 1]
            return {
                "action": "advance",
                "next_difficulty": next_diff,
                "show_hints": False,
                "message": f"🚀 Great job! You've unlocked the {next_diff.title()} level!",
            }
        else:
            return {
                "action": "advance",
                "next_difficulty": DIFFICULTY_ADVANCED,
                "show_hints": False,
                "message": "🏆 You've mastered the Advanced level! You're a CyberQuest expert!",
            }

    # ── Rule: moderate — repeat at same level with light hints ────────────────
    elif band == "moderate":
        return {
            "action": "repeat",
            "next_difficulty": current_difficulty,
            "show_hints": True,
            "message": "👍 Good effort! Try again to reach mastery — hints are available.",
        }

    # ── Rule: struggling — reduce difficulty or give extended hints ───────────
    else:
        if curr_order > 0:
            difficulties = [DIFFICULTY_BEGINNER, DIFFICULTY_INTERMEDIATE, DIFFICULTY_ADVANCED]
            lower_diff = difficulties[curr_order - 1]
            return {
                "action": "reduce",
                "next_difficulty": lower_diff,
                "show_hints": True,
                "message": f"💡 Let's try the {lower_diff.title()} level — hints are on to help you!",
            }
        else:
            return {
                "action": "reduce",
                "next_difficulty": DIFFICULTY_BEGINNER,
                "show_hints": True,
                "message": "💡 Don't give up! Read the hints carefully and try again.",
            }


# ─── Recommendations ─────────────────────────────────────────────────────────

def get_recommendations(
    user_id: int,
    age_group: str,
    adaptive_profile: dict,
    limit: int = 3,
) -> list[dict]:
    """
    Generate module recommendations based on the user's adaptive profile.

    Rules (in priority order):
      1. Weak topics (score < 50%) → highest priority, beginner module
      2. Incomplete topics (started but not mastered) → medium priority
      3. Untouched topics → low priority (variety recommendation)

    Args:
        user_id:          Current user's ID
        age_group:        User's age band
        adaptive_profile: Profile dict from session_state
        limit:            Max recommendations to return

    Returns:
        List of dicts: {module_id, topic, reason, priority}
    """
    from db.repositories.module_repo import ModuleRepository
    from db.repositories.progress_repo import ProgressRepository

    module_repo = ModuleRepository()
    progress_repo = ProgressRepository()

    weak_topics = set(adaptive_profile.get("weak_topics", []))
    topic_mastery = adaptive_profile.get("topic_mastery", {})
    completed_topics = {t for t, mastered in topic_mastery.items() if mastered}

    recs: list[dict] = []

    # Priority 1 — weak topics
    for topic in weak_topics:
        if len(recs) >= limit:
            break
        module = module_repo.get_by_topic_age_difficulty(
            topic=topic,
            age_group=age_group,
            difficulty=DIFFICULTY_BEGINNER,
        )
        if module and module.is_published:
            recs.append({
                "module_id": module.id,
                "topic": topic,
                "reason": "You scored below 50% on this topic. Let's practise it again!",
                "priority": 1,
            })

    # Priority 2 — started but not mastered
    progress_records = progress_repo.get_all_for_user(user_id)
    in_progress_topics = {
        rec.module.topic
        for rec in progress_records
        if rec.module and rec.attempt_count > 0 and rec.module.topic not in completed_topics
    }
    for topic in in_progress_topics:
        if len(recs) >= limit:
            break
        if topic in weak_topics:
            continue  # already covered above
        module = module_repo.get_by_topic_age_difficulty(
            topic=topic, age_group=age_group, difficulty=DIFFICULTY_BEGINNER
        )
        if module and module.is_published:
            recs.append({
                "module_id": module.id,
                "topic": topic,
                "reason": "You've started this topic — keep going to master it!",
                "priority": 2,
            })

    # Priority 3 — untouched topics
    all_topics = set(TOPICS.keys())
    tried_topics = {rec.module.topic for rec in progress_records if rec.module}
    fresh_topics = all_topics - tried_topics - weak_topics

    for topic in sorted(fresh_topics):
        if len(recs) >= limit:
            break
        module = module_repo.get_by_topic_age_difficulty(
            topic=topic, age_group=age_group, difficulty=DIFFICULTY_BEGINNER
        )
        if module and module.is_published:
            recs.append({
                "module_id": module.id,
                "topic": topic,
                "reason": "Explore a new cybersecurity topic!",
                "priority": 3,
            })

    return recs[:limit]


# ─── Streak update ───────────────────────────────────────────────────────────

def update_streak(user_id: int) -> int:
    """
    Recalculate and persist the user's login streak.
    Increments streak if last login was yesterday (UTC); resets if gap > 1 day.

    Returns the new streak_count.
    """
    from datetime import date, timedelta
    from db.database import get_db
    from db.models import User

    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if user is None:
            return 0

        today = date.today()
        last_login_date = user.last_login.date() if user.last_login else None

        if last_login_date is None or last_login_date < today - timedelta(days=1):
            user.streak_count = 1   # Reset streak
        elif last_login_date == today - timedelta(days=1):
            user.streak_count += 1  # Extend streak
        # else last_login_date == today: no change (already logged in today)

        new_streak = user.streak_count
    return new_streak

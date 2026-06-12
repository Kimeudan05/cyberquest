"""
core/reward_service.py
-----------------------
Gamification service for CyberQuest Kids.

Responsibilities:
  - Award points for correct answers, module completion, and daily login
  - Calculate and persist XP levels
  - Check badge unlock criteria and award badges
  - Update user streak
  - Fetch leaderboard data (anonymised, top-N)

All badge unlock logic uses the criteria_type / criteria_value
fields from the badges table, keeping the rules data-driven.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.constants import (
    LEADERBOARD_TOP_N,
    LEVEL_XP_THRESHOLDS,
    MAX_LEVEL,
    POINTS_CORRECT_ANSWER,
    POINTS_DAILY_LOGIN,
    POINTS_MODULE_COMPLETE,
    POINTS_PERFECT_SCORE,
    calculate_level,
)
from db.repositories.reward_repo import RewardRepository
from db.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from db.models import Badge, UserBadge


# ─── Points ──────────────────────────────────────────────────────────────────

def award_points(user_id: int, points: int, reason: str = "") -> int:
    """
    Add points to the user's total and update their XP level.

    Args:
        user_id: The user to award points to
        points:  Number of points to add (can be 0)
        reason:  Human-readable reason for the award (for logs)

    Returns:
        New total points for the user
    """
    repo = RewardRepository()
    user_repo = UserRepository()

    new_total = repo.add_points(user_id=user_id, points=points)
    new_level = calculate_level(new_total)

    # Persist level to both user_points and users tables for fast queries
    repo.set_xp_level(user_id=user_id, level=new_level)
    user_repo.update_level_and_points(
        user_id=user_id,
        total_points=new_total,
        current_level=new_level,
    )
    return new_total


def award_daily_login_points(user_id: int) -> int:
    """
    Award the daily login bonus if not already awarded today (UTC).
    Returns the new total points.
    """
    repo = RewardRepository()
    already_awarded = repo.has_received_points_today(user_id)
    if already_awarded:
        return repo.get_total_points(user_id)
    return award_points(user_id=user_id, points=POINTS_DAILY_LOGIN, reason="daily_login")


# ─── Badge evaluation ────────────────────────────────────────────────────────

def check_and_award_badges(
    user_id: int,
    context: dict,
) -> list[dict]:
    """
    Evaluate all active badge criteria against the current user context.
    Award any badges not yet held by the user.

    Args:
        user_id: The user to check badges for
        context: Dict of current state values:
            {
                "total_points":     int,
                "score_pct":        float,     (latest quiz)
                "streak_count":     int,
                "topic_mastery":    dict[str, bool],
                "modules_completed": int,      (total)
                "current_level":    int,
                "topics_completed": list[str], (all mastered topics)
            }

    Returns:
        List of newly awarded badge dicts: {id, name, description, image_filename}
    """
    repo = RewardRepository()
    all_badges = repo.get_all_active_badges()
    already_earned = {ub.badge_id for ub in repo.get_user_badges(user_id)}
    newly_awarded: list[dict] = []

    for badge in all_badges:
        if badge.id in already_earned:
            continue
        if _evaluate_badge_criteria(badge, context):
            repo.award_badge(user_id=user_id, badge_id=badge.id)
            newly_awarded.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "image_filename": badge.image_filename,
            })

    return newly_awarded


def _evaluate_badge_criteria(badge: "Badge", context: dict) -> bool:
    """
    Return True if the badge's unlock criteria are met by the context dict.

    Supported criteria_types:
        module_complete  — criteria_value = N (int): N modules completed
        topic_mastery    — criteria_value = topic_key: that topic is mastered
        streak           — criteria_value = N (int): streak_count >= N
        level            — criteria_value = N (int): current_level >= N
        score            — criteria_value = F (float): latest score_pct >= F
        special          — criteria_value = "all_topics_complete": all 7 mastered
    """
    ctype = badge.criteria_type
    cval = badge.criteria_value

    try:
        if ctype == "module_complete":
            return context.get("modules_completed", 0) >= int(cval)

        elif ctype == "topic_mastery":
            return context.get("topic_mastery", {}).get(cval, False)

        elif ctype == "streak":
            return context.get("streak_count", 0) >= int(cval)

        elif ctype == "level":
            return context.get("current_level", 1) >= int(cval)

        elif ctype == "score":
            return context.get("score_pct", 0.0) >= float(cval)

        elif ctype == "special":
            if cval == "all_topics_complete":
                mastery = context.get("topic_mastery", {})
                from config.constants import TOPIC_LIST
                return all(mastery.get(t, False) for t in TOPIC_LIST)

    except (ValueError, TypeError):
        pass

    return False


# ─── Leaderboard ─────────────────────────────────────────────────────────────

def get_leaderboard(top_n: int = LEADERBOARD_TOP_N) -> list[dict]:
    """
    Return the top N users by total_points for the leaderboard.

    The leaderboard shows only: rank, username, level.
    It does NOT expose: score breakdown, age, or any PII.

    Returns:
        List of dicts: {rank, username, current_level, total_points}
    """
    repo = RewardRepository()
    rows = repo.get_top_users_by_points(limit=top_n)
    return [
        {
            "rank": idx + 1,
            "username": row.username,
            "current_level": row.current_level,
            "total_points": row.total_points,
        }
        for idx, row in enumerate(rows)
    ]


# ─── XP level helpers ────────────────────────────────────────────────────────

def get_level_progress(total_points: int) -> dict:
    """
    Return XP level info for display in the progress bar widget.

    Returns:
        {
            "level":          int,     current level (1–10)
            "points_in_level": int,    points earned within this level
            "points_to_next": int,     points needed to reach next level
            "pct":            float,   0.0–1.0 progress within current level
            "is_max":         bool,    True if at MAX_LEVEL
        }
    """
    level = calculate_level(total_points)
    is_max = level >= MAX_LEVEL

    if is_max:
        return {
            "level": level,
            "points_in_level": total_points - LEVEL_XP_THRESHOLDS[level - 1],
            "points_to_next": 0,
            "pct": 1.0,
            "is_max": True,
        }

    current_threshold = LEVEL_XP_THRESHOLDS[level - 1]
    next_threshold = LEVEL_XP_THRESHOLDS[level]
    points_in_level = total_points - current_threshold
    points_span = next_threshold - current_threshold
    pct = points_in_level / points_span if points_span > 0 else 0.0

    return {
        "level": level,
        "points_in_level": points_in_level,
        "points_to_next": next_threshold - total_points,
        "pct": round(pct, 4),
        "is_max": False,
    }

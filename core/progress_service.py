"""
core/progress_service.py
-------------------------
Progress tracking and statistics service for CyberQuest Kids.

Responsibilities:
  - Mark a module as completed after a successful quiz
  - Update the per-module progress snapshot after every quiz attempt
  - Retrieve aggregated user statistics for the dashboard
  - Return a topic mastery map (for Plotly/Altair charts)
  - Log significant user events to the activity_log table
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from db.repositories.progress_repo import ProgressRepository
from db.repositories.quiz_repo import QuizRepository
from db.repositories.module_repo import ModuleRepository
from config.constants import MASTERY_THRESHOLD, MODERATE_THRESHOLD, TOPICS


# ─── Module progress ─────────────────────────────────────────────────────────

def update_progress(
    user_id: int,
    module_id: int,
    score_pct: float,
    passed: bool,
) -> None:
    """
    Update (or create) the Progress record for user × module after a quiz.

    Mastery level mapping:
        0 — not started
        1 — in progress (attempt made, not yet passed)
        2 — completed (passed at least once)
        3 — mastered (best_score_pct >= MASTERY_THRESHOLD)

    Args:
        user_id:   Authenticated user's ID
        module_id: Module that was just completed
        score_pct: Final quiz score (0.0–1.0)
        passed:    True if score_pct >= MASTERY_THRESHOLD
    """
    repo = ProgressRepository()
    existing = repo.get(user_id=user_id, module_id=module_id)

    if existing is None:
        # First attempt at this module
        mastery_level = 3 if score_pct >= MASTERY_THRESHOLD else (2 if passed else 1)
        repo.create(
            user_id=user_id,
            module_id=module_id,
            is_completed=passed,
            best_score_pct=score_pct,
            attempt_count=1,
            mastery_level=mastery_level,
        )
    else:
        new_best = max(existing.best_score_pct, score_pct)
        new_completed = existing.is_completed or passed
        new_attempts = existing.attempt_count + 1
        new_mastery = _derive_mastery_level(new_best, new_completed)
        repo.update(
            user_id=user_id,
            module_id=module_id,
            is_completed=new_completed,
            best_score_pct=new_best,
            attempt_count=new_attempts,
            mastery_level=new_mastery,
        )


def _derive_mastery_level(best_score_pct: float, is_completed: bool) -> int:
    """Map best score and completion flag to mastery_level integer (0–3)."""
    if best_score_pct >= MASTERY_THRESHOLD:
        return 3
    elif is_completed:
        return 2
    elif best_score_pct > 0:
        return 1
    else:
        return 0


def mark_module_complete(user_id: int, module_id: int) -> None:
    """
    Explicitly mark a module as completed (mastery_level = 2).
    Called when the learner finishes a module without passing the mastery bar.
    """
    repo = ProgressRepository()
    existing = repo.get(user_id=user_id, module_id=module_id)
    if existing and not existing.is_completed:
        repo.update(
            user_id=user_id,
            module_id=module_id,
            is_completed=True,
            best_score_pct=existing.best_score_pct,
            attempt_count=existing.attempt_count,
            mastery_level=max(existing.mastery_level, 2),
        )


# ─── User statistics ─────────────────────────────────────────────────────────

def get_user_stats(user_id: int) -> dict:
    """
    Return aggregated statistics for the learner dashboard.

    Returns:
        {
            "modules_started":   int,
            "modules_completed": int,
            "modules_mastered":  int,
            "total_attempts":    int,
            "average_score":     float,   (0.0–1.0, or 0.0 if no attempts)
            "best_score":        float,
            "badges_earned":     int,
            "total_points":      int,
            "current_level":     int,
            "streak_count":      int,
        }
    """
    progress_repo = ProgressRepository()
    quiz_repo = QuizRepository()

    from db.repositories.reward_repo import RewardRepository
    from db.repositories.user_repo import UserRepository
    reward_repo = RewardRepository()
    user_repo = UserRepository()

    user = user_repo.get_by_id(user_id)
    records = progress_repo.get_all_for_user(user_id)
    attempts = quiz_repo.get_all_attempts_for_user(user_id)
    badge_count = len(reward_repo.get_user_badges(user_id))

    modules_started = len(records)
    modules_completed = sum(1 for r in records if r.is_completed)
    modules_mastered = sum(1 for r in records if r.mastery_level >= 3)
    total_attempts = len(attempts)

    avg_score = (
        sum(a.score_pct for a in attempts) / total_attempts
        if total_attempts > 0
        else 0.0
    )
    best_score = max((a.score_pct for a in attempts), default=0.0)

    return {
        "modules_started": modules_started,
        "modules_completed": modules_completed,
        "modules_mastered": modules_mastered,
        "total_attempts": total_attempts,
        "average_score": round(avg_score, 4),
        "best_score": round(best_score, 4),
        "badges_earned": badge_count,
        "total_points": user.total_points if user else 0,
        "current_level": user.current_level if user else 1,
        "streak_count": user.streak_count if user else 0,
    }


def get_topic_mastery_map(user_id: int) -> list[dict]:
    """
    Return topic-level performance data for Plotly radar/bar charts.

    Returns:
        List of dicts:
            {
                "topic":        str,    topic key
                "label":        str,    human-readable topic name
                "best_score":   float,  best score across all attempts (0.0–1.0)
                "attempts":     int,    total attempts on this topic
                "mastered":     bool,
            }
    """
    progress_repo = ProgressRepository()
    records = progress_repo.get_all_for_user(user_id)

    # Aggregate by topic (user may have attempted multiple difficulty levels)
    topic_data: dict[str, dict] = {}
    for rec in records:
        topic = rec.module.topic if rec.module else None
        if topic is None:
            continue
        if topic not in topic_data:
            topic_data[topic] = {
                "best_score": 0.0,
                "attempts": 0,
                "mastered": False,
            }
        topic_data[topic]["best_score"] = max(
            topic_data[topic]["best_score"], rec.best_score_pct
        )
        topic_data[topic]["attempts"] += rec.attempt_count
        if rec.mastery_level >= 3:
            topic_data[topic]["mastered"] = True

    # Fill in zeros for untouched topics
    result = []
    for topic_key, meta in TOPICS.items():
        data = topic_data.get(topic_key, {"best_score": 0.0, "attempts": 0, "mastered": False})
        result.append({
            "topic": topic_key,
            "label": meta["label"],
            "best_score": round(data["best_score"], 4),
            "attempts": data["attempts"],
            "mastered": data["mastered"],
        })

    return result


def get_recent_activity(user_id: int, limit: int = 10) -> list[dict]:
    """
    Return the most recent activity_log entries for the user.

    Returns:
        List of dicts: {event_type, event_data (parsed), created_at}
    """
    from db.database import get_db
    from db.models import ActivityLog

    with get_db() as db:
        rows = (
            db.query(ActivityLog)
            .filter_by(user_id=user_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .all()
        )
    return [
        {
            "event_type": row.event_type,
            "event_data": json.loads(row.event_data) if row.event_data else {},
            "created_at": row.created_at,
        }
        for row in rows
    ]


# ─── Activity logging ────────────────────────────────────────────────────────

def log_activity(
    user_id: int | None,
    event_type: str,
    event_data: dict | None = None,
) -> None:
    """
    Append an event to the activity_log table.

    Args:
        user_id:    User performing the action (None for system events)
        event_type: Short event key, e.g. "login", "quiz_complete", "badge_earned"
        event_data: Optional dict of additional context
    """
    from db.database import get_db
    from db.models import ActivityLog

    payload = json.dumps(event_data, default=str) if event_data else None
    with get_db() as db:
        db.add(ActivityLog(
            user_id=user_id,
            event_type=event_type,
            event_data=payload,
        ))

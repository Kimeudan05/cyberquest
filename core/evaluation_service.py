"""
core/evaluation_service.py
--------------------------
Learning effectiveness evaluation service for CyberQuest Kids.

Responsibilities:
  - Record pre-test and post-test quiz attempts (flagged in quiz_attempts)
  - Calculate pre/post score improvement for a user × module
  - Save learner feedback form submissions
  - Return evaluation data for admin reporting

Pre/post design:
  - A "pre-test" is taken before studying a module (attempt marked is_pre_test=True)
  - A "post-test" is taken after completing a module (attempt marked is_post_test=True)
  - Improvement = post_score - pre_score (positive = learning gain)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from db.repositories.quiz_repo import QuizRepository


# ─── Pre/post test recording ─────────────────────────────────────────────────

def record_pre_test(
    user_id: int,
    module_id: int,
    score_raw: int,
    score_total: int,
    difficulty: str,
    started_at: datetime,
) -> int:
    """
    Record a pre-test quiz attempt (is_pre_test=True).
    Returns the new QuizAttempt.id.
    """
    return _record_test_attempt(
        user_id=user_id,
        module_id=module_id,
        score_raw=score_raw,
        score_total=score_total,
        difficulty=difficulty,
        started_at=started_at,
        is_pre_test=True,
        is_post_test=False,
    )


def record_post_test(
    user_id: int,
    module_id: int,
    score_raw: int,
    score_total: int,
    difficulty: str,
    started_at: datetime,
) -> int:
    """
    Record a post-test quiz attempt (is_post_test=True).
    Returns the new QuizAttempt.id.
    """
    return _record_test_attempt(
        user_id=user_id,
        module_id=module_id,
        score_raw=score_raw,
        score_total=score_total,
        difficulty=difficulty,
        started_at=started_at,
        is_pre_test=False,
        is_post_test=True,
    )


def _record_test_attempt(
    user_id: int,
    module_id: int,
    score_raw: int,
    score_total: int,
    difficulty: str,
    started_at: datetime,
    is_pre_test: bool,
    is_post_test: bool,
) -> int:
    """Shared helper for pre/post test recording."""
    repo = QuizRepository()
    score_pct = score_raw / score_total if score_total > 0 else 0.0
    completed_at = datetime.now(timezone.utc)
    attempt_number = repo.get_attempt_count(user_id, module_id) + 1

    return repo.create_attempt(
        user_id=user_id,
        module_id=module_id,
        attempt_number=attempt_number,
        score_raw=score_raw,
        score_total=score_total,
        score_pct=score_pct,
        passed=False,           # pre/post tests do not trigger progression
        difficulty=difficulty,
        time_taken_secs=int((completed_at - started_at).total_seconds()),
        started_at=started_at,
        completed_at=completed_at,
        is_pre_test=is_pre_test,
        is_post_test=is_post_test,
    )


# ─── Pre/post comparison ─────────────────────────────────────────────────────

def compare_scores(user_id: int, module_id: int) -> dict | None:
    """
    Compare the user's first pre-test with their most recent post-test.

    Returns:
        {
            "pre_score":     float,  (0.0–1.0)
            "post_score":    float,
            "improvement":   float,  (post - pre; positive = learning gain)
            "has_pre_test":  bool,
            "has_post_test": bool,
        }
        or None if neither test has been taken.
    """
    repo = QuizRepository()
    pre_test = repo.get_first_pre_test(user_id=user_id, module_id=module_id)
    post_test = repo.get_latest_post_test(user_id=user_id, module_id=module_id)

    if pre_test is None and post_test is None:
        return None

    pre_score = pre_test.score_pct if pre_test else None
    post_score = post_test.score_pct if post_test else None
    improvement = (
        round(post_score - pre_score, 4)
        if pre_score is not None and post_score is not None
        else None
    )

    return {
        "pre_score": pre_score,
        "post_score": post_score,
        "improvement": improvement,
        "has_pre_test": pre_test is not None,
        "has_post_test": post_test is not None,
    }


# ─── Feedback form ───────────────────────────────────────────────────────────

def save_feedback(
    user_id: int,
    module_id: int | None,
    rating: int,
    enjoyment: str,
    difficulty_rating: str,
    free_text: str = "",
) -> None:
    """
    Save a learner's feedback form response to the activity_log.

    We store feedback as a structured JSON payload in activity_log.event_data
    rather than creating a separate table for MVP.

    Args:
        user_id:           User submitting the feedback
        module_id:         Module the feedback relates to (None = general)
        rating:            1–5 star overall rating
        enjoyment:         "too_easy" | "just_right" | "too_hard"
        difficulty_rating: "too_easy" | "just_right" | "too_hard"
        free_text:         Optional open-ended comment (max 500 chars)
    """
    import bleach
    from db.database import get_db
    from db.models import ActivityLog

    safe_text = bleach.clean(free_text, tags=[], strip=True)[:500]
    payload = json.dumps({
        "module_id": module_id,
        "rating": max(1, min(5, int(rating))),
        "enjoyment": enjoyment,
        "difficulty_rating": difficulty_rating,
        "free_text": safe_text,
    })

    with get_db() as db:
        db.add(ActivityLog(
            user_id=user_id,
            event_type="feedback_submitted",
            event_data=payload,
        ))


# ─── Evaluation report ───────────────────────────────────────────────────────

def get_evaluation_report(user_id: int) -> list[dict]:
    """
    Return pre/post comparison data for all modules the user has attempted.

    Used on the My Progress page to show learning gain per topic.
    """
    repo = QuizRepository()
    module_ids = repo.get_attempted_module_ids(user_id)
    report = []
    for module_id in module_ids:
        comparison = compare_scores(user_id=user_id, module_id=module_id)
        if comparison:
            comparison["module_id"] = module_id
            report.append(comparison)
    return report

"""
core/quiz_engine.py
-------------------
Quiz lifecycle service for CyberQuest Kids.

Responsibilities:
  - Select questions for a quiz sitting (respecting difficulty and age_group)
  - Evaluate an individual answer (correct / incorrect)
  - Calculate the final quiz score (raw, total, percentage)
  - Check mastery threshold
  - Record quiz attempts in the database
  - Provide the next-question index during an active quiz session

No Streamlit imports — all state is passed in / returned as plain data.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from config.constants import (
    MASTERY_THRESHOLD,
    MODERATE_THRESHOLD,
    POINTS_CORRECT_ANSWER,
    POINTS_MODULE_COMPLETE,
    POINTS_PERFECT_SCORE,
)
from db.repositories.quiz_repo import QuizRepository
from db.repositories.module_repo import ModuleRepository

if TYPE_CHECKING:
    from db.models import Question, QuizAttempt


# ─── Question selection ──────────────────────────────────────────────────────

def get_questions(
    module_id: int,
    difficulty: str,
    max_questions: int = 5,
    shuffle: bool = True,
) -> list[dict]:
    """
    Fetch active questions for a module at the given difficulty level.

    Returns a list of question dicts suitable for use in session_state.
    Questions are shuffled by default to prevent memorisation.

    Args:
        module_id:      ID of the module to fetch questions for
        difficulty:     beginner | intermediate | advanced
        max_questions:  Maximum number of questions to return (default 5)
        shuffle:        Whether to randomise question order

    Returns:
        List of dicts with keys: id, body, options, correct_option,
        explanation, hint, points
    """
    repo = QuizRepository()
    questions = repo.get_questions_for_module(
        module_id=module_id,
        difficulty=difficulty,
        active_only=True,
    )

    if shuffle:
        random.shuffle(questions)

    selected = questions[:max_questions]

    return [
        {
            "id": q.id,
            "body": q.body,
            "options": q.options,   # dict: {"a": ..., "b": ..., "c": ..., "d": ...}
            "correct_option": q.correct_option,
            "explanation": q.explanation,
            "hint": q.hint,
            "points": q.points,
        }
        for q in selected
    ]


# ─── Answer evaluation ───────────────────────────────────────────────────────

def evaluate_answer(question: dict, chosen_option: str) -> dict:
    """
    Check whether the learner's chosen_option is correct.

    Args:
        question:       Question dict from get_questions()
        chosen_option:  The letter chosen by the learner: a | b | c | d

    Returns:
        Dict with keys:
          correct (bool)       — was the answer right?
          points_earned (int)  — 0 or question["points"]
          explanation (str)    — feedback text to show
          correct_option (str) — the right answer letter
          correct_text (str)   — the text of the correct answer
    """
    is_correct = chosen_option.lower() == question["correct_option"].lower()
    return {
        "correct": is_correct,
        "points_earned": question["points"] if is_correct else 0,
        "explanation": question["explanation"],
        "hint": question.get("hint"),
        "correct_option": question["correct_option"],
        "correct_text": question["options"][question["correct_option"]],
    }


# ─── Score calculation ───────────────────────────────────────────────────────

def calculate_score(answers: list[dict]) -> dict:
    """
    Aggregate individual answer results into a quiz score.

    Args:
        answers:  List of result dicts from evaluate_answer()

    Returns:
        Dict with keys:
          score_raw (int)      — number of correct answers
          score_total (int)    — total number of questions
          score_pct (float)    — 0.0–1.0
          points_earned (int)  — total points for correct answers
          passed (bool)        — score_pct >= MASTERY_THRESHOLD
          is_perfect (bool)    — score_pct == 1.0
    """
    score_raw = sum(1 for a in answers if a["correct"])
    score_total = len(answers)
    score_pct = score_raw / score_total if score_total > 0 else 0.0
    points_earned = sum(a.get("points_earned", 0) for a in answers)

    is_perfect = score_pct == 1.0
    if is_perfect:
        points_earned += POINTS_PERFECT_SCORE

    passed = score_pct >= MASTERY_THRESHOLD

    return {
        "score_raw": score_raw,
        "score_total": score_total,
        "score_pct": score_pct,
        "points_earned": points_earned,
        "passed": passed,
        "is_perfect": is_perfect,
    }


def classify_performance(score_pct: float) -> str:
    """
    Classify a score percentage into a performance band.

    Returns:
        "mastered"    — score >= MASTERY_THRESHOLD (80%)
        "moderate"    — MODERATE_THRESHOLD <= score < MASTERY_THRESHOLD
        "struggling"  — score < MODERATE_THRESHOLD (50%)
    """
    if score_pct >= MASTERY_THRESHOLD:
        return "mastered"
    elif score_pct >= MODERATE_THRESHOLD:
        return "moderate"
    else:
        return "struggling"


def check_mastery(score_pct: float) -> bool:
    """Return True if score_pct meets the mastery threshold."""
    return score_pct >= MASTERY_THRESHOLD


# ─── Quiz attempt recording ──────────────────────────────────────────────────

def record_quiz_attempt(
    user_id: int,
    module_id: int,
    score_result: dict,
    difficulty: str,
    started_at: datetime,
    is_pre_test: bool = False,
    is_post_test: bool = False,
) -> int:
    """
    Persist a completed quiz attempt to the database.

    Args:
        user_id:        Authenticated user's ID
        module_id:      Module that was quizzed
        score_result:   Dict from calculate_score()
        difficulty:     Difficulty level attempted
        started_at:     UTC datetime when the quiz began
        is_pre_test:    True if this is a pre-test attempt
        is_post_test:   True if this is a post-test attempt

    Returns:
        The new QuizAttempt.id
    """
    repo = QuizRepository()
    completed_at = datetime.now(timezone.utc)
    time_taken = int((completed_at - started_at).total_seconds())

    attempt_number = repo.get_attempt_count(user_id, module_id) + 1

    attempt_id = repo.create_attempt(
        user_id=user_id,
        module_id=module_id,
        attempt_number=attempt_number,
        score_raw=score_result["score_raw"],
        score_total=score_result["score_total"],
        score_pct=score_result["score_pct"],
        passed=score_result["passed"],
        difficulty=difficulty,
        time_taken_secs=time_taken,
        started_at=started_at,
        completed_at=completed_at,
        is_pre_test=is_pre_test,
        is_post_test=is_post_test,
    )
    return attempt_id


# ─── Difficulty selection ────────────────────────────────────────────────────

def select_difficulty_for_user(
    age_group: str,
    current_level: int,
    topic_mastery: dict[str, bool],
    topic: str,
) -> str:
    """
    Determine the appropriate difficulty level for a given user and topic.
    Called by the adaptive engine when starting a new quiz.

    Logic:
      - If topic is mastered and user level >= 4 → advanced
      - If topic is mastered → intermediate
      - Otherwise → beginner (age-group appropriate)

    Args:
        age_group:      junior | explorer | ranger
        current_level:  User's current XP level (1–10)
        topic_mastery:  Dict of topic_key → bool (mastered or not)
        topic:          The topic being studied

    Returns:
        beginner | intermediate | advanced
    """
    from config.constants import (
        DIFFICULTY_ADVANCED,
        DIFFICULTY_BEGINNER,
        DIFFICULTY_INTERMEDIATE,
    )

    is_mastered = topic_mastery.get(topic, False)

    if age_group == "junior":
        return DIFFICULTY_BEGINNER

    if is_mastered and current_level >= 4:
        return DIFFICULTY_ADVANCED
    elif is_mastered:
        return DIFFICULTY_INTERMEDIATE
    else:
        return DIFFICULTY_BEGINNER

"""
db/repositories/quiz_repo.py
-----------------------------
QuizRepository — data access for questions and quiz_attempts.
"""

from __future__ import annotations

from datetime import datetime

from db.database import get_db
from db.models import Question, QuizAttempt


class QuizRepository:

    # ── Questions ─────────────────────────────────────────────────────────────

    def get_questions_for_module(
        self,
        module_id: int,
        difficulty: str,
        active_only: bool = True,
    ) -> list[Question]:
        with get_db() as db:
            q = db.query(Question).filter_by(
                module_id=module_id,
                difficulty=difficulty,
            )
            if active_only:
                q = q.filter_by(is_active=True)
            questions = q.all()
            for item in questions:
                db.expunge(item)
        return questions

    def get_question_by_id(self, question_id: int) -> Question | None:
        with get_db() as db:
            q = db.query(Question).filter_by(id=question_id).first()
            if q:
                db.expunge(q)
        return q

    # ── Quiz attempts ─────────────────────────────────────────────────────────

    def create_attempt(
        self,
        user_id: int,
        module_id: int,
        attempt_number: int,
        score_raw: int,
        score_total: int,
        score_pct: float,
        passed: bool,
        difficulty: str,
        time_taken_secs: int | None,
        started_at: datetime,
        completed_at: datetime | None,
        is_pre_test: bool = False,
        is_post_test: bool = False,
    ) -> int:
        """Insert a quiz attempt and return its ID."""
        with get_db() as db:
            attempt = QuizAttempt(
                user_id=user_id,
                module_id=module_id,
                attempt_number=attempt_number,
                score_raw=score_raw,
                score_total=score_total,
                score_pct=score_pct,
                passed=passed,
                difficulty=difficulty,
                time_taken_secs=time_taken_secs,
                started_at=started_at,
                completed_at=completed_at,
                is_pre_test=is_pre_test,
                is_post_test=is_post_test,
            )
            db.add(attempt)
            db.flush()
            attempt_id = attempt.id
        return attempt_id

    def get_attempt_count(self, user_id: int, module_id: int) -> int:
        with get_db() as db:
            return (
                db.query(QuizAttempt)
                .filter_by(user_id=user_id, module_id=module_id)
                .count()
            )

    def get_recent_attempts(
        self,
        user_id: int,
        limit: int = 10,
    ) -> list[QuizAttempt]:
        """Return the N most recent quiz attempts for rolling score average."""
        with get_db() as db:
            attempts = (
                db.query(QuizAttempt)
                .filter_by(user_id=user_id, is_pre_test=False, is_post_test=False)
                .order_by(QuizAttempt.completed_at.desc())
                .limit(limit)
                .all()
            )
            for a in attempts:
                db.expunge(a)
        return attempts

    def get_all_attempts_for_user(self, user_id: int) -> list[QuizAttempt]:
        with get_db() as db:
            attempts = (
                db.query(QuizAttempt)
                .filter_by(user_id=user_id)
                .order_by(QuizAttempt.completed_at.desc())
                .all()
            )
            for a in attempts:
                db.expunge(a)
        return attempts

    def get_attempted_module_ids(self, user_id: int) -> list[int]:
        with get_db() as db:
            rows = (
                db.query(QuizAttempt.module_id)
                .filter_by(user_id=user_id)
                .distinct()
                .all()
            )
        return [row[0] for row in rows]

    def get_first_pre_test(
        self, user_id: int, module_id: int
    ) -> QuizAttempt | None:
        with get_db() as db:
            a = (
                db.query(QuizAttempt)
                .filter_by(user_id=user_id, module_id=module_id, is_pre_test=True)
                .order_by(QuizAttempt.started_at.asc())
                .first()
            )
            if a:
                db.expunge(a)
        return a

    def get_latest_post_test(
        self, user_id: int, module_id: int
    ) -> QuizAttempt | None:
        with get_db() as db:
            a = (
                db.query(QuizAttempt)
                .filter_by(user_id=user_id, module_id=module_id, is_post_test=True)
                .order_by(QuizAttempt.completed_at.desc())
                .first()
            )
            if a:
                db.expunge(a)
        return a

"""
db/repositories/admin_repo.py
------------------------------
AdminRepository — data access for admin content management and metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.database import get_db
from db.models import (
    ActivityLog,
    Badge,
    Module,
    Question,
    QuizAttempt,
    Scenario,
    User,
    UserBadge,
)


class AdminRepository:

    # ── Module CRUD ───────────────────────────────────────────────────────────

    def create_module(
        self,
        title: str,
        topic: str,
        description: str,
        age_group: str,
        difficulty: str,
        icon: str,
        order_index: int,
        is_published: bool,
    ) -> int:
        with get_db() as db:
            m = Module(
                title=title, topic=topic, description=description,
                age_group=age_group, difficulty=difficulty,
                icon=icon, order_index=order_index, is_published=is_published,
            )
            db.add(m)
            db.flush()
            return m.id

    def update_module(self, module_id: int, **kwargs) -> None:
        with get_db() as db:
            db.query(Module).filter_by(id=module_id).update(kwargs)

    def delete_module(self, module_id: int) -> None:
        with get_db() as db:
            db.query(Module).filter_by(id=module_id).delete()

    # ── Question CRUD ─────────────────────────────────────────────────────────

    def create_question(
        self,
        module_id: int,
        body: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        correct_option: str,
        explanation: str,
        difficulty: str,
        hint: str | None,
        points: int,
    ) -> int:
        with get_db() as db:
            q = Question(
                module_id=module_id, body=body,
                option_a=option_a, option_b=option_b,
                option_c=option_c, option_d=option_d,
                correct_option=correct_option, explanation=explanation,
                difficulty=difficulty, hint=hint, points=points,
                is_active=True,
            )
            db.add(q)
            db.flush()
            return q.id

    def update_question(self, question_id: int, **kwargs) -> None:
        with get_db() as db:
            db.query(Question).filter_by(id=question_id).update(kwargs)

    def soft_delete_question(self, question_id: int) -> None:
        with get_db() as db:
            db.query(Question).filter_by(id=question_id).update({"is_active": False})

    # ── Badge CRUD ────────────────────────────────────────────────────────────

    def create_badge(
        self,
        name: str,
        description: str,
        image_filename: str,
        criteria_type: str,
        criteria_value: str,
        age_group: str,
        sort_order: int,
    ) -> int:
        with get_db() as db:
            b = Badge(
                name=name, description=description,
                image_filename=image_filename, criteria_type=criteria_type,
                criteria_value=criteria_value, age_group=age_group,
                sort_order=sort_order, is_active=True,
            )
            db.add(b)
            db.flush()
            return b.id

    def delete_badge(self, badge_id: int) -> None:
        with get_db() as db:
            db.query(UserBadge).filter_by(badge_id=badge_id).delete()
            db.query(Badge).filter_by(id=badge_id).delete()

    # ── Metrics ───────────────────────────────────────────────────────────────

    def get_engagement_metrics(self) -> dict:
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        with get_db() as db:
            total_users = db.query(User).filter_by(is_active=True, role="learner").count()
            active_this_week = (
                db.query(User)
                .filter(User.last_login >= one_week_ago, User.role == "learner")
                .count()
            )
            total_attempts = db.query(QuizAttempt).count()
            badge_count = db.query(UserBadge).count()

            attempts = db.query(QuizAttempt).all()
            avg_score = (
                sum(a.score_pct for a in attempts) / len(attempts)
                if attempts else 0.0
            )

            recent_logs = (
                db.query(ActivityLog)
                .order_by(ActivityLog.created_at.desc())
                .limit(50)
                .all()
            )
            recent_activity = [
                {
                    "user_id": log.user_id,
                    "event_type": log.event_type,
                    "created_at": log.created_at,
                }
                for log in recent_logs
            ]

        return {
            "total_users": total_users,
            "active_this_week": active_this_week,
            "total_quiz_attempts": total_attempts,
            "average_score": round(avg_score, 4),
            "badges_awarded": badge_count,
            "recent_activity": recent_activity,
        }

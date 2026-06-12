"""
db/repositories/user_repo.py
-----------------------------
UserRepository — data access for the users table.
"""

from __future__ import annotations

from datetime import datetime, timezone

from db.database import get_db
from db.models import User, UserPoints


class UserRepository:

    def create(
        self,
        username: str,
        password_hash: str,
        age: int,
        age_group: str,
        role: str = "learner",
    ) -> User:
        """Insert a new user and initialise their UserPoints record."""
        with get_db() as db:
            user = User(
                username=username,
                password_hash=password_hash,
                age=age,
                age_group=age_group,
                role=role,
                is_active=True,
                streak_count=0,
                total_points=0,
                current_level=1,
            )
            db.add(user)
            db.flush()
            db.add(UserPoints(user_id=user.id, total_points=0, xp_level=1))
            # Detach from session before returning to avoid lazy-load issues
            db.expunge(user)
        return user

    def get_by_username(self, username: str) -> User | None:
        with get_db() as db:
            user = db.query(User).filter_by(username=username).first()
            if user:
                db.expunge(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if user:
                db.expunge(user)
        return user

    def update_last_login(self, user_id: int) -> None:
        with get_db() as db:
            db.query(User).filter_by(id=user_id).update(
                {"last_login": datetime.now(timezone.utc)}
            )

    def update_level_and_points(
        self,
        user_id: int,
        total_points: int,
        current_level: int,
    ) -> None:
        with get_db() as db:
            db.query(User).filter_by(id=user_id).update(
                {"total_points": total_points, "current_level": current_level}
            )

    def update_streak(self, user_id: int, streak_count: int) -> None:
        with get_db() as db:
            db.query(User).filter_by(id=user_id).update(
                {"streak_count": streak_count}
            )

    def get_adaptive_profile(self, user_id: int) -> dict:
        """
        Build a minimal adaptive profile dict from the users table.
        Full profile is built by adaptive_engine.build_adaptive_profile().
        """
        user = self.get_by_id(user_id)
        if user is None:
            return {}
        return {
            "current_level": user.current_level,
            "average_score": 0.0,
            "streak_count": user.streak_count,
            "weak_topics": [],
            "strong_topics": [],
            "topic_mastery": {},
        }

    def get_all_active(self) -> list[User]:
        """Return all active user records (for admin panel)."""
        with get_db() as db:
            users = db.query(User).filter_by(is_active=True).order_by(User.username).all()
            for u in users:
                db.expunge(u)
        return users

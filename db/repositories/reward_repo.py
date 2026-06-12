"""
db/repositories/reward_repo.py
-------------------------------
RewardRepository — data access for user_points, badges, user_badges.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from db.database import get_db
from db.models import Badge, User, UserBadge, UserPoints


class RewardRepository:

    # ── Points ────────────────────────────────────────────────────────────────

    def add_points(self, user_id: int, points: int) -> int:
        """Add points to the user's running total. Returns new total."""
        with get_db() as db:
            record = db.query(UserPoints).filter_by(user_id=user_id).first()
            if record is None:
                record = UserPoints(user_id=user_id, total_points=points, xp_level=1)
                db.add(record)
            else:
                record.total_points += points
                record.last_updated = datetime.now(timezone.utc)
                # Reset daily total if it's a new UTC day
                if record.last_updated.date() != date.today():
                    record.points_today = points
                else:
                    record.points_today += points
            db.flush()
            new_total = record.total_points
        return new_total

    def get_total_points(self, user_id: int) -> int:
        with get_db() as db:
            record = db.query(UserPoints).filter_by(user_id=user_id).first()
        return record.total_points if record else 0

    def set_xp_level(self, user_id: int, level: int) -> None:
        with get_db() as db:
            db.query(UserPoints).filter_by(user_id=user_id).update(
                {"xp_level": level}
            )

    def has_received_points_today(self, user_id: int) -> bool:
        """Return True if the user already received daily login points today (UTC)."""
        with get_db() as db:
            record = db.query(UserPoints).filter_by(user_id=user_id).first()
            if record is None:
                return False
            return (
                record.last_updated is not None
                and record.last_updated.date() == date.today()
                and record.points_today > 0
            )

    # ── Badges ────────────────────────────────────────────────────────────────

    def get_all_active_badges(self) -> list[Badge]:
        with get_db() as db:
            badges = (
                db.query(Badge)
                .filter_by(is_active=True)
                .order_by(Badge.sort_order)
                .all()
            )
            for b in badges:
                db.expunge(b)
        return badges

    def get_user_badges(self, user_id: int) -> list[UserBadge]:
        with get_db() as db:
            ubs = (
                db.query(UserBadge)
                .filter_by(user_id=user_id)
                .all()
            )
            for ub in ubs:
                db.expunge(ub)
        return ubs

    def award_badge(self, user_id: int, badge_id: int) -> None:
        """Award a badge to a user. No-op if already held."""
        with get_db() as db:
            existing = (
                db.query(UserBadge)
                .filter_by(user_id=user_id, badge_id=badge_id)
                .first()
            )
            if existing is None:
                db.add(UserBadge(user_id=user_id, badge_id=badge_id))

    def get_unnotified_badges(self, user_id: int) -> list[UserBadge]:
        """Return badges earned but not yet shown in the reveal animation."""
        with get_db() as db:
            ubs = (
                db.query(UserBadge)
                .filter_by(user_id=user_id, notified=False)
                .all()
            )
            for ub in ubs:
                db.expunge(ub)
        return ubs

    def mark_badge_notified(self, user_badge_id: int) -> None:
        with get_db() as db:
            db.query(UserBadge).filter_by(id=user_badge_id).update(
                {"notified": True}
            )

    # ── Leaderboard ───────────────────────────────────────────────────────────

    def get_top_users_by_points(self, limit: int = 10) -> list[User]:
        """Return top N active users sorted by total_points descending."""
        with get_db() as db:
            users = (
                db.query(User)
                .filter_by(is_active=True, role="learner")
                .order_by(User.total_points.desc())
                .limit(limit)
                .all()
            )
            for u in users:
                db.expunge(u)
        return users

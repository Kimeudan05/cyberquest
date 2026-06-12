"""
db/repositories/progress_repo.py
----------------------------------
ProgressRepository — data access for the progress table.
"""

from __future__ import annotations

from datetime import datetime, timezone

from db.database import get_db
from db.models import Progress


class ProgressRepository:

    def get(self, user_id: int, module_id: int) -> Progress | None:
        """Return the Progress record for user × module, or None."""
        with get_db() as db:
            rec = db.query(Progress).filter_by(
                user_id=user_id, module_id=module_id
            ).first()
            if rec:
                # Eagerly load the module relationship before expunge
                _ = rec.module
                db.expunge(rec)
        return rec

    def create(
        self,
        user_id: int,
        module_id: int,
        is_completed: bool,
        best_score_pct: float,
        attempt_count: int,
        mastery_level: int,
    ) -> Progress:
        with get_db() as db:
            rec = Progress(
                user_id=user_id,
                module_id=module_id,
                is_completed=is_completed,
                best_score_pct=best_score_pct,
                attempt_count=attempt_count,
                last_attempted=datetime.now(timezone.utc),
                mastery_level=mastery_level,
            )
            db.add(rec)
            db.flush()
            db.expunge(rec)
        return rec

    def update(
        self,
        user_id: int,
        module_id: int,
        is_completed: bool,
        best_score_pct: float,
        attempt_count: int,
        mastery_level: int,
    ) -> None:
        with get_db() as db:
            db.query(Progress).filter_by(
                user_id=user_id, module_id=module_id
            ).update({
                "is_completed": is_completed,
                "best_score_pct": best_score_pct,
                "attempt_count": attempt_count,
                "mastery_level": mastery_level,
                "last_attempted": datetime.now(timezone.utc),
            })

    def get_all_for_user(self, user_id: int) -> list[Progress]:
        """Return all progress records for a user, with module relationship loaded."""
        with get_db() as db:
            from sqlalchemy.orm import joinedload
            records = (
                db.query(Progress)
                .options(joinedload(Progress.module))
                .filter_by(user_id=user_id)
                .all()
            )
            for rec in records:
                _ = rec.module  # force load before expunge
                db.expunge(rec)
        return records

    def get_completed_count(self, user_id: int) -> int:
        with get_db() as db:
            return (
                db.query(Progress)
                .filter_by(user_id=user_id, is_completed=True)
                .count()
            )

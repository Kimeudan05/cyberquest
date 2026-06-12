"""
db/repositories/module_repo.py
-------------------------------
ModuleRepository — data access for modules, scenarios.
"""

from __future__ import annotations

from db.database import get_db
from db.models import Module, Scenario


class ModuleRepository:

    def get_by_id(self, module_id: int) -> Module | None:
        with get_db() as db:
            m = db.query(Module).filter_by(id=module_id).first()
            if m:
                db.expunge(m)
        return m

    def get_all(self) -> list[Module]:
        with get_db() as db:
            modules = db.query(Module).order_by(Module.topic, Module.order_index).all()
            for m in modules:
                db.expunge(m)
        return modules

    def get_for_age_group(
        self,
        age_group: str,
        published_only: bool = True,
    ) -> list[Module]:
        """Return modules for a specific age_group (and 'all' tagged ones)."""
        with get_db() as db:
            q = db.query(Module).filter(
                Module.age_group.in_([age_group, "all"])
            )
            if published_only:
                q = q.filter_by(is_published=True)
            modules = q.order_by(Module.topic, Module.order_index).all()
            for m in modules:
                db.expunge(m)
        return modules

    def get_by_topic_and_age_group(
        self,
        topic: str,
        age_group: str,
        published_only: bool = True,
    ) -> list[Module]:
        with get_db() as db:
            q = db.query(Module).filter_by(topic=topic, age_group=age_group)
            if published_only:
                q = q.filter_by(is_published=True)
            modules = q.order_by(Module.order_index).all()
            for m in modules:
                db.expunge(m)
        return modules

    def get_by_topic_age_difficulty(
        self,
        topic: str,
        age_group: str,
        difficulty: str,
    ) -> Module | None:
        with get_db() as db:
            m = db.query(Module).filter_by(
                topic=topic,
                age_group=age_group,
                difficulty=difficulty,
            ).first()
            if m:
                db.expunge(m)
        return m

    def get_scenarios(self, module_id: int) -> list[Scenario]:
        with get_db() as db:
            scenarios = (
                db.query(Scenario)
                .filter_by(module_id=module_id)
                .order_by(Scenario.order_index)
                .all()
            )
            for s in scenarios:
                db.expunge(s)
        return scenarios

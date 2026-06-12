"""
core/content_service.py
-----------------------
Content retrieval service for CyberQuest Kids.

Responsibilities:
  - Fetch modules filtered by age_group and published status
  - Fetch scenarios for a module (ordered by order_index)
  - Filter content by age_group (junior / explorer / ranger)
  - Return structured dicts suitable for UI rendering

No Streamlit imports. All filtering is done in service logic or via the ORM.
"""

from __future__ import annotations

from db.repositories.module_repo import ModuleRepository


# ─── Modules ─────────────────────────────────────────────────────────────────

def get_modules_for_user(
    age_group: str,
    published_only: bool = True,
) -> list[dict]:
    """
    Return all modules appropriate for the given age group.

    Includes modules tagged for the specific age_group plus those tagged "all".
    Results are sorted by topic, then order_index.

    Args:
        age_group:      junior | explorer | ranger
        published_only: Skip unpublished modules (default True)

    Returns:
        List of module dicts with keys:
            id, title, topic, description, difficulty,
            order_index, icon, is_published
    """
    repo = ModuleRepository()
    modules = repo.get_for_age_group(
        age_group=age_group,
        published_only=published_only,
    )
    return [_module_to_dict(m) for m in modules]


def get_module(module_id: int) -> dict | None:
    """Return a single module dict by ID, or None if not found."""
    repo = ModuleRepository()
    module = repo.get_by_id(module_id)
    return _module_to_dict(module) if module else None


def get_modules_by_topic(
    topic: str,
    age_group: str,
    published_only: bool = True,
) -> list[dict]:
    """
    Return all difficulty variants of a topic for a given age group.
    Used to show 'beginner → intermediate → advanced' progression.
    """
    repo = ModuleRepository()
    modules = repo.get_by_topic_and_age_group(
        topic=topic,
        age_group=age_group,
        published_only=published_only,
    )
    return [_module_to_dict(m) for m in modules]


def get_all_modules_admin() -> list[dict]:
    """Return all modules (including unpublished) for the admin panel."""
    repo = ModuleRepository()
    modules = repo.get_all()
    return [_module_to_dict(m) for m in modules]


# ─── Scenarios ───────────────────────────────────────────────────────────────

def get_scenarios_for_module(module_id: int) -> list[dict]:
    """
    Return all scenarios for a module, ordered by order_index.

    Returns:
        List of scenario dicts:
            id, module_id, title, body, order_index, image_filename
    """
    repo = ModuleRepository()
    scenarios = repo.get_scenarios(module_id=module_id)
    return [
        {
            "id": s.id,
            "module_id": s.module_id,
            "title": s.title,
            "body": s.body,
            "order_index": s.order_index,
            "image_filename": s.image_filename,
        }
        for s in scenarios
    ]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _module_to_dict(module) -> dict:  # noqa: ANN001
    """Convert a Module ORM object to a plain dict."""
    from config.constants import TOPICS
    topic_meta = TOPICS.get(module.topic, {})
    return {
        "id": module.id,
        "title": module.title,
        "topic": module.topic,
        "topic_label": topic_meta.get("label", module.topic),
        "description": module.description,
        "age_group": module.age_group,
        "difficulty": module.difficulty,
        "order_index": module.order_index,
        "icon": module.icon,
        "is_published": module.is_published,
        "created_at": module.created_at,
        "updated_at": module.updated_at,
    }

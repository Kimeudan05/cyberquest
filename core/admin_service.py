"""
core/admin_service.py
---------------------
Content management service for CyberQuest Kids admin panel.

Responsibilities:
  - CRUD for modules, scenarios, questions, and badges
  - Publish / unpublish content items
  - Fetch engagement metrics for the admin metrics page
  - Content validation (reuses or mirrors auth_service validators)

Only callable from admin-gated pages.
No Streamlit imports.
"""

from __future__ import annotations

import bleach
from datetime import datetime, timezone

from db.repositories.admin_repo import AdminRepository
from db.repositories.module_repo import ModuleRepository


# ─── Text sanitisation ────────────────────────────────────────────────────────

_ALLOWED_TAGS: list[str] = []  # No HTML allowed in user-supplied text
_MAX_TITLE_LEN = 100
_MAX_BODY_LEN = 5000


def _sanitise(text: str, max_len: int = _MAX_BODY_LEN) -> str:
    """Strip HTML and enforce length limit on admin-supplied text."""
    cleaned = bleach.clean(text, tags=_ALLOWED_TAGS, strip=True).strip()
    return cleaned[:max_len]


# ─── Module management ───────────────────────────────────────────────────────

def create_module(
    title: str,
    topic: str,
    description: str,
    age_group: str,
    difficulty: str,
    icon: str = "📚",
    order_index: int = 0,
    publish: bool = False,
) -> tuple[bool, str, int | None]:
    """
    Create a new module record.

    Returns:
        (True, "", new_id)  on success
        (False, error, None) on failure
    """
    from config.constants import AGE_GROUP_LIST, DIFFICULTY_LEVELS, TOPIC_LIST
    if topic not in TOPIC_LIST:
        return False, f"Unknown topic: {topic}", None
    if age_group not in AGE_GROUP_LIST + ["all"]:
        return False, f"Unknown age_group: {age_group}", None
    if difficulty not in DIFFICULTY_LEVELS:
        return False, f"Unknown difficulty: {difficulty}", None

    repo = AdminRepository()
    try:
        new_id = repo.create_module(
            title=_sanitise(title, _MAX_TITLE_LEN),
            topic=topic,
            description=_sanitise(description),
            age_group=age_group,
            difficulty=difficulty,
            icon=icon,
            order_index=order_index,
            is_published=publish,
        )
        return True, "", new_id
    except Exception as exc:
        return False, str(exc), None


def update_module(module_id: int, **kwargs) -> tuple[bool, str]:
    """Update mutable fields on a module. Returns (ok, error_msg)."""
    if "title" in kwargs:
        kwargs["title"] = _sanitise(kwargs["title"], _MAX_TITLE_LEN)
    if "description" in kwargs:
        kwargs["description"] = _sanitise(kwargs["description"])
    repo = AdminRepository()
    try:
        repo.update_module(module_id=module_id, **kwargs)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def delete_module(module_id: int) -> tuple[bool, str]:
    """Delete a module and cascade to its scenarios and questions."""
    repo = AdminRepository()
    try:
        repo.delete_module(module_id)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def publish_module(module_id: int, publish: bool = True) -> tuple[bool, str]:
    """Toggle published state of a module."""
    return update_module(module_id, is_published=publish)


# ─── Question management ─────────────────────────────────────────────────────

def create_question(
    module_id: int,
    body: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_option: str,
    explanation: str,
    difficulty: str,
    hint: str = "",
    points: int = 10,
) -> tuple[bool, str, int | None]:
    """Create a new MCQ question. Returns (ok, error, new_id)."""
    if correct_option not in ("a", "b", "c", "d"):
        return False, "correct_option must be one of: a, b, c, d", None

    repo = AdminRepository()
    try:
        new_id = repo.create_question(
            module_id=module_id,
            body=_sanitise(body),
            option_a=_sanitise(option_a, 300),
            option_b=_sanitise(option_b, 300),
            option_c=_sanitise(option_c, 300),
            option_d=_sanitise(option_d, 300),
            correct_option=correct_option.lower(),
            explanation=_sanitise(explanation),
            difficulty=difficulty,
            hint=_sanitise(hint) if hint else None,
            points=max(1, int(points)),
        )
        return True, "", new_id
    except Exception as exc:
        return False, str(exc), None


def update_question(question_id: int, **kwargs) -> tuple[bool, str]:
    """Update mutable fields on a question. Returns (ok, error_msg)."""
    for text_field in ("body", "option_a", "option_b", "option_c", "option_d",
                       "explanation", "hint"):
        if text_field in kwargs:
            kwargs[text_field] = _sanitise(kwargs[text_field])
    repo = AdminRepository()
    try:
        repo.update_question(question_id=question_id, **kwargs)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def delete_question(question_id: int) -> tuple[bool, str]:
    """Soft-delete a question (sets is_active = False)."""
    repo = AdminRepository()
    try:
        repo.soft_delete_question(question_id)
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ─── Badge management ────────────────────────────────────────────────────────

def create_badge(
    name: str,
    description: str,
    image_filename: str,
    criteria_type: str,
    criteria_value: str,
    age_group: str = "all",
    sort_order: int = 0,
) -> tuple[bool, str, int | None]:
    """Create a new badge in the catalogue. Returns (ok, error, new_id)."""
    repo = AdminRepository()
    try:
        new_id = repo.create_badge(
            name=_sanitise(name, 60),
            description=_sanitise(description, 200),
            image_filename=_sanitise(image_filename, 100),
            criteria_type=criteria_type,
            criteria_value=criteria_value,
            age_group=age_group,
            sort_order=sort_order,
        )
        return True, "", new_id
    except Exception as exc:
        return False, str(exc), None


def delete_badge(badge_id: int) -> tuple[bool, str]:
    """Delete a badge and all user_badge records for it."""
    repo = AdminRepository()
    try:
        repo.delete_badge(badge_id)
        return True, ""
    except Exception as exc:
        return False, str(exc)


# ─── Metrics ─────────────────────────────────────────────────────────────────

def get_engagement_metrics() -> dict:
    """
    Return a metrics summary for the admin metrics dashboard.

    Returns:
        {
            "total_users":        int,
            "active_this_week":   int,
            "total_quiz_attempts": int,
            "average_score":      float,
            "badges_awarded":     int,
            "recent_activity":    list[dict]  (last 50 events)
        }
    """
    repo = AdminRepository()
    return repo.get_engagement_metrics()

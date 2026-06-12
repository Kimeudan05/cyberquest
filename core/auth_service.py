"""
core/auth_service.py
--------------------
Authentication service for CyberQuest Kids.

Responsibilities:
  - Register new users (validate input, hash password, create DB record)
  - Authenticate users at login (verify password, update last_login)
  - Manage session state (set_session, clear_session)
  - Guard pages that require authentication or admin role

No Streamlit imports except where session_state is explicitly needed.
All validation logic lives here, not in pages.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import bcrypt
import streamlit as st

from config.constants import (
    AGE_MAX,
    AGE_MIN,
    PASSWORD_MAX_LEN,
    PASSWORD_MIN_LEN,
    ROLE_ADMIN,
    ROLE_LEARNER,
    USERNAME_ALLOWED_CHARS_PATTERN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
    get_age_group,
)
from config.settings import BCRYPT_ROUNDS
from db.repositories.user_repo import UserRepository

if TYPE_CHECKING:
    from db.models import User


# ─── Password helpers ────────────────────────────────────────────────────────

def hash_password(plaintext: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    return bcrypt.hashpw(
        plaintext.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the stored bcrypt hash."""
    return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))


# ─── Input validation ────────────────────────────────────────────────────────

def validate_username(username: str) -> str | None:
    """
    Validate a proposed username.
    Returns an error message string, or None if valid.
    """
    if len(username) < USERNAME_MIN_LEN:
        return f"Username must be at least {USERNAME_MIN_LEN} characters."
    if len(username) > USERNAME_MAX_LEN:
        return f"Username must be {USERNAME_MAX_LEN} characters or fewer."
    if not re.match(USERNAME_ALLOWED_CHARS_PATTERN, username):
        return "Username may only contain letters, numbers, and underscores."
    return None


def validate_password(password: str) -> str | None:
    """
    Validate a proposed password.
    Returns an error message string, or None if valid.
    """
    if len(password) < PASSWORD_MIN_LEN:
        return f"Password must be at least {PASSWORD_MIN_LEN} characters."
    if len(password) > PASSWORD_MAX_LEN:
        return f"Password must be {PASSWORD_MAX_LEN} characters or fewer."
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        return "Password must contain at least one letter and one number."
    return None


def validate_age(age: int) -> str | None:
    """
    Validate a self-reported age.
    Returns an error message string, or None if valid.
    """
    if not (AGE_MIN <= age <= AGE_MAX):
        return f"Age must be between {AGE_MIN} and {AGE_MAX}."
    return None


# ─── Registration ────────────────────────────────────────────────────────────

def register_user(
    username: str,
    password: str,
    age: int,
) -> tuple[bool, str]:
    """
    Register a new learner account.

    Returns:
        (True, "")          on success
        (False, error_msg)  on failure
    """
    # Validate inputs
    err = validate_username(username)
    if err:
        return False, err
    err = validate_password(password)
    if err:
        return False, err
    err = validate_age(age)
    if err:
        return False, err

    repo = UserRepository()

    # Check username uniqueness
    if repo.get_by_username(username) is not None:
        return False, "That username is already taken. Please choose another."

    age_group = get_age_group(age)
    password_hash = hash_password(password)

    try:
        repo.create(
            username=username,
            password_hash=password_hash,
            age=age,
            age_group=age_group,
        )
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"Registration failed: {exc}"


# ─── Login ───────────────────────────────────────────────────────────────────

def login_user(username: str, password: str) -> tuple[bool, str]:
    """
    Authenticate a user and populate st.session_state on success.

    Returns:
        (True, "")          on success
        (False, error_msg)  on failure
    """
    if not username or not password:
        return False, "Please enter both a username and password."

    repo = UserRepository()
    user: User | None = repo.get_by_username(username)

    if user is None or not user.is_active:
        return False, "Username or password is incorrect."

    if not verify_password(password, user.password_hash):
        return False, "Username or password is incorrect."

    # Successful login — populate session
    _set_session(user)
    repo.update_last_login(user.id)
    return True, ""


# ─── Session management ──────────────────────────────────────────────────────

def _set_session(user: "User") -> None:
    """Write user data into st.session_state. Called only by login_user."""
    from db.repositories.user_repo import UserRepository
    repo = UserRepository()
    adaptive = repo.get_adaptive_profile(user.id)

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user.id
    st.session_state["username"] = user.username
    st.session_state["role"] = user.role
    st.session_state["age_group"] = user.age_group
    st.session_state["adaptive_profile"] = adaptive
    st.session_state["active_quiz"] = None
    st.session_state["selected_module_id"] = None
    st.session_state["last_page"] = "home"


def clear_session() -> None:
    """Wipe all CyberQuest session keys. Call on logout."""
    for key in [
        "authenticated", "user_id", "username", "role",
        "age_group", "adaptive_profile", "active_quiz",
        "selected_module_id", "last_page",
    ]:
        st.session_state.pop(key, None)


def logout_user() -> None:
    """Log the current user out and clear session state."""
    clear_session()
    st.rerun()


# ─── Page guards ────────────────────────────────────────────────────────────

def require_login() -> None:
    """
    Call at the top of any learner page.
    Stops rendering and redirects to login if not authenticated.
    """
    if not st.session_state.get("authenticated", False):
        st.warning("🔐 Please log in to access this page.")
        st.stop()


def require_admin() -> None:
    """
    Call at the top of any admin page.
    Stops rendering if not authenticated as admin.
    """
    require_login()
    if st.session_state.get("role") != ROLE_ADMIN:
        st.error("🚫 You do not have permission to access this page.")
        st.stop()


def get_current_user_id() -> int | None:
    """Return the authenticated user's ID, or None if not logged in."""
    return st.session_state.get("user_id")


def get_current_role() -> str:
    """Return the authenticated user's role (learner or admin)."""
    return st.session_state.get("role", ROLE_LEARNER)


def is_authenticated() -> bool:
    """Return True if a user is currently logged in."""
    return st.session_state.get("authenticated", False)

"""
config/settings.py
------------------
Centralised configuration for CyberQuest Kids.

Reads values in this priority order:
  1. st.secrets (when running in Streamlit context)
  2. Environment variables
  3. Hard-coded defaults (safe for local dev only)

Usage:
    from config.settings import DATABASE_URL, BCRYPT_ROUNDS, DEBUG
"""

from __future__ import annotations

import os

# ── Lazy import of streamlit so this module can be imported in tests
# ── without a running Streamlit server.
def _get_secret(section: str, key: str, default: str) -> str:
    """
    Attempt to read a value from st.secrets; fall back to an env var,
    then to the provided default.
    """
    try:
        import streamlit as st
        return st.secrets.get(section, {}).get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)


# ─── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = _get_secret(
    "database",
    "DATABASE_URL",
    "sqlite:///cyberquest.db",
)

# ─── Security ─────────────────────────────────────────────────────────────────
BCRYPT_ROUNDS: int = int(
    _get_secret("security", "BCRYPT_ROUNDS", "12")
)

ADMIN_SEED_PASSWORD: str = _get_secret(
    "app",
    "ADMIN_SEED_PASSWORD",
    "ChangeMe123!",   # Must be overridden in production
)

# ─── Application ──────────────────────────────────────────────────────────────
DEBUG: bool = _get_secret("app", "DEBUG", "true").lower() == "true"

APP_NAME: str = "CyberQuest Kids"
APP_VERSION: str = "0.1.0"

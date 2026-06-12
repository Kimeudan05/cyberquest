"""
db/database.py
--------------
Database engine initialisation, session factory, and the get_db()
context manager used by every repository.

Supports both SQLite (local dev) and PostgreSQL (production) via a
single DATABASE_URL setting — no other code changes needed to switch.

Usage:
    from db.database import get_db, init_db

    # Initialise all tables (run once at startup)
    init_db()

    # Use in a repository method
    with get_db() as db:
        user = db.query(User).filter_by(username="alice").first()
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import DATABASE_URL, DEBUG

logger = logging.getLogger(__name__)

# ─── Engine ───────────────────────────────────────────────────────────────────

# SQLite-specific: enable WAL mode and foreign key enforcement
_connect_args: dict = {}
_engine_kwargs: dict = {
    "echo": DEBUG,           # SQL logging in debug mode
    "pool_pre_ping": True,   # Detect stale connections
}

if DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    _engine_kwargs["connect_args"] = _connect_args
else:
    # PostgreSQL: use a connection pool
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

engine = create_engine(DATABASE_URL, **_engine_kwargs)


# Enable SQLite foreign key enforcement per connection
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


# ─── Session factory ──────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # Avoid lazy-load issues after commit
)


# ─── Declarative base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Shared declarative base for all ORM models.
    Importing this in models.py registers all table definitions.
    """
    pass


# ─── Session context manager ──────────────────────────────────────────────────

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and guarantee cleanup.

    Commits on success, rolls back on any exception, and always
    closes the session. Use this in every repository method.

    Example:
        with get_db() as db:
            db.add(new_user)
        # session is committed and closed here
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Database transaction rolled back")
        raise
    finally:
        db.close()


# ─── Database initialisation ──────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables defined in models.py if they do not already exist.
    Safe to call on every application startup (idempotent).
    """
    # Import models here so Base.metadata is populated before create_all
    from db import models  # noqa: F401  (side-effect import)

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised: %s", DATABASE_URL)


def drop_all_tables() -> None:
    """
    Drop all tables. USE ONLY IN TESTS — never in production code.
    """
    from db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped.")


def health_check() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False

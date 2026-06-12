"""
data/seed_db.py
---------------
Database initialisation and seed data loader for CyberQuest Kids.

What this script does:
  1. Creates all database tables (idempotent — safe to re-run)
  2. Seeds modules, scenarios, questions, and badges from JSON files
  3. Creates the default admin account (password from settings)

Run with:
    python -m data.seed_db

Or from the project root:
    .venv\\Scripts\\python -m data.seed_db
"""

from __future__ import annotations

import json
import io
import logging
import sys
from pathlib import Path

# ── Fix emoji output on Windows terminals that use cp1252 ────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Make sure the project root is on the Python path ─────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.database import get_db, init_db
from db.models import Badge, Module, Question, Scenario, User, UserPoints
from config.settings import ADMIN_SEED_PASSWORD, BCRYPT_ROUNDS

import bcrypt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "seed_content"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_json(filename: str) -> list | dict:
    path = SEED_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(
        plaintext.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")


# ─── Seeding functions ────────────────────────────────────────────────────────

def seed_modules() -> dict[tuple, int]:
    """
    Insert modules from modules.json.
    Returns a lookup dict: (topic, age_group, difficulty) → module_id
    """
    data = _load_json("modules.json")
    module_data = data if isinstance(data, list) else data["modules"]
    index: dict[tuple, int] = {}

    with get_db() as db:
        for item in module_data:
            key = (item["topic"], item["age_group"], item["difficulty"])
            existing = (
                db.query(Module)
                .filter_by(
                    topic=item["topic"],
                    age_group=item["age_group"],
                    difficulty=item["difficulty"],
                )
                .first()
            )
            if existing:
                index[key] = existing.id
                logger.info("  Module already exists: %s", existing.title)
                continue

            module = Module(
                title=item["title"],
                topic=item["topic"],
                description=item["description"],
                age_group=item["age_group"],
                difficulty=item["difficulty"],
                order_index=item.get("order_index", 0),
                icon=item.get("icon", "📚"),
                is_published=item.get("is_published", False),
            )
            db.add(module)
            db.flush()  # get the generated id before commit
            index[key] = module.id
            logger.info("  Seeded module: %s (id=%d)", module.title, module.id)

    return index


def seed_scenarios(module_index: dict[tuple, int]) -> None:
    """Insert scenarios from scenarios.json, resolving module_ref to module_id."""
    scenarios = _load_json("scenarios.json")
    with get_db() as db:
        for item in scenarios:
            ref = item["module_ref"]
            key = (ref["topic"], ref["age_group"], ref["difficulty"])
            module_id = module_index.get(key)
            if module_id is None:
                logger.warning("  Skipping scenario — module not found: %s", key)
                continue

            existing = (
                db.query(Scenario)
                .filter_by(module_id=module_id, title=item["title"])
                .first()
            )
            if existing:
                logger.info("  Scenario already exists: %s", item["title"])
                continue

            scenario = Scenario(
                module_id=module_id,
                title=item["title"],
                body=item["body"],
                order_index=item.get("order_index", 0),
                image_filename=item.get("image_filename"),
            )
            db.add(scenario)
            logger.info("  Seeded scenario: %s → module_id=%d", item["title"], module_id)


def seed_questions(module_index: dict[tuple, int]) -> None:
    """Insert questions from questions.json, resolving module_ref to module_id."""
    question_sets = _load_json("questions.json")
    with get_db() as db:
        for qset in question_sets:
            ref = qset["module_ref"]
            key = (ref["topic"], ref["age_group"], ref["difficulty"])
            module_id = module_index.get(key)
            if module_id is None:
                logger.warning("  Skipping questions — module not found: %s", key)
                continue

            for q in qset["questions"]:
                existing = (
                    db.query(Question)
                    .filter_by(module_id=module_id, body=q["body"])
                    .first()
                )
                if existing:
                    logger.info("  Question already exists: %.50s…", q["body"])
                    continue

                question = Question(
                    module_id=module_id,
                    body=q["body"],
                    option_a=q["option_a"],
                    option_b=q["option_b"],
                    option_c=q["option_c"],
                    option_d=q["option_d"],
                    correct_option=q["correct_option"],
                    explanation=q["explanation"],
                    difficulty=q["difficulty"],
                    hint=q.get("hint"),
                    points=q.get("points", 10),
                    is_active=True,
                )
                db.add(question)
                logger.info("  Seeded question: %.50s…", q["body"])


def seed_badges() -> None:
    """Insert badges from badges.json."""
    badges = _load_json("badges.json")
    with get_db() as db:
        for item in badges:
            existing = db.query(Badge).filter_by(name=item["name"]).first()
            if existing:
                logger.info("  Badge already exists: %s", item["name"])
                continue

            badge = Badge(
                name=item["name"],
                description=item["description"],
                image_filename=item["image_filename"],
                criteria_type=item["criteria_type"],
                criteria_value=item["criteria_value"],
                age_group=item.get("age_group", "all"),
                is_active=True,
                sort_order=item.get("sort_order", 0),
            )
            db.add(badge)
            logger.info("  Seeded badge: %s", item["name"])


def seed_admin_user() -> None:
    """Create the default admin account if it does not exist."""
    with get_db() as db:
        existing = db.query(User).filter_by(username="admin").first()
        if existing:
            logger.info("  Admin user already exists.")
            return

        admin = User(
            username="admin",
            password_hash=_hash_password(ADMIN_SEED_PASSWORD),
            age=99,            # Sentinel value — admin is not a learner
            age_group="ranger",
            role="admin",
            is_active=True,
            streak_count=0,
            total_points=0,
            current_level=1,
        )
        db.add(admin)
        db.flush()

        points = UserPoints(user_id=admin.id, total_points=0, xp_level=1)
        db.add(points)

        logger.info(
            "  Admin user created (username=admin). "
            "Change the password via the Admin panel after first login!"
        )


# ─── Main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    logger.info("═" * 55)
    logger.info("  CyberQuest Kids — Database Seed Script")
    logger.info("═" * 55)

    logger.info("\n[1/5] Initialising database tables…")
    init_db()
    logger.info("  Tables created (or already exist).")

    logger.info("\n[2/5] Seeding modules…")
    module_index = seed_modules()
    logger.info("  %d module keys in index.", len(module_index))

    logger.info("\n[3/5] Seeding scenarios…")
    seed_scenarios(module_index)

    logger.info("\n[4/5] Seeding questions…")
    seed_questions(module_index)

    logger.info("\n[5/5] Seeding badges…")
    seed_badges()

    logger.info("\n[+] Seeding admin user…")
    seed_admin_user()

    logger.info("\n" + "═" * 55)
    logger.info("  ✅  Seed complete! Run: streamlit run app.py")
    logger.info("═" * 55)


if __name__ == "__main__":
    run()

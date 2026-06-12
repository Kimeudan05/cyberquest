"""
db/models.py
------------
All 12 SQLAlchemy ORM models for CyberQuest Kids.

Tables:
  1.  users            — Learner and admin accounts
  2.  modules          — Curriculum modules (topics × difficulty × age_group)
  3.  scenarios        — Narrative story content linked to a module
  4.  questions        — Multiple-choice questions linked to a module
  5.  quiz_attempts    — Each quiz sitting: user × module × score
  6.  progress         — Per-user per-module progress snapshot
  7.  badges           — Badge catalogue with unlock criteria
  8.  user_badges      — Many-to-many: user ↔ badge, earned_at
  9.  user_points      — Running points total and XP level per user
  10. activity_log     — Append-only event log for every significant action
  11. recommendations  — Rule-engine output: topics recommended per user
  12. admin_content    — Draft/published flag for admin-managed content items

All timestamps are stored as UTC.
All text fields that accept user input have explicit max length limits.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    """Return a timezone-aware UTC datetime. Used as column defaults."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# 1. users
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Learner and admin account.

    Purpose: Central identity table. Stores only the minimum required data.
    No email, no real name — username and age only.

    Columns:
        id              — Primary key (auto-increment)
        username        — Unique display name (3–20 chars, alphanumeric + _)
        password_hash   — bcrypt hash (never store plaintext)
        age             — Self-reported age (6–15)
        age_group       — Derived band: junior | explorer | ranger
        role            — learner | admin
        is_active       — Soft-delete flag (False = deactivated)
        date_joined     — UTC timestamp of registration
        last_login      — UTC timestamp of most recent login
        streak_count    — Current consecutive daily login streak
        total_points    — Denormalised total for fast leaderboard queries
        current_level   — Derived XP level (1–10), cached here for speed
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    age_group: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # junior | explorer | ranger
    role: Mapped[str] = mapped_column(
        String(10), nullable=False, default="learner"
    )  # learner | admin
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    streak_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Relationships ──────────────────────────────────────────────────────────
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    progress_records: Mapped[list["Progress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_badges: Mapped[list["UserBadge"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    points_record: Mapped["UserPoints | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    activity_logs: Mapped[list["ActivityLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 2. modules
# ─────────────────────────────────────────────────────────────────────────────

class Module(Base):
    """
    A curriculum module grouping scenarios and questions by topic,
    difficulty, and target age group.

    Purpose: Top-level content unit. Learners complete modules in order
    (sequential unlock within age group and difficulty tier).

    Columns:
        id              — Primary key
        title           — Short display title (max 100 chars)
        topic           — Topic key (password_safety | phishing | …)
        description     — 1–3 sentence description for the module card
        age_group       — Target audience: junior | explorer | ranger | all
        difficulty      — beginner | intermediate | advanced
        order_index     — Display and unlock order within topic+age_group
        is_published    — Only published modules are visible to learners
        icon            — Emoji or icon identifier for the module card
        created_at      — UTC creation timestamp
        updated_at      — UTC last-updated timestamp
    """

    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("topic", "age_group", "difficulty", name="uq_module_topic_age_diff"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    age_group: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(15), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    icon: Mapped[str] = mapped_column(String(10), nullable=False, default="📚")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    scenarios: Mapped[list["Scenario"]] = relationship(
        back_populates="module", cascade="all, delete-orphan", order_by="Scenario.order_index"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="module")
    progress_records: Mapped[list["Progress"]] = relationship(back_populates="module")

    def __repr__(self) -> str:
        return f"<Module id={self.id} topic={self.topic!r} difficulty={self.difficulty!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 3. scenarios
# ─────────────────────────────────────────────────────────────────────────────

class Scenario(Base):
    """
    A narrative story or situation presented before a quiz in a module.

    Purpose: Provide context and engagement. Learners read the scenario,
    then answer questions based on it.

    Columns:
        id              — Primary key
        module_id       — FK → modules.id
        title           — Short scenario title
        body            — Full scenario text (Markdown supported)
        order_index     — Display order within the module
        image_filename  — Optional illustration filename in assets/images/
    """

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_filename: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    module: Mapped["Module"] = relationship(back_populates="scenarios")

    def __repr__(self) -> str:
        return f"<Scenario id={self.id} module_id={self.module_id} title={self.title!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 4. questions
# ─────────────────────────────────────────────────────────────────────────────

class Question(Base):
    """
    A multiple-choice question (MCQ) linked to a module.

    Purpose: Core quiz content. Each question has 4 options stored as
    pipe-delimited text (option_a|option_b|option_c|option_d) for simplicity
    with SQLite; the quiz engine splits them at runtime.

    Columns:
        id              — Primary key
        module_id       — FK → modules.id
        body            — Question text (Markdown supported)
        option_a        — First answer choice
        option_b        — Second answer choice
        option_c        — Third answer choice
        option_d        — Fourth answer choice
        correct_option  — Correct answer letter: a | b | c | d
        explanation     — Feedback shown after answering (why this is correct)
        difficulty      — beginner | intermediate | advanced
        hint            — Short hint shown when score < 50% (optional)
        points          — Point value for a correct answer (default 10)
        is_active       — False = soft-deleted / not shown to learners
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(300), nullable=False)
    option_b: Mapped[str] = mapped_column(String(300), nullable=False)
    option_c: Mapped[str] = mapped_column(String(300), nullable=False)
    option_d: Mapped[str] = mapped_column(String(300), nullable=False)
    correct_option: Mapped[str] = mapped_column(String(1), nullable=False)  # a|b|c|d
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(15), nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    module: Mapped["Module"] = relationship(back_populates="questions")

    @property
    def options(self) -> dict[str, str]:
        """Return all answer options as a dict for the quiz UI."""
        return {
            "a": self.option_a,
            "b": self.option_b,
            "c": self.option_c,
            "d": self.option_d,
        }

    def __repr__(self) -> str:
        return f"<Question id={self.id} module_id={self.module_id} correct={self.correct_option!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 5. quiz_attempts
# ─────────────────────────────────────────────────────────────────────────────

class QuizAttempt(Base):
    """
    Records every quiz sitting: one row per user × module × attempt.

    Purpose: Audit trail for scoring, adaptive engine input, and
    pre/post comparison in the evaluation service.

    Columns:
        id              — Primary key
        user_id         — FK → users.id
        module_id       — FK → modules.id
        attempt_number  — Sequential attempt count for this user+module
        score_raw       — Number of correct answers
        score_total     — Total number of questions in the quiz
        score_pct       — score_raw / score_total as a float (0.0 – 1.0)
        passed          — True if score_pct >= MASTERY_THRESHOLD (0.80)
        difficulty      — Difficulty level attempted: beginner|intermediate|advanced
        time_taken_secs — Duration of the quiz in seconds (nullable if interrupted)
        started_at      — UTC timestamp when quiz began
        completed_at    — UTC timestamp when results were submitted
        is_pre_test     — True if this attempt was a pre-test (evaluation)
        is_post_test    — True if this attempt was a post-test (evaluation)
    """

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    score_raw: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    difficulty: Mapped[str] = mapped_column(String(15), nullable=False)
    time_taken_secs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_pre_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_post_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="quiz_attempts")
    module: Mapped["Module"] = relationship(back_populates="quiz_attempts")

    def __repr__(self) -> str:
        return (
            f"<QuizAttempt id={self.id} user_id={self.user_id} "
            f"module_id={self.module_id} score={self.score_pct:.0%}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. progress
# ─────────────────────────────────────────────────────────────────────────────

class Progress(Base):
    """
    Per-user, per-module progress snapshot. One row per user × module.
    Updated after each quiz attempt.

    Purpose: Fast dashboard queries (progress bars, completion %) without
    aggregating quiz_attempts every time.

    Columns:
        id              — Primary key
        user_id         — FK → users.id
        module_id       — FK → modules.id
        is_completed    — True when learner has passed at mastery threshold
        best_score_pct  — Highest score_pct ever achieved in this module
        attempt_count   — Total number of quiz attempts for this module
        last_attempted  — UTC timestamp of the most recent quiz attempt
        mastery_level   — 0=not started, 1=in progress, 2=completed, 3=mastered
    """

    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("user_id", "module_id", name="uq_progress_user_module"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    best_score_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mastery_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0=not started | 1=in progress | 2=completed | 3=mastered

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="progress_records")
    module: Mapped["Module"] = relationship(back_populates="progress_records")

    def __repr__(self) -> str:
        return (
            f"<Progress user_id={self.user_id} module_id={self.module_id} "
            f"best={self.best_score_pct:.0%} mastery={self.mastery_level}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. badges
# ─────────────────────────────────────────────────────────────────────────────

class Badge(Base):
    """
    Badge catalogue. Defines all possible achievements learners can earn.

    Purpose: Gamification reward catalogue. The reward_service checks
    unlock criteria after each quiz and awards badges automatically.

    Columns:
        id              — Primary key
        name            — Short badge name (e.g. "Password Pro")
        description     — What the learner did to earn this
        image_filename  — SVG/PNG filename in assets/badges/
        criteria_type   — Rule type: module_complete | streak | score | level | special
        criteria_value  — Threshold value interpreted by criteria_type
                          e.g. criteria_type="streak", criteria_value=7 → 7-day streak
        age_group       — Which age group can earn this (or "all")
        is_active       — False = not currently awardable
        sort_order      — Display order in the badges showcase
    """

    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    image_filename: Mapped[str] = mapped_column(String(100), nullable=False)
    criteria_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # module_complete | streak | score | level | special
    criteria_value: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Interpreted by reward_service based on criteria_type
    age_group: Mapped[str] = mapped_column(
        String(10), nullable=False, default="all"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ──────────────────────────────────────────────────────────
    user_badges: Mapped[list["UserBadge"]] = relationship(
        back_populates="badge", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Badge id={self.id} name={self.name!r} criteria={self.criteria_type}:{self.criteria_value}>"


# ─────────────────────────────────────────────────────────────────────────────
# 8. user_badges  (many-to-many junction)
# ─────────────────────────────────────────────────────────────────────────────

class UserBadge(Base):
    """
    Junction table: records which badge a user earned and when.

    Columns:
        id              — Primary key
        user_id         — FK → users.id
        badge_id        — FK → badges.id
        earned_at       — UTC timestamp when the badge was awarded
        notified        — False until the "badge unlocked" reveal has been shown
    """

    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="user_badges")
    badge: Mapped["Badge"] = relationship(back_populates="user_badges")

    def __repr__(self) -> str:
        return f"<UserBadge user_id={self.user_id} badge_id={self.badge_id}>"


# ─────────────────────────────────────────────────────────────────────────────
# 9. user_points
# ─────────────────────────────────────────────────────────────────────────────

class UserPoints(Base):
    """
    Running points ledger and XP level for each user. One row per user.

    Purpose: Separate from users.total_points so detailed point history
    can be added in future without altering the users table.

    Columns:
        id              — Primary key
        user_id         — FK → users.id (unique: one record per user)
        total_points    — Cumulative points earned across all activities
        xp_level        — Derived XP level (1–10) recalculated on each award
        points_today    — Points earned since last UTC midnight (streak bonus calc)
        last_updated    — UTC timestamp of the most recent point award
    """

    __tablename__ = "user_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="points_record")

    def __repr__(self) -> str:
        return f"<UserPoints user_id={self.user_id} total={self.total_points} level={self.xp_level}>"


# ─────────────────────────────────────────────────────────────────────────────
# 10. activity_log
# ─────────────────────────────────────────────────────────────────────────────

class ActivityLog(Base):
    """
    Append-only event log. Records every meaningful user action.

    Purpose: Engagement metrics, admin monitoring, adaptive engine input,
    and debugging. Never updated — only inserted.

    Columns:
        id              — Primary key
        user_id         — FK → users.id (nullable: system events have no user)
        event_type      — e.g. login | quiz_start | quiz_complete | badge_earned |
                                module_complete | logout | pre_test | post_test
        event_data      — JSON string of additional context (score, module_id, etc.)
        created_at      — UTC timestamp of the event
    """

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_data: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User | None"] = relationship(back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog id={self.id} user_id={self.user_id} event={self.event_type!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# 11. recommendations
# ─────────────────────────────────────────────────────────────────────────────

class Recommendation(Base):
    """
    Rule-engine generated topic/module recommendations per user.

    Purpose: Output of adaptive_engine.get_recommendations().
    Displayed on the Home page as "We suggest you try…" cards.

    Columns:
        id              — Primary key
        user_id         — FK → users.id
        module_id       — FK → modules.id (the recommended module)
        reason          — Human-readable explanation (shown to learner)
                          e.g. "You scored below 50% on this topic last time."
        priority        — 1 (highest) to 5 (lowest) — controls display order
        is_dismissed    — True if the learner has dismissed this suggestion
        created_at      — UTC timestamp when the recommendation was generated
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="recommendations")
    module: Mapped["Module"] = relationship()

    def __repr__(self) -> str:
        return f"<Recommendation user_id={self.user_id} module_id={self.module_id} priority={self.priority}>"


# ─────────────────────────────────────────────────────────────────────────────
# 12. admin_content
# ─────────────────────────────────────────────────────────────────────────────

class AdminContent(Base):
    """
    Tracks draft/published state and authorship of admin-managed content.
    One row per content item (module, question, or badge).

    Purpose: Enables an editorial workflow — admins create content as
    draft, review it, then publish. Unpublished content is invisible
    to learners regardless of the parent table's own is_published flag.

    Columns:
        id              — Primary key
        content_type    — module | question | badge | scenario
        content_id      — ID of the item in its respective table
        status          — draft | review | published | archived
        created_by      — FK → users.id (admin who created the item)
        reviewed_by     — FK → users.id (admin who approved it, nullable)
        notes           — Internal admin notes (not shown to learners)
        created_at      — UTC creation timestamp
        published_at    — UTC timestamp when status changed to 'published'
    """

    __tablename__ = "admin_content"
    __table_args__ = (
        UniqueConstraint("content_type", "content_id", name="uq_admin_content_type_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_type: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # module | question | badge | scenario
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="draft"
    )  # draft | review | published | archived
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<AdminContent type={self.content_type!r} id={self.content_id} "
            f"status={self.status!r}>"
        )

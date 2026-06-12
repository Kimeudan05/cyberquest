"""
config/constants.py
-------------------
All app-wide constants for CyberQuest Kids.

Centralised here so that any change (e.g. adding an age group or topic)
only requires an edit in this one file.
"""

from __future__ import annotations

# ─── Age Groups ───────────────────────────────────────────────────────────────

AGE_GROUP_JUNIOR: str = "junior"
AGE_GROUP_EXPLORER: str = "explorer"
AGE_GROUP_RANGER: str = "ranger"

# Maps each group to its human-readable label and age range
AGE_GROUPS: dict[str, dict] = {
    AGE_GROUP_JUNIOR: {
        "label": "🐣 Junior",
        "min_age": 6,
        "max_age": 8,
        "description": "Simple words, bright colours, short activities.",
    },
    AGE_GROUP_EXPLORER: {
        "label": "🔭 Explorer",
        "min_age": 9,
        "max_age": 12,
        "description": "Moderate scenarios, fun challenges, real examples.",
    },
    AGE_GROUP_RANGER: {
        "label": "🛡️ Ranger",
        "min_age": 13,
        "max_age": 15,
        "description": "Detailed scenarios, advanced concepts, deeper thinking.",
    },
}

AGE_GROUP_LIST: list[str] = list(AGE_GROUPS.keys())


def get_age_group(age: int) -> str:
    """Return the age group key for a given integer age."""
    for group, info in AGE_GROUPS.items():
        if info["min_age"] <= age <= info["max_age"]:
            return group
    raise ValueError(f"Age {age} is outside the supported range (6–15).")


# ─── Difficulty Levels ────────────────────────────────────────────────────────

DIFFICULTY_BEGINNER: str = "beginner"
DIFFICULTY_INTERMEDIATE: str = "intermediate"
DIFFICULTY_ADVANCED: str = "advanced"

DIFFICULTY_LEVELS: list[str] = [
    DIFFICULTY_BEGINNER,
    DIFFICULTY_INTERMEDIATE,
    DIFFICULTY_ADVANCED,
]

DIFFICULTY_ORDER: dict[str, int] = {
    DIFFICULTY_BEGINNER: 0,
    DIFFICULTY_INTERMEDIATE: 1,
    DIFFICULTY_ADVANCED: 2,
}


# ─── Module Topics ────────────────────────────────────────────────────────────

TOPIC_PASSWORD: str = "password_safety"
TOPIC_PHISHING: str = "phishing"
TOPIC_PRIVACY: str = "privacy"
TOPIC_SOCIAL_MEDIA: str = "social_media_safety"
TOPIC_CYBERBULLYING: str = "cyberbullying"
TOPIC_SAFE_DOWNLOADS: str = "safe_downloads"
TOPIC_DEVICE_SECURITY: str = "device_security"

TOPICS: dict[str, dict] = {
    TOPIC_PASSWORD: {
        "label": "🔑 Password Safety",
        "icon": "🔑",
        "description": "Learn how to create strong passwords and keep them safe.",
    },
    TOPIC_PHISHING: {
        "label": "🎣 Phishing",
        "icon": "🎣",
        "description": "Spot fake emails, messages, and websites trying to trick you.",
    },
    TOPIC_PRIVACY: {
        "label": "🔒 Privacy",
        "icon": "🔒",
        "description": "Understand what personal information to keep private online.",
    },
    TOPIC_SOCIAL_MEDIA: {
        "label": "📱 Social Media Safety",
        "icon": "📱",
        "description": "Stay safe and kind when using social media.",
    },
    TOPIC_CYBERBULLYING: {
        "label": "🤝 Cyberbullying",
        "icon": "🤝",
        "description": "Recognise, respond to, and report online bullying.",
    },
    TOPIC_SAFE_DOWNLOADS: {
        "label": "💾 Safe Downloads",
        "icon": "💾",
        "description": "Know what is safe to download and what could harm your device.",
    },
    TOPIC_DEVICE_SECURITY: {
        "label": "🖥️ Device Security",
        "icon": "🖥️",
        "description": "Keep your devices updated, locked, and protected.",
    },
}

TOPIC_LIST: list[str] = list(TOPICS.keys())


# ─── User Roles ───────────────────────────────────────────────────────────────

ROLE_LEARNER: str = "learner"
ROLE_ADMIN: str = "admin"
ROLES: list[str] = [ROLE_LEARNER, ROLE_ADMIN]


# ─── Adaptive Engine Thresholds ───────────────────────────────────────────────

MASTERY_THRESHOLD: float = 0.80          # ≥80% → mastered
MODERATE_THRESHOLD: float = 0.50         # 50–79% → keep level with hints
# Below MODERATE_THRESHOLD → reduce difficulty


# ─── Gamification ─────────────────────────────────────────────────────────────

POINTS_CORRECT_ANSWER: int = 10
POINTS_MODULE_COMPLETE: int = 50
POINTS_PERFECT_SCORE: int = 25           # bonus for 100%
POINTS_DAILY_LOGIN: int = 5

# XP required to reach each level (index = level, value = cumulative XP)
LEVEL_XP_THRESHOLDS: list[int] = [
    0,     # Level 1 — starting level
    100,   # Level 2
    250,   # Level 3
    500,   # Level 4
    850,   # Level 5
    1300,  # Level 6
    1900,  # Level 7
    2700,  # Level 8
    3700,  # Level 9
    5000,  # Level 10 — max level
]

MAX_LEVEL: int = len(LEVEL_XP_THRESHOLDS)


def calculate_level(total_points: int) -> int:
    """Return the XP level (1–MAX_LEVEL) for a given total point score."""
    level = 1
    for i, threshold in enumerate(LEVEL_XP_THRESHOLDS):
        if total_points >= threshold:
            level = i + 1
    return min(level, MAX_LEVEL)


# ─── Validation ───────────────────────────────────────────────────────────────

USERNAME_MIN_LEN: int = 3
USERNAME_MAX_LEN: int = 20
PASSWORD_MIN_LEN: int = 8
PASSWORD_MAX_LEN: int = 64
AGE_MIN: int = 6
AGE_MAX: int = 15

# Allowed characters in a username (alphanumeric + underscore)
USERNAME_ALLOWED_CHARS_PATTERN: str = r"^[a-zA-Z0-9_]+$"


# ─── Miscellaneous ────────────────────────────────────────────────────────────

ACTIVITY_LOG_MAX_ROWS: int = 500         # Max rows shown in admin metrics
ROLLING_SCORE_WINDOW: int = 10           # Attempts used for rolling avg score
LEADERBOARD_TOP_N: int = 10             # Number of entries on leaderboard

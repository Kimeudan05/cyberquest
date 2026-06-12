# 🛡️ CyberQuest Kids

**CyberQuest Kids** is an interactive, gamified cybersecurity learning platform built entirely in Python with Streamlit. It’s designed specifically for children (ages 6–15) to teach foundational cybersecurity awareness through engaging stories, quizzes, and adaptive learning paths.

## ✨ Features

- **Educational First:** Age-appropriate, friendly, and transparent rules. No generative AI or hallucinations—every scenario, question, and hint is fully structured and data-driven.
- **Adaptive Engine:** Routes learners based on performance.
  - ≥ 80%: Mastered. Advances to harder topics.
  - 50–79%: Keep practising. Provides hints on the next attempt.
  - < 50%: Struggling. Reduces difficulty or recommends a different topic.
- **Gamified Progression:** Earn points per correct answer, level up with XP thresholds, and unlock custom badges for streaks and mastery.
- **Visual Analytics:** Interactive Plotly charts for topic mastery (radar maps) and score history over time.
- **Admin Dashboard:** Fully fledged administrative interface to edit content, manage badges, and view platform engagement metrics.
- **Robust Architecture:** Clean, decoupled 4-layer design (UI → Service → Repository → DB) running on SQLAlchemy and SQLite.

## 🚀 Quickstart

### 1. Requirements
- **Python 3.12+**
- (Optional) A virtual environment

### 2. Installation
Clone the repository and install the dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Mac/Linux

pip install -r requirements.txt
```

### 3. Database Setup & Seeding
Initialise the SQLite database and populate it with the starter curriculum (modules, scenarios, 40+ questions, and 14 badges):
```bash
python data/seed_db.py
```
*Note: Run `seed_db.py` anytime to reset missing core content. It is fully idempotent.*

### 4. Run the Application
```bash
streamlit run app.py
```

## 🎮 How to Play

1. **Register:** Create a new learner account. Your age determines your starting group (Junior, Explorer, or Ranger).
2. **Dashboard:** Check your daily login points, recommended modules, and recent badges.
3. **Modules:** Pick a topic (e.g., Password Safety, Spotting Phishing).
4. **Scenario:** Read the interactive story that sets the scene.
5. **Quiz:** Answer multiple-choice questions. Get instant feedback and explanations.
6. **Progress:** Visit "My Progress" to see your radar chart fill up as you master new topics!

## ⚙️ Admin Access

An admin account is created automatically during `seed_db.py`.
- **Username:** `admin`
- **Password:** `admin123`

Log in with these credentials to unlock the **⚙️ Admin** navigation section, where you can:
- View engagement metrics and activity logs.
- Publish, unpublish, and edit learning modules.
- Add and deactivate quiz questions.
- Create new gamification badges.

## 📁 Project Structure

```text
cyberquest/
├── app.py                     # Streamlit entry point + global CSS & routing
├── requirements.txt           # Dependencies (streamlit, sqlalchemy, plotly, etc.)
├── config/
│   ├── settings.py            # App version, DB URI, session config
│   └── constants.py           # Tokens, thresholds, difficulty matrices
├── data/
│   └── seed_db.py             # Idempotent DB initialisation script
├── db/
│   ├── database.py            # SQLAlchemy engine and session context
│   ├── models.py              # 12 schema tables (User, Module, Progress...)
│   └── repositories/          # Data access layer (UserRepo, QuizRepo...)
├── core/
│   ├── auth_service.py        # Bcrypt, sessions, role guards
│   ├── quiz_engine.py         # Scoring and evaluation
│   ├── adaptive_engine.py     # Routing, hints, recommendations
│   ├── reward_service.py      # Points, level-ups, badge evaluation
│   ├── progress_service.py    # Per-module tracking
│   ├── content_service.py     # Module/scenario retrieval
│   ├── evaluation_service.py  # Pre/post test comparisons
│   └── admin_service.py       # Admin CRUD & sanitisation
└── pages/
    ├── components.py          # Reusable Streamlit UI widgets
    ├── 00_login.py            # Glassmorphic auth
    ├── 01_home.py             # KPI dashboard
    ├── 02_modules.py          # Topic catalogue
    ├── 03_scenario.py         # Story reader
    ├── 04_quiz.py             # Interactive quizzes
    ├── 05_results.py          # Summary and badge reveal
    ├── 06_progress.py         # Plotly analytics
    ├── 07_leaderboard.py      # Top 10 rankings
    ├── 08_profile.py          # Badge collection
    └── 09_admin/              # Admin interface pages
```

## 🔐 Security Notes
- Passwords are hashed using `bcrypt` before storage.
- All admin inputs are sanitised using `bleach` to prevent XSS.
- The `is_authenticated` guard is checked at the top of every protected page.

---
*Built with ❤️ for cybersecurity education.*

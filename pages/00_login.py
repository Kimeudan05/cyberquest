"""
pages/00_login.py
-----------------
Login and registration page for CyberQuest Kids.
"""

from __future__ import annotations
import streamlit as st
from core.auth_service import login_user, register_user, is_authenticated
from config.constants import AGE_GROUPS, AGE_MIN, AGE_MAX

# Redirect if already logged in (unlikely to be hit with st.navigation)
if is_authenticated():
    st.rerun()


# ─── Page styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}
.login-box {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 24px;
    padding: 2.5rem 2rem;
    backdrop-filter: blur(16px);
    box-shadow: 0 24px 64px rgba(0,0,0,0.4);
}
.hero-title {
    font-size: 3.2rem;
    font-weight: 900;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
}
.hero-sub {
    color: #94a3b8;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}
.stat-pill {
    display: inline-block;
    background: rgba(167,139,250,0.15);
    border: 1px solid rgba(167,139,250,0.3);
    border-radius: 99px;
    padding: 0.3rem 1rem;
    color: #c4b5fd;
    font-size: 0.85rem;
    margin: 0.2rem;
}
</style>
""", unsafe_allow_html=True)


# ─── Layout ──────────────────────────────────────────────────────────────────
left, right = st.columns([1.1, 0.9], gap="large")

with left:
    st.markdown('<div class="hero-title">🛡️ CyberQuest Kids</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Learn cybersecurity through fun stories, quizzes, and adventures!</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <span class="stat-pill">🔑 Password Safety</span>
        <span class="stat-pill">🎣 Spot Phishing</span>
        <span class="stat-pill">🔒 Stay Private</span>
        <span class="stat-pill">🤝 Beat Bullying</span>
        <span class="stat-pill">💾 Safe Downloads</span>
        <span class="stat-pill">🖥️ Device Security</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Topics", "7", "🗂️")
    with col2:
        st.metric("Age Groups", "3", "👧")
    with col3:
        st.metric("Badges", "14+", "🏅")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    > 🌟 **Educational first.** All content is written by cybersecurity educators
    > and designed specifically for children aged 6–15.
    """)

with right:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    tab_login, tab_reg = st.tabs(["🔐 Login", "✨ Join"])

    # ── Login tab ────────────────────────────────────────────────────────────
    with tab_login:
        st.markdown("### Welcome back! 👋")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="your_username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            submitted = st.form_submit_button("Login →", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Please enter both your username and password.")
            else:
                with st.spinner("Logging in..."):
                    ok, msg = login_user(username.strip(), password)
                if ok:
                    st.success("Welcome back! Loading your quest... 🚀")
                    st.switch_page("pages/01_home.py")
                else:
                    st.error(f"❌ {msg}")

    # ── Register tab ─────────────────────────────────────────────────────────
    with tab_reg:
        st.markdown("### Start your CyberQuest! 🚀")
        with st.form("register_form", clear_on_submit=True):
            reg_username = st.text_input(
                "Choose a username",
                placeholder="cool_hero_123",
                help="3–20 characters, letters, numbers, underscore",
                key="reg_username",
            )
            reg_age = st.number_input(
                "Your age",
                min_value=AGE_MIN,
                max_value=AGE_MAX,
                value=10,
                step=1,
                key="reg_age",
            )

            # Show age group preview
            from config.constants import get_age_group
            try:
                ag = get_age_group(int(reg_age))
                ag_info = AGE_GROUPS[ag]
                st.info(f"{ag_info['label']} — {ag_info['description']}")
            except ValueError:
                pass

            reg_password = st.text_input(
                "Create a password",
                type="password",
                placeholder="Min 8 characters + numbers",
                key="reg_password",
            )
            reg_password2 = st.text_input(
                "Confirm password",
                type="password",
                placeholder="Same password again",
                key="reg_password2",
            )
            reg_submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

        if reg_submitted:
            if reg_password != reg_password2:
                st.error("❌ Passwords don't match. Try again!")
            else:
                with st.spinner("Creating your account..."):
                    ok, msg = register_user(
                        username=reg_username.strip(),
                        password=reg_password,
                        age=int(reg_age),
                    )
                if ok:
                    st.success("🎉 Account created! Welcome to CyberQuest!")
                    # Auto-log in and redirect to home
                    ok2, _ = login_user(reg_username.strip(), reg_password)
                    if ok2:
                        st.switch_page("pages/01_home.py")
                else:
                    st.error(f"❌ {msg}")

    st.markdown('</div>', unsafe_allow_html=True)

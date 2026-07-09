# ============================================================
# AUTH.PY — GasFeel Dashboard Login System
# Handles user authentication before dashboard access.
# To add/remove users: edit the USERS dictionary below only.
# Format: "username": "password"
# ============================================================

import streamlit as st

# ============================================================
# USER CREDENTIALS
# Add or remove users here.
# To change a password — just update the value next to the name.
# ============================================================
# ============================================================
# USER CREDENTIALS — loaded from Streamlit secrets
# To add users: update secrets.toml locally and
# Streamlit Cloud secrets in the dashboard settings.
# ============================================================
USERS = st.secrets["USERS"]

# ============================================================
# LOGIN PAGE RENDERER
# Shows a branded login form — called from app.py when
# the user is not yet authenticated in their session.
# ============================================================
def show_login():
    # --------------------------------------------------------
    # PAGE STYLING — Clean centered login card
    # --------------------------------------------------------
    st.markdown("""
        <style>
        /* Hide sidebar on login page */
        [data-testid="stSidebar"] {
            display: none;
        }

        /* Full page blue background */
        .stApp {
            background: linear-gradient(135deg, #001f6e 0%, #003399 60%, #0044cc 100%) !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Input fields — dark text on white background */
        .stTextInput input {
            background: white !important;
            color: #001f6e !important;
            border: 2px solid #003399 !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }

        .stTextInput input::placeholder {
            color: #aaaaaa !important;
        }

        .stTextInput input:focus {
            border-color: #0044cc !important;
            box-shadow: 0 0 0 3px rgba(0,51,153,0.2) !important;
            outline: none !important;
        }

        /* Input label — white so visible on blue background */
        .stTextInput label p {
            color: white !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }

        /* Login button */
        .stButton button {
            background: white !important;
            color: #003399 !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 12px 0 !important;
            font-size: 15px !important;
            font-weight: 800 !important;
            width: 100% !important;
            margin-top: 8px !important;
            letter-spacing: 0.5px !important;
        }

        .stButton button:hover {
            background: #f0f4ff !important;
            color: #001f6e !important;
        }

        /* Tab bar on login — hide it */
        .stTabs {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # LOGIN CARD HEADER
    # --------------------------------------------------------
    st.markdown("""
        <div style='text-align:center;padding:40px 0 20px 0;'>
            <div style='font-size:64px;'>⛽</div>
            <h1 style='color:white;font-size:28px;font-weight:800;margin:12px 0 4px 0;'>
                GasFeel Analytics
            </h1>
            <p style='color:#a0c4ff;font-size:14px;margin:0;'>
                Sign in to access your dashboard
            </p>
        </div>
    """, unsafe_allow_html=True)
    # --------------------------------------------------------
    # LOGIN FORM
    # Centered column so it doesn't stretch full width
    # --------------------------------------------------------
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username"
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password"
        )

        # Show error message if previous login failed
        if st.session_state.get("login_failed"):
            st.markdown("""
                <div class='login-error'>
                    ❌ Incorrect username or password. Please try again.
                </div>
            """, unsafe_allow_html=True)

        # Login button
        if st.button("Sign In →", key="login_btn"):
            # Check credentials against USERS dictionary
            if username in USERS and USERS[username] == password:
                # Correct — set session as authenticated
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["login_failed"] = False
                st.rerun()
            else:
                # Wrong — flag the error and re-render
                st.session_state["login_failed"] = True
                st.rerun()


# ============================================================
# AUTHENTICATION CHECK
# Called at the top of app.py before rendering anything.
# Returns True if user is logged in, False if not.
# ============================================================
def is_authenticated():
    return st.session_state.get("authenticated", False)


# ============================================================
# LOGOUT FUNCTION
# Called from the sidebar logout button in app.py.
# Clears the session and returns to login page.
# ============================================================
def logout():
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["login_failed"] = False
    st.rerun()
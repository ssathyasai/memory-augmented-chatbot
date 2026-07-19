"""Streamlit session state management and authentication helper utilities.

Process Flow:
1. `init_session_state`: Sets up session keys (`user`, `jwt_token`, `current_session_id`, `messages`).
2. `is_authenticated` & `require_auth`: Verifies active session tokens and forces page redirection to `app.py` if unauthorized.
3. `set_user` & `clear_session`: Manages login/logout session state persistence.
4. `apply_theme`: Dynamically injects dark/light CSS themes based on user profile settings stored in MongoDB.
"""

import streamlit as st
from typing import Optional
from auth.models import UserResponse


def init_session_state():
    """Initialize session state variables."""
    if "user" not in st.session_state:
        st.session_state.user = None
    
    if "jwt_token" not in st.session_state:
        st.session_state.jwt_token = None
    
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "uploaded_docs" not in st.session_state:
        st.session_state.uploaded_docs = []


def is_authenticated() -> bool:
    """
    Check if user is authenticated.
    
    Returns:
        True if user is logged in, False otherwise
    """
    return st.session_state.get("user") is not None and st.session_state.get("jwt_token") is not None


def get_current_user() -> Optional[UserResponse]:
    """
    Get currently logged in user.
    
    Returns:
        User or None if not logged in
    """
    return st.session_state.get("user")


def get_jwt_token() -> Optional[str]:
    """
    Get current JWT token.
    
    Returns:
        JWT token or None if not logged in
    """
    return st.session_state.get("jwt_token")


def set_user(user: UserResponse, token: str):
    """
    Set authenticated user in session.
    
    Args:
        user: User object
        token: JWT token
    """
    st.session_state.user = user
    st.session_state.jwt_token = token


def clear_session():
    """Clear session state (logout)."""
    st.session_state.user = None
    st.session_state.jwt_token = None
    st.session_state.current_session_id = None
    st.session_state.messages = []
    st.session_state.uploaded_docs = []


def require_auth():
    """
    Function to require authentication.
    Redirects to main login page if not authenticated.
    """
    if not is_authenticated():
        st.warning("Please log in to access this page. Redirecting to login...")
        st.switch_page("app.py")
        st.stop()
    apply_theme()


def apply_theme():
    """Apply the user's selected theme dynamically via CSS injection."""
    user = get_current_user()
    if not user or not user.settings:
        return
    
    theme = user.settings.get("theme", "auto").lower()
    if theme == "dark":
        st.markdown("""
            <style>
                /* Dark Mode Theme Overrides */
                html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
                    background-color: #0E1117 !important;
                    color: #FAFAFA !important;
                }
                [data-testid="stSidebar"] {
                    background-color: #262730 !important;
                }
                .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
                    color: #FAFAFA !important;
                    background-color: #1E1E24 !important;
                }
                h1, h2, h3, h4, h5, h6, label, p, span {
                    color: #FAFAFA !important;
                }
                div[data-testid="stForm"] {
                    border-color: #333333 !important;
                }
            </style>
        """, unsafe_allow_html=True)
    elif theme == "light":
        st.markdown("""
            <style>
                /* Light Mode Theme Overrides */
                html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
                    background-color: #FFFFFF !important;
                    color: #31333F !important;
                }
                [data-testid="stSidebar"] {
                    background-color: #F0F2F6 !important;
                }
                .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
                    color: #31333F !important;
                    background-color: #F8FAFC !important;
                }
                h1, h2, h3, h4, h5, h6, label, p, span {
                    color: #31333F !important;
                }
            </style>
        """, unsafe_allow_html=True)


def get_user_id() -> Optional[str]:
    """
    Get current user ID.
    
    Returns:
        User ID or None if not logged in
    """
    user = get_current_user()
    return user.id if user else None

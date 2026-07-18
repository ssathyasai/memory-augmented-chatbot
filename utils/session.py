"""Streamlit session state management."""

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
    Decorator/function to require authentication.
    Redirects to login if not authenticated.
    """
    if not is_authenticated():
        st.warning("Please log in to access this page.")
        st.stop()


def get_user_id() -> Optional[str]:
    """
    Get current user ID.
    
    Returns:
        User ID or None if not logged in
    """
    user = get_current_user()
    return user.id if user else None

"""Authentication UI components."""

import streamlit as st
import logging
from auth.manager import auth_manager
from auth.models import UserCreate, UserLogin
from utils.session import set_user
from errors.handlers import get_user_message

logger = logging.getLogger(__name__)


def show_auth_page():
    """Display authentication page with login and register tabs."""
    st.markdown('<div class="main-header">🤖 Memory-Augmented Chatbot</div>', unsafe_allow_html=True)
    
    st.markdown("### Welcome! Please login or register to continue.")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_register_form()


def show_login_form():
    """Display login form."""
    with st.form("login_form"):
        st.subheader("Login")
        
        email = st.text_input("Email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", placeholder="Your password")
        
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("Please fill in all fields")
                return
            
            try:
                # Attempt login
                credentials = UserLogin(email=email, password=password)
                user, token = auth_manager.login_user(credentials)
                
                # Set session
                set_user(user, token)
                
                st.success(f"Welcome back, {user.email}!")
                logger.info(f"User logged in: {user.email}")
                
                # Rerun to refresh page
                st.rerun()
            
            except Exception as e:
                error_msg = get_user_message(e)
                st.error(error_msg)
                logger.error(f"Login error: {e}")


def show_register_form():
    """Display registration form."""
    with st.form("register_form"):
        st.subheader("Register")
        
        email = st.text_input("Email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", placeholder="Min 8 chars, 1 upper, 1 lower, 1 digit")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        st.caption("Password requirements: At least 8 characters, 1 uppercase, 1 lowercase, 1 digit")
        
        submit = st.form_submit_button("Register", use_container_width=True)
        
        if submit:
            # Validation
            if not email or not password or not confirm_password:
                st.error("Please fill in all fields")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return
            
            try:
                # Attempt registration
                user_data = UserCreate(email=email, password=password)
                user, token = auth_manager.register_user(user_data)
                
                # Set session
                set_user(user, token)
                
                st.success(f"Registration successful! Welcome, {user.email}!")
                logger.info(f"User registered: {user.email}")
                
                # Rerun to refresh page
                st.rerun()
            
            except Exception as e:
                error_msg = get_user_message(e)
                st.error(error_msg)
                logger.error(f"Registration error: {e}")


def show_logout_button():
    """Display logout button in sidebar."""
    if st.sidebar.button("Logout", key="logout_btn"):
        from utils.session import clear_session
        clear_session()
        st.rerun()

"""Authentication package initialization.

Process Flow:
1. Exports core authentication entities (AuthManager).
2. Exports Pydantic schemas for authentication requests and responses (User, UserCreate, UserLogin, UserResponse).
"""

from .models import User, UserCreate, UserLogin, UserResponse
from .manager import AuthManager, auth_manager

__all__ = ["AuthManager", "auth_manager", "User", "UserCreate", "UserLogin", "UserResponse"]

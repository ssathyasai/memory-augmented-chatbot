"""Authentication package initialization.

Process Flow:
1. Exports core authentication entities (AuthManager).
2. Exports Pydantic schemas for authentication requests and responses (User, UserCreate, UserLogin, UserResponse).
"""

from .manager import AuthManager
from .models import User, UserCreate, UserLogin, UserResponse

__all__ = ["AuthManager", "User", "UserCreate", "UserLogin", "UserResponse"]

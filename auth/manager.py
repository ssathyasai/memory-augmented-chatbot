"""Authentication manager for user operations.

Process Flow:
1. Validates registration data and verifies uniqueness of user emails in MongoDB.
2. Hashes raw passwords using bcrypt before saving user documents.
3. Authenticates login requests by verifying credentials against stored hashes.
4. Generates signed JWT access tokens upon successful authentication or registration.
5. Manages user profile settings, application preferences, and quota limits.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple
from bson import ObjectId

from config.database import get_database
from config.settings import settings
from errors.exceptions import AuthenticationError, ValidationError, DatabaseError
from .models import User, UserCreate, UserLogin, UserResponse
from .security import hash_password, verify_password
from .jwt import create_access_token

logger = logging.getLogger(__name__)


class AuthManager:
    """Manage user authentication and authorization."""
    
    def __init__(self):
        """Initialize authentication manager."""
        self.db = get_database()
        if self.db is None:
            logger.warning("Database not available during AuthManager initialization")
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            self.db = get_database()
            if self.db is None:
                raise DatabaseError("Database connection not available")
    
    def register_user(self, user_data: UserCreate) -> Tuple[UserResponse, str]:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
        
        Returns:
            Tuple of (User, JWT token)
        
        Raises:
            ValidationError: If user already exists or validation fails
            DatabaseError: If database operation fails
        """
        self._ensure_db()
        
        try:
            # Check if user already exists
            existing_user = self.db.users.find_one({"email": user_data.email})
            if existing_user:
                raise ValidationError("User with this email already exists")
            
            # Create user document
            user_doc = {
                "email": user_data.email,
                "password_hash": hash_password(user_data.password),
                "role": "user",
                "created_at": datetime.utcnow(),
                "last_login": None,
                "settings": {
                    "theme": "light",
                    "language": "en",
                    "notifications": True
                },
                "quota": {
                    "documents": settings.MAX_DOCUMENTS_PER_USER,
                    "storage_mb": settings.MAX_STORAGE_MB_PER_USER
                }
            }
            
            # Insert user
            result = self.db.users.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            logger.info(f"User registered: {user_data.email}")
            
            # Create JWT token
            token = create_access_token(
                data={
                    "sub": user_id,
                    "email": user_data.email,
                    "role": "user"
                }
            )
            
            # Create response
            user_response = UserResponse(
                id=user_id,
                email=user_data.email,
                role="user",
                created_at=user_doc["created_at"],
                last_login=None,
                settings=user_doc["settings"],
                quota=user_doc["quota"]
            )
            
            return user_response, token
        
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            raise DatabaseError(f"Failed to register user: {str(e)}")
    
    def login_user(self, credentials: UserLogin) -> Tuple[UserResponse, str]:
        """
        Authenticate user and create session.
        
        Args:
            credentials: User login credentials
        
        Returns:
            Tuple of (User, JWT token)
        
        Raises:
            AuthenticationError: If credentials are invalid
            DatabaseError: If database operation fails
        """
        self._ensure_db()
        
        try:
            # Find user
            user_doc = self.db.users.find_one({"email": credentials.email})
            if not user_doc:
                raise AuthenticationError("Invalid email or password")
            
            # Verify password
            if not verify_password(credentials.password, user_doc["password_hash"]):
                raise AuthenticationError("Invalid email or password")
            
            # Update last login
            self.db.users.update_one(
                {"_id": user_doc["_id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            user_id = str(user_doc["_id"])
            
            logger.info(f"User logged in: {credentials.email}")
            
            # Create JWT token
            token = create_access_token(
                data={
                    "sub": user_id,
                    "email": user_doc["email"],
                    "role": user_doc["role"]
                }
            )
            
            # Create response
            user_response = UserResponse(
                id=user_id,
                email=user_doc["email"],
                role=user_doc["role"],
                created_at=user_doc["created_at"],
                last_login=datetime.utcnow(),
                settings=user_doc.get("settings", {}),
                quota=user_doc.get("quota", {})
            )
            
            return user_response, token
        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            raise DatabaseError(f"Failed to login: {str(e)}")
    
    def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
        
        Returns:
            User or None if not found
        """
        self._ensure_db()
        
        try:
            user_doc = self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                return None
            
            return UserResponse(
                id=str(user_doc["_id"]),
                email=user_doc["email"],
                role=user_doc["role"],
                created_at=user_doc["created_at"],
                last_login=user_doc.get("last_login"),
                settings=user_doc.get("settings", {}),
                quota=user_doc.get("quota", {})
            )
        
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def update_user_settings(self, user_id: str, settings: dict) -> bool:
        """
        Update user settings.
        
        Args:
            user_id: User ID
            settings: New settings
        
        Returns:
            True if successful
        """
        self._ensure_db()
        
        try:
            result = self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"settings": settings}}
            )
            return result.matched_count > 0
        
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
        
        Returns:
            True if successful
        
        Raises:
            AuthenticationError: If current password is incorrect
        """
        self._ensure_db()
        
        try:
            # Get user
            user_doc = self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                raise AuthenticationError("User not found")
            
            # Verify current password
            if not verify_password(current_password, user_doc["password_hash"]):
                raise AuthenticationError("Current password is incorrect")
            
            # Update password
            new_hash = hash_password(new_password)
            result = self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"password_hash": new_hash}}
            )
            
            logger.info(f"Password changed for user: {user_id}")
            return result.modified_count > 0
        
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            raise DatabaseError(f"Failed to change password: {str(e)}")


# Global auth manager instance
auth_manager = AuthManager()

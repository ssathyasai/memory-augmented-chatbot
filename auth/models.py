"""User data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr


class UserCreate(UserBase):
    """Model for user registration."""
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLogin(UserBase):
    """Model for user login."""
    password: str


class User(UserBase):
    """Complete user model."""
    id: str
    password_hash: str
    role: str = "user"
    created_at: datetime
    last_login: Optional[datetime] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    quota: Dict[str, int] = Field(
        default_factory=lambda: {
            "documents": 100,
            "storage_mb": 500
        }
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "role": "user",
                "created_at": "2024-01-01T00:00:00",
                "settings": {
                    "theme": "light",
                    "language": "en"
                },
                "quota": {
                    "documents": 100,
                    "storage_mb": 500
                }
            }
        }


class UserResponse(UserBase):
    """User model for API responses (no password)."""
    id: str
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None
    settings: Dict[str, Any]
    quota: Dict[str, int]


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PasswordChange(BaseModel):
    """Model for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be at most 128 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

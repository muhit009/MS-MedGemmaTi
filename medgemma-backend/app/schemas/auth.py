"""
Authentication schemas.
Pydantic models for auth-related requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Token(BaseModel):
    """
    JWT Token response schema.
    """
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class TokenData(BaseModel):
    """
    Token payload data schema.
    """
    user_id: Optional[str] = Field(None, description="User ID from token")
    username: Optional[str] = Field(None, description="Username from token")


class LoginRequest(BaseModel):
    """
    Login request schema for JSON-based authentication.
    """
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "dr_smith",
                "password": "securepassword123"
            }
        }


class UserResponse(BaseModel):
    """
    User information response schema.
    """
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    role: str = Field(default="physician", description="User role")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "dr_smith",
                "full_name": "Dr. John Smith",
                "role": "physician"
            }
        }


class UserCreate(BaseModel):
    """
    User creation request schema.
    """
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=6, description="Password")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    role: str = Field(default="physician", description="User role")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "dr_jones",
                "password": "securepassword123",
                "full_name": "Dr. Sarah Jones",
                "role": "physician"
            }
        }
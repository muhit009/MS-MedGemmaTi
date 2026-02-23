"""
Patient schemas.
Pydantic models for patient-related requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PatientSearchRequest(BaseModel):
    """
    Patient search request schema.
    """
    patientId: Optional[str] = Field(None, description="Patient business ID to search for")
    name: Optional[str] = Field(None, description="Patient name to search for")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patientId": "8492-A",
                "name": "John"
            }
        }


class PatientSearchResponse(BaseModel):
    """
    Patient search result schema.
    Used in the Patient Selection dialog.
    """
    id: str = Field(..., description="Patient business ID")
    name: str = Field(..., description="Patient full name")
    dob: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    age: int = Field(..., description="Patient age in years")
    sex: Optional[str] = Field(None, description="Patient sex")
    weight: Optional[str] = Field(None, description="Weight with unit (e.g., '180 lbs')")
    height: Optional[str] = Field(None, description="Height with unit (e.g., '182 cm')")
    avatarUrl: Optional[str] = Field(None, description="URL to patient avatar image")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "8492-A5-2026",
                "name": "John Doe",
                "dob": "1980-05-12",
                "age": 45,
                "sex": "Male",
                "weight": "81.6 kg",
                "height": "182 cm",
                "avatarUrl": "/images/patients/8492-A5-2026.jpg"
            }
        }


class PatientResponse(BaseModel):
    """
    Full patient details response schema.
    Used to populate the Patient Identification card.
    """
    id: str = Field(..., description="Patient business ID")
    uuid: str = Field(..., description="Patient internal UUID")
    name: str = Field(..., description="Patient full name")
    dob: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    age: int = Field(..., description="Patient age in years")
    sex: Optional[str] = Field(None, description="Patient sex")
    weight: Optional[str] = Field(None, description="Weight with unit")
    height: Optional[str] = Field(None, description="Height with unit")
    avatarUrl: Optional[str] = Field(None, description="URL to patient avatar image")
    createdAt: Optional[str] = Field(None, description="Record creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "8492-A5-2026",
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "name": "John Doe",
                "dob": "1980-05-12",
                "age": 45,
                "sex": "Male",
                "weight": "81.6 kg",
                "height": "182 cm",
                "avatarUrl": "/images/patients/8492-A5-2026.jpg",
                "createdAt": "2024-01-15T10:30:00Z"
            }
        }


class PatientCreateRequest(BaseModel):
    """
    Patient creation request schema.
    """
    businessId: str = Field(..., min_length=1, max_length=50, description="Patient business ID")
    fullName: str = Field(..., min_length=1, max_length=255, description="Patient full name")
    dob: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    sex: Optional[str] = Field(None, max_length=10, description="Patient sex")
    weightKg: Optional[float] = Field(None, ge=0, le=500, description="Weight in kg")
    heightCm: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")
    avatarUrl: Optional[str] = Field(None, description="URL to patient avatar image")
    
    class Config:
        json_schema_extra = {
            "example": {
                "businessId": "8492-A5-2026",
                "fullName": "John Doe",
                "dob": "1980-05-12",
                "sex": "Male",
                "weightKg": 81.6,
                "heightCm": 182,
                "avatarUrl": "/images/patients/8492-A5-2026.jpg"
            }
        }


class PatientUpdateRequest(BaseModel):
    """
    Patient update request schema.
    All fields are optional.
    """
    fullName: Optional[str] = Field(None, min_length=1, max_length=255, description="Patient full name")
    dob: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    sex: Optional[str] = Field(None, max_length=10, description="Patient sex")
    weightKg: Optional[float] = Field(None, ge=0, le=500, description="Weight in kg")
    heightCm: Optional[float] = Field(None, ge=0, le=300, description="Height in cm")
    avatarUrl: Optional[str] = Field(None, description="URL to patient avatar image")
    
    class Config:
        json_schema_extra = {
            "example": {
                "weightKg": 83.0,
                "heightCm": 182
            }
        }
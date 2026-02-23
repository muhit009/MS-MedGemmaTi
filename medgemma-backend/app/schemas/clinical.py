"""
Clinical data schemas.
Pydantic models for vitals, alerts, and notes.
"""

from pydantic import BaseModel, Field
from typing import Optional, Union


class VitalReading(BaseModel):
    """
    Single vital sign reading schema.
    """
    value: Union[int, float, str] = Field(..., description="Vital sign value")
    unit: str = Field(..., description="Unit of measurement")
    status: str = Field(..., description="Status indicator (stable, low, high, critical, unknown)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": 72,
                "unit": "bpm",
                "status": "stable"
            }
        }


class VitalsResponse(BaseModel):
    """
    Complete vitals response schema.
    Used to populate the Biometric HUD.
    """
    heartRate: VitalReading = Field(..., description="Heart rate reading")
    spO2: VitalReading = Field(..., description="Blood oxygen saturation reading")
    bloodPressure: VitalReading = Field(..., description="Blood pressure reading")
    
    class Config:
        json_schema_extra = {
            "example": {
                "heartRate": {"value": 72, "unit": "bpm", "status": "stable"},
                "spO2": {"value": 98, "unit": "%", "status": "stable"},
                "bloodPressure": {"value": "120/80", "unit": "mmHg", "status": "stable"}
            }
        }


class AlertResponse(BaseModel):
    """
    Clinical alert response schema.
    Used for the Clinical Alert card.
    """
    id: Optional[str] = Field(None, description="Alert ID")
    content: str = Field(..., description="Alert content text")
    severity: str = Field(..., description="Alert severity (nominal, warning, critical)")
    updatedAt: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Monitor RLL nodule stability. Patient reports mild shortness of breath.",
                "severity": "warning",
                "updatedAt": "2026-01-22T10:00:00Z"
            }
        }


class AlertUpdateRequest(BaseModel):
    """
    Alert update request schema.
    """
    content: str = Field(..., description="Updated alert content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated alert: Patient condition improving. Continue monitoring."
            }
        }


class NoteResponse(BaseModel):
    """
    Clinical note response schema.
    Used in the Patient Notes section.
    """
    id: str = Field(..., description="Note ID")
    date: str = Field(..., description="Note date (YYYY-MM-DD)")
    content: str = Field(..., description="Note content")
    createdAt: Optional[str] = Field(None, description="Creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "date": "2026-01-20",
                "content": "Patient complained of persistent cough for the past week. No fever reported.",
                "createdAt": "2026-01-20T14:30:00Z",
                "updatedAt": "2026-01-20T14:30:00Z"
            }
        }


class NoteCreateRequest(BaseModel):
    """
    Note creation request schema.
    """
    content: str = Field(..., min_length=1, description="Note content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "New clinical observation: Patient shows improvement in respiratory function."
            }
        }


class NoteUpdateRequest(BaseModel):
    """
    Note update request schema.
    """
    content: str = Field(..., min_length=1, description="Updated note content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Updated observation: Symptoms have resolved completely."
            }
        }


class VitalsCreateRequest(BaseModel):
    """
    Vitals creation request schema.
    """
    heartRate: int = Field(..., ge=0, le=300, description="Heart rate in bpm")
    spO2: int = Field(..., ge=0, le=100, description="Blood oxygen saturation percentage")
    systolicBp: int = Field(..., ge=0, le=300, description="Systolic blood pressure")
    diastolicBp: int = Field(..., ge=0, le=200, description="Diastolic blood pressure")
    
    class Config:
        json_schema_extra = {
            "example": {
                "heartRate": 72,
                "spO2": 98,
                "systolicBp": 120,
                "diastolicBp": 80
            }
        }
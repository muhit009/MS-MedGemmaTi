"""
Schemas module initialization.
Contains Pydantic schemas for request/response validation.
"""

from app.schemas.auth import Token, TokenData, LoginRequest, UserResponse
from app.schemas.patient import (
    PatientResponse,
    PatientSearchRequest,
    PatientSearchResponse,
)
from app.schemas.clinical import (
    VitalReading,
    VitalsResponse,
    AlertResponse,
    AlertUpdateRequest,
    NoteResponse,
    NoteCreateRequest,
    NoteUpdateRequest,
)
from app.schemas.imaging import ImageResponse
from app.schemas.conversation import (
    ConsultationResponse,
    ConsultationListResponse,
    MessageResponse,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisContext,
    ModelConfig,
)

__all__ = [
    # Auth
    "Token",
    "TokenData",
    "LoginRequest",
    "UserResponse",
    # Patient
    "PatientResponse",
    "PatientSearchRequest",
    "PatientSearchResponse",
    # Clinical
    "VitalReading",
    "VitalsResponse",
    "AlertResponse",
    "AlertUpdateRequest",
    "NoteResponse",
    "NoteCreateRequest",
    "NoteUpdateRequest",
    # Imaging
    "ImageResponse",
    # Conversation
    "ConsultationResponse",
    "ConsultationListResponse",
    "MessageResponse",
    "AnalysisRequest",
    "AnalysisResponse",
    "AnalysisContext",
    "ModelConfig",
]
"""
Imaging schemas.
Pydantic models for medical imaging requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ImageResponse(BaseModel):
    """
    Patient image response schema.
    Used in the Imaging History section.
    """
    id: str = Field(..., description="Image ID")
    src: str = Field(..., description="Signed URL to the image")
    modality: str = Field(..., description="Imaging modality (e.g., X-Ray, CT, MRI)")
    date: str = Field(..., description="Visit date and time")
    reading: Optional[str] = Field(None, description="AI reading summary")
    confidence: str = Field(..., description="AI confidence level (High, Medium, Low)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "src": "https://storage.example.com/images/xray-001.jpg?token=abc123",
                "modality": "X-Ray (Chest AP)",
                "date": "2025-10-14 09:30 AM",
                "reading": "Clear lung fields. No acute cardiopulmonary abnormality.",
                "confidence": "High"
            }
        }


class ImageUploadRequest(BaseModel):
    """
    Image upload metadata request schema.
    Note: Actual file upload handled separately via multipart/form-data.
    """
    modality: str = Field(..., description="Imaging modality")
    visitDate: str = Field(..., description="Visit date (ISO format)")
    aiReadingSummary: Optional[str] = Field(None, description="AI reading summary")
    aiConfidenceScore: Optional[float] = Field(None, ge=0, le=1, description="AI confidence score (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "modality": "X-Ray (Chest AP)",
                "visitDate": "2025-10-14T09:30:00Z",
                "aiReadingSummary": "Clear lung fields. No acute cardiopulmonary abnormality.",
                "aiConfidenceScore": 0.95
            }
        }


class ImageListResponse(BaseModel):
    """
    Paginated image list response schema.
    """
    images: list[ImageResponse] = Field(..., description="List of images")
    total: int = Field(..., description="Total number of images")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    hasMore: bool = Field(..., description="Whether more pages exist")
    
    class Config:
        json_schema_extra = {
            "example": {
                "images": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "src": "https://storage.example.com/images/xray-001.jpg",
                        "modality": "X-Ray (Chest AP)",
                        "date": "2025-10-14 09:30 AM",
                        "reading": "Clear lung fields.",
                        "confidence": "High"
                    }
                ],
                "total": 15,
                "page": 1,
                "limit": 10,
                "hasMore": True
            }
        }
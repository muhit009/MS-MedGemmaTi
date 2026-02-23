"""
Imaging data models.
Represents medical images and related metadata.
"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID
from enum import Enum


class Modality(str, Enum):
    """Medical imaging modalities."""
    XRAY = "X-Ray"
    XRAY_CHEST_AP = "X-Ray (Chest AP)"
    XRAY_CHEST_PA = "X-Ray (Chest PA)"
    XRAY_CHEST_LATERAL = "X-Ray (Chest Lateral)"
    CT = "CT"
    CT_CHEST = "CT (Chest)"
    CT_ABDOMEN = "CT (Abdomen)"
    CT_HEAD = "CT (Head)"
    MRI = "MRI"
    MRI_BRAIN = "MRI (Brain)"
    MRI_SPINE = "MRI (Spine)"
    ULTRASOUND = "Ultrasound"
    MAMMOGRAM = "Mammogram"
    PET = "PET"
    OTHER = "Other"


class ConfidenceLevel(str, Enum):
    """AI confidence levels for readings."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "Unknown"


@dataclass
class ImageBlob:
    """
    Image blob entity.
    Represents deduplicated image storage.
    """
    file_hash: str
    storage_path: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "ImageBlob":
        """Create an ImageBlob from a dictionary."""
        return cls(
            file_hash=data["file_hash"],
            storage_path=data["storage_path"],
            mime_type=data.get("mime_type"),
            size_bytes=data.get("size_bytes"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "file_hash": self.file_hash,
            "storage_path": self.storage_path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class PatientImage:
    """
    Patient image entity.
    Links a patient to an image with clinical metadata.
    """
    id: UUID
    patient_id: UUID
    image_blob_hash: Optional[str] = None
    visit_date: Optional[datetime] = None
    modality: Optional[str] = None
    ai_reading_summary: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None
    
    # Joined data
    image_blob: Optional[ImageBlob] = None
    
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level from score."""
        if self.ai_confidence_score is None:
            return ConfidenceLevel.UNKNOWN
        if self.ai_confidence_score >= 0.8:
            return ConfidenceLevel.HIGH
        if self.ai_confidence_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
    
    @property
    def date_display(self) -> str:
        """Format visit date for display."""
        if self.visit_date:
            return self.visit_date.strftime("%Y-%m-%d %I:%M %p")
        return ""
    
    @property
    def storage_path(self) -> Optional[str]:
        """Get storage path from image blob."""
        if self.image_blob:
            return self.image_blob.storage_path
        return None
    
    @classmethod
    def from_dict(cls, data: dict) -> "PatientImage":
        """Create a PatientImage from a dictionary."""
        image_blob = None
        if data.get("image_blobs"):
            image_blob = ImageBlob.from_dict(data["image_blobs"]) if isinstance(data["image_blobs"], dict) else None
        
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            patient_id=UUID(data["patient_id"]) if isinstance(data["patient_id"], str) else data["patient_id"],
            image_blob_hash=data.get("image_blob_hash"),
            visit_date=datetime.fromisoformat(data["visit_date"].replace("Z", "+00:00")) if data.get("visit_date") else None,
            modality=data.get("modality"),
            ai_reading_summary=data.get("ai_reading_summary"),
            ai_confidence_score=data.get("ai_confidence_score"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            image_blob=image_blob
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "image_blob_hash": self.image_blob_hash,
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "modality": self.modality,
            "ai_reading_summary": self.ai_reading_summary,
            "ai_confidence_score": self.ai_confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class ImageCreate:
    """
    Data model for creating a new patient image record.
    """
    patient_id: UUID
    image_blob_hash: str
    visit_date: datetime
    modality: str
    ai_reading_summary: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "patient_id": str(self.patient_id),
            "image_blob_hash": self.image_blob_hash,
            "visit_date": self.visit_date.isoformat(),
            "modality": self.modality,
            "ai_reading_summary": self.ai_reading_summary,
            "ai_confidence_score": self.ai_confidence_score
        }
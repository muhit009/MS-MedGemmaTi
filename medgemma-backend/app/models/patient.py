"""
Patient data models.
Represents patient entities and related operations.
"""

from typing import Optional
from datetime import date, datetime
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Patient:
    """
    Patient entity model.
    
    Represents a patient record in the system.
    """
    id: UUID
    business_id: str
    full_name: str
    dob: date
    sex: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def age(self) -> int:
        """Calculate patient's age from date of birth."""
        today = date.today()
        return today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )
    
    @property
    def weight_display(self) -> Optional[str]:
        """Format weight for display."""
        if self.weight_kg:
            return f"{self.weight_kg} kg"
        return None
    
    @property
    def height_display(self) -> Optional[str]:
        """Format height for display."""
        if self.height_cm:
            return f"{self.height_cm} cm"
        return None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Patient":
        """Create a Patient instance from a dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            business_id=data["business_id"],
            full_name=data["full_name"],
            dob=date.fromisoformat(data["dob"]) if isinstance(data["dob"], str) else data["dob"],
            sex=data.get("sex"),
            weight_kg=data.get("weight_kg"),
            height_cm=data.get("height_cm"),
            avatar_url=data.get("avatar_url"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert Patient instance to dictionary."""
        return {
            "id": str(self.id),
            "business_id": self.business_id,
            "full_name": self.full_name,
            "dob": self.dob.isoformat(),
            "sex": self.sex,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class PatientCreate:
    """
    Data model for creating a new patient.
    """
    business_id: str
    full_name: str
    dob: date
    sex: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    avatar_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        return {
            "business_id": self.business_id,
            "full_name": self.full_name,
            "dob": self.dob.isoformat(),
            "sex": self.sex,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "avatar_url": self.avatar_url
        }


@dataclass
class PatientUpdate:
    """
    Data model for updating a patient.
    All fields are optional.
    """
    full_name: Optional[str] = None
    dob: Optional[date] = None
    sex: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    avatar_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.full_name is not None:
            result["full_name"] = self.full_name
        if self.dob is not None:
            result["dob"] = self.dob.isoformat()
        if self.sex is not None:
            result["sex"] = self.sex
        if self.weight_kg is not None:
            result["weight_kg"] = self.weight_kg
        if self.height_cm is not None:
            result["height_cm"] = self.height_cm
        if self.avatar_url is not None:
            result["avatar_url"] = self.avatar_url
        return result
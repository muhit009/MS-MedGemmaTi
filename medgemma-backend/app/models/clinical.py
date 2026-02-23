"""
Clinical data models.
Represents clinical notes, alerts, and vital signs.
"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from uuid import UUID
from enum import Enum


class VitalStatus(str, Enum):
    """Status indicators for vital signs."""
    STABLE = "stable"
    LOW = "low"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertSeverity(str, Enum):
    """Severity levels for clinical alerts."""
    NOMINAL = "nominal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class VitalReading:
    """
    Single vital sign reading.
    """
    value: any
    unit: str
    status: VitalStatus
    
    @classmethod
    def from_dict(cls, data: dict) -> "VitalReading":
        """Create a VitalReading from a dictionary."""
        return cls(
            value=data["value"],
            unit=data["unit"],
            status=VitalStatus(data.get("status", "unknown"))
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "unit": self.unit,
            "status": self.status.value
        }


@dataclass
class Vitals:
    """
    Complete vital signs record.
    """
    id: Optional[UUID] = None
    patient_id: Optional[UUID] = None
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    recorded_at: Optional[datetime] = None
    
    @property
    def heart_rate_reading(self) -> VitalReading:
        """Get heart rate as VitalReading."""
        status = VitalStatus.UNKNOWN
        if self.heart_rate:
            if self.heart_rate < 60:
                status = VitalStatus.LOW
            elif self.heart_rate > 100:
                status = VitalStatus.HIGH
            else:
                status = VitalStatus.STABLE
        return VitalReading(
            value=self.heart_rate or 0,
            unit="bpm",
            status=status
        )
    
    @property
    def spo2_reading(self) -> VitalReading:
        """Get SpO2 as VitalReading."""
        status = VitalStatus.UNKNOWN
        if self.spo2:
            if self.spo2 < 90:
                status = VitalStatus.CRITICAL
            elif self.spo2 < 95:
                status = VitalStatus.LOW
            else:
                status = VitalStatus.STABLE
        return VitalReading(
            value=self.spo2 or 0,
            unit="%",
            status=status
        )
    
    @property
    def blood_pressure_reading(self) -> VitalReading:
        """Get blood pressure as VitalReading."""
        status = VitalStatus.UNKNOWN
        if self.systolic_bp and self.diastolic_bp:
            if self.systolic_bp > 180 or self.diastolic_bp > 120:
                status = VitalStatus.CRITICAL
            elif self.systolic_bp > 140 or self.diastolic_bp > 90:
                status = VitalStatus.HIGH
            elif self.systolic_bp < 90 or self.diastolic_bp < 60:
                status = VitalStatus.LOW
            else:
                status = VitalStatus.STABLE
        
        bp_value = f"{self.systolic_bp or '--'}/{self.diastolic_bp or '--'}"
        return VitalReading(
            value=bp_value,
            unit="mmHg",
            status=status
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "Vitals":
        """Create a Vitals instance from a dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else None,
            patient_id=UUID(data["patient_id"]) if data.get("patient_id") else None,
            heart_rate=data.get("heart_rate"),
            spo2=data.get("spo2"),
            systolic_bp=data.get("systolic_bp"),
            diastolic_bp=data.get("diastolic_bp"),
            recorded_at=datetime.fromisoformat(data["recorded_at"].replace("Z", "+00:00")) if data.get("recorded_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "patient_id": str(self.patient_id) if self.patient_id else None,
            "heart_rate": self.heart_rate,
            "spo2": self.spo2,
            "systolic_bp": self.systolic_bp,
            "diastolic_bp": self.diastolic_bp,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None
        }


@dataclass
class ClinicalNote:
    """
    Clinical note entity.
    """
    id: UUID
    patient_id: UUID
    content: str
    is_alert: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def date_display(self) -> str:
        """Format date for display."""
        if self.created_at:
            return self.created_at.strftime("%Y-%m-%d")
        return ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "ClinicalNote":
        """Create a ClinicalNote from a dictionary."""
        return cls(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            patient_id=UUID(data["patient_id"]) if isinstance(data["patient_id"], str) else data["patient_id"],
            content=data["content"],
            is_alert=data.get("is_alert", False),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "content": self.content,
            "is_alert": self.is_alert,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class Alert:
    """
    Clinical alert entity.
    A specialized view of ClinicalNote for alerts.
    """
    id: Optional[UUID]
    content: str
    severity: AlertSeverity
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_clinical_note(cls, note: Optional[ClinicalNote]) -> "Alert":
        """Create an Alert from a ClinicalNote."""
        if note is None or not note.content:
            return cls(
                id=None,
                content="",
                severity=AlertSeverity.NOMINAL,
                updated_at=None
            )
        
        return cls(
            id=note.id,
            content=note.content,
            severity=AlertSeverity.WARNING,
            updated_at=note.updated_at
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """Create an Alert from a dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else None,
            content=data.get("content", ""),
            severity=AlertSeverity(data.get("severity", "nominal")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id) if self.id else None,
            "content": self.content,
            "severity": self.severity.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
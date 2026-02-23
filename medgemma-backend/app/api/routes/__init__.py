"""
API Routes initialization.
Aggregates all route modules into a single router.
"""

from fastapi import APIRouter

from app.api.routes import (
    auth,
    patients,
    vitals,
    alerts,
    notes,
    imaging,
    consultations,
    analysis,
)

api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(vitals.router, tags=["Vitals"])
api_router.include_router(alerts.router, tags=["Alerts"])
api_router.include_router(notes.router, tags=["Notes"])
api_router.include_router(imaging.router, tags=["Imaging"])
api_router.include_router(consultations.router, tags=["Consultations"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["AI Analysis"])
"""
Patient vitals routes.
Handles retrieval of biometric data.
"""

from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.clinical import VitalsResponse, VitalReading
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/patients/{patient_id}/vitals/latest", response_model=VitalsResponse)
async def get_latest_vitals(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the latest vital signs for a patient.
    
    Used to populate the Biometric HUD / Real-time Vitals section.
    """
    supabase = get_supabase_client()
    
    try:
        # First get the patient UUID from business_id
        patient_response = supabase.table("patients").select("id").eq("business_id", patient_id).execute()
        
        if not patient_response.data or len(patient_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        patient_uuid = patient_response.data[0]["id"]
        
        # Get latest vitals
        vitals_response = supabase.table("patient_vitals").select("*").eq(
            "patient_id", patient_uuid
        ).order("recorded_at", desc=True).limit(1).execute()
        
        if not vitals_response.data or len(vitals_response.data) == 0:
            # Return default/empty vitals if none recorded
            return VitalsResponse(
                heartRate=VitalReading(value=0, unit="bpm", status="unknown"),
                spO2=VitalReading(value=0, unit="%", status="unknown"),
                bloodPressure=VitalReading(value="--/--", unit="mmHg", status="unknown")
            )
        
        vitals = vitals_response.data[0]
        
        # Determine status based on values
        def get_hr_status(hr: int) -> str:
            if hr < 60:
                return "low"
            elif hr > 100:
                return "high"
            return "stable"
        
        def get_spo2_status(spo2: int) -> str:
            if spo2 < 95:
                return "low"
            return "stable"
        
        def get_bp_status(systolic: int, diastolic: int) -> str:
            if systolic > 140 or diastolic > 90:
                return "high"
            elif systolic < 90 or diastolic < 60:
                return "low"
            return "stable"
        
        heart_rate = vitals.get("heart_rate", 0)
        spo2 = vitals.get("spo2", 0)
        systolic = vitals.get("systolic_bp", 0)
        diastolic = vitals.get("diastolic_bp", 0)
        
        return VitalsResponse(
            heartRate=VitalReading(
                value=heart_rate,
                unit="bpm",
                status=get_hr_status(heart_rate)
            ),
            spO2=VitalReading(
                value=spo2,
                unit="%",
                status=get_spo2_status(spo2)
            ),
            bloodPressure=VitalReading(
                value=f"{systolic}/{diastolic}",
                unit="mmHg",
                status=get_bp_status(systolic, diastolic)
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving vitals: {str(e)}"
        )
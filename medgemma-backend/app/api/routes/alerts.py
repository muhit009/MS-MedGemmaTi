"""
Clinical alerts routes.
Handles viewing and updating patient alerts.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime

from app.schemas.clinical import AlertResponse, AlertUpdateRequest
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/patients/{patient_id}/alerts/active", response_model=AlertResponse)
async def get_active_alert(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the active clinical alert for a patient.
    
    Used for the Clinical Alert card.
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
        
        # Get active alert (is_alert = true)
        alert_response = supabase.table("clinical_notes").select("*").eq(
            "patient_id", patient_uuid
        ).eq("is_alert", True).order("updated_at", desc=True).limit(1).execute()
        
        if not alert_response.data or len(alert_response.data) == 0:
            # Return nominal status if no alert
            return AlertResponse(
                id=None,
                content="",
                severity="nominal",
                updatedAt=None
            )
        
        alert = alert_response.data[0]
        
        # Determine severity based on content
        severity = "warning" if alert.get("content") else "nominal"
        
        return AlertResponse(
            id=alert["id"],
            content=alert.get("content", ""),
            severity=severity,
            updatedAt=alert.get("updated_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert: {str(e)}"
        )


@router.put("/patients/{patient_id}/alerts", response_model=AlertResponse)
async def update_alert(
    patient_id: str,
    alert_request: AlertUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update or create the clinical alert for a patient.
    
    Supports in-place editing of the sticky alert.
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
        
        # Check if an alert already exists
        existing_alert = supabase.table("clinical_notes").select("*").eq(
            "patient_id", patient_uuid
        ).eq("is_alert", True).execute()
        
        now = datetime.utcnow().isoformat()
        
        if existing_alert.data and len(existing_alert.data) > 0:
            # Update existing alert
            alert_id = existing_alert.data[0]["id"]
            update_response = supabase.table("clinical_notes").update({
                "content": alert_request.content,
                "updated_at": now
            }).eq("id", alert_id).execute()
            
            updated_alert = update_response.data[0]
        else:
            # Create new alert
            insert_response = supabase.table("clinical_notes").insert({
                "patient_id": patient_uuid,
                "content": alert_request.content,
                "is_alert": True,
                "created_at": now,
                "updated_at": now
            }).execute()
            
            updated_alert = insert_response.data[0]
        
        severity = "warning" if alert_request.content else "nominal"
        
        return AlertResponse(
            id=updated_alert["id"],
            content=updated_alert.get("content", ""),
            severity=severity,
            updatedAt=updated_alert.get("updated_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating alert: {str(e)}"
        )
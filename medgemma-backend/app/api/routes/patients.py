"""
Patient management routes.
Handles patient search and retrieval.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional

from app.schemas.patient import (
    PatientResponse,
    PatientSearchRequest,
    PatientSearchResponse,
    PatientCreateRequest,
)
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client

router = APIRouter()


@router.post("/search", response_model=List[PatientSearchResponse])
async def search_patients(
    search_request: PatientSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search for patients by ID or name.
    
    Used in the initial Patient Selection dialog.
    """
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("patients").select("*")
        
        # Apply filters based on search criteria
        if search_request.patientId:
            query = query.ilike("business_id", f"%{search_request.patientId}%")
        
        if search_request.name:
            query = query.ilike("full_name", f"%{search_request.name}%")
        
        # Limit results
        query = query.limit(20)
        
        response = query.execute()
        
        # Transform to response format
        patients = []
        for patient in response.data:
            # Calculate age from DOB
            from datetime import date
            dob = date.fromisoformat(patient["dob"])
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            # Convert weight and height to display format
            weight_display = f"{patient.get('weight_kg', 0)} kg" if patient.get('weight_kg') else None
            height_display = f"{patient.get('height_cm', 0)} cm" if patient.get('height_cm') else None
            
            patients.append(PatientSearchResponse(
                id=patient["business_id"],
                name=patient["full_name"],
                dob=patient["dob"],
                age=age,
                sex=patient.get("sex"),
                weight=weight_display,
                height=height_display,
                avatarUrl=patient.get("avatar_url")
            ))
        
        return patients
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching patients: {str(e)}"
        )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get full patient details by ID.
    
    Used to populate the Patient Identification card.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("patients").select("*").eq("business_id", patient_id).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found"
            )
        
        patient = response.data[0]
        
        # Calculate age from DOB
        from datetime import date
        dob = date.fromisoformat(patient["dob"])
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Convert weight and height to display format
        weight_display = f"{patient.get('weight_kg', 0)} kg" if patient.get('weight_kg') else None
        height_display = f"{patient.get('height_cm', 0)} cm" if patient.get('height_cm') else None
        
        return PatientResponse(
            id=patient["business_id"],
            uuid=patient["id"],
            name=patient["full_name"],
            dob=patient["dob"],
            age=age,
            sex=patient.get("sex"),
            weight=weight_display,
            height=height_display,
            avatarUrl=patient.get("avatar_url"),
            createdAt=patient.get("created_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving patient: {str(e)}"
        )


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_request: PatientCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new patient record.
    """
    supabase = get_supabase_client()

    try:
        # Check if business_id already exists
        existing = supabase.table("patients").select("id").eq(
            "business_id", patient_request.businessId
        ).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patient with ID {patient_request.businessId} already exists"
            )

        # Build insert payload
        insert_data = {
            "business_id": patient_request.businessId,
            "full_name": patient_request.fullName,
            "dob": patient_request.dob,
        }
        if patient_request.sex is not None:
            insert_data["sex"] = patient_request.sex
        if patient_request.weightKg is not None:
            insert_data["weight_kg"] = patient_request.weightKg
        if patient_request.heightCm is not None:
            insert_data["height_cm"] = patient_request.heightCm
        if patient_request.avatarUrl is not None:
            insert_data["avatar_url"] = patient_request.avatarUrl

        response = supabase.table("patients").insert(insert_data).execute()

        patient = response.data[0]

        # Calculate age from DOB
        from datetime import date
        dob = date.fromisoformat(patient["dob"])
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        weight_display = f"{patient.get('weight_kg', 0)} kg" if patient.get('weight_kg') else None
        height_display = f"{patient.get('height_cm', 0)} cm" if patient.get('height_cm') else None

        return PatientResponse(
            id=patient["business_id"],
            uuid=patient["id"],
            name=patient["full_name"],
            dob=patient["dob"],
            age=age,
            sex=patient.get("sex"),
            weight=weight_display,
            height=height_display,
            avatarUrl=patient.get("avatar_url"),
            createdAt=patient.get("created_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating patient: {str(e)}"
        )
"""
Consultations routes.
Handles AI consultation sessions and chat history.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.schemas.conversation import (
    ConsultationResponse,
    ConsultationListResponse,
    MessageResponse,
)
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client

router = APIRouter()


def format_relative_date(date_str: str) -> str:
    """Convert datetime to relative format (Today, Yesterday, etc.)"""
    if not date_str:
        return ""
    
    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    now = datetime.now(date_obj.tzinfo) if date_obj.tzinfo else datetime.utcnow()
    
    diff = now.date() - date_obj.date()
    
    if diff.days == 0:
        return "Today"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return date_obj.strftime("%Y-%m-%d")


@router.get("/patients/{patient_id}/consultations", response_model=List[ConsultationListResponse])
async def list_consultations(
    patient_id: str,
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Get consultation history for a patient.
    
    Used for the Past Consultations collapsible list.
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
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Get consultations
        consultations_response = supabase.table("conversations").select("*").eq(
            "patient_id", patient_uuid
        ).order("started_at", desc=True).range(offset, offset + limit - 1).execute()
        
        consultations = []
        for consultation in consultations_response.data:
            # Get first message as snippet
            messages_response = supabase.table("messages").select("content").eq(
                "conversation_id", consultation["id"]
            ).order("created_at", desc=False).limit(1).execute()
            
            snippet = ""
            if messages_response.data and len(messages_response.data) > 0:
                content = messages_response.data[0].get("content", "")
                snippet = content[:100] + "..." if len(content) > 100 else content
            
            consultations.append(ConsultationListResponse(
                id=consultation["id"],
                title=consultation.get("title", "Consultation"),
                date=format_relative_date(consultation.get("started_at")),
                snippet=snippet
            ))
        
        return consultations
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving consultations: {str(e)}"
        )


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific consultation with its messages.
    """
    supabase = get_supabase_client()
    
    try:
        # Get consultation
        consultation_response = supabase.table("conversations").select("*").eq(
            "id", consultation_id
        ).execute()
        
        if not consultation_response.data or len(consultation_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consultation with ID {consultation_id} not found"
            )
        
        consultation = consultation_response.data[0]
        
        # Get messages
        messages_response = supabase.table("messages").select("*").eq(
            "conversation_id", consultation_id
        ).order("created_at", desc=False).execute()
        
        messages = []
        for msg in messages_response.data:
            messages.append(MessageResponse(
                id=msg["id"],
                sender=msg.get("sender", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("created_at")
            ))
        
        return ConsultationResponse(
            id=consultation["id"],
            title=consultation.get("title", "Consultation"),
            date=format_relative_date(consultation.get("started_at")),
            messages=messages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving consultation: {str(e)}"
        )


@router.get("/consultations/{consultation_id}/messages", response_model=List[MessageResponse])
async def get_consultation_messages(
    consultation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages for a specific consultation.
    
    Used when clicking on a past consultation item.
    """
    supabase = get_supabase_client()
    
    try:
        # Verify consultation exists
        consultation_response = supabase.table("conversations").select("id").eq(
            "id", consultation_id
        ).execute()
        
        if not consultation_response.data or len(consultation_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consultation with ID {consultation_id} not found"
            )
        
        # Get messages
        messages_response = supabase.table("messages").select("*").eq(
            "conversation_id", consultation_id
        ).order("created_at", desc=False).execute()
        
        messages = []
        for msg in messages_response.data:
            messages.append(MessageResponse(
                id=msg["id"],
                sender=msg.get("sender", "user"),
                content=msg.get("content", ""),
                timestamp=msg.get("created_at")
            ))
        
        return messages
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving messages: {str(e)}"
        )
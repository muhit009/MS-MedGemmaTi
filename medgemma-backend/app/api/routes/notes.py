"""
Patient notes routes.
Handles CRUD operations for clinical notes.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime

from app.schemas.clinical import NoteResponse, NoteCreateRequest, NoteUpdateRequest
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/patients/{patient_id}/notes", response_model=List[NoteResponse])
async def list_notes(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all clinical notes for a patient.
    
    Used for the collapsible Patient Notes section.
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
        
        # Get all non-alert notes
        notes_response = supabase.table("clinical_notes").select("*").eq(
            "patient_id", patient_uuid
        ).eq("is_alert", False).order("created_at", desc=True).execute()
        
        notes = []
        for note in notes_response.data:
            # Format date for display
            created_at = note.get("created_at", "")
            if created_at:
                date_obj = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_display = date_obj.strftime("%Y-%m-%d")
            else:
                date_display = ""
            
            notes.append(NoteResponse(
                id=note["id"],
                date=date_display,
                content=note.get("content", ""),
                createdAt=note.get("created_at"),
                updatedAt=note.get("updated_at")
            ))
        
        return notes
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving notes: {str(e)}"
        )


@router.post("/patients/{patient_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    patient_id: str,
    note_request: NoteCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new clinical note for a patient.
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
        
        now = datetime.utcnow().isoformat()
        
        # Create new note
        insert_response = supabase.table("clinical_notes").insert({
            "patient_id": patient_uuid,
            "content": note_request.content,
            "is_alert": False,
            "created_at": now,
            "updated_at": now
        }).execute()
        
        new_note = insert_response.data[0]
        
        # Format date for display
        date_display = datetime.utcnow().strftime("%Y-%m-%d")
        
        return NoteResponse(
            id=new_note["id"],
            date=date_display,
            content=new_note.get("content", ""),
            createdAt=new_note.get("created_at"),
            updatedAt=new_note.get("updated_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating note: {str(e)}"
        )


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_request: NoteUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing clinical note.
    """
    supabase = get_supabase_client()
    
    try:
        # Check if note exists
        existing_note = supabase.table("clinical_notes").select("*").eq("id", note_id).execute()
        
        if not existing_note.data or len(existing_note.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID {note_id} not found"
            )
        
        now = datetime.utcnow().isoformat()
        
        # Update note
        update_response = supabase.table("clinical_notes").update({
            "content": note_request.content,
            "updated_at": now
        }).eq("id", note_id).execute()
        
        updated_note = update_response.data[0]
        
        # Format date for display
        created_at = updated_note.get("created_at", "")
        if created_at:
            date_obj = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            date_display = date_obj.strftime("%Y-%m-%d")
        else:
            date_display = ""
        
        return NoteResponse(
            id=updated_note["id"],
            date=date_display,
            content=updated_note.get("content", ""),
            createdAt=updated_note.get("created_at"),
            updatedAt=updated_note.get("updated_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating note: {str(e)}"
        )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a clinical note.
    """
    supabase = get_supabase_client()
    
    try:
        # Check if note exists
        existing_note = supabase.table("clinical_notes").select("*").eq("id", note_id).execute()
        
        if not existing_note.data or len(existing_note.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Note with ID {note_id} not found"
            )
        
        # Delete note
        supabase.table("clinical_notes").delete().eq("id", note_id).execute()
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting note: {str(e)}"
        )
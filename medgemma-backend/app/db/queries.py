"""
Database queries and utilities.
Provides helper functions for common database operations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.services.supabase_client import get_supabase_client


# ============================================================================
# PATIENT QUERIES
# ============================================================================

def get_patient_by_business_id(business_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a patient by their business ID.
    
    Args:
        business_id: The patient's business ID (e.g., "8492-A").
    
    Returns:
        Patient data dictionary or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("patients").select("*").eq("business_id", business_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def get_patient_by_uuid(patient_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get a patient by their internal UUID.
    
    Args:
        patient_uuid: The patient's internal UUID.
    
    Returns:
        Patient data dictionary or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("patients").select("*").eq("id", patient_uuid).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def search_patients(
    patient_id: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for patients by ID or name.
    
    Args:
        patient_id: Optional patient business ID to search for.
        name: Optional patient name to search for.
        limit: Maximum number of results to return.
    
    Returns:
        List of matching patient records.
    """
    supabase = get_supabase_client()
    query = supabase.table("patients").select("*")
    
    if patient_id:
        query = query.ilike("business_id", f"%{patient_id}%")
    
    if name:
        query = query.ilike("full_name", f"%{name}%")
    
    response = query.limit(limit).execute()
    return response.data


def get_patient_uuid_from_business_id(business_id: str) -> Optional[str]:
    """
    Get patient UUID from business ID.
    
    Args:
        business_id: The patient's business ID.
    
    Returns:
        The patient's UUID or None if not found.
    """
    patient = get_patient_by_business_id(business_id)
    if patient:
        return patient["id"]
    return None


def calculate_age(dob: str) -> int:
    """
    Calculate age from date of birth.
    
    Args:
        dob: Date of birth in ISO format (YYYY-MM-DD).
    
    Returns:
        Age in years.
    """
    dob_date = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
    return age


# ============================================================================
# VITALS QUERIES
# ============================================================================

def get_latest_vitals(patient_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get the latest vital signs for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
    
    Returns:
        Latest vitals data or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("patient_vitals").select("*").eq(
        "patient_id", patient_uuid
    ).order("recorded_at", desc=True).limit(1).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def create_vitals_record(
    patient_uuid: str,
    heart_rate: int,
    spo2: int,
    systolic_bp: int,
    diastolic_bp: int
) -> Dict[str, Any]:
    """
    Create a new vitals record for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
        heart_rate: Heart rate in bpm.
        spo2: Blood oxygen saturation percentage.
        systolic_bp: Systolic blood pressure.
        diastolic_bp: Diastolic blood pressure.
    
    Returns:
        The created vitals record.
    """
    supabase = get_supabase_client()
    
    record = {
        "patient_id": patient_uuid,
        "heart_rate": heart_rate,
        "spo2": spo2,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "recorded_at": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("patient_vitals").insert(record).execute()
    return response.data[0]


# ============================================================================
# CLINICAL NOTES QUERIES
# ============================================================================

def get_patient_notes(patient_uuid: str, include_alerts: bool = False) -> List[Dict[str, Any]]:
    """
    Get all clinical notes for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
        include_alerts: Whether to include alert notes.
    
    Returns:
        List of clinical notes.
    """
    supabase = get_supabase_client()
    query = supabase.table("clinical_notes").select("*").eq("patient_id", patient_uuid)
    
    if not include_alerts:
        query = query.eq("is_alert", False)
    
    response = query.order("created_at", desc=True).execute()
    return response.data


def get_active_alert(patient_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get the active clinical alert for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
    
    Returns:
        Alert data or None if no active alert.
    """
    supabase = get_supabase_client()
    response = supabase.table("clinical_notes").select("*").eq(
        "patient_id", patient_uuid
    ).eq("is_alert", True).order("updated_at", desc=True).limit(1).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def create_note(patient_uuid: str, content: str, is_alert: bool = False) -> Dict[str, Any]:
    """
    Create a new clinical note.
    
    Args:
        patient_uuid: The patient's internal UUID.
        content: The note content.
        is_alert: Whether this is an alert note.
    
    Returns:
        The created note record.
    """
    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()
    
    record = {
        "patient_id": patient_uuid,
        "content": content,
        "is_alert": is_alert,
        "created_at": now,
        "updated_at": now
    }
    
    response = supabase.table("clinical_notes").insert(record).execute()
    return response.data[0]


def update_note(note_id: str, content: str) -> Dict[str, Any]:
    """
    Update an existing clinical note.
    
    Args:
        note_id: The note's UUID.
        content: The updated content.
    
    Returns:
        The updated note record.
    """
    supabase = get_supabase_client()
    
    response = supabase.table("clinical_notes").update({
        "content": content,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", note_id).execute()
    
    return response.data[0]


def delete_note(note_id: str) -> bool:
    """
    Delete a clinical note.
    
    Args:
        note_id: The note's UUID.
    
    Returns:
        True if deleted successfully.
    """
    supabase = get_supabase_client()
    supabase.table("clinical_notes").delete().eq("id", note_id).execute()
    return True


def upsert_alert(patient_uuid: str, content: str) -> Dict[str, Any]:
    """
    Create or update the clinical alert for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
        content: The alert content.
    
    Returns:
        The alert record.
    """
    existing_alert = get_active_alert(patient_uuid)
    
    if existing_alert:
        return update_note(existing_alert["id"], content)
    else:
        return create_note(patient_uuid, content, is_alert=True)


# ============================================================================
# IMAGING QUERIES
# ============================================================================

def get_patient_images(
    patient_uuid: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get imaging history for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
        limit: Maximum number of results.
        offset: Number of results to skip.
    
    Returns:
        List of imaging records.
    """
    supabase = get_supabase_client()
    response = supabase.table("patient_images").select(
        "*, image_blobs(storage_path, mime_type)"
    ).eq("patient_id", patient_uuid).order(
        "visit_date", desc=True
    ).range(offset, offset + limit - 1).execute()
    
    return response.data


def get_image_by_id(image_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific image by ID.
    
    Args:
        image_id: The image's UUID.
    
    Returns:
        Image data or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("patient_images").select(
        "*, image_blobs(storage_path, mime_type)"
    ).eq("id", image_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def get_images_by_ids(image_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get multiple images by their IDs.
    
    Args:
        image_ids: List of image UUIDs.
    
    Returns:
        List of image records.
    """
    supabase = get_supabase_client()
    response = supabase.table("patient_images").select(
        "*, image_blobs(storage_path, mime_type)"
    ).in_("id", image_ids).execute()
    
    return response.data


# ============================================================================
# CONVERSATION QUERIES
# ============================================================================

def get_patient_conversations(
    patient_uuid: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get conversation history for a patient.
    
    Args:
        patient_uuid: The patient's internal UUID.
        limit: Maximum number of results.
        offset: Number of results to skip.
    
    Returns:
        List of conversation records.
    """
    supabase = get_supabase_client()
    response = supabase.table("conversations").select("*").eq(
        "patient_id", patient_uuid
    ).order("started_at", desc=True).range(offset, offset + limit - 1).execute()
    
    return response.data


def get_conversation_by_id(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: The conversation's UUID.
    
    Returns:
        Conversation data or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("conversations").select("*").eq("id", conversation_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def get_conversation_messages(conversation_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a conversation.
    
    Args:
        conversation_id: The conversation's UUID.
    
    Returns:
        List of message records.
    """
    supabase = get_supabase_client()
    response = supabase.table("messages").select("*").eq(
        "conversation_id", conversation_id
    ).order("created_at", desc=False).execute()
    
    return response.data


def create_conversation(patient_uuid: str, title: str) -> Dict[str, Any]:
    """
    Create a new conversation.
    
    Args:
        patient_uuid: The patient's internal UUID.
        title: The conversation title.
    
    Returns:
        The created conversation record.
    """
    supabase = get_supabase_client()
    
    record = {
        "patient_id": patient_uuid,
        "title": title,
        "started_at": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("conversations").insert(record).execute()
    return response.data[0]


def create_message(
    conversation_id: str,
    sender: str,
    content: str
) -> Dict[str, Any]:
    """
    Create a new message in a conversation.
    
    Args:
        conversation_id: The conversation's UUID.
        sender: The sender ('user' or 'ai').
        content: The message content.
    
    Returns:
        The created message record.
    """
    supabase = get_supabase_client()
    
    record = {
        "conversation_id": conversation_id,
        "sender": sender,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("messages").insert(record).execute()
    return response.data[0]


def add_message_context(
    message_id: str,
    image_id: Optional[str] = None,
    note_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add context (attached image or note) to a message.
    
    Args:
        message_id: The message's UUID.
        image_id: Optional attached image UUID.
        note_id: Optional attached note UUID.
    
    Returns:
        The created context record.
    """
    supabase = get_supabase_client()
    
    record = {
        "message_id": message_id
    }
    
    if image_id:
        record["attached_image_id"] = image_id
    if note_id:
        record["attached_note_id"] = note_id
    
    response = supabase.table("message_context").insert(record).execute()
    return response.data[0]


# ============================================================================
# USER QUERIES
# ============================================================================

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by username.
    
    Args:
        username: The username to search for.
    
    Returns:
        User data or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("users").select("*").eq("username", username).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.
    
    Args:
        user_id: The user's UUID.
    
    Returns:
        User data or None if not found.
    """
    supabase = get_supabase_client()
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def create_user(
    username: str,
    hashed_password: str,
    full_name: Optional[str] = None,
    role: str = "physician"
) -> Dict[str, Any]:
    """
    Create a new user.
    
    Args:
        username: The username.
        hashed_password: The hashed password.
        full_name: Optional full name.
        role: User role (default: physician).
    
    Returns:
        The created user record.
    """
    supabase = get_supabase_client()
    
    record = {
        "username": username,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = supabase.table("users").insert(record).execute()
    return response.data[0]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_datetime_for_display(dt_string: str) -> str:
    """
    Format a datetime string for display.
    
    Args:
        dt_string: ISO format datetime string.
    
    Returns:
        Formatted datetime string.
    """
    if not dt_string:
        return ""
    
    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except ValueError:
        return dt_string


def format_relative_date(dt_string: str) -> str:
    """
    Format a datetime string as relative date (Today, Yesterday, etc.).
    
    Args:
        dt_string: ISO format datetime string.
    
    Returns:
        Relative date string.
    """
    if not dt_string:
        return ""
    
    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
        
        diff = now.date() - dt.date()
        
        if diff.days == 0:
            return "Today"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%Y-%m-%d")
    except ValueError:
        return dt_string
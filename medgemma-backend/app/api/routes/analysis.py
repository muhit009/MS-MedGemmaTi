"""
AI Analysis routes.
Handles the main AI generation endpoint for medical image analysis.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import base64
import logging
import uuid as _uuid

from app.schemas.conversation import (
    AnalysisRequest,
    AnalysisResponse,
    MessageResponse,
    InlineImage,
)
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client
from app.services.ai_service import generate_ai_response, generate_ai_response_stream, AIServiceError
from app.core.config import settings

log = logging.getLogger("analysis")

router = APIRouter()


def _download_image_as_base64(supabase, storage_path: str) -> Optional[str]:
    """Download an image from Supabase Storage and return as base64 string."""
    try:
        file_bytes = supabase.storage.from_(settings.STORAGE_BUCKET).download(storage_path)
        return base64.b64encode(file_bytes).decode("utf-8")
    except Exception as e:
        log.warning("Failed to download image %s: %s", storage_path, e)
        return None


def _fetch_conversation_history(supabase, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch recent messages from the conversation for context."""
    try:
        response = supabase.table("messages").select(
            "sender, content, created_at"
        ).eq("conversation_id", conversation_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        if response.data:
            return list(reversed(response.data))
        return []
    except Exception as e:
        log.warning("Failed to fetch conversation history: %s", e)
        return []


def _fetch_patient_info(supabase, patient_uuid: str) -> Dict[str, Any]:
    """Fetch patient demographics (age, sex, dob, etc.)."""
    try:
        resp = supabase.table("patients").select(
            "full_name, dob, sex, weight_kg, height_cm"
        ).eq("id", patient_uuid).execute()
        if resp.data:
            patient = resp.data[0]
            # Calculate age from dob
            age = None
            if patient.get("dob"):
                try:
                    born = datetime.fromisoformat(patient["dob"].replace("Z", "+00:00"))
                    today = datetime.utcnow()
                    age = today.year - born.year - (
                        (today.month, today.day) < (born.month, born.day)
                    )
                except Exception:
                    pass
            return {
                "name": patient.get("full_name"),
                "age": age,
                "sex": patient.get("sex"),
                "weight_kg": patient.get("weight_kg"),
                "height_cm": patient.get("height_cm"),
            }
    except Exception as e:
        log.warning("Failed to fetch patient info: %s", e)
    return {}


def _is_valid_uuid(val: str) -> bool:
    try:
        _uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _fetch_selected_images(supabase, patient_uuid: str, selected_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch only the explicitly selected images (by imageIds from the request).
    Downloads actual image bytes for each.
    The newest is marked 'Current Img', older ones 'Previous Img'.
    Returns empty list if no images were selected.
    """
    if not selected_ids:
        return []

    # Guard: drop any non-UUID strings (e.g. ephemeral "demo-img-..." IDs from
    # the frontend) before they reach PostgreSQL's uuid column and cause an error
    # that silently drops every image from the result.
    selected_ids = [sid for sid in selected_ids if _is_valid_uuid(sid)]
    if not selected_ids:
        return []

    try:
        imaging_response = supabase.table("patient_images").select(
            "*, image_blobs(storage_path, mime_type)"
        ).eq("patient_id", patient_uuid).in_("id", selected_ids).order(
            "visit_date", desc=False
        ).execute()

        if not imaging_response.data:
            return []

        images = []
        total = len(imaging_response.data)
        for idx, image in enumerate(imaging_response.data):
            storage_path = (image.get("image_blobs") or {}).get("storage_path")
            image_b64 = None
            if storage_path:
                image_b64 = _download_image_as_base64(supabase, storage_path)

            is_current = (idx == total - 1)
            images.append({
                "id": image["id"],
                "modality": image.get("modality"),
                "visit_date": image.get("visit_date"),
                "reading": image.get("ai_reading_summary"),
                "storage_path": storage_path,
                "image_base64": image_b64,
                "mime_type": (image.get("image_blobs") or {}).get("mime_type", "image/png"),
                "role": "Current Img" if is_current else "Previous Img",
                "study_number": idx + 1,
            })

        return images
    except Exception as e:
        log.warning("Failed to fetch patient images: %s", e)
        return []


def _gather_context(supabase, request, patient_uuid: str) -> Dict[str, Any]:
    """Gather full context for the AI model: patient info, all images, notes, alert."""
    selected_image_ids = [str(i) for i in (request.context.imageIds or [])] if request.context else []
    selected_note_ids = [str(i) for i in (request.context.noteIds or [])] if request.context else []

    context_data: Dict[str, Any] = {
        "patient": _fetch_patient_info(supabase, patient_uuid),
        "images": _fetch_selected_images(supabase, patient_uuid, selected_image_ids),
        "notes": [],
    }

    # Alert
    if request.context and request.context.alertContent:
        context_data["alert"] = request.context.alertContent

    # Fetch selected notes
    for note_id in selected_note_ids:
        note_response = supabase.table("clinical_notes").select("*").eq(
            "id", note_id
        ).execute()
        if note_response.data:
            note = note_response.data[0]
            context_data["notes"].append({
                "id": note["id"],
                "content": note.get("content"),
                "created_at": note.get("created_at"),
            })

    return context_data


# ---------------------------------------------------------------------------
# Helpers — inline image merging (for ephemeral demo uploads)
# ---------------------------------------------------------------------------

def _merge_inline_images(context_data: Dict[str, Any], inline_images) -> None:
    """
    Append inline base64 images from the request into context_data['images'],
    then re-sort by visit_date and reassign study numbers so temporal ordering
    is correct for the AI prompt.
    """
    if not inline_images:
        return
    for inline in inline_images:
        context_data["images"].append({
            "id": None,
            "modality": "X-Ray",
            "visit_date": inline.visitDate,
            "reading": None,
            "storage_path": None,
            "image_base64": inline.base64,
            "mime_type": inline.mimeType or "image/jpeg",
            "role": None,
            "study_number": None,
        })
    context_data["images"].sort(key=lambda x: x.get("visit_date") or "")
    for i, img in enumerate(context_data["images"]):
        img["study_number"] = i + 1


# ---------------------------------------------------------------------------
# Helpers — conversation persistence (skipped for demo patients)
# ---------------------------------------------------------------------------

def _is_demo_patient(business_id: str) -> bool:
    return business_id in settings.demo_patient_ids_set


def _get_or_create_conversation(supabase, patient_uuid: str, prompt: str) -> str:
    """Find a recent conversation or create a new one. Returns conversation_id."""
    now = datetime.utcnow().isoformat()
    conv_resp = supabase.table("conversations").select("*").eq(
        "patient_id", patient_uuid
    ).order("started_at", desc=True).limit(1).execute()

    if conv_resp.data:
        last = conv_resp.data[0]
        started_at = datetime.fromisoformat(last["started_at"].replace("Z", "+00:00"))
        if (datetime.utcnow().replace(tzinfo=started_at.tzinfo) - started_at).total_seconds() < 1800:
            return last["id"]

    title = prompt[:50] + ("..." if len(prompt) > 50 else "")
    new_conv = supabase.table("conversations").insert({
        "patient_id": patient_uuid, "title": title, "started_at": now,
    }).execute()
    return new_conv.data[0]["id"]


def _save_user_message(supabase, conversation_id: str, request: "AnalysisRequest") -> None:
    """Persist user message + context links to DB."""
    now = datetime.utcnow().isoformat()
    user_msg = supabase.table("messages").insert({
        "conversation_id": conversation_id, "sender": "user",
        "content": request.prompt, "created_at": now,
    }).execute()
    msg_id = user_msg.data[0]["id"]

    if request.context:
        for image_id in (request.context.imageIds or []):
            supabase.table("message_context").insert({
                "message_id": msg_id, "attached_image_id": str(image_id),
            }).execute()
        for note_id in (request.context.noteIds or []):
            supabase.table("message_context").insert({
                "message_id": msg_id, "attached_note_id": str(note_id),
            }).execute()


def _save_ai_message(supabase, conversation_id: str, text: str) -> None:
    """Persist AI response to DB."""
    supabase.table("messages").insert({
        "conversation_id": conversation_id, "sender": "ai",
        "content": text, "created_at": datetime.utcnow().isoformat(),
    }).execute()


# ---------------------------------------------------------------------------
# Non-streaming endpoint
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=AnalysisResponse)
async def generate_analysis(
    request: AnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI analysis based on prompt and context."""
    supabase = get_supabase_client()

    try:
        patient_response = supabase.table("patients").select("id").eq(
            "business_id", request.patientId
        ).execute()

        if not patient_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {request.patientId} not found"
            )

        patient_uuid = patient_response.data[0]["id"]
        demo = _is_demo_patient(request.patientId)
        context_data = _gather_context(supabase, request, patient_uuid)
        _merge_inline_images(context_data, request.inlineImages)

        # For non-demo patients: load conversation history (but don't save yet)
        conversation_id = None
        if not demo:
            conversation_id = _get_or_create_conversation(supabase, patient_uuid, request.prompt)
            context_data["conversation_history"] = _fetch_conversation_history(supabase, conversation_id)
        else:
            context_data["conversation_history"] = []

        model_config = request.modelConfig.model_dump() if request.modelConfig else {}
        effective_mode = request.mode or (
            'discussion' if context_data.get('conversation_history') else 'analysis'
        )
        model_config['mode'] = effective_mode

        try:
            ai_response_text = await generate_ai_response(
                prompt=request.prompt, context=context_data, config=model_config
            )
        except AIServiceError as e:
            log.error("AI service error (not persisted): %s", e)
            return AnalysisResponse(
                text="Analysis could not be completed. Please try again.",
                timestamp=datetime.utcnow().isoformat(),
                sender="ai",
            )

        ai_time = datetime.utcnow().isoformat()

        # Only persist after a successful AI response
        if not demo and conversation_id:
            _save_user_message(supabase, conversation_id, request)
            _save_ai_message(supabase, conversation_id, ai_response_text)

        return AnalysisResponse(text=ai_response_text, timestamp=ai_time, sender="ai")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analysis: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Streaming endpoint
# ---------------------------------------------------------------------------

@router.post("/generate/stream")
async def generate_analysis_stream(
    request: AnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate AI analysis with Server-Sent Events (SSE) streaming."""
    supabase = get_supabase_client()

    try:
        patient_response = supabase.table("patients").select("id").eq(
            "business_id", request.patientId
        ).execute()

        if not patient_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {request.patientId} not found"
            )

        patient_uuid = patient_response.data[0]["id"]
        demo = _is_demo_patient(request.patientId)
        context_data = _gather_context(supabase, request, patient_uuid)
        _merge_inline_images(context_data, request.inlineImages)

        # For non-demo patients: load conversation history (but don't save yet)
        conversation_id = None
        if not demo:
            conversation_id = _get_or_create_conversation(supabase, patient_uuid, request.prompt)
            context_data["conversation_history"] = _fetch_conversation_history(supabase, conversation_id)
        else:
            context_data["conversation_history"] = []

        model_config = request.modelConfig.model_dump() if request.modelConfig else {}
        effective_mode = request.mode or (
            'discussion' if context_data.get('conversation_history') else 'analysis'
        )
        model_config['mode'] = effective_mode

        async def event_generator():
            full_response = ""
            errored = False

            try:
                async for chunk in generate_ai_response_stream(
                    prompt=request.prompt, context=context_data, config=model_config
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
            except AIServiceError as e:
                log.error("AI service error during stream (not persisted): %s", e)
                errored = True
                yield f"data: {json.dumps({'text': 'Analysis could not be completed. Please try again.'})}\n\n"

            # Only persist after a successful AI response
            if not errored and not demo and conversation_id:
                _save_user_message(supabase, conversation_id, request)
                _save_ai_message(supabase, conversation_id, full_response)

            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating analysis: {str(e)}"
        )

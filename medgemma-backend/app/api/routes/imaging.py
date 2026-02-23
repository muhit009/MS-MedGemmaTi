"""
Imaging history routes.
Handles retrieval, upload, and deletion of patient imaging records.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File, Form
from fastapi.responses import Response
from typing import List, Optional
from datetime import datetime, timezone
import io
import uuid

from PIL import Image

from app.schemas.imaging import ImageResponse
from app.core.security import get_current_user
from app.services.supabase_client import get_supabase_client
from app.core.config import settings

MAX_IMAGES_PER_PATIENT = 5

router = APIRouter()


@router.get("/patients/{patient_id}/imaging", response_model=List[ImageResponse])
async def get_imaging_history(
    patient_id: str,
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user)
):
    """
    Get imaging history for a patient.
    
    Used for the Imaging History section and Selected Images chips.
    Supports pagination for patients with extensive records.
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
        
        # Get imaging records with blob information
        imaging_response = supabase.table("patient_images").select(
            "*, image_blobs(storage_path, mime_type)"
        ).eq("patient_id", patient_uuid).order(
            "visit_date", desc=True
        ).range(offset, offset + limit - 1).execute()
        
        images = []
        for image in imaging_response.data:
            # Format date for display
            visit_date = image.get("visit_date", "")
            if visit_date:
                date_obj = datetime.fromisoformat(visit_date.replace("Z", "+00:00"))
                date_display = date_obj.strftime("%Y-%m-%d %I:%M %p")
            else:
                date_display = ""
            
            # Generate signed URL for the image
            # In production, this would use Supabase Storage signed URLs
            storage_path = ""
            if image.get("image_blobs") and image["image_blobs"].get("storage_path"):
                storage_path = image["image_blobs"]["storage_path"]
                # Generate signed URL (valid for 1 hour)
                try:
                    signed_url_response = supabase.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
                        storage_path, 3600
                    )
                    src = signed_url_response.get("signedURL", storage_path)
                except Exception:
                    src = storage_path
            else:
                src = ""

            # Convert confidence score to display format
            confidence_score = image.get("ai_confidence_score") or 0
            if confidence_score >= 0.8:
                confidence = "High"
            elif confidence_score >= 0.5:
                confidence = "Medium"
            else:
                confidence = "Low"

            images.append(ImageResponse(
                id=image["id"],
                src=src,
                modality=image.get("modality", "Unknown"),
                date=date_display,
                reading=image.get("ai_reading_summary", ""),
                confidence=confidence
            ))
        
        return images
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving imaging history: {str(e)}"
        )


@router.get("/patients/{patient_id}/imaging/{image_id}", response_model=ImageResponse)
async def get_image_details(
    patient_id: str,
    image_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details for a specific image.
    """
    supabase = get_supabase_client()
    
    try:
        # Get the specific image
        image_response = supabase.table("patient_images").select(
            "*, image_blobs(storage_path, mime_type)"
        ).eq("id", image_id).execute()
        
        if not image_response.data or len(image_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image with ID {image_id} not found"
            )
        
        image = image_response.data[0]
        
        # Format date for display
        visit_date = image.get("visit_date", "")
        if visit_date:
            date_obj = datetime.fromisoformat(visit_date.replace("Z", "+00:00"))
            date_display = date_obj.strftime("%Y-%m-%d %I:%M %p")
        else:
            date_display = ""
        
        # Generate signed URL for the image
        storage_path = ""
        if image.get("image_blobs") and image["image_blobs"].get("storage_path"):
            storage_path = image["image_blobs"]["storage_path"]
            try:
                signed_url_response = supabase.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
                    storage_path, 3600
                )
                src = signed_url_response.get("signedURL", storage_path)
            except Exception:
                src = storage_path
        else:
            src = ""

        # Convert confidence score to display format
        confidence_score = image.get("ai_confidence_score") or 0
        if confidence_score >= 0.8:
            confidence = "High"
        elif confidence_score >= 0.5:
            confidence = "Medium"
        else:
            confidence = "Low"

        return ImageResponse(
            id=image["id"],
            src=src,
            modality=image.get("modality", "Unknown"),
            date=date_display,
            reading=image.get("ai_reading_summary", ""),
            confidence=confidence
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving image: {str(e)}"
        )


def _convert_to_jpeg(file_bytes: bytes, filename: str) -> bytes:
    """
    Convert uploaded image bytes to JPEG format.
    Supports JPEG, PNG, and DICOM files.
    """
    lower_name = filename.lower()

    if lower_name.endswith(".dcm"):
        # DICOM handling via pydicom
        try:
            import pydicom
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DICOM support not available (pydicom not installed)",
            )
        try:
            ds = pydicom.dcmread(io.BytesIO(file_bytes))
            pixel_array = ds.pixel_array
            import numpy as np
            arr = pixel_array.astype(np.float64)
            if arr.max() != arr.min():
                arr = (arr - arr.min()) / (arr.max() - arr.min()) * 255.0
            arr = arr.astype(np.uint8)
            pil_image = Image.fromarray(arr)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read DICOM file: {exc}",
            )
    else:
        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file. Supported formats: JPEG, PNG, DICOM (.dcm)",
            )

    # Convert to RGB if necessary (JPEG doesn't support RGBA or palette modes)
    if pil_image.mode not in ("RGB", "L"):
        pil_image = pil_image.convert("RGB")

    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@router.post("/patients/{patient_id}/imaging", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    patient_id: str,
    file: UploadFile = File(...),
    visit_date: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a medical image for a patient.

    Accepts JPEG, PNG, and DICOM (.dcm) files.
    All images are converted to JPEG before storage.
    Maximum 5 images per patient.

    visit_date: optional date string in MM/DD/YYYY format (defaults to today).
    """
    supabase = get_supabase_client()

    # Parse visit_date (MM/DD/YYYY) or default to today
    if visit_date and visit_date.strip():
        try:
            parsed_date = datetime.strptime(visit_date.strip(), "%m/%d/%Y")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid visit_date format. Expected MM/DD/YYYY.",
            )
    else:
        parsed_date = datetime.now(timezone.utc)

    visit_date_iso = parsed_date.replace(tzinfo=timezone.utc).isoformat()
    date_mmddyyyy = parsed_date.strftime("%m%d%Y")

    # Resolve patient UUID from business_id
    patient_response = supabase.table("patients").select("id").eq("business_id", patient_id).execute()
    if not patient_response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient with ID {patient_id} not found")
    patient_uuid = patient_response.data[0]["id"]

    # Check image count limit & determine next sequence number
    count_resp = supabase.table("patient_images").select("id", count="exact").eq("patient_id", patient_uuid).execute()
    current_count = count_resp.count if count_resp.count is not None else len(count_resp.data)
    if current_count >= MAX_IMAGES_PER_PATIENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_IMAGES_PER_PATIENT} images per patient. Delete an existing image first.",
        )
    next_number = current_count + 1

    # Read and convert to JPEG
    file_bytes = await file.read()
    jpeg_bytes = _convert_to_jpeg(file_bytes, file.filename or "upload.jpg")

    # Sequential storage path
    storage_path = f"patients/{patient_id}/{next_number}_{patient_id}_{date_mmddyyyy}_xray.jpeg"

    # Upload to Supabase Storage
    try:
        supabase.storage.from_(settings.STORAGE_BUCKET).upload(
            storage_path,
            jpeg_bytes,
            {"content-type": "image/jpeg"},
        )
    except Exception as exc:
        if "Duplicate" not in str(exc) and "already exists" not in str(exc):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to storage: {exc}",
            )

    # Generate a unique file_hash for the blob record (based on storage path)
    import hashlib
    file_hash = hashlib.sha256(storage_path.encode()).hexdigest()

    # Upsert image_blobs
    supabase.table("image_blobs").upsert({
        "file_hash": file_hash,
        "storage_path": storage_path,
        "mime_type": "image/jpeg",
        "size_bytes": len(jpeg_bytes),
    }).execute()

    # Insert patient_images record — always X-Ray modality
    image_id = str(uuid.uuid4())
    supabase.table("patient_images").insert({
        "id": image_id,
        "patient_id": patient_uuid,
        "image_blob_hash": file_hash,
        "visit_date": visit_date_iso,
        "modality": "X-Ray",
    }).execute()

    # Generate signed URL
    try:
        signed = supabase.storage.from_(settings.STORAGE_BUCKET).create_signed_url(storage_path, 3600)
        src = signed.get("signedURL", storage_path)
    except Exception:
        src = storage_path

    date_display = parsed_date.strftime("%Y-%m-%d %I:%M %p")

    return ImageResponse(
        id=image_id,
        src=src,
        modality="X-Ray",
        date=date_display,
        reading=None,
        confidence="Low",
    )


@router.delete("/patients/{patient_id}/imaging/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    patient_id: str,
    image_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a patient image.
    Removes the patient_images record, storage file, and image_blobs record
    (if no other patient_images reference the same blob).
    """
    import logging
    log = logging.getLogger("imaging")

    supabase = get_supabase_client()

    try:
        # Fetch the patient_images record
        img_resp = supabase.table("patient_images").select("id, image_blob_hash").eq("id", image_id).execute()
        if not img_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image {image_id} not found")

        blob_hash = img_resp.data[0]["image_blob_hash"]

        # Get storage path from image_blobs
        blob_resp = supabase.table("image_blobs").select("storage_path").eq("file_hash", blob_hash).execute()
        storage_path = blob_resp.data[0]["storage_path"] if blob_resp.data else None

        # Delete the patient_images record
        del_resp = supabase.table("patient_images").delete().eq("id", image_id).execute()
        log.info("Deleted patient_images row %s, response data: %s", image_id, del_resp.data)

        # Check if any other patient_images reference the same blob
        remaining = supabase.table("patient_images").select("id", count="exact").eq("image_blob_hash", blob_hash).execute()
        remaining_count = remaining.count if remaining.count is not None else len(remaining.data)

        if remaining_count == 0:
            # No other references — clean up blob and storage
            if storage_path:
                try:
                    supabase.storage.from_(settings.STORAGE_BUCKET).remove([storage_path])
                except Exception:
                    pass  # Best-effort storage cleanup
            supabase.table("image_blobs").delete().eq("file_hash", blob_hash).execute()

    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to delete image %s: %s", image_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
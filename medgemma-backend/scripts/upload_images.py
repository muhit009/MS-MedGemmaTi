"""
Upload demo X-ray images to Supabase Storage and update DB records.

Usage:
    cd medgemma-backend
    python -m scripts.upload_images
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.supabase_client import get_supabase_client

BUCKET = "medical-images"
# Project root is two levels up from scripts/upload_images.py -> medgemma-backend/ -> project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGE_DIR = os.path.join(PROJECT_ROOT, "frontend", "public")

# Map: storage_path -> local file
# We upload the same image to different paths so each patient_image
# gets a distinct signed URL (easier to debug in the UI).
UPLOADS = {
    "patients/8492-A/xray_chest_ap_20251014.jpg": "xray1.jpg",
    "patients/8492-A/ct_chest_20251128.jpg": "xray2.jpg",
    "patients/8492-A/xray_chest_ap_20260115.jpg": "xray3.jpg",
    "patients/5519-C/mri_lumbar_20260120.jpg": "xray4.jpg",
    "patients/7731-B/xray_chest_20260105.jpg": "xray5.jpg",
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    sb = get_supabase_client()

    print("=" * 60)
    print("MedGemma — Image Uploader")
    print("=" * 60)

    # ── Ensure bucket exists ──────────────────────────────────
    print(f"\nEnsuring bucket '{BUCKET}' exists ...")
    try:
        sb.storage.get_bucket(BUCKET)
        print(f"  bucket '{BUCKET}' already exists")
    except Exception:
        sb.storage.create_bucket(
            BUCKET,
            options={
                "public": False,
                "file_size_limit": 52428800,
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
            },
        )
        print(f"  created bucket '{BUCKET}'")

    storage = sb.storage.from_(BUCKET)

    # ── Upload files ──────────────────────────────────────────
    print(f"\nUploading to bucket '{BUCKET}' ...")
    hashes = {}  # storage_path -> sha256

    for storage_path, local_file in UPLOADS.items():
        local_path = os.path.join(IMAGE_DIR, local_file)
        if not os.path.exists(local_path):
            print(f"  SKIP {local_file} — not found at {local_path}")
            continue

        file_hash = sha256_file(local_path)
        file_size = os.path.getsize(local_path)
        hashes[storage_path] = (file_hash, file_size)

        with open(local_path, "rb") as f:
            data = f.read()

        try:
            # Remove existing file if present (upsert)
            try:
                storage.remove([storage_path])
            except Exception:
                pass
            storage.upload(storage_path, data, {"content-type": "image/jpeg"})
            print(f"  uploaded {local_file} -> {storage_path} ({file_size:,} bytes)")
        except Exception as e:
            print(f"  ERROR uploading {local_file}: {e}")
            continue

    # ── Update DB records ─────────────────────────────────────
    print("\nUpdating database records ...")

    # Clear old image data (respect FK: message_context -> patient_images -> image_blobs)
    sb.table("message_context").delete().not_.is_("attached_image_id", "null").execute()
    print("  cleared message_context (image refs)")
    sb.table("patient_images").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    sb.table("image_blobs").delete().neq("file_hash", "0000000000000000000000000000000000000000000000000000000000000000").execute()
    print("  cleared old image records")

    # Since all files are identical, they share one hash.
    # But we store separate blob records per storage_path to keep
    # each patient_image's signed URL distinct.
    # To make this work with the file_hash PK, we use unique
    # synthetic hashes (real hash + path suffix).
    blobs = []
    for storage_path, (file_hash, file_size) in hashes.items():
        # Create a unique hash per path by hashing (hash + path)
        unique_hash = hashlib.sha256(
            (file_hash + storage_path).encode()
        ).hexdigest()
        blobs.append({
            "file_hash": unique_hash,
            "storage_path": storage_path,
            "mime_type": "image/jpeg",
            "size_bytes": file_size,
        })

    sb.table("image_blobs").insert(blobs).execute()
    print(f"  inserted {len(blobs)} image_blobs")

    # Build hash lookup: storage_path -> unique_hash
    path_to_hash = {
        b["storage_path"]: b["file_hash"] for b in blobs
    }

    # Patient images (same structure as seed, now with real blobs)
    images = [
        # John Doe — 3 studies
        {
            "id": "40000000-0000-0000-0000-000000000001",
            "patient_id": "10000000-0000-0000-0000-000000000001",
            "image_blob_hash": path_to_hash["patients/8492-A/xray_chest_ap_20251014.jpg"],
            "visit_date": "2025-10-14T09:30:00+00:00",
            "modality": "X-Ray (Chest AP)",
            "ai_reading_summary": "Clear lung fields bilaterally. No acute cardiopulmonary abnormality. Heart size within normal limits.",
            "ai_confidence_score": 0.92,
        },
        {
            "id": "40000000-0000-0000-0000-000000000002",
            "patient_id": "10000000-0000-0000-0000-000000000001",
            "image_blob_hash": path_to_hash["patients/8492-A/ct_chest_20251128.jpg"],
            "visit_date": "2025-11-28T14:15:00+00:00",
            "modality": "CT (Chest)",
            "ai_reading_summary": "Small 1.2cm nodule identified in the right lower lobe. No lymphadenopathy. Recommend follow-up imaging in 3 months.",
            "ai_confidence_score": 0.87,
        },
        {
            "id": "40000000-0000-0000-0000-000000000003",
            "patient_id": "10000000-0000-0000-0000-000000000001",
            "image_blob_hash": path_to_hash["patients/8492-A/xray_chest_ap_20260115.jpg"],
            "visit_date": "2026-01-15T10:00:00+00:00",
            "modality": "X-Ray (Chest AP)",
            "ai_reading_summary": "RLL nodule appears stable compared to prior CT. No new infiltrates. Continued monitoring recommended.",
            "ai_confidence_score": 0.85,
        },
        # Robert Chen — 1 study
        {
            "id": "40000000-0000-0000-0000-000000000004",
            "patient_id": "10000000-0000-0000-0000-000000000003",
            "image_blob_hash": path_to_hash["patients/5519-C/mri_lumbar_20260120.jpg"],
            "visit_date": "2026-01-20T11:00:00+00:00",
            "modality": "MRI (Lumbar Spine)",
            "ai_reading_summary": "Mild disc desiccation at L4-L5. Small central disc protrusion without significant canal stenosis. Facet arthropathy at L5-S1.",
            "ai_confidence_score": 0.90,
        },
        # Jane Martinez — 1 study (new)
        {
            "id": "40000000-0000-0000-0000-000000000005",
            "patient_id": "10000000-0000-0000-0000-000000000002",
            "image_blob_hash": path_to_hash["patients/7731-B/xray_chest_20260105.jpg"],
            "visit_date": "2026-01-05T14:00:00+00:00",
            "modality": "X-Ray (Chest PA)",
            "ai_reading_summary": "No acute findings. Clear lung fields. Normal cardiac silhouette. No pleural effusion.",
            "ai_confidence_score": 0.95,
        },
    ]
    sb.table("patient_images").insert(images).execute()
    print(f"  inserted {len(images)} patient_images")

    # ── Verify signed URLs work ───────────────────────────────
    print("\nVerifying signed URLs ...")
    for blob in blobs[:2]:
        try:
            url = storage.create_signed_url(blob["storage_path"], 60)
            print(f"  {blob['storage_path'][:40]}... -> URL OK")
        except Exception as e:
            print(f"  {blob['storage_path'][:40]}... -> ERROR: {e}")

    print("\n" + "=" * 60)
    print("Done! 5 images uploaded and linked.")
    print("  John Doe (8492-A):     3 images")
    print("  Jane Martinez (7731-B): 1 image")
    print("  Robert Chen (5519-C):  1 image")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Full seed script — replaces all demo data in Supabase.
Mirrors the SQL migration's seed section (section 7) exactly.

Usage:
    cd medgemma-backend
    python -m scripts.seed_full
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from app.services.supabase_client import get_supabase_client
from app.core.security import get_password_hash


def now():
    return datetime.now(timezone.utc)


def ts(dt: datetime) -> str:
    return dt.isoformat()


def main():
    sb = get_supabase_client()
    n = now()

    print("=" * 60)
    print("MedGemma — Full Database Seeder")
    print("=" * 60)

    # ── 1. Clear existing data (FK-safe order) ────────────────
    print("\n[1/8] Clearing existing data ...")
    for table in [
        "message_context",
        "messages",
        "conversations",
        "patient_images",
        "image_blobs",
        "clinical_notes",
        "patient_vitals",
        "patients",
        "users",
    ]:
        try:
            sb.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print(f"  cleared {table}")
        except Exception as e:
            # image_blobs PK is file_hash, not id
            if table == "image_blobs":
                try:
                    sb.table(table).delete().neq("file_hash", "x").execute()
                    print(f"  cleared {table}")
                except Exception as e2:
                    print(f"  skip {table}: {e2}")
            else:
                print(f"  skip {table}: {e}")

    # ── 2. Users ──────────────────────────────────────────────
    print("\n[2/8] Creating users ...")
    sb.table("users").insert({
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "dr.smith",
        "hashed_password": get_password_hash("password"),
        "full_name": "Dr. Sarah Smith",
        "role": "physician",
        "is_active": True,
    }).execute()
    print("  dr.smith / password")

    # ── 3. Patients ───────────────────────────────────────────
    print("\n[3/8] Creating patients ...")
    patients = [
        {
            "id": "10000000-0000-0000-0000-000000000001",
            "business_id": "8492-A",
            "full_name": "John Doe",
            "dob": "1980-05-12",
            "sex": "Male",
            "weight_kg": 81.65,
            "height_cm": 182.00,
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "business_id": "7731-B",
            "full_name": "Jane Martinez",
            "dob": "1992-11-03",
            "sex": "Female",
            "weight_kg": 63.50,
            "height_cm": 165.00,
        },
        {
            "id": "10000000-0000-0000-0000-000000000003",
            "business_id": "5519-C",
            "full_name": "Robert Chen",
            "dob": "1975-08-22",
            "sex": "Male",
            "weight_kg": 90.72,
            "height_cm": 175.00,
        },
    ]
    sb.table("patients").insert(patients).execute()
    for p in patients:
        print(f"  {p['full_name']} ({p['business_id']})")

    # ── 4. Vitals ─────────────────────────────────────────────
    print("\n[4/8] Creating vitals ...")
    vitals = [
        # John Doe — stable
        {"patient_id": "10000000-0000-0000-0000-000000000001", "heart_rate": 72, "spo2": 98, "systolic_bp": 120, "diastolic_bp": 80, "recorded_at": ts(n - timedelta(minutes=5))},
        {"patient_id": "10000000-0000-0000-0000-000000000001", "heart_rate": 74, "spo2": 97, "systolic_bp": 122, "diastolic_bp": 82, "recorded_at": ts(n - timedelta(hours=1))},
        {"patient_id": "10000000-0000-0000-0000-000000000001", "heart_rate": 70, "spo2": 98, "systolic_bp": 118, "diastolic_bp": 78, "recorded_at": ts(n - timedelta(hours=3))},
        # Jane Martinez — slightly elevated HR
        {"patient_id": "10000000-0000-0000-0000-000000000002", "heart_rate": 88, "spo2": 99, "systolic_bp": 115, "diastolic_bp": 75, "recorded_at": ts(n - timedelta(minutes=10))},
        {"patient_id": "10000000-0000-0000-0000-000000000002", "heart_rate": 85, "spo2": 98, "systolic_bp": 118, "diastolic_bp": 76, "recorded_at": ts(n - timedelta(hours=2))},
        # Robert Chen — borderline high BP
        {"patient_id": "10000000-0000-0000-0000-000000000003", "heart_rate": 68, "spo2": 96, "systolic_bp": 142, "diastolic_bp": 92, "recorded_at": ts(n - timedelta(minutes=15))},
        {"patient_id": "10000000-0000-0000-0000-000000000003", "heart_rate": 71, "spo2": 97, "systolic_bp": 138, "diastolic_bp": 88, "recorded_at": ts(n - timedelta(hours=4))},
    ]
    sb.table("patient_vitals").insert(vitals).execute()
    print(f"  {len(vitals)} vitals records")

    # ── 5. Clinical notes + alerts ────────────────────────────
    print("\n[5/8] Creating clinical notes ...")
    notes = [
        # John Doe
        {"id": "30000000-0000-0000-0000-000000000001", "patient_id": "10000000-0000-0000-0000-000000000001",
         "content": "Patient complained of persistent cough lasting 3 weeks. No fever. Ordered chest X-ray to rule out underlying pathology.",
         "is_alert": False, "created_at": ts(n - timedelta(days=5)), "updated_at": ts(n - timedelta(days=5))},
        {"id": "30000000-0000-0000-0000-000000000002", "patient_id": "10000000-0000-0000-0000-000000000001",
         "content": "Follow-up: Chest X-ray shows a 1.2cm RLL nodule. Recommend CT for further evaluation. Patient informed.",
         "is_alert": False, "created_at": ts(n - timedelta(days=3)), "updated_at": ts(n - timedelta(days=3))},
        {"id": "30000000-0000-0000-0000-000000000003", "patient_id": "10000000-0000-0000-0000-000000000001",
         "content": "Monitor RLL nodule stability. Patient reports mild shortness of breath during exertion.",
         "is_alert": True, "created_at": ts(n - timedelta(days=1)), "updated_at": ts(n - timedelta(days=1))},
        # Jane Martinez
        {"id": "30000000-0000-0000-0000-000000000004", "patient_id": "10000000-0000-0000-0000-000000000002",
         "content": "Annual physical. All vitals within normal range. Patient reports occasional headaches, likely tension-related.",
         "is_alert": False, "created_at": ts(n - timedelta(days=10)), "updated_at": ts(n - timedelta(days=10))},
        {"id": "30000000-0000-0000-0000-000000000005", "patient_id": "10000000-0000-0000-0000-000000000002",
         "content": "Routine blood work ordered. CBC, BMP, lipid panel. Results pending.",
         "is_alert": False, "created_at": ts(n - timedelta(days=2)), "updated_at": ts(n - timedelta(days=2))},
        # Robert Chen
        {"id": "30000000-0000-0000-0000-000000000006", "patient_id": "10000000-0000-0000-0000-000000000003",
         "content": "Patient presents with chronic lower back pain. MRI of lumbar spine ordered.",
         "is_alert": False, "created_at": ts(n - timedelta(days=7)), "updated_at": ts(n - timedelta(days=7))},
        {"id": "30000000-0000-0000-0000-000000000007", "patient_id": "10000000-0000-0000-0000-000000000003",
         "content": "Hypertension noted on consecutive visits. Started on Lisinopril 10mg daily. Monitor BP closely.",
         "is_alert": True, "created_at": ts(n - timedelta(days=2)), "updated_at": ts(n - timedelta(days=2))},
    ]
    sb.table("clinical_notes").insert(notes).execute()
    print(f"  {len(notes)} notes (including 2 alerts)")

    # ── 6. Image blobs + patient images ───────────────────────
    print("\n[6/8] Creating imaging records ...")
    blobs = [
        {"file_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
         "storage_path": "patients/8492-A/xray_chest_ap_20251014.jpg", "mime_type": "image/jpeg", "size_bytes": 2048576},
        {"file_hash": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
         "storage_path": "patients/8492-A/ct_chest_20251128.jpg", "mime_type": "image/jpeg", "size_bytes": 4096000},
        {"file_hash": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
         "storage_path": "patients/8492-A/xray_chest_ap_20260115.jpg", "mime_type": "image/jpeg", "size_bytes": 2150400},
        {"file_hash": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
         "storage_path": "patients/5519-C/mri_lumbar_20260120.jpg", "mime_type": "image/jpeg", "size_bytes": 5242880},
    ]
    sb.table("image_blobs").insert(blobs).execute()

    images = [
        # John Doe — 3 studies
        {"id": "40000000-0000-0000-0000-000000000001", "patient_id": "10000000-0000-0000-0000-000000000001",
         "image_blob_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
         "visit_date": "2025-10-14T09:30:00+00:00", "modality": "X-Ray (Chest AP)",
         "ai_reading_summary": "Clear lung fields bilaterally. No acute cardiopulmonary abnormality. Heart size within normal limits.",
         "ai_confidence_score": 0.92},
        {"id": "40000000-0000-0000-0000-000000000002", "patient_id": "10000000-0000-0000-0000-000000000001",
         "image_blob_hash": "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
         "visit_date": "2025-11-28T14:15:00+00:00", "modality": "CT (Chest)",
         "ai_reading_summary": "Small 1.2cm nodule identified in the right lower lobe. No lymphadenopathy. Recommend follow-up imaging in 3 months.",
         "ai_confidence_score": 0.87},
        {"id": "40000000-0000-0000-0000-000000000003", "patient_id": "10000000-0000-0000-0000-000000000001",
         "image_blob_hash": "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
         "visit_date": "2026-01-15T10:00:00+00:00", "modality": "X-Ray (Chest AP)",
         "ai_reading_summary": "RLL nodule appears stable compared to prior CT. No new infiltrates. Continued monitoring recommended.",
         "ai_confidence_score": 0.85},
        # Robert Chen — 1 study
        {"id": "40000000-0000-0000-0000-000000000004", "patient_id": "10000000-0000-0000-0000-000000000003",
         "image_blob_hash": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
         "visit_date": "2026-01-20T11:00:00+00:00", "modality": "MRI (Lumbar Spine)",
         "ai_reading_summary": "Mild disc desiccation at L4-L5. Small central disc protrusion without significant canal stenosis. Facet arthropathy at L5-S1.",
         "ai_confidence_score": 0.90},
    ]
    sb.table("patient_images").insert(images).execute()
    print(f"  {len(blobs)} image blobs, {len(images)} patient images")

    # ── 7. Conversations ──────────────────────────────────────
    print("\n[7/8] Creating conversations ...")
    convos = [
        {"id": "50000000-0000-0000-0000-000000000001", "patient_id": "10000000-0000-0000-0000-000000000001",
         "title": "Chest Pain Analysis - RLL Nodule", "started_at": ts(n - timedelta(days=2))},
        {"id": "50000000-0000-0000-0000-000000000002", "patient_id": "10000000-0000-0000-0000-000000000001",
         "title": "Follow-up Imaging Comparison", "started_at": ts(n - timedelta(hours=6))},
        {"id": "50000000-0000-0000-0000-000000000003", "patient_id": "10000000-0000-0000-0000-000000000003",
         "title": "Lower Back Pain Assessment", "started_at": ts(n - timedelta(days=1))},
    ]
    sb.table("conversations").insert(convos).execute()
    print(f"  {len(convos)} conversations")

    # ── 8. Messages + context ─────────────────────────────────
    print("\n[8/8] Creating messages ...")
    msgs = [
        # Convo 1: Chest Pain Analysis
        {"id": "60000000-0000-0000-0000-000000000001", "conversation_id": "50000000-0000-0000-0000-000000000001",
         "sender": "user", "content": "Review the chest X-ray from October and identify any areas of concern.",
         "created_at": ts(n - timedelta(days=2))},
        {"id": "60000000-0000-0000-0000-000000000002", "conversation_id": "50000000-0000-0000-0000-000000000001",
         "sender": "ai",
         "content": "Based on the chest X-ray (AP view) from October 14, 2025, the lung fields appear generally clear bilaterally. The cardiac silhouette is within normal limits. No acute cardiopulmonary process is identified. However, I would recommend clinical correlation with the patient's symptoms of persistent cough, and consider follow-up imaging if symptoms persist beyond 4 weeks.",
         "created_at": ts(n - timedelta(days=2) + timedelta(seconds=30))},
        {"id": "60000000-0000-0000-0000-000000000003", "conversation_id": "50000000-0000-0000-0000-000000000001",
         "sender": "user", "content": "The follow-up CT from November showed a 1.2cm RLL nodule. What is the recommended course of action?",
         "created_at": ts(n - timedelta(days=2) + timedelta(minutes=3))},
        {"id": "60000000-0000-0000-0000-000000000004", "conversation_id": "50000000-0000-0000-0000-000000000001",
         "sender": "ai",
         "content": "The 1.2cm right lower lobe (RLL) nodule identified on the November CT warrants careful follow-up per Fleischner Society guidelines. For a solid nodule of this size in a patient with potential risk factors:\n\n1. **Follow-up CT** at 3 months to assess stability\n2. **Risk stratification** based on morphology (solid vs. ground-glass), patient age, smoking history\n3. If stable at 3 months, repeat CT at 6 and 12 months\n4. Consider **PET-CT** if the nodule grows or has suspicious morphological features\n\nThe nodule does not appear to have aggressive features on initial assessment, but serial imaging is essential to confirm stability.",
         "created_at": ts(n - timedelta(days=2) + timedelta(minutes=4))},
        # Convo 2: Follow-up Imaging
        {"id": "60000000-0000-0000-0000-000000000005", "conversation_id": "50000000-0000-0000-0000-000000000002",
         "sender": "user", "content": "Analyze the progression of the nodule compared to the October and January scans.",
         "created_at": ts(n - timedelta(hours=6))},
        {"id": "60000000-0000-0000-0000-000000000006", "conversation_id": "50000000-0000-0000-0000-000000000002",
         "sender": "ai",
         "content": "Comparing the imaging studies across the three time points:\n\n**October 14, 2025 (X-Ray AP):** Lung fields clear. No visible nodule on plain film, which is expected given the resolution limitations of standard radiography for sub-2cm nodules.\n\n**November 28, 2025 (CT Chest):** 1.2cm solid nodule identified in the RLL. No associated lymphadenopathy or pleural effusion.\n\n**January 15, 2026 (X-Ray AP):** The RLL region appears stable. No new infiltrates or interval changes on plain film.\n\n**Assessment:** The nodule appears radiologically stable over the ~2 month interval. This is a reassuring sign, but given the short follow-up period, continued serial imaging per Fleischner guidelines is recommended. The next CT scan at the 3-month mark will be critical for confirming true stability.",
         "created_at": ts(n - timedelta(hours=6) + timedelta(seconds=45))},
        # Convo 3: Lower Back Pain
        {"id": "60000000-0000-0000-0000-000000000007", "conversation_id": "50000000-0000-0000-0000-000000000003",
         "sender": "user", "content": "Evaluate the lumbar MRI findings and suggest a treatment plan.",
         "created_at": ts(n - timedelta(days=1))},
        {"id": "60000000-0000-0000-0000-000000000008", "conversation_id": "50000000-0000-0000-0000-000000000003",
         "sender": "ai",
         "content": "The lumbar MRI reveals:\n\n1. **L4-L5:** Mild disc desiccation with a small central disc protrusion. No significant spinal canal stenosis or neural foraminal narrowing.\n2. **L5-S1:** Facet arthropathy bilaterally, consistent with degenerative changes.\n\n**Recommended Treatment Plan:**\n- **Conservative management** as first-line: physical therapy focusing on core stabilization, NSAIDs for pain management\n- **Activity modification**: avoid prolonged sitting, proper ergonomics\n- **Weight management**: patient's BMI suggests potential benefit from weight reduction\n- **Follow-up** in 6-8 weeks to reassess symptoms\n- **Consider epidural steroid injection** if conservative measures fail\n- **Surgical referral** only if progressive neurological deficits develop\n\nGiven the concurrent hypertension, NSAID use should be monitored carefully. Consider acetaminophen as an alternative or adjunct.",
         "created_at": ts(n - timedelta(days=1) + timedelta(minutes=1))},
    ]
    sb.table("messages").insert(msgs).execute()
    print(f"  {len(msgs)} messages")

    # Message context (image/note attachments)
    ctx = [
        {"message_id": "60000000-0000-0000-0000-000000000001", "attached_image_id": "40000000-0000-0000-0000-000000000001"},
        {"message_id": "60000000-0000-0000-0000-000000000003", "attached_image_id": "40000000-0000-0000-0000-000000000002"},
        {"message_id": "60000000-0000-0000-0000-000000000005", "attached_image_id": "40000000-0000-0000-0000-000000000001"},
        {"message_id": "60000000-0000-0000-0000-000000000005", "attached_image_id": "40000000-0000-0000-0000-000000000003"},
        {"message_id": "60000000-0000-0000-0000-000000000007", "attached_note_id": "30000000-0000-0000-0000-000000000006"},
        {"message_id": "60000000-0000-0000-0000-000000000007", "attached_image_id": "40000000-0000-0000-0000-000000000004"},
    ]
    sb.table("message_context").insert(ctx).execute()
    print(f"  {len(ctx)} message context links")

    # ── Done ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Seed complete!")
    print("  Login:    dr.smith / password")
    print("  Patients: 8492-A (John Doe), 7731-B (Jane Martinez), 5519-C (Robert Chen)")
    print("=" * 60)


if __name__ == "__main__":
    main()

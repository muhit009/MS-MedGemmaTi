"""
Seed script for MedGemma Clinical Suite.

Populates the Supabase database with demo data for testing.
Run this AFTER executing the SQL migration (001_initial_schema.sql).

Usage:
    cd medgemma-backend
    python -m scripts.seed_data

Demo credentials:
    Username: dr.smith
    Password: password
"""

import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.services.supabase_client import get_supabase_client
from app.core.security import get_password_hash


def seed_user():
    """Create the demo physician user."""
    supabase = get_supabase_client()

    user = {
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "dr.smith",
        "hashed_password": get_password_hash("password"),
        "full_name": "Dr. Sarah Smith",
        "role": "physician",
        "is_active": True,
    }

    print("Creating demo user (dr.smith / password) ...")
    result = supabase.table("users").upsert(user, on_conflict="username").execute()
    print(f"  -> User created: {result.data[0]['username']}")
    return result.data[0]


def seed_patients():
    """Create sample patients."""
    supabase = get_supabase_client()

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

    print("Creating patients ...")
    for p in patients:
        result = supabase.table("patients").upsert(p, on_conflict="business_id").execute()
        print(f"  -> {result.data[0]['full_name']} ({result.data[0]['business_id']})")


def seed_vitals():
    """Create sample vital signs."""
    supabase = get_supabase_client()
    now = datetime.utcnow()

    vitals = [
        # John Doe - stable
        {"patient_id": "10000000-0000-0000-0000-000000000001", "heart_rate": 72, "spo2": 98, "systolic_bp": 120, "diastolic_bp": 80, "recorded_at": (now - timedelta(minutes=5)).isoformat()},
        {"patient_id": "10000000-0000-0000-0000-000000000001", "heart_rate": 74, "spo2": 97, "systolic_bp": 122, "diastolic_bp": 82, "recorded_at": (now - timedelta(hours=1)).isoformat()},
        # Jane Martinez
        {"patient_id": "10000000-0000-0000-0000-000000000002", "heart_rate": 88, "spo2": 99, "systolic_bp": 115, "diastolic_bp": 75, "recorded_at": (now - timedelta(minutes=10)).isoformat()},
        # Robert Chen - borderline high BP
        {"patient_id": "10000000-0000-0000-0000-000000000003", "heart_rate": 68, "spo2": 96, "systolic_bp": 142, "diastolic_bp": 92, "recorded_at": (now - timedelta(minutes=15)).isoformat()},
    ]

    print("Creating vitals records ...")
    for v in vitals:
        supabase.table("patient_vitals").insert(v).execute()
    print(f"  -> {len(vitals)} vitals records created")


def seed_notes():
    """Create clinical notes and alerts."""
    supabase = get_supabase_client()
    now = datetime.utcnow()

    notes = [
        {"id": "30000000-0000-0000-0000-000000000001", "patient_id": "10000000-0000-0000-0000-000000000001", "content": "Patient complained of persistent cough lasting 3 weeks. No fever. Ordered chest X-ray to rule out underlying pathology.", "is_alert": False, "created_at": (now - timedelta(days=5)).isoformat(), "updated_at": (now - timedelta(days=5)).isoformat()},
        {"id": "30000000-0000-0000-0000-000000000002", "patient_id": "10000000-0000-0000-0000-000000000001", "content": "Follow-up: Chest X-ray shows a 1.2cm RLL nodule. Recommend CT for further evaluation. Patient informed.", "is_alert": False, "created_at": (now - timedelta(days=3)).isoformat(), "updated_at": (now - timedelta(days=3)).isoformat()},
        {"id": "30000000-0000-0000-0000-000000000003", "patient_id": "10000000-0000-0000-0000-000000000001", "content": "Monitor RLL nodule stability. Patient reports mild shortness of breath during exertion.", "is_alert": True, "created_at": (now - timedelta(days=1)).isoformat(), "updated_at": (now - timedelta(days=1)).isoformat()},
        {"id": "30000000-0000-0000-0000-000000000004", "patient_id": "10000000-0000-0000-0000-000000000002", "content": "Annual physical. All vitals within normal range. Patient reports occasional headaches.", "is_alert": False, "created_at": (now - timedelta(days=10)).isoformat(), "updated_at": (now - timedelta(days=10)).isoformat()},
        {"id": "30000000-0000-0000-0000-000000000007", "patient_id": "10000000-0000-0000-0000-000000000003", "content": "Hypertension noted on consecutive visits. Started on Lisinopril 10mg daily. Monitor BP closely.", "is_alert": True, "created_at": (now - timedelta(days=2)).isoformat(), "updated_at": (now - timedelta(days=2)).isoformat()},
    ]

    print("Creating clinical notes ...")
    for n in notes:
        supabase.table("clinical_notes").upsert(n).execute()
    print(f"  -> {len(notes)} notes created (including alerts)")


def main():
    print("=" * 60)
    print("MedGemma Clinical Suite - Database Seeder")
    print("=" * 60)
    print()

    try:
        seed_user()
        seed_patients()
        seed_vitals()
        seed_notes()
        print()
        print("Seed complete! You can now log in with:")
        print("  Username: dr.smith")
        print("  Password: password")
        print()
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure the SQL migration has been run first.")
        sys.exit(1)


if __name__ == "__main__":
    main()

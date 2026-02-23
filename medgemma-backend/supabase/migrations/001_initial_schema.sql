-- ============================================================================
-- MedGemma Clinical Suite - Complete Supabase Migration
-- ============================================================================
-- Run this entire file in the Supabase SQL Editor (Dashboard > SQL Editor)
-- This creates all tables, indexes, RLS policies, storage, and seed data.
-- ============================================================================


-- ============================================================================
-- 1. EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid(), crypt(), gen_salt()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Trigram index for ILIKE patient search


-- ============================================================================
-- 2. TABLES
-- ============================================================================

-- ----- Users (backend authentication) -----
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'physician',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Patients -----
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    dob DATE NOT NULL,
    sex VARCHAR(10),
    weight_kg DECIMAL(5,2),
    height_cm DECIMAL(5,2),
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Patient Vitals -----
CREATE TABLE IF NOT EXISTS patient_vitals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    heart_rate INTEGER,
    spo2 INTEGER,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Image Blobs (deduplicated file storage) -----
CREATE TABLE IF NOT EXISTS image_blobs (
    file_hash CHAR(64) PRIMARY KEY,
    storage_path VARCHAR(512) NOT NULL,
    mime_type VARCHAR(50),
    size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Patient Images -----
CREATE TABLE IF NOT EXISTS patient_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    image_blob_hash CHAR(64) REFERENCES image_blobs(file_hash),
    visit_date TIMESTAMPTZ NOT NULL,
    modality VARCHAR(50),
    ai_reading_summary TEXT,
    ai_confidence_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Clinical Notes & Alerts -----
CREATE TABLE IF NOT EXISTS clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_alert BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Conversations (AI chat sessions) -----
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    title VARCHAR(255),
    started_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Messages -----
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'ai')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ----- Message Context (image/note attachments per message) -----
CREATE TABLE IF NOT EXISTS message_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    attached_image_id UUID REFERENCES patient_images(id) ON DELETE SET NULL,
    attached_note_id UUID REFERENCES clinical_notes(id) ON DELETE SET NULL,
    CONSTRAINT check_context_source CHECK (
        (attached_image_id IS NOT NULL AND attached_note_id IS NULL) OR
        (attached_image_id IS NULL AND attached_note_id IS NOT NULL)
    )
);


-- ============================================================================
-- 3. INDEXES
-- ============================================================================

-- Patients - fast search by business_id and name (trigram for ILIKE)
CREATE INDEX IF NOT EXISTS idx_patients_business_id ON patients(business_id);
CREATE INDEX IF NOT EXISTS idx_patients_full_name_trgm ON patients USING gin(full_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_patients_business_id_trgm ON patients USING gin(business_id gin_trgm_ops);

-- Vitals - latest per patient
CREATE INDEX IF NOT EXISTS idx_patient_vitals_patient_id ON patient_vitals(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_vitals_recorded_at ON patient_vitals(patient_id, recorded_at DESC);

-- Clinical notes - per patient, alert lookup
CREATE INDEX IF NOT EXISTS idx_clinical_notes_patient_id ON clinical_notes(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_alert ON clinical_notes(patient_id, is_alert) WHERE is_alert = TRUE;

-- Images - per patient, chronological
CREATE INDEX IF NOT EXISTS idx_patient_images_patient_id ON patient_images(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_images_visit_date ON patient_images(patient_id, visit_date DESC);

-- Conversations - per patient, chronological
CREATE INDEX IF NOT EXISTS idx_conversations_patient_id ON conversations(patient_id);
CREATE INDEX IF NOT EXISTS idx_conversations_started_at ON conversations(patient_id, started_at DESC);

-- Messages - per conversation, chronological
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(conversation_id, created_at);

-- Message context - per message
CREATE INDEX IF NOT EXISTS idx_message_context_message_id ON message_context(message_id);


-- ============================================================================
-- 4. AUTO-UPDATE updated_at TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_clinical_notes_updated_at
    BEFORE UPDATE ON clinical_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 5. ROW LEVEL SECURITY
-- ============================================================================
-- The backend uses the Supabase SERVICE ROLE key, which bypasses RLS.
-- RLS is enabled to block direct access via the anon/publishable key.
-- Policies below are for future frontend direct-access if needed.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_vitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_context ENABLE ROW LEVEL SECURITY;

-- Service role key bypasses all RLS automatically.
-- The policies below allow authenticated users (via Supabase Auth JWT) read access.
-- These are optional and only matter if you later use the anon key from a frontend.

CREATE POLICY "Authenticated read access" ON patients
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated read access" ON patient_vitals
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated read access" ON image_blobs
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated read access" ON patient_images
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated read access" ON clinical_notes
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated full access" ON clinical_notes
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Authenticated read access" ON conversations
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated full access" ON conversations
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Authenticated read access" ON messages
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated full access" ON messages
    FOR ALL TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Authenticated read access" ON message_context
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "Authenticated full access" ON message_context
    FOR ALL TO authenticated USING (true) WITH CHECK (true);


-- ============================================================================
-- 6. STORAGE BUCKET
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'medical-images',
    'medical-images',
    false,
    52428800,  -- 50 MB max file size
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/dicom', 'application/dicom']
)
ON CONFLICT (id) DO NOTHING;

-- Storage policies: only authenticated users via backend (service role bypasses these)
CREATE POLICY "Backend can upload images"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'medical-images');

CREATE POLICY "Backend can read images"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (bucket_id = 'medical-images');

CREATE POLICY "Backend can delete images"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (bucket_id = 'medical-images');


-- ============================================================================
-- 7. SEED DATA
-- ============================================================================
-- Demo credentials:  Username: dr.smith  |  Password: password
-- ============================================================================

-- ----- Demo User -----
-- crypt() + gen_salt('bf') produces a bcrypt hash that passlib can verify
INSERT INTO users (id, username, hashed_password, full_name, role, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'dr.smith',
    crypt('password', gen_salt('bf', 12)),
    'Dr. Sarah Smith',
    'physician',
    true
)
ON CONFLICT (username) DO NOTHING;

-- ----- Patients -----
INSERT INTO patients (id, business_id, full_name, dob, sex, weight_kg, height_cm) VALUES
(
    '10000000-0000-0000-0000-000000000001',
    '8492-A',
    'John Doe',
    '1980-05-12',
    'Male',
    81.65,  -- ~180 lbs
    182.00
),
(
    '10000000-0000-0000-0000-000000000002',
    '7731-B',
    'Jane Martinez',
    '1992-11-03',
    'Female',
    63.50,
    165.00
),
(
    '10000000-0000-0000-0000-000000000003',
    '5519-C',
    'Robert Chen',
    '1975-08-22',
    'Male',
    90.72,
    175.00
)
ON CONFLICT (business_id) DO NOTHING;

-- ----- Patient Vitals -----
-- John Doe - stable vitals
INSERT INTO patient_vitals (patient_id, heart_rate, spo2, systolic_bp, diastolic_bp, recorded_at) VALUES
('10000000-0000-0000-0000-000000000001', 72, 98, 120, 80, NOW() - INTERVAL '5 minutes'),
('10000000-0000-0000-0000-000000000001', 74, 97, 122, 82, NOW() - INTERVAL '1 hour'),
('10000000-0000-0000-0000-000000000001', 70, 98, 118, 78, NOW() - INTERVAL '3 hours');

-- Jane Martinez - slightly elevated HR
INSERT INTO patient_vitals (patient_id, heart_rate, spo2, systolic_bp, diastolic_bp, recorded_at) VALUES
('10000000-0000-0000-0000-000000000002', 88, 99, 115, 75, NOW() - INTERVAL '10 minutes'),
('10000000-0000-0000-0000-000000000002', 85, 98, 118, 76, NOW() - INTERVAL '2 hours');

-- Robert Chen - borderline high BP
INSERT INTO patient_vitals (patient_id, heart_rate, spo2, systolic_bp, diastolic_bp, recorded_at) VALUES
('10000000-0000-0000-0000-000000000003', 68, 96, 142, 92, NOW() - INTERVAL '15 minutes'),
('10000000-0000-0000-0000-000000000003', 71, 97, 138, 88, NOW() - INTERVAL '4 hours');

-- ----- Clinical Notes -----
-- John Doe - notes + alert
INSERT INTO clinical_notes (id, patient_id, content, is_alert, created_at, updated_at) VALUES
(
    '30000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'Patient complained of persistent cough lasting 3 weeks. No fever. Ordered chest X-ray to rule out underlying pathology.',
    false,
    NOW() - INTERVAL '5 days',
    NOW() - INTERVAL '5 days'
),
(
    '30000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'Follow-up: Chest X-ray shows a 1.2cm RLL nodule. Recommend CT for further evaluation. Patient informed.',
    false,
    NOW() - INTERVAL '3 days',
    NOW() - INTERVAL '3 days'
),
(
    '30000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000001',
    'Monitor RLL nodule stability. Patient reports mild shortness of breath during exertion.',
    true,  -- This is the sticky alert
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '1 day'
);

-- Jane Martinez - notes
INSERT INTO clinical_notes (id, patient_id, content, is_alert, created_at, updated_at) VALUES
(
    '30000000-0000-0000-0000-000000000004',
    '10000000-0000-0000-0000-000000000002',
    'Annual physical. All vitals within normal range. Patient reports occasional headaches, likely tension-related.',
    false,
    NOW() - INTERVAL '10 days',
    NOW() - INTERVAL '10 days'
),
(
    '30000000-0000-0000-0000-000000000005',
    '10000000-0000-0000-0000-000000000002',
    'Routine blood work ordered. CBC, BMP, lipid panel. Results pending.',
    false,
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '2 days'
);

-- Robert Chen - notes + alert
INSERT INTO clinical_notes (id, patient_id, content, is_alert, created_at, updated_at) VALUES
(
    '30000000-0000-0000-0000-000000000006',
    '10000000-0000-0000-0000-000000000003',
    'Patient presents with chronic lower back pain. MRI of lumbar spine ordered.',
    false,
    NOW() - INTERVAL '7 days',
    NOW() - INTERVAL '7 days'
),
(
    '30000000-0000-0000-0000-000000000007',
    '10000000-0000-0000-0000-000000000003',
    'Hypertension noted on consecutive visits. Started on Lisinopril 10mg daily. Monitor BP closely.',
    true,
    NOW() - INTERVAL '2 days',
    NOW() - INTERVAL '2 days'
);

-- ----- Image Blobs (simulated file references) -----
INSERT INTO image_blobs (file_hash, storage_path, mime_type, size_bytes) VALUES
(
    'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    'patients/8492-A/xray_chest_ap_20251014.jpg',
    'image/jpeg',
    2048576
),
(
    'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3',
    'patients/8492-A/ct_chest_20251128.jpg',
    'image/jpeg',
    4096000
),
(
    'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
    'patients/8492-A/xray_chest_ap_20260115.jpg',
    'image/jpeg',
    2150400
),
(
    'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5',
    'patients/5519-C/mri_lumbar_20260120.jpg',
    'image/jpeg',
    5242880
)
ON CONFLICT (file_hash) DO NOTHING;

-- ----- Patient Images -----
-- John Doe - 3 imaging studies showing progression
INSERT INTO patient_images (id, patient_id, image_blob_hash, visit_date, modality, ai_reading_summary, ai_confidence_score) VALUES
(
    '40000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    '2025-10-14 09:30:00+00',
    'X-Ray (Chest AP)',
    'Clear lung fields bilaterally. No acute cardiopulmonary abnormality. Heart size within normal limits.',
    0.92
),
(
    '40000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3',
    '2025-11-28 14:15:00+00',
    'CT (Chest)',
    'Small 1.2cm nodule identified in the right lower lobe. No lymphadenopathy. Recommend follow-up imaging in 3 months.',
    0.87
),
(
    '40000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000001',
    'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
    '2026-01-15 10:00:00+00',
    'X-Ray (Chest AP)',
    'RLL nodule appears stable compared to prior CT. No new infiltrates. Continued monitoring recommended.',
    0.85
);

-- Robert Chen - 1 imaging study
INSERT INTO patient_images (id, patient_id, image_blob_hash, visit_date, modality, ai_reading_summary, ai_confidence_score) VALUES
(
    '40000000-0000-0000-0000-000000000004',
    '10000000-0000-0000-0000-000000000003',
    'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5',
    '2026-01-20 11:00:00+00',
    'MRI (Lumbar Spine)',
    'Mild disc desiccation at L4-L5. Small central disc protrusion without significant canal stenosis. Facet arthropathy at L5-S1.',
    0.90
);

-- ----- Conversations -----
-- John Doe - past consultation about the chest nodule
INSERT INTO conversations (id, patient_id, title, started_at) VALUES
(
    '50000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'Chest Pain Analysis - RLL Nodule',
    NOW() - INTERVAL '2 days'
),
(
    '50000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'Follow-up Imaging Comparison',
    NOW() - INTERVAL '6 hours'
);

-- Robert Chen - consultation
INSERT INTO conversations (id, patient_id, title, started_at) VALUES
(
    '50000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000003',
    'Lower Back Pain Assessment',
    NOW() - INTERVAL '1 day'
);

-- ----- Messages -----
-- Conversation 1: Chest Pain Analysis
INSERT INTO messages (id, conversation_id, sender, content, created_at) VALUES
(
    '60000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000001',
    'user',
    'Review the chest X-ray from October and identify any areas of concern.',
    NOW() - INTERVAL '2 days'
),
(
    '60000000-0000-0000-0000-000000000002',
    '50000000-0000-0000-0000-000000000001',
    'ai',
    'Based on the chest X-ray (AP view) from October 14, 2025, the lung fields appear generally clear bilaterally. The cardiac silhouette is within normal limits. No acute cardiopulmonary process is identified. However, I would recommend clinical correlation with the patient''s symptoms of persistent cough, and consider follow-up imaging if symptoms persist beyond 4 weeks.',
    NOW() - INTERVAL '2 days' + INTERVAL '30 seconds'
),
(
    '60000000-0000-0000-0000-000000000003',
    '50000000-0000-0000-0000-000000000001',
    'user',
    'The follow-up CT from November showed a 1.2cm RLL nodule. What is the recommended course of action?',
    NOW() - INTERVAL '2 days' + INTERVAL '3 minutes'
),
(
    '60000000-0000-0000-0000-000000000004',
    '50000000-0000-0000-0000-000000000001',
    'ai',
    'The 1.2cm right lower lobe (RLL) nodule identified on the November CT warrants careful follow-up per Fleischner Society guidelines. For a solid nodule of this size in a patient with potential risk factors:\n\n1. **Follow-up CT** at 3 months to assess stability\n2. **Risk stratification** based on morphology (solid vs. ground-glass), patient age, smoking history\n3. If stable at 3 months, repeat CT at 6 and 12 months\n4. Consider **PET-CT** if the nodule grows or has suspicious morphological features\n\nThe nodule does not appear to have aggressive features on initial assessment, but serial imaging is essential to confirm stability.',
    NOW() - INTERVAL '2 days' + INTERVAL '4 minutes'
);

-- Conversation 2: Follow-up Imaging
INSERT INTO messages (id, conversation_id, sender, content, created_at) VALUES
(
    '60000000-0000-0000-0000-000000000005',
    '50000000-0000-0000-0000-000000000002',
    'user',
    'Analyze the progression of the nodule compared to the October and January scans.',
    NOW() - INTERVAL '6 hours'
),
(
    '60000000-0000-0000-0000-000000000006',
    '50000000-0000-0000-0000-000000000002',
    'ai',
    'Comparing the imaging studies across the three time points:\n\n**October 14, 2025 (X-Ray AP):** Lung fields clear. No visible nodule on plain film, which is expected given the resolution limitations of standard radiography for sub-2cm nodules.\n\n**November 28, 2025 (CT Chest):** 1.2cm solid nodule identified in the RLL. No associated lymphadenopathy or pleural effusion.\n\n**January 15, 2026 (X-Ray AP):** The RLL region appears stable. No new infiltrates or interval changes on plain film.\n\n**Assessment:** The nodule appears radiologically stable over the ~2 month interval. This is a reassuring sign, but given the short follow-up period, continued serial imaging per Fleischner guidelines is recommended. The next CT scan at the 3-month mark will be critical for confirming true stability.',
    NOW() - INTERVAL '6 hours' + INTERVAL '45 seconds'
);

-- Conversation 3: Lower Back Pain
INSERT INTO messages (id, conversation_id, sender, content, created_at) VALUES
(
    '60000000-0000-0000-0000-000000000007',
    '50000000-0000-0000-0000-000000000003',
    'user',
    'Evaluate the lumbar MRI findings and suggest a treatment plan.',
    NOW() - INTERVAL '1 day'
),
(
    '60000000-0000-0000-0000-000000000008',
    '50000000-0000-0000-0000-000000000003',
    'ai',
    'The lumbar MRI reveals:\n\n1. **L4-L5:** Mild disc desiccation with a small central disc protrusion. No significant spinal canal stenosis or neural foraminal narrowing.\n2. **L5-S1:** Facet arthropathy bilaterally, consistent with degenerative changes.\n\n**Recommended Treatment Plan:**\n- **Conservative management** as first-line: physical therapy focusing on core stabilization, NSAIDs for pain management\n- **Activity modification**: avoid prolonged sitting, proper ergonomics\n- **Weight management**: patient''s BMI suggests potential benefit from weight reduction\n- **Follow-up** in 6-8 weeks to reassess symptoms\n- **Consider epidural steroid injection** if conservative measures fail\n- **Surgical referral** only if progressive neurological deficits develop\n\nGiven the concurrent hypertension, NSAID use should be monitored carefully. Consider acetaminophen as an alternative or adjunct.',
    NOW() - INTERVAL '1 day' + INTERVAL '1 minute'
);

-- ----- Message Context (attachments) -----
-- Link images to the messages that referenced them
INSERT INTO message_context (message_id, attached_image_id) VALUES
('60000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001'),  -- X-ray Oct
('60000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000002'),  -- CT Nov
('60000000-0000-0000-0000-000000000005', '40000000-0000-0000-0000-000000000001'),  -- X-ray Oct
('60000000-0000-0000-0000-000000000005', '40000000-0000-0000-0000-000000000003');  -- X-ray Jan

-- Link note to the lower back message
INSERT INTO message_context (message_id, attached_note_id) VALUES
('60000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000006'); -- LBP note

-- Link image to the lower back message
INSERT INTO message_context (message_id, attached_image_id) VALUES
('60000000-0000-0000-0000-000000000007', '40000000-0000-0000-0000-000000000004'); -- MRI lumbar


-- ============================================================================
-- DONE. Verify with:
--   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- ============================================================================

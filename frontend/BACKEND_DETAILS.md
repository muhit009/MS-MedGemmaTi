# Backend API Specification for MedGemma Clinical Suite

This document outlines the API endpoints required to support the current frontend implementation of the MedGemma Clinical Suite.

## Overview
The application is a single-page clinical dashboard used by physicians to analyze patient imaging, review history, and interact with an AI model for diagnosis assistance.

## Base URL
(e.g., `http://localhost:8000/api/v1`)

## Authentication
*Assume standard Bearer Token authentication for all endpoints.*

---

## 1. Patient Management

### Search / Authenticate Patient
Used in the initial "Patient Selection" dialog.
- **Endpoint:** `POST /patients/search`
- **Payload:**
  ```json
  {
    "patientId": "8492-A", // optional
    "name": "Jane Doe"     // optional
  }
  ```
- **Response:** `200 OK`
  ```json
  [
    {
      "id": "8492-A5-2026",
      "name": "John Doe",
      "dob": "1980-05-12",
      "age": 45,
      "sex": "Male",
      "weight": "180 lbs",
      "height": "182 cm",
      "avatarUrl": "/path/to/image.jpg" // optional
    }
  ]
  ```

### Get Patient Details
Used to populate the "Patient Identification" card in the Left Pane.
- **Endpoint:** `GET /patients/{patientId}`
- **Response:** Patient Object (same as above).

---

## 2. Clinical Data

### Get Latest Vitals
Used to populate the "Biometric HUD" / "Real-time Vitals" section.
- **Endpoint:** `GET /patients/{patientId}/vitals/latest`
- **Response:** `200 OK`
  ```json
  {
    "heartRate": { "value": 72, "unit": "bpm", "status": "stable" },
    "spO2": { "value": 98, "unit": "%", "status": "stable" },
    "bloodPressure": { "value": "120/80", "unit": "mmHg", "status": "stable" }
  }
  ```

### Clinical Alerts
Used for the "Clinical Alert" card. Supports viewing and in-place editing.

**Get Active Alert:**
- **Endpoint:** `GET /patients/{patientId}/alerts/active`
- **Response:** `200 OK`
  ```json
  {
    "id": 101,
    "content": "Monitor RLL nodule stability. Patient reports mild shortness of breath.",
    "severity": "warning", // or 'nominal' if empty
    "updatedAt": "2026-01-22T10:00:00Z"
  }
  ```

**Update/Set Alert:**
- **Endpoint:** `PUT /patients/{patientId}/alerts`
- **Payload:**
  ```json
  {
    "content": "Updated alert text here..."
  }
  ```

---

## 3. Patient Notes
Used for the collapsible "Patient Notes" section. Supports full CRUD.

### List Notes
- **Endpoint:** `GET /patients/{patientId}/notes`
- **Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "date": "2026-01-20",
      "content": "Patient complained of persistent cough..."
    }
  ]
  ```

### Create Note
- **Endpoint:** `POST /patients/{patientId}/notes`
- **Payload:**
  ```json
  {
    "content": "New clinical observation..."
  }
  ```

### Update Note
- **Endpoint:** `PATCH /notes/{noteId}`
- **Payload:**
  ```json
  {
    "content": "Updated content..."
  }
  ```

### Delete Note
- **Endpoint:** `DELETE /notes/{noteId}`

---

## 4. Imaging History
Used for the "Imaging History" section and the "Selected Images" chips.

### Get Imaging History
- **Endpoint:** `GET /patients/{patientId}/imaging`
- **Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "src": "https://signed-url-to-image.jpg",
      "modality": "X-Ray (Chest AP)",
      "date": "2025-10-14 09:30 AM",
      "reading": "Clear lung fields...",
      "confidence": "High" // AI pre-reading confidence
    }
  ]
  ```

---

## 5. Consultations & AI Analysis
Used for the Right Pane Chat Interface and "Past Consultations" history.

### Get Chat History (Past Sessions)
Used for the "Past Consultations" collapsible list.
- **Endpoint:** `GET /patients/{patientId}/consultations`
- **Response:** `200 OK`
  ```json
  [
    {
      "id": "session_123",
      "title": "Chest Pain Analysis",
      "date": "Yesterday",
      "snippet": "Patient reported mild discomfort..."
    }
  ]
  ```

### Get Specific Consultation Messages
Used when clicking on a past consultation item.
- **Endpoint:** `GET /consultations/{consultationId}/messages`

### Generate AI Analysis (The Main "Submit" Action)
Triggered when the doctor sends a prompt from the input bar.

- **Endpoint:** `POST /analysis/generate` (or `/consultations/new` / `/consultations/{id}/messages`)
- **Payload:**
  ```json
  {
    "patientId": "8492-A5-2026",
    "prompt": "Analyze the progression of the nodule compared to the 2024 scan.",
    "context": {
      "imageIds": [3, 5], // IDs of selected X-rays
      "noteIds": [1]      // IDs of selected Patient Notes
    },
    "modelConfig": {
      "temperature": 0.2, // Optional, for medical precision
      "stream": true      // Frontend expects streaming response? (Currently mocked as full text)
    }
  }
  ```
- **Response:**
  ```json
  {
    "text": "Based on the comparison...",
    "timestamp": "2026-01-22T14:30:00Z",
    "sender": "ai"
  }
  ```
  *(Note: Backend should ideally support Server-Sent Events (SSE) or WebSocket if streaming is desired later, but JSON response is fine for current MVP)*.

---

# 6. Communication Optimization Strategy

To ensure the "Techno-Cool" yet "Professional" feel remains performant:

1.  **Optimistic UI:** The frontend immediately adds the user's message and clears the input/selection state *before* the server responds. The backend API must be fast enough to acknowledge receipt, even if the AI inference takes time.
2.  **Server-Sent Events (SSE):** For `/analysis/generate`, use SSE to stream the AI's response token-by-token. This reduces perceived latency compared to waiting for the full paragraph to generate.
3.  **Signed URLs for Images:** The `/imaging` endpoints should return temporary signed URLs (e.g., AWS S3 presigned URLs) rather than serving binary data directly through the API, reducing backend load.
4.  **Lazy Loading:** `Imaging History` and `Chat History` should support pagination (`?page=1&limit=20`) if the patient has extensive records, though loading the most recent ~50 items at once is acceptable for the MVP.

---

# 7. Endpoint Summary (Implementation Checklist)

*This section summarizes the exact requirements for the backend developer.*

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/auth/login` | (Implied) standard JWT exchange. |
| **POST** | `/patients/search` | Search by ID or Name. Returns summary list. |
| **GET** | `/patients/{id}` | Full demographic details. |
| **GET** | `/patients/{id}/vitals` | Latest biometric data (HR, BP, SpO2). |
| **GET** | `/patients/{id}/alerts` | Active clinical alert text. |
| **PUT** | `/patients/{id}/alerts` | Update the sticky clinical alert. |
| **GET** | `/patients/{id}/notes` | List of manual patient notes. |
| **POST** | `/patients/{id}/notes` | Create a new note. |
| **PATCH** | `/notes/{id}` | Edit an existing note. |
| **DELETE**| `/notes/{id}` | Remove a note. |
| **GET** | `/patients/{id}/imaging` | List of X-rays/CTs with metadata & thumbnails. |
| **GET** | `/patients/{id}/consultations`| List of previous AI chat sessions. |
| **POST** | `/analysis/generate` | **CORE:** Send prompt + Context IDs -> Receive AI Response. |

---

# 8. Database Schema Design

*Designed for deduplicated storage, temporal analysis, and scalability.*

### Core Entity: Patients
*Unique constraints on Business ID, but internal UUID for relations.*
```sql
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., "8492-A"
    full_name VARCHAR(255) NOT NULL,
    dob DATE NOT NULL,
    sex VARCHAR(10),
    weight_kg DECIMAL(5,2),
    height_cm DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Storage Optimization: Image Blobs
*Stores the actual file reference. Designed to not duplicate files if re-uploaded.*
```sql
CREATE TABLE image_blobs (
    file_hash CHAR(64) PRIMARY KEY, -- SHA-256 of the file content
    storage_path VARCHAR(512) NOT NULL, -- S3 Key or local path
    mime_type VARCHAR(50),
    size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Clinical Record: Imaging
*Links a patient's temporal visit to a stored image blob.*
```sql
CREATE TABLE patient_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    image_blob_hash CHAR(64) REFERENCES image_blobs(file_hash),
    
    visit_date TIMESTAMP NOT NULL, -- Crucial for "Chronological" sort
    modality VARCHAR(50), -- X-Ray, CT, MRI
    
    ai_reading_summary TEXT, -- Cached summary of what the AI saw initially
    ai_confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Clinical Record: Notes & Alerts
```sql
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    content TEXT NOT NULL,
    is_alert BOOLEAN DEFAULT FALSE, -- If TRUE, this is the sticky "Clinical Alert"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### AI Interaction: Conversations
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    title VARCHAR(255), -- Auto-generated summary of chat
    started_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    sender VARCHAR(10) CHECK (sender IN ('user', 'ai')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Context Linking (The "Attachment" Logic)
*Tracks exactly which images/notes were used for a specific message/deduction.*
```sql
CREATE TABLE message_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    
    -- Polymorphic-style or separate columns
    attached_image_id UUID REFERENCES patient_images(id),
    attached_note_id UUID REFERENCES clinical_notes(id),
    
    CONSTRAINT check_context_source CHECK (
        (attached_image_id IS NOT NULL AND attached_note_id IS NULL) OR
        (attached_image_id IS NULL AND attached_note_id IS NOT NULL)
    )
);
```

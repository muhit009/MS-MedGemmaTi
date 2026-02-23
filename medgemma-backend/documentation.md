# MedGemma Clinical Suite - Backend Documentation

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Database Setup (Supabase)](#database-setup-supabase)
  - [Running the Server](#running-the-server)
- [Authentication](#authentication)
- [API Reference](#api-reference)
  - [Auth Endpoints](#1-auth-endpoints)
  - [Patient Endpoints](#2-patient-endpoints)
  - [Vitals Endpoints](#3-vitals-endpoints)
  - [Alerts Endpoints](#4-alerts-endpoints)
  - [Notes Endpoints](#5-notes-endpoints)
  - [Imaging Endpoints](#6-imaging-endpoints)
  - [Consultations Endpoints](#7-consultations-endpoints)
  - [AI Analysis Endpoints](#8-ai-analysis-endpoints)
  - [Health / Debug Endpoints](#9-health--debug-endpoints)
- [Database Schema](#database-schema)
- [AI Service](#ai-service)
- [Demo Credentials & Seed Data](#demo-credentials--seed-data)
- [Assumptions & Roadmap](#assumptions--roadmap)

---

## Overview

The MedGemma Clinical Suite backend is a FastAPI application that powers a clinical dashboard for physicians. It provides APIs for patient management, real-time vitals, clinical notes, medical imaging history, and AI-powered diagnostic consultations via MedGemma.

All data is stored in **Supabase** (hosted PostgreSQL accessed over REST). The backend communicates with Supabase using the `supabase-py` SDK — no local PostgreSQL installation is required.

**Base URL:** `http://localhost:8000/api/v1`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115.6 |
| Server | Uvicorn 0.34.0 (ASGI) |
| Database | Supabase (hosted PostgreSQL via REST API) |
| Auth | JWT (HS256) via `python-jose` + `bcrypt` |
| AI | MedGemma API (with mock fallback) |
| HTTP Client | httpx 0.27.2 (async, for MedGemma calls) |
| Validation | Pydantic v2 |
| Storage | Supabase Storage (signed URLs for images) |

---

## Project Structure

```
medgemma-backend/
├── app/
│   ├── main.py                     # FastAPI app entry point, lifespan, middleware
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py          # Router aggregator
│   │       ├── auth.py              # Login, current user
│   │       ├── patients.py          # Patient search & details
│   │       ├── vitals.py            # Latest vital signs
│   │       ├── alerts.py            # Clinical alerts (get/update)
│   │       ├── notes.py             # Patient notes CRUD
│   │       ├── imaging.py           # Imaging history
│   │       ├── consultations.py     # Past AI consultations
│   │       └── analysis.py          # AI analysis generation + SSE streaming
│   ├── core/
│   │   ├── config.py                # Settings from .env
│   │   └── security.py              # JWT + bcrypt password utilities
│   ├── db/
│   │   └── queries.py               # Supabase query helper functions
│   ├── models/
│   │   ├── patient.py               # Patient domain model
│   │   ├── clinical.py              # Vitals, notes, alerts models
│   │   ├── imaging.py               # Image blob + patient image models
│   │   └── conversation.py          # Conversation + message models
│   ├── schemas/
│   │   ├── auth.py                  # Auth request/response schemas
│   │   ├── patient.py               # Patient request/response schemas
│   │   ├── clinical.py              # Vitals, alerts, notes schemas
│   │   ├── imaging.py               # Imaging schemas
│   │   └── conversation.py          # Consultation + analysis schemas
│   └── services/
│       ├── supabase_client.py       # Supabase client, storage, SupabaseService class
│       └── ai_service.py            # MedGemma integration + mock responses
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql   # Full DB schema + RLS + indexes + seed data
├── scripts/
│   └── seed_data.py                 # Python seeder (alternative to SQL seed)
├── tests/
│   └── test_patients.py             # Patient endpoint tests
├── .env                             # Environment variables (do not commit)
├── .env.example                     # Example environment file
├── requirements.txt                 # Python dependencies
├── BACKEND_DETAILS.md               # Original API specification
└── documentation.md                 # This file
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A Supabase project (free tier works)
- No local PostgreSQL needed

### Installation

```bash
cd medgemma-backend

# Create virtual environment (if not already done)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Application
APP_NAME=MedGemma Clinical Suite API
APP_VERSION=1.0.0
DEBUG=True

# CORS
CORS_ORIGINS=["*"]

# Supabase - get these from Dashboard > Settings > API
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# JWT Authentication
JWT_SECRET_KEY=<your-jwt-secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# MedGemma AI Service (leave defaults if not yet configured)
MEDGEMMA_API_URL=http://localhost:8080/generate
MEDGEMMA_API_KEY=your-medgemma-api-key

# Storage
STORAGE_BUCKET=medical-images
```

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_KEY` | Yes | Service role key (bypasses RLS, used by backend) |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret from Supabase dashboard |
| `JWT_SECRET_KEY` | Yes | Secret for signing backend JWTs (can match `SUPABASE_JWT_SECRET`) |
| `MEDGEMMA_API_URL` | No | MedGemma model endpoint. If not configured, mock responses are used |
| `MEDGEMMA_API_KEY` | No | API key for MedGemma service |
| `STORAGE_BUCKET` | No | Supabase Storage bucket name (default: `medical-images`) |

### Database Setup (Supabase)

1. Go to your **Supabase Dashboard > SQL Editor**
2. Paste the entire contents of `supabase/migrations/001_initial_schema.sql`
3. Click **Run**

This creates all 9 tables, indexes, RLS policies, the storage bucket, and seed data.

**Alternative:** Run the Python seeder for demo data:
```bash
python -m scripts.seed_data
```

### Running the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at:
- **API:** http://localhost:8000/api/v1
- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc
- **Health check:** http://localhost:8000/health

---

## Authentication

All endpoints (except `/health` and `/`) require a Bearer token.

**Flow:**
1. Call `POST /api/v1/auth/login/json` with `username` and `password`
2. Receive a JWT `access_token`
3. Pass it in the `Authorization` header on every subsequent request:
   ```
   Authorization: Bearer <access_token>
   ```

Tokens expire after 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).

---

## API Reference

### 1. Auth Endpoints

#### `POST /api/v1/auth/login` (OAuth2 form)

Standard OAuth2 password flow (used by Swagger UI).

**Input:** `application/x-www-form-urlencoded`
| Field | Type | Required |
|---|---|---|
| `username` | string | Yes |
| `password` | string | Yes |

#### `POST /api/v1/auth/login/json`

JSON-based login (recommended for frontend).

**Input:**
```json
{
  "username": "dr.smith",
  "password": "password"
}
```

**Output (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors:** `401` if credentials are wrong.

#### `GET /api/v1/auth/me`

Returns the currently authenticated user.

**Output (200):**
```json
{
  "id": "b99d2629-4d00-4556-bec1-5c9c4da010b2",
  "username": "dr.smith",
  "full_name": "Dr. Sarah Smith",
  "role": "physician"
}
```

---

### 2. Patient Endpoints

#### `POST /api/v1/patients/search`

Search patients by ID or name. Both fields are optional (empty body returns all patients, max 20).

**Input:**
```json
{
  "patientId": "8492",
  "name": "John"
}
```

**Output (200):**
```json
[
  {
    "id": "8492-A5-2026",
    "name": "John Doe",
    "dob": "1980-05-12",
    "age": 45,
    "sex": "Male",
    "weight": "81.6 kg",
    "height": "182.0 cm",
    "avatarUrl": null
  }
]
```

#### `GET /api/v1/patients/{patient_id}`

Get full details for a patient by their business ID.

**URL parameter:** `patient_id` = the patient's business ID (e.g., `8492-A5-2026`)

**Output (200):**
```json
{
  "id": "8492-A5-2026",
  "uuid": "10000000-0000-0000-0000-000000000001",
  "name": "John Doe",
  "dob": "1980-05-12",
  "age": 45,
  "sex": "Male",
  "weight": "81.6 kg",
  "height": "182.0 cm",
  "avatarUrl": null,
  "createdAt": "2026-02-05T18:06:08.762194+00:00"
}
```

**Errors:** `404` if patient not found.

---

### 3. Vitals Endpoints

#### `GET /api/v1/patients/{patient_id}/vitals/latest`

Get the most recent vital signs for a patient.

**Output (200):**
```json
{
  "heartRate": { "value": 72, "unit": "bpm", "status": "stable" },
  "spO2": { "value": 98, "unit": "%", "status": "stable" },
  "bloodPressure": { "value": "120/80", "unit": "mmHg", "status": "stable" }
}
```

**Status logic:**
| Vital | Status |
|---|---|
| Heart Rate | `< 60` = low, `> 100` = high, else stable |
| SpO2 | `< 95` = low, else stable |
| Blood Pressure | systolic `> 140` or diastolic `> 90` = high; systolic `< 90` or diastolic `< 60` = low |

If no vitals exist, values are `0` / `"--/--"` with status `"unknown"`.

---

### 4. Alerts Endpoints

#### `GET /api/v1/patients/{patient_id}/alerts/active`

Get the active sticky clinical alert for a patient.

**Output (200):**
```json
{
  "id": "432c8b19-c03f-4923-a6fa-25bd194c71a5",
  "content": "Monitor RLL nodule stability. Patient reports mild shortness of breath.",
  "severity": "warning",
  "updatedAt": "2026-02-05T18:06:08.762194+00:00"
}
```

If no alert exists, returns `severity: "nominal"` with empty content.

#### `PUT /api/v1/patients/{patient_id}/alerts`

Create or update the sticky clinical alert.

**Input:**
```json
{
  "content": "Updated alert text here..."
}
```

**Output (200):** Same as GET response above.

---

### 5. Notes Endpoints

#### `GET /api/v1/patients/{patient_id}/notes`

List all clinical notes for a patient (excludes alerts). Ordered newest first.

**Output (200):**
```json
[
  {
    "id": "95f61367-42a2-4412-84e5-30d78da8315b",
    "date": "2026-02-05",
    "content": "Patient complained of persistent cough...",
    "createdAt": "2026-02-05T18:06:08.762194+00:00",
    "updatedAt": "2026-02-05T18:06:08.762194+00:00"
  }
]
```

#### `POST /api/v1/patients/{patient_id}/notes`

Create a new clinical note.

**Input:**
```json
{
  "content": "New clinical observation..."
}
```

**Output (201):** The created note (same shape as GET list item).

#### `PATCH /api/v1/notes/{note_id}`

Update an existing note by its UUID.

**Input:**
```json
{
  "content": "Updated content..."
}
```

**Output (200):** The updated note.

**Errors:** `404` if note not found.

#### `DELETE /api/v1/notes/{note_id}`

Delete a note by its UUID.

**Output:** `204 No Content`

**Errors:** `404` if note not found.

---

### 6. Imaging Endpoints

#### `GET /api/v1/patients/{patient_id}/imaging`

Get imaging history for a patient. Supports pagination.

**Query parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number (1-indexed) |
| `limit` | int | 20 | Items per page (max 50) |

**Output (200):**
```json
[
  {
    "id": "40000000-0000-0000-0000-000000000001",
    "src": "https://...supabase.co/storage/v1/...?token=...",
    "modality": "X-Ray (Chest AP)",
    "date": "2025-10-14 09:30 AM",
    "reading": "Clear lung fields bilaterally. No acute cardiopulmonary abnormality.",
    "confidence": "High"
  }
]
```

**Confidence mapping:** score `>= 0.8` = High, `>= 0.5` = Medium, else Low.

`src` is a Supabase Storage signed URL (valid for 1 hour). If no image file exists, `src` is an empty string.

#### `GET /api/v1/patients/{patient_id}/imaging/{image_id}`

Get details for a specific image.

**Output (200):** Same shape as a single item above.

---

### 7. Consultations Endpoints

#### `GET /api/v1/patients/{patient_id}/consultations`

List past AI consultation sessions for a patient. Supports pagination.

**Query parameters:** Same as imaging (`page`, `limit`).

**Output (200):**
```json
[
  {
    "id": "50000000-0000-0000-0000-000000000001",
    "title": "Chest Pain Analysis - RLL Nodule",
    "date": "Yesterday",
    "snippet": "Review the chest X-ray from October and identify any areas of concern."
  }
]
```

`date` is relative: "Today", "Yesterday", "3 days ago", or "YYYY-MM-DD" if older than 7 days.

#### `GET /api/v1/consultations/{consultation_id}`

Get a full consultation with all its messages.

**Output (200):**
```json
{
  "id": "50000000-0000-0000-0000-000000000001",
  "title": "Chest Pain Analysis - RLL Nodule",
  "date": "Yesterday",
  "messages": [
    {
      "id": "60000000-...",
      "sender": "user",
      "content": "Review the chest X-ray...",
      "timestamp": "2026-02-04T12:00:00+00:00"
    },
    {
      "id": "60000000-...",
      "sender": "ai",
      "content": "Based on the chest X-ray...",
      "timestamp": "2026-02-04T12:00:30+00:00"
    }
  ]
}
```

#### `GET /api/v1/consultations/{consultation_id}/messages`

Get just the messages for a consultation (same `messages` array as above, without the wrapper).

---

### 8. AI Analysis Endpoints

#### `POST /api/v1/analysis/generate`

The core endpoint. Sends a prompt with optional image/note context to the AI and returns the response.

**Input:**
```json
{
  "patientId": "8492-A5-2026",
  "prompt": "Analyze the progression of the nodule compared to the 2024 scan.",
  "context": {
    "imageIds": ["40000000-0000-0000-0000-000000000001", "40000000-0000-0000-0000-000000000003"],
    "noteIds": ["30000000-0000-0000-0000-000000000001"]
  },
  "modelConfig": {
    "temperature": 0.2,
    "stream": false,
    "maxTokens": 1024
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `patientId` | string | Yes | Patient's business ID |
| `prompt` | string | Yes | The doctor's question/instruction |
| `context.imageIds` | string[] | No | UUIDs of selected images to include |
| `context.noteIds` | string[] | No | UUIDs of selected notes to include |
| `modelConfig.temperature` | float | No | 0-1, default 0.2 (lower = more precise) |
| `modelConfig.stream` | bool | No | Ignored here (use `/generate/stream` for SSE) |
| `modelConfig.maxTokens` | int | No | Max tokens in response |

**Output (200):**
```json
{
  "text": "Based on the comparison of the imaging studies...",
  "timestamp": "2026-02-05T19:30:00.000000",
  "sender": "ai"
}
```

**Side effects:**
- Creates or continues a conversation (continues if last one was < 30 min ago)
- Saves the user message, AI response, and context links to the database

#### `POST /api/v1/analysis/generate/stream`

Same input as `/generate`, but returns a **Server-Sent Events (SSE)** stream for token-by-token response display.

**Response:** `text/event-stream`

```
data: {"text": "Based on "}

data: {"text": "the comparison "}

data: {"text": "of the imaging studies..."}

data: {"done": true}
```

Each `data:` line is a JSON object with either `text` (a chunk) or `done: true` (stream complete). The full conversation is saved to the database after streaming finishes.

---

### 9. Health / Debug Endpoints

These do NOT require authentication.

#### `GET /`

```json
{
  "name": "MedGemma Clinical Suite API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/api/v1/docs",
  "health": "/health"
}
```

#### `GET /health`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": { "status": "healthy", "type": "supabase" },
    "ai": { "status": "configured", "mode": "live" }
  }
}
```

`status` can be `"healthy"`, `"degraded"` (DB not configured), or `"unhealthy"` (DB connection failed).

`ai.mode` is `"live"` if `MEDGEMMA_API_URL` is set, otherwise `"mock"`.

#### `GET /health/ready`

Returns `{"ready": true}` if the database is reachable. Returns `503` otherwise.

#### `GET /health/live`

Always returns `{"alive": true}`.

#### `GET /debug/config` (DEBUG mode only)

Shows current configuration (without secrets).

#### `GET /debug/routes` (DEBUG mode only)

Lists all registered routes with their methods.

---

## Database Schema

9 tables stored in Supabase (PostgreSQL):

```
users                 Physician accounts (username, bcrypt hash, role)
patients              Demographics (business_id, name, DOB, sex, weight, height)
patient_vitals        Time-series vitals (HR, SpO2, BP per patient)
image_blobs           Deduplicated file storage (SHA-256 hash as PK)
patient_images        Links patients to images (modality, visit date, AI reading)
clinical_notes        Notes + alerts (is_alert boolean distinguishes them)
conversations         AI chat sessions per patient
messages              Individual messages (sender: user | ai)
message_context       Tracks which images/notes were attached to each message
```

**Key relationships:**
- All patient-owned tables reference `patients(id)` with `ON DELETE CASCADE`
- `patient_images.image_blob_hash` references `image_blobs(file_hash)` (deduplication)
- `messages.conversation_id` references `conversations(id)`
- `message_context` has a CHECK constraint enforcing exactly one attachment type per row

**RLS:** Enabled on all tables. The backend uses the service role key which bypasses RLS. Direct access via the publishable/anon key is blocked.

**Full schema:** See `supabase/migrations/001_initial_schema.sql`

---

## AI Service

The AI service (`app/services/ai_service.py`) handles communication with the MedGemma model.

**Two modes:**

| Mode | When | Behavior |
|---|---|---|
| **Live** | `MEDGEMMA_API_URL` is set | Sends prompt + context to the MedGemma API via HTTP |
| **Mock** | `MEDGEMMA_API_URL` is not set or unreachable | Returns pre-written clinical responses based on prompt keywords |

Mock mode is fully functional for development and testing. It generates realistic-looking medical analysis text based on the content of the prompt.

**SSE streaming** is supported in both modes. In mock mode, the response is delivered word-by-word with a small delay to simulate real-time generation.

---

## Demo Credentials & Seed Data

After running the SQL migration, the following data is available:

**Login:**
| Username | Password |
|---|---|
| `dr.smith` | `password` |

**Patients:** (business IDs depend on your seed data)

The SQL migration seeds 3 patients, each with:
- Vital signs records
- Clinical notes (some patients have active alerts)
- Imaging records with AI readings
- Past AI consultation sessions with full message threads
- Message context links (which images/notes were referenced)

To re-seed the demo user via Python:
```bash
python -m scripts.seed_data
```

---

## Assumptions & Roadmap

**Current assumptions:**
- The frontend will be connected later (backend is frontend-ready with CORS enabled)
- The fine-tuned MedGemma model will be connected later (mock mode works for development)
- Supabase is the sole database — no local PostgreSQL needed
- The service role key is used by the backend (bypasses RLS)
- Image files are stored in Supabase Storage; the API returns signed URLs

**What is ready now:**
- All 13 spec endpoints implemented and tested
- 3 bonus endpoints (`/auth/me`, `/consultations/{id}`, `/analysis/generate/stream`)
- Full Supabase integration (9 tables, indexes, RLS, storage bucket)
- JWT authentication with bcrypt password hashing
- AI mock responses for development
- SSE streaming for real-time AI responses
- Pagination on imaging and consultations
- Health checks (ready/live probes for deployment)

**What comes next:**
- Connect the frontend SPA
- Connect the fine-tuned MedGemma model to `/analysis/generate`
- Upload actual medical images to Supabase Storage
- Add rate limiting and request validation
- Add comprehensive test coverage

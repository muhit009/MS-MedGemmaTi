// ─── Authentication ──────────────────────────────────────────────

export interface Token {
  access_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface UserResponse {
  id: string;
  username: string;
  full_name: string | null;
  role: string;
}

// ─── Patients ────────────────────────────────────────────────────

export interface PatientSearchRequest {
  patientId?: string;
  name?: string;
}

export interface PatientSearchResponse {
  id: string;
  name: string;
  dob: string;
  age: number;
  sex: string | null;
  weight: string | null;
  height: string | null;
  avatarUrl: string | null;
}

export interface PatientResponse extends PatientSearchResponse {
  uuid: string;
  createdAt: string | null;
}

export interface PatientCreateRequest {
  businessId: string;
  fullName: string;
  dob: string;
  sex?: string;
  weightKg?: number;
  heightCm?: number;
}

// ─── Vitals ──────────────────────────────────────────────────────

export interface VitalReading {
  value: number | string;
  unit: string;
  status: 'stable' | 'low' | 'high' | 'critical' | 'unknown';
}

export interface VitalsResponse {
  heartRate: VitalReading;
  spO2: VitalReading;
  bloodPressure: VitalReading;
}

// ─── Alerts ──────────────────────────────────────────────────────

export interface AlertResponse {
  id: string | null;
  content: string;
  severity: 'nominal' | 'warning' | 'critical';
  updatedAt: string | null;
}

export interface AlertUpdateRequest {
  content: string;
}

// ─── Notes ───────────────────────────────────────────────────────

export interface NoteResponse {
  id: string;
  date: string;
  content: string;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface NoteCreateRequest {
  content: string;
}

export interface NoteUpdateRequest {
  content: string;
}

// ─── Imaging ─────────────────────────────────────────────────────

export interface ImageResponse {
  id: string;
  src: string;
  modality: string;
  date: string;
  reading: string | null;
  confidence: 'High' | 'Medium' | 'Low';
}

// ─── Consultations ───────────────────────────────────────────────

export interface MessageResponse {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: string | null;
}

export interface ConsultationListResponse {
  id: string;
  title: string;
  date: string;
  snippet: string;
}

export interface ConsultationResponse {
  id: string;
  title: string;
  date: string;
  messages: MessageResponse[];
}

// ─── AI Analysis ─────────────────────────────────────────────────

export interface AnalysisContext {
  imageIds?: (string | number)[];
  noteIds?: (string | number)[];
  alertContent?: string;
}

export interface ModelConfig {
  temperature?: number;
  stream?: boolean;
  maxTokens?: number;
}

export interface InlineImage {
  base64: string;
  mimeType: string;
  visitDate?: string;
}

export interface AnalysisRequest {
  patientId: string;
  prompt: string;
  mode?: 'analysis' | 'discussion';
  inlineImages?: InlineImage[];
  context?: AnalysisContext;
  modelConfig?: ModelConfig;
}

export interface AnalysisResponse {
  text: string;
  timestamp: string;
  sender: 'ai';
}

export interface StreamChunk {
  text?: string;
  done?: boolean;
}

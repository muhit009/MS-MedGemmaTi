import type {
  Token,
  LoginRequest,
  UserResponse,
  PatientSearchRequest,
  PatientSearchResponse,
  PatientResponse,
  PatientCreateRequest,
  VitalsResponse,
  AlertResponse,
  AlertUpdateRequest,
  NoteResponse,
  NoteCreateRequest,
  NoteUpdateRequest,
  ImageResponse,
  ConsultationListResponse,
  ConsultationResponse,
  AnalysisRequest,
  AnalysisResponse,
  StreamChunk,
} from '@/types/api';

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

// ─── Token helpers ───────────────────────────────────────────────

const TOKEN_KEY = 'medgemma_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Generic fetch wrapper ───────────────────────────────────────

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
    this.name = 'ApiError';
  }
}

export { ApiError };

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

// ─── Auth ────────────────────────────────────────────────────────

export async function login(credentials: LoginRequest): Promise<Token> {
  return request<Token>('/auth/login/json', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function getMe(): Promise<UserResponse> {
  return request<UserResponse>('/auth/me');
}

// ─── Patients ────────────────────────────────────────────────────

export async function searchPatients(
  params: PatientSearchRequest,
): Promise<PatientSearchResponse[]> {
  return request<PatientSearchResponse[]>('/patients/search', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getPatient(patientId: string): Promise<PatientResponse> {
  return request<PatientResponse>(`/patients/${encodeURIComponent(patientId)}`);
}

export async function createPatient(
  data: PatientCreateRequest,
): Promise<PatientResponse> {
  return request<PatientResponse>('/patients', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ─── Vitals ──────────────────────────────────────────────────────

export async function getLatestVitals(
  patientId: string,
): Promise<VitalsResponse> {
  return request<VitalsResponse>(
    `/patients/${encodeURIComponent(patientId)}/vitals/latest`,
  );
}

// ─── Alerts ──────────────────────────────────────────────────────

export async function getActiveAlert(
  patientId: string,
): Promise<AlertResponse> {
  return request<AlertResponse>(
    `/patients/${encodeURIComponent(patientId)}/alerts/active`,
  );
}

export async function updateAlert(
  patientId: string,
  data: AlertUpdateRequest,
): Promise<AlertResponse> {
  return request<AlertResponse>(
    `/patients/${encodeURIComponent(patientId)}/alerts`,
    { method: 'PUT', body: JSON.stringify(data) },
  );
}

// ─── Notes ───────────────────────────────────────────────────────

export async function getNotes(patientId: string): Promise<NoteResponse[]> {
  return request<NoteResponse[]>(
    `/patients/${encodeURIComponent(patientId)}/notes`,
  );
}

export async function createNote(
  patientId: string,
  data: NoteCreateRequest,
): Promise<NoteResponse> {
  return request<NoteResponse>(
    `/patients/${encodeURIComponent(patientId)}/notes`,
    { method: 'POST', body: JSON.stringify(data) },
  );
}

export async function updateNote(
  noteId: string,
  data: NoteUpdateRequest,
): Promise<NoteResponse> {
  return request<NoteResponse>(`/notes/${encodeURIComponent(noteId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteNote(noteId: string): Promise<void> {
  return request<void>(`/notes/${encodeURIComponent(noteId)}`, {
    method: 'DELETE',
  });
}

// ─── Imaging ─────────────────────────────────────────────────────

export async function getImaging(
  patientId: string,
  page = 1,
  limit = 20,
): Promise<ImageResponse[]> {
  return request<ImageResponse[]>(
    `/patients/${encodeURIComponent(patientId)}/imaging?page=${page}&limit=${limit}`,
  );
}

export async function uploadImage(
  patientId: string,
  file: File,
  visitDate: string,
): Promise<ImageResponse> {
  const token = getToken();
  const formData = new FormData();
  formData.append('file', file);
  formData.append('visit_date', visitDate);

  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(
    `${BASE_URL}/patients/${encodeURIComponent(patientId)}/imaging`,
    { method: 'POST', headers, body: formData },
  );

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  return res.json();
}

export async function deleteImage(
  patientId: string,
  imageId: string,
): Promise<void> {
  return request<void>(
    `/patients/${encodeURIComponent(patientId)}/imaging/${encodeURIComponent(imageId)}`,
    { method: 'DELETE' },
  );
}

// ─── Consultations ───────────────────────────────────────────────

export async function getConsultations(
  patientId: string,
  page = 1,
  limit = 20,
): Promise<ConsultationListResponse[]> {
  return request<ConsultationListResponse[]>(
    `/patients/${encodeURIComponent(patientId)}/consultations?page=${page}&limit=${limit}`,
  );
}

export async function getConsultation(
  consultationId: string,
): Promise<ConsultationResponse> {
  return request<ConsultationResponse>(
    `/consultations/${encodeURIComponent(consultationId)}`,
  );
}

// ─── AI Analysis ─────────────────────────────────────────────────

export async function generateAnalysis(
  data: AnalysisRequest,
): Promise<AnalysisResponse> {
  return request<AnalysisResponse>('/analysis/generate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Stream AI analysis via Server-Sent Events.
 * Yields StreamChunk objects as they arrive.
 */
export async function* streamAnalysis(
  data: AnalysisRequest,
): AsyncGenerator<StreamChunk> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}/analysis/generate/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Keep the last (possibly incomplete) line in the buffer
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;
      const json = trimmed.slice(6);
      if (!json) continue;
      try {
        const chunk: StreamChunk = JSON.parse(json);
        yield chunk;
        if (chunk.done) return;
      } catch {
        // skip malformed chunks
      }
    }
  }
}

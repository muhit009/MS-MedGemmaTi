"""
Conversation schemas.
Pydantic models for AI consultations and analysis.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union


class MessageResponse(BaseModel):
    """
    Chat message response schema.
    """
    id: str = Field(..., description="Message ID")
    sender: str = Field(..., description="Message sender (user or ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "sender": "user",
                "content": "Analyze the progression of the nodule compared to the 2024 scan.",
                "timestamp": "2026-01-22T14:30:00Z"
            }
        }


class ConsultationListResponse(BaseModel):
    """
    Consultation list item response schema.
    Used in the Past Consultations list.
    """
    id: str = Field(..., description="Consultation ID")
    title: str = Field(..., description="Consultation title")
    date: str = Field(..., description="Relative date (Today, Yesterday, etc.)")
    snippet: str = Field(..., description="Preview snippet of first message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_123",
                "title": "Chest Pain Analysis",
                "date": "Yesterday",
                "snippet": "Patient reported mild discomfort in the left chest area..."
            }
        }


class ConsultationResponse(BaseModel):
    """
    Full consultation response schema with messages.
    """
    id: str = Field(..., description="Consultation ID")
    title: str = Field(..., description="Consultation title")
    date: str = Field(..., description="Relative date")
    messages: List[MessageResponse] = Field(..., description="List of messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_123",
                "title": "Chest Pain Analysis",
                "date": "Yesterday",
                "messages": [
                    {
                        "id": "msg_1",
                        "sender": "user",
                        "content": "Analyze the chest X-ray for any abnormalities.",
                        "timestamp": "2026-01-21T10:00:00Z"
                    },
                    {
                        "id": "msg_2",
                        "sender": "ai",
                        "content": "Based on the chest X-ray analysis...",
                        "timestamp": "2026-01-21T10:00:05Z"
                    }
                ]
            }
        }


class AnalysisContext(BaseModel):
    """
    Context for AI analysis request.
    Specifies which images and notes to include.
    """
    imageIds: Optional[List[Union[str, int]]] = Field(None, description="IDs of selected images")
    noteIds: Optional[List[Union[str, int]]] = Field(None, description="IDs of selected notes")
    alertContent: Optional[str] = Field(None, description="Alert content for context")

    class Config:
        json_schema_extra = {
            "example": {
                "imageIds": [3, 5],
                "noteIds": [1],
                "alertContent": "Critical: Elevated troponin levels detected"
            }
        }


class ModelConfig(BaseModel):
    """
    AI model configuration options.
    """
    temperature: Optional[float] = Field(0.2, ge=0, le=1, description="Model temperature (0-1)")
    stream: Optional[bool] = Field(False, description="Enable streaming response")
    maxTokens: Optional[int] = Field(None, ge=1, le=4096, description="Maximum response tokens")
    
    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 0.2,
                "stream": True,
                "maxTokens": 1024
            }
        }


class InlineImage(BaseModel):
    """
    Ephemeral image sent as base64 (used for demo patient uploads that have no Supabase backing).
    """
    base64: str = Field(..., description="Raw base64-encoded image data (no data: prefix)")
    mimeType: str = Field("image/jpeg", description="MIME type of the image")
    visitDate: Optional[str] = Field(None, description="Visit/study date for timeline ordering")


class AnalysisRequest(BaseModel):
    """
    AI analysis request schema.
    The main Submit action from the chat interface.
    """
    patientId: str = Field(..., description="Patient business ID")
    prompt: str = Field(..., min_length=1, description="User prompt/question")
    mode: Optional[str] = Field(None, description="'analysis' | 'discussion' | None (auto-detect)")
    inlineImages: Optional[List[InlineImage]] = Field(None, description="Ephemeral images sent as base64")
    context: Optional[AnalysisContext] = Field(None, description="Context (images and notes)")
    modelConfig: Optional[ModelConfig] = Field(None, description="Model configuration")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patientId": "8492-A5-2026",
                "prompt": "Analyze the progression of the nodule compared to the 2024 scan.",
                "context": {
                    "imageIds": [3, 5],
                    "noteIds": [1]
                },
                "modelConfig": {
                    "temperature": 0.2,
                    "stream": False
                }
            }
        }


class AnalysisResponse(BaseModel):
    """
    AI analysis response schema.
    """
    text: str = Field(..., description="AI response text")
    timestamp: str = Field(..., description="Response timestamp")
    sender: str = Field(default="ai", description="Sender (always 'ai')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Based on the comparison of the chest X-rays from 2024 and 2025, I observe the following regarding the nodule progression...",
                "timestamp": "2026-01-22T14:30:00Z",
                "sender": "ai"
            }
        }


class StreamChunk(BaseModel):
    """
    Streaming response chunk schema.
    Used for SSE streaming.
    """
    text: Optional[str] = Field(None, description="Text chunk")
    done: Optional[bool] = Field(None, description="Stream completion flag")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Based on the ",
                "done": False
            }
        }
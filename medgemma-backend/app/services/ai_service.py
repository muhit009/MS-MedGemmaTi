"""
AI Service for MedGemma integration.
Handles communication with the MedGemma model for medical image analysis.

Supports three modes (checked in order):
1. RunPod Serverless — if RUNPOD_ENDPOINT_ID is set
2. Local model server — if MEDGEMMA_API_URL is set
3. Mock responses — fallback for development/testing
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, AsyncGenerator, List
import json
import logging

from app.core.config import settings

log = logging.getLogger("ai_service")


class AIServiceError(Exception):
    """Raised when the AI backend returns an error instead of a valid response."""
    pass

MEDICAL_SYSTEM_PROMPT = """You are MedGemma-TI, a medical AI assistant specialized in temporal chest X-ray analysis for physicians. When imaging studies are provided, analyze them in the chronological order shown and identify interval changes. When no images are provided, respond naturally and thoroughly to clinical questions using proper medical terminology."""


def _temporal_label(idx: int, total: int) -> str:
    """
    Return the role label matching the training data format.
    Training uses: Role: Baseline / Role: Intermediate / Role: Current
    """
    if total == 1:
        return "Current"
    if idx == 0:
        return "Baseline"
    if idx == total - 1:
        return "Current"
    return "Intermediate"


def _get_mode() -> str:
    """Return the active inference mode."""
    if settings.AI_SERVICE_MODE == "debug":
        return "debug"
    if settings.RUNPOD_ENDPOINT_ID:
        return "runpod"
    if settings.MEDGEMMA_API_URL:
        return "local"
    return "mock"


def _build_messages(prompt: str, context: Dict[str, Any], mode: str = 'analysis') -> List[Dict[str, Any]]:
    """
    Build chat messages matching the model's training/eval format exactly.

    From train_mult.py (format_for_training) + inference_script.py (format_raw_entry):
      - All {"type": "image"} entries come FIRST in user content
      - The ENTIRE text prompt follows as ONE {"type": "text"} part
      - No system message was used during training

    The text prompt itself includes <image_1>, <image_2> etc. as TEXT markers
    inside the IMAGING TIMELINE section — these are literal strings the model
    learned to associate with image positions, not actual image tokens.

    Section order (from JSONL training data):
      PATIENT CONTEXT
      IMAGING TIMELINE  (with <image_N> text markers)
      CLINICAL ALERT    (only if present)
      PATIENT NOTES     (only if present)
      CLINICAL REQUEST
      PREVIOUS FINDINGS (only if baseline reading exists — comes AFTER request)
      TASK              (only when images present — eval-style with classification terms)
    """
    # System message for discussion mode only — the LoRA was trained without a
    # system message, so this channel is unaffected by the fine-tuning.
    if mode == 'discussion':
        messages = [{
            "role": "system",
            "content": (
                "You are MedGemma-TI, a medical AI assistant. "
                "Answer the physician's follow-up question directly and concisely. "
                "Do NOT repeat or echo the patient context. "
                "Do NOT generate CLINICAL REQUEST, TASK, IMAGING TIMELINE, "
                "PREVIOUS FINDINGS, or any structured report sections."
            )
        }]
    else:
        # No system message — training used a single user→assistant turn only.
        messages = []

    # Conversation history (text-only — images are never re-sent in history)
    for msg in context.get("conversation_history", []):
        role = "assistant" if msg.get("sender") == "ai" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})

    # Images arrive sorted by visit_date ASC (from _fetch_selected_images)
    images = context.get("images", [])
    content_parts: List[Any] = []

    # --- ALL actual image parts first (both modes) ---
    for img in images:
        b64 = img.get("image_base64")
        if b64:
            mime = img.get("mime_type", "image/png")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })

    text_lines: List[str] = []

    patient = context.get("patient", {})

    if mode == 'discussion':
        # --- Discussion mode: natural language framing, no ALL-CAPS headers ---
        # Avoids triggering the LoRA's analysis-format conditioning.
        header_parts = []
        if patient.get("age") is not None:
            header_parts.append(f"{patient['age']}-year-old")
        if patient.get("sex"):
            header_parts.append(patient["sex"])
        if images:
            n = len(images)
            header_parts.append(f"\u00b7 {n} chest X-ray{'s' if n > 1 else ''} provided")
        if header_parts:
            text_lines.append(f"[Patient: {' '.join(header_parts)}]")
            text_lines.append("")

        alert = context.get("alert")
        if alert:
            text_lines.append(f"Clinical alert: {alert}")
            text_lines.append("")

        notes = context.get("notes", [])
        if notes:
            text_lines.append("Patient notes:")
            for note in notes:
                date = note.get("created_at", "Unknown date")
                text_lines.append(f"  ({date}) {note.get('content', '')}")
            text_lines.append("")

        text_lines.append(f"Physician's question: {prompt}")
    else:
        # --- Analysis mode: full fine-tuned prompt format ---

        # PATIENT CONTEXT
        if patient:
            ctx_parts = []
            if patient.get("age") is not None:
                ctx_parts.append(f"Age: {patient['age']} years")
            if patient.get("sex"):
                ctx_parts.append(f"Sex: {patient['sex']}")
            if ctx_parts:
                text_lines.append("PATIENT CONTEXT:")
                text_lines.append(" | ".join(ctx_parts))
                text_lines.append("")

        # IMAGING TIMELINE — labels + <image_N> text markers
        if images:
            text_lines.append("IMAGING TIMELINE:")
            total = len(images)
            for idx, img in enumerate(images):
                study_num = img.get("study_number", idx + 1)
                visit_date = (img.get("visit_date", "") or "").split("T")[0].split(" ")[0]
                role_label = _temporal_label(idx, total)
                image_num = idx + 1

                if visit_date:
                    label = f"[IMAGE_{image_num} | Date: {visit_date} | Role: {role_label}]"
                else:
                    label = f"[IMAGE_{image_num} | Study {study_num} | Role: {role_label}]"

                text_lines.append(label)
                text_lines.append(f"<image_{image_num}>")
                text_lines.append("")

        alert = context.get("alert")
        if alert:
            text_lines.append("CLINICAL ALERT:")
            text_lines.append(alert)
            text_lines.append("")

        notes = context.get("notes", [])
        if notes:
            text_lines.append("PATIENT NOTES:")
            for note in notes:
                date = note.get("created_at", "Unknown date")
                text_lines.append(f"({date})")
                text_lines.append(note.get("content", ""))
                text_lines.append("")

        text_lines.append("CLINICAL REQUEST:")
        text_lines.append(prompt)
        text_lines.append("")

        # PREVIOUS FINDINGS — comes AFTER clinical request (matches training JSONL order)
        if images:
            baseline_readings = [
                img.get("reading") for img in images[:-1] if img.get("reading")
            ]
            if baseline_readings:
                text_lines.append("PREVIOUS FINDINGS:")
                for reading in baseline_readings:
                    text_lines.append(reading)
                text_lines.append("")

        # TASK suffix — eval-style (with explicit classification terms), images only
        if images:
            text_lines.append(
                "TASK: Analyze the current study compared to the prior study and identify "
                "any interval changes. Conclude your analysis with a clear overall assessment "
                "using one of these terms: IMPROVED, STABLE, WORSENED, or MIXED."
            )

    content_parts.append({"type": "text", "text": "\n".join(text_lines)})
    messages.append({"role": "user", "content": content_parts})
    return messages


def _build_full_prompt(prompt: str, context: Dict[str, Any], mode: str = 'analysis') -> str:
    """Build a text-only prompt (fallback for mock/local mode)."""
    lines = []

    patient = context.get("patient", {})
    images = context.get("images", [])

    if mode == 'discussion':
        # Natural language header (replaces ALL-CAPS PATIENT CONTEXT section)
        header_parts = []
        if patient.get("age") is not None:
            header_parts.append(f"{patient['age']}-year-old")
        if patient.get("sex"):
            header_parts.append(patient["sex"])
        if images:
            n = len(images)
            header_parts.append(f"\u00b7 {n} chest X-ray{'s' if n > 1 else ''} provided")
        if header_parts:
            lines.append(f"[Patient: {' '.join(header_parts)}]")
            lines.append("")
    else:
        if patient:
            ctx_parts = []
            if patient.get("age") is not None:
                ctx_parts.append(f"Age: {patient['age']} years")
            if patient.get("sex"):
                ctx_parts.append(f"Sex: {patient['sex']}")
            if ctx_parts:
                lines.append("PATIENT CONTEXT:")
                lines.append(" | ".join(ctx_parts))
                lines.append("")

    for msg in context.get("conversation_history", []):
        role = "Assistant" if msg.get("sender") == "ai" else "Physician"
        lines.append(f"{role}: {msg.get('content', '')}")

    if mode == 'discussion':
        alert = context.get("alert")
        if alert:
            lines.append(f"Clinical alert: {alert}")
            lines.append("")

        notes = context.get("notes", [])
        if notes:
            lines.append("Patient notes:")
            for note in notes:
                lines.append(f"  ({note.get('created_at', 'Unknown date')}) {note.get('content', '')}")
            lines.append("")

        lines.append(f"Physician's question: {prompt}")
    else:
        if images:
            lines.append("IMAGING TIMELINE:")
            total = len(images)
            for idx, img in enumerate(images):
                study_num = img.get("study_number", idx + 1)
                visit_date = (img.get("visit_date", "") or "").split("T")[0].split(" ")[0]
                role_label = _temporal_label(idx, total)
                image_num = idx + 1
                if visit_date:
                    lines.append(f"[IMAGE_{image_num} | Date: {visit_date} | Role: {role_label}]")
                else:
                    lines.append(f"[IMAGE_{image_num} | Study {study_num} | Role: {role_label}]")
                lines.append(f"<image_{image_num}>")
                lines.append("")

        alert = context.get("alert")
        if alert:
            lines.append("CLINICAL ALERT:")
            lines.append(alert)
            lines.append("")

        notes = context.get("notes", [])
        if notes:
            lines.append("PATIENT NOTES:")
            for note in notes:
                lines.append(f"({note.get('created_at', 'Unknown date')})")
                lines.append(note.get("content", ""))
            lines.append("")

        lines.append("CLINICAL REQUEST:")
        lines.append(prompt)
        lines.append("")

        if images:
            baseline_readings = [
                img.get("reading") for img in images[:-1] if img.get("reading")
            ]
            if baseline_readings:
                lines.append("PREVIOUS FINDINGS:")
                for reading in baseline_readings:
                    lines.append(reading)
                lines.append("")

        if images:
            lines.append(
                "TASK: Analyze the current study compared to the prior study and identify "
                "any interval changes. Conclude your analysis with a clear overall assessment "
                "using one of these terms: IMPROVED, STABLE, WORSENED, or MIXED."
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Debug mode
# ---------------------------------------------------------------------------

def _generate_debug_response(prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None, prompt_mode: str = 'analysis') -> str:
    """
    Build the full RunPod payload, log it to the terminal, and return a mock
    response prefixed with debug metadata.  No network call is made.
    """
    temperature, max_tokens = _extract_config(config)
    messages = _build_messages(prompt, context, mode=prompt_mode)

    payload = {
        "input": {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    }

    # Count images and measure sizes
    image_count = 0
    image_sizes: List[str] = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    image_count += 1
                    url = part.get("image_url", {}).get("url", "")
                    # Approximate size from base64 length
                    b64_len = len(url.split(",", 1)[-1]) if "," in url else len(url)
                    approx_bytes = b64_len * 3 // 4
                    if approx_bytes > 1_048_576:
                        image_sizes.append(f"{approx_bytes / 1_048_576:.1f} MB")
                    else:
                        image_sizes.append(f"{approx_bytes / 1024:.0f} KB")

    history = context.get("conversation_history", [])
    patient = context.get("patient", {})

    # --- Reconstruct the text the model actually sees ---
    # Walk each message and render its text content with <image_N> placeholders
    img_counter = 0
    rendered_messages: List[Dict[str, str]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")
        if isinstance(content, str):
            rendered_messages.append({"role": role, "text": content})
        elif isinstance(content, list):
            text_buf: List[str] = []
            for part in content:
                if part.get("type") == "text":
                    text_buf.append(part.get("text", ""))
                elif part.get("type") == "image_url":
                    img_counter += 1
                    url = part.get("image_url", {}).get("url", "")
                    b64_len = len(url.split(",", 1)[-1]) if "," in url else len(url)
                    approx_kb = (b64_len * 3 // 4) / 1024
                    text_buf.append(f"<image_{img_counter}>  ({approx_kb:.0f} KB)")
            rendered_messages.append({"role": role, "text": "\n".join(text_buf)})

    # --- Terminal log ---
    log.info("=" * 60)
    log.info("[DEBUG MODE] Full payload inspection")
    log.info("-" * 60)
    log.info("Messages: %d | Images: %d (%s) | History: %d | Temp: %s | Max tokens: %s",
             len(messages), image_count,
             ", ".join(image_sizes) if image_sizes else "none",
             len(history), temperature, max_tokens)
    log.info("-" * 60)
    for rm in rendered_messages:
        for line in rm["text"].splitlines():
            log.info("  [%s] %s", rm["role"], line)
        log.info("")
    log.info("=" * 60)

    # --- Build response showing exact prompt structure ---
    lines = [
        "**[DEBUG MODE]** — No AI call was made.\n",
        f"**Config:** temperature={temperature}, max_tokens={max_tokens}, "
        f"images={image_count} ({', '.join(image_sizes) if image_sizes else 'none'}), "
        f"history={len(history)} turns\n",
        "---\n",
    ]

    for rm in rendered_messages:
        lines.append(f"**`[{rm['role']}]`**")
        lines.append("```")
        lines.append(rm["text"])
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("*Remove `AI_SERVICE_MODE=debug` from `.env` to call the real model.*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_ai_response(
    prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None
) -> str:
    config = dict(config) if config else {}
    prompt_mode = config.pop('mode', 'analysis')
    service_mode = _get_mode()
    if service_mode == "debug":
        return _generate_debug_response(prompt, context, config, prompt_mode=prompt_mode)
    if service_mode == "runpod":
        return await _call_runpod(prompt, context, config, prompt_mode=prompt_mode)
    elif service_mode == "local":
        return await _call_medgemma_api(prompt, context, config, prompt_mode=prompt_mode)
    else:
        return _generate_mock_response(prompt, context)


async def generate_ai_response_stream(
    prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None
) -> AsyncGenerator[str, None]:
    config = dict(config) if config else {}
    prompt_mode = config.pop('mode', 'analysis')
    service_mode = _get_mode()
    if service_mode == "debug":
        debug_response = _generate_debug_response(prompt, context, config, prompt_mode=prompt_mode)
        words = debug_response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
        return
    if service_mode == "runpod":
        async for chunk in _call_runpod_fake_stream(prompt, context, config, prompt_mode=prompt_mode):
            yield chunk
    elif service_mode == "local":
        async for chunk in _call_medgemma_api_stream(prompt, context, config, prompt_mode=prompt_mode):
            yield chunk
    else:
        mock_response = _generate_mock_response(prompt, context)
        words = mock_response.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")


# ---------------------------------------------------------------------------
# RunPod Serverless
# ---------------------------------------------------------------------------

def _runpod_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }

def _runpod_run_url() -> str:
    return f"https://api.runpod.ai/v2/{settings.RUNPOD_ENDPOINT_ID}/run"

def _runpod_status_url(job_id: str) -> str:
    return f"https://api.runpod.ai/v2/{settings.RUNPOD_ENDPOINT_ID}/status/{job_id}"

def _extract_config(config: Optional[Dict[str, Any]]) -> tuple:
    _temp = config.get("temperature") if config else None
    _maxt = config.get("maxTokens") if config else None
    temperature = _temp if _temp is not None else 0.2
    max_tokens = _maxt if _maxt is not None else 2048
    return temperature, max_tokens


RUNPOD_MAX_WAIT = 300       # total seconds to wait (covers cold starts)
RUNPOD_POLL_INTERVAL = 2    # seconds between status polls


async def _call_runpod(prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None, prompt_mode: str = 'analysis') -> str:
    """
    Submit a job via the async /run endpoint, then poll /status/{id} until
    COMPLETED, FAILED, or timeout.  This tolerates cold-start queuing that
    would kill a /runsync call.
    """
    temperature, max_tokens = _extract_config(config)
    messages = _build_messages(prompt, context, mode=prompt_mode)

    payload = {
        "input": {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    }

    num_images = sum(
        1 for msg in messages if isinstance(msg.get("content"), list)
        for part in (msg.get("content") if isinstance(msg.get("content"), list) else [])
        if part.get("type") == "image_url"
    )
    log.info("RunPod request: %d messages, %d images", len(messages), num_images)

    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # --- Submit job ---
            response = await client.post(_runpod_run_url(), json=payload, headers=_runpod_headers())
            response.raise_for_status()
            submit_result = response.json()
            job_id = submit_result.get("id")
            if not job_id:
                raise AIServiceError(f"RunPod /run did not return a job id: {submit_result}")
            log.info("RunPod job submitted: %s, status=%s", job_id, submit_result.get("status"))

            # If it completed immediately (warm worker)
            if submit_result.get("status") == "COMPLETED":
                return _extract_runpod_output(submit_result)

            # --- Poll for completion ---
            elapsed = 0.0
            while elapsed < RUNPOD_MAX_WAIT:
                await asyncio.sleep(RUNPOD_POLL_INTERVAL)
                elapsed += RUNPOD_POLL_INTERVAL

                poll_resp = await client.get(_runpod_status_url(job_id), headers=_runpod_headers())
                poll_resp.raise_for_status()
                result = poll_resp.json()
                status = result.get("status")

                if status == "COMPLETED":
                    log.info("RunPod job %s completed after %.0fs", job_id, elapsed)
                    return _extract_runpod_output(result)
                elif status == "FAILED":
                    error = result.get("error", "Unknown error")
                    log.error("RunPod job %s failed: %s", job_id, str(error)[:300])
                    raise AIServiceError(f"RunPod error: {error}")
                # IN_QUEUE or IN_PROGRESS — keep polling
                if elapsed % 30 < RUNPOD_POLL_INTERVAL:
                    log.info("RunPod job %s still %s (%.0fs elapsed)", job_id, status, elapsed)

            raise AIServiceError(f"RunPod job {job_id} timed out after {RUNPOD_MAX_WAIT}s (last status: {status})")

        except AIServiceError:
            raise
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"Error communicating with RunPod: {e.response.status_code}")
        except httpx.RequestError as e:
            raise AIServiceError(f"Error connecting to RunPod: {str(e)}")
        except Exception as e:
            raise AIServiceError(f"Unexpected error: {str(e)}")


def _extract_runpod_output(result: dict) -> str:
    """Pull the generated text out of a COMPLETED RunPod response."""
    output = result.get("output", {})
    log.info("RunPod output keys: %s", list(output.keys()) if isinstance(output, dict) else type(output))
    return output.get("response", "") if isinstance(output, dict) else str(output)


async def _call_runpod_fake_stream(
    prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None, prompt_mode: str = 'analysis'
) -> AsyncGenerator[str, None]:
    full_response = await _call_runpod(prompt, context, config, prompt_mode=prompt_mode)
    words = full_response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        await asyncio.sleep(0.03)


# ---------------------------------------------------------------------------
# Local model server
# ---------------------------------------------------------------------------

async def _call_medgemma_api(prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None, prompt_mode: str = 'analysis') -> str:
    temperature, max_tokens = _extract_config(config)
    messages = _build_messages(prompt, context, mode=prompt_mode)

    payload = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Content-Type": "application/json"}
    if settings.MEDGEMMA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.MEDGEMMA_API_KEY}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(settings.MEDGEMMA_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, dict):
                return result.get("text") or result.get("response") or result.get("generated_text", "")
            return str(result)
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"Error communicating with AI service: {e.response.status_code}")
        except httpx.RequestError as e:
            raise AIServiceError(f"Error connecting to AI service: {str(e)}")
        except Exception as e:
            raise AIServiceError(f"Unexpected error: {str(e)}")


async def _call_medgemma_api_stream(
    prompt: str, context: Dict[str, Any], config: Optional[Dict[str, Any]] = None, prompt_mode: str = 'analysis'
) -> AsyncGenerator[str, None]:
    temperature, max_tokens = _extract_config(config)
    messages = _build_messages(prompt, context, mode=prompt_mode)

    payload = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True}
    headers = {"Content-Type": "application/json"}
    if settings.MEDGEMMA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.MEDGEMMA_API_KEY}"

    timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", settings.MEDGEMMA_API_URL, json=payload, headers=headers) as response:
                response.raise_for_status()
                buffer = ""
                async for raw_bytes in response.aiter_bytes():
                    buffer += raw_bytes.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                return
                            try:
                                chunk = json.loads(data)
                                text = chunk.get("text") or chunk.get("token") or ""
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                continue
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"Error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise AIServiceError(f"Connection error: {str(e)}")
        except Exception as e:
            raise AIServiceError(f"Error: {str(e)}")


# ---------------------------------------------------------------------------
# Mock responses
# ---------------------------------------------------------------------------

def _generate_mock_response(prompt: str, context: Dict[str, Any]) -> str:
    num_images = len(context.get("images", []))
    num_notes = len(context.get("notes", []))
    patient = context.get("patient", {})
    has_history = len(context.get("conversation_history", [])) > 0

    parts = ["## Analysis Summary\n"]

    if patient.get("age") or patient.get("sex"):
        parts.append(f"**Patient:** {patient.get('age', '?')} y/o {patient.get('sex', 'Unknown')}\n\n")

    if has_history:
        parts.append("I have reviewed our previous conversation context. ")

    if num_images > 0:
        has_actual = any(img.get("image_base64") for img in context.get("images", []))
        parts.append(f"I have analyzed {num_images} imaging study/studies")
        if has_actual:
            parts.append(" (with image data)")
        parts.append(". ")
    if num_notes > 0:
        parts.append(f"I have reviewed {num_notes} clinical note(s). ")

    parts.append("\n\n")

    prompt_lower = prompt.lower()

    if "nodule" in prompt_lower or "mass" in prompt_lower:
        parts.append("""### Findings

**Primary Observation:** A pulmonary nodule is identified in the region of interest.

**Characteristics:**
- Location: Right lower lobe (RLL)
- Size: Appears to be in the 6-8mm range based on available imaging
- Margins: Partially spiculated borders noted

### Recommendations

1. **Short-term follow-up:** Consider repeat CT in 3-6 months
2. **Clinical correlation:** Correlate with patient symptoms and risk factors

*Note: This analysis is provided as decision support.*
""")
    elif "compare" in prompt_lower or "progression" in prompt_lower or "change" in prompt_lower:
        parts.append("""### Comparative Analysis

**Interval Changes:**
- No significant interval change in the primary finding
- Cardiac silhouette remains within normal limits
- No new infiltrates or consolidations identified

**Stability Assessment:**
- The findings appear radiologically stable
- Continued surveillance per standard protocols is appropriate

*Note: This comparative analysis is provided as decision support.*
""")
    else:
        parts.append("""### General Assessment

**Key Observations:**
1. The imaging studies have been reviewed systematically
2. Relevant anatomical structures are within normal limits
3. No acute pathology is identified

**Impression:**
- No acute cardiopulmonary abnormality
- Routine findings consistent with patient demographics

### Recommendations

1. Clinical correlation with presenting symptoms
2. Follow-up as clinically indicated

*Note: This analysis serves as decision support.*
""")

    return "".join(parts)


# ---------------------------------------------------------------------------
# Service status
# ---------------------------------------------------------------------------

def get_ai_service_status() -> Dict[str, Any]:
    mode = _get_mode()
    if mode == "debug":
        return {"configured": True, "mode": "debug", "description": "Debug mode — payloads logged to terminal, no AI calls made"}
    if mode == "runpod":
        return {"configured": True, "mode": "runpod", "endpoint_id": settings.RUNPOD_ENDPOINT_ID, "has_api_key": bool(settings.RUNPOD_API_KEY)}
    elif mode == "local":
        return {"configured": True, "mode": "live", "api_url": settings.MEDGEMMA_API_URL, "has_api_key": bool(settings.MEDGEMMA_API_KEY)}
    else:
        return {"configured": False, "mode": "mock", "api_url": "Not configured (using mock responses)", "has_api_key": False}

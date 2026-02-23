"""
MedGemma Model Server
=====================
Loads google/medgemma-4b-it with the sh3hryarkhan/MedGemma-TI LoRA adapter
in 4-bit quantization and serves it on localhost:8080.

Designed to match the request/response contract expected by ai_service.py.

Usage:
    python model_server.py
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from threading import Thread

import torch
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_MODEL_ID = os.getenv("BASE_MODEL_ID", "google/medgemma-4b-it")
LORA_ADAPTER_ID = os.getenv("LORA_ADAPTER_ID", "sh3hryarkhan/MedGemma-TI")
HOST = os.getenv("MODEL_SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("MODEL_SERVER_PORT", "8080"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger("model_server")

# ---------------------------------------------------------------------------
# Global model / tokenizer (populated at startup)
# ---------------------------------------------------------------------------
model = None
tokenizer = None
device = None
load_time_seconds: float = 0.0


def load_model():
    """Load the base model in 4-bit, merge the LoRA adapter, and warm up."""
    global model, tokenizer, device, load_time_seconds

    t0 = time.time()
    log.info("Loading tokenizer from %s ...", BASE_MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    log.info("Loading base model in 4-bit quantization ...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        dtype=torch.bfloat16,
    )

    log.info("Merging LoRA adapter from %s ...", LORA_ADAPTER_ID)
    model = PeftModel.from_pretrained(model, LORA_ADAPTER_ID)

    device = next(model.parameters()).device
    log.info("Model loaded on %s", device)

    # Warm-up generation
    log.info("Warming up with a test generation ...")
    warmup_ids = tokenizer("Hello", return_tensors="pt").input_ids.to(device)
    with torch.no_grad():
        model.generate(warmup_ids, max_new_tokens=5)

    load_time_seconds = round(time.time() - t0, 1)
    log.info("Model ready in %.1fs", load_time_seconds)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield

app = FastAPI(title="MedGemma Model Server", lifespan=lifespan)


def _build_messages(system_prompt: str, user_prompt: str) -> list[dict]:
    """Build a chat-style message list for the tokenizer."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _vram_info() -> dict:
    """Return VRAM usage for the first CUDA device, if available."""
    if not torch.cuda.is_available():
        return {"device": "cpu"}
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    return {
        "device": torch.cuda.get_device_name(0),
        "vram_allocated_gb": round(allocated, 2),
        "vram_reserved_gb": round(reserved, 2),
        "vram_total_gb": round(total, 2),
    }


# ---- Health endpoint -----------------------------------------------------

@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok" if model is not None else "loading",
        "base_model": BASE_MODEL_ID,
        "lora_adapter": LORA_ADAPTER_ID,
        "load_time_seconds": load_time_seconds,
        "gpu": _vram_info(),
    })


# ---- Generate endpoint ---------------------------------------------------

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()

    prompt: str = body.get("prompt", "")
    system_prompt: str = body.get("system_prompt", "")
    temperature: float = body.get("temperature", 0.2)
    max_tokens: int = body.get("max_tokens", 2048)
    stream: bool = body.get("stream", False)

    messages = _build_messages(system_prompt, prompt)
    encoded = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    )
    input_ids = encoded["input_ids"].to(device)

    gen_kwargs = {
        "input_ids": input_ids,
        "max_new_tokens": max_tokens,
        "do_sample": temperature > 0,
        "temperature": temperature if temperature > 0 else None,
        "top_p": 0.9 if temperature > 0 else None,
        "repetition_penalty": 1.1,
    }

    if stream:
        return _stream_response(input_ids, gen_kwargs)
    else:
        return await _full_response(input_ids, gen_kwargs)


async def _full_response(input_ids, gen_kwargs):
    """Generate the complete response and return it as JSON."""
    with torch.no_grad():
        output_ids = model.generate(**gen_kwargs)

    # Slice off the input tokens to get only the new generation
    new_tokens = output_ids[0, input_ids.shape[-1]:]
    text = tokenizer.decode(new_tokens, skip_special_tokens=True)

    return JSONResponse({"text": text, "done": True})


_STREAM_DONE = object()  # sentinel to signal end of iteration


def _next_token(streamer):
    """Wrapper around next() that returns a sentinel instead of raising
    StopIteration, which cannot propagate through asyncio Futures."""
    try:
        return next(streamer)
    except StopIteration:
        return _STREAM_DONE


def _stream_response(input_ids, gen_kwargs):
    """Return a Server-Sent Events stream of generated tokens."""

    streamer = TextIteratorStreamer(
        tokenizer, skip_prompt=True, skip_special_tokens=True
    )
    gen_kwargs["streamer"] = streamer

    # Run generation in a background thread so we can stream tokens out
    thread = Thread(target=_generate_in_thread, args=(gen_kwargs,))
    thread.start()

    async def event_generator():
        loop = asyncio.get_event_loop()
        try:
            while True:
                token_text = await loop.run_in_executor(
                    None, _next_token, streamer
                )
                if token_text is _STREAM_DONE:
                    break
                if token_text:
                    yield f"data: {json.dumps({'text': token_text})}\n\n"
            # Signal completion
            yield f"data: {json.dumps({'done': True})}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            thread.join(timeout=30)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _generate_in_thread(gen_kwargs):
    """Wrapper so we can catch and log generation errors in the thread."""
    try:
        with torch.no_grad():
            model.generate(**gen_kwargs)
    except Exception:
        log.exception("Error during generation")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "model_server:app",
        host=HOST,
        port=PORT,
        log_level="info",
        workers=1,  # single worker — one model in VRAM
    )


import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

import sys
sys.path.append("..")

# ── Aegis Bridge config ──────────────────────────────────────────────────────

BRIDGE_URL = "http://127.0.0.1:7523"
bridge_enabled: bool = True

app = FastAPI()

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon demo, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    messages: List[dict]  # Format: [{"role": "user", "content": "..."}]


# ── Aegis Bridge helper ──────────────────────────────────────────────────────

async def analyze_via_bridge(text: str) -> dict:
    """
    Run text through the Aegis Bridge: single /classify call.
    Falls back to classify_safe on any network/bridge error so chat is never blocked.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            cls_resp = await client.post(f"{BRIDGE_URL}/classify", json={"text": text})
            cls_resp.raise_for_status()
            cls_data = cls_resp.json()

            tool_name = cls_data.get("tool", "request_permission")
            arguments = cls_data.get("arguments", {})
            confidence = cls_data.get("confidence", 0.0)
            classify_time = cls_data.get("time_ms", 0)

            return {
                "success": True,
                "classification": tool_name,
                "reason": arguments.get("reason", ""),
                "pii_types": arguments.get("types", ""),  # only populated for flag_pii
                "confidence": confidence,
                "summary": "",  # No separate summary stage anymore; field kept for FE compat
                "execution_time_ms": classify_time,
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "classification": "classify_safe",
            "reason": "Bridge unreachable — proceeding without classification",
            "confidence": 0.0,
            "pii_types": "",
            "summary": "",
            "execution_time_ms": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "classification": "classify_safe",
            "reason": f"Bridge error: {str(e)}",
            "confidence": 0.0,
            "pii_types": "",
            "summary": "",
            "execution_time_ms": 0,
        }


# ── Chat endpoint ────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    msgs = request.messages
    last_msg = msgs[-1]['content']

    async def event_generator():
        sanitized_msg = last_msg

        # Real Aegis Bridge classification (when enabled)
        if bridge_enabled:
            analysis = await analyze_via_bridge(last_msg)
            verdict = analysis["classification"]

            if verdict == "block_transfer":
                yield "🔴 **TRANSFER BLOCKED** — Aegis DataGuard\n\n"
                yield f"**Reason**: {analysis['reason']}\n\n"
                yield "*This content was NOT sent to any cloud service.*"
                return  # Hard stop — do not call Gemini

            elif verdict == "flag_pii":
                pii_types = analysis.get("pii_types", "")
                yield "⚠️ **PII Detected** — redacting before cloud transfer"
                if pii_types:
                    yield f" *(Types: {pii_types})*"
                yield "\n\n"

            elif verdict == "request_permission":
                yield f"⚠️ **Review Required** — {analysis['reason']}\n\n"

        # Gemini Cloud call
        try:
            from google import genai
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            yield "\n---\n**☁️ Gemini 2.5 Flash**:\n"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=sanitized_msg,
            )
            yield response.text
        except Exception as e:
            yield f"\n\n❌ **Cloud Error**: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain")


# ── Title endpoint ───────────────────────────────────────────────────────────

class TitleRequest(BaseModel):
    message: str

@app.post("/api/title")
async def generate_title(request: TitleRequest):
    """Generate a short conversation title using Gemini."""
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Generate a short, descriptive title (4-6 words max, no quotes, no punctuation at the end) for a conversation that starts with this message: {request.message[:300]}"
        )
        title = response.text.strip().strip('"\'').strip()
        return {"title": title}
    except Exception as e:
        return {"title": None, "error": str(e)}


# ── Aegis Bridge proxy endpoints ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str
    filename: str = ""

@app.post("/api/analyze")
async def analyze_endpoint(request: AnalyzeRequest):
    """Analyze file text through the Aegis Bridge. Called by frontend on file upload."""
    if not bridge_enabled:
        return {
            "success": False,
            "classification": "classify_safe",
            "reason": "Bridge is disabled",
            "confidence": 0.0,
            "pii_types": "",
            "summary": "",
            "execution_time_ms": 0,
            "filename": request.filename,
        }
    result = await analyze_via_bridge(request.text)
    result["filename"] = request.filename
    return result

@app.get("/api/bridge/health")
async def bridge_health():
    """
    Proxy the Aegis Bridge /health endpoint.
    Always returns HTTP 200; 'status' field indicates bridge reachability.
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{BRIDGE_URL}/health")
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status", "ok"),
                "backend": data.get("backend", "unknown"),
                "model": data.get("model", "unknown"),
                "bridge_enabled": bridge_enabled,
            }
    except:
        return {
            "status": "unreachable",
            "backend": "none",
            "model": "none",
            "bridge_enabled": bridge_enabled,
        }

@app.post("/api/bridge/toggle")
async def bridge_toggle():
    """Flip the bridge_enabled flag. Returns new state."""
    global bridge_enabled
    bridge_enabled = not bridge_enabled
    return {"bridge_enabled": bridge_enabled}


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "system": "Aegis Local Privacy Layer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Import our core logic (we will move/refactor aegis.py slightly to be importable if needed, 
# or just import specific functions if they exist. For now, we scaffold.)
import sys
sys.path.append("..") 
# Assuming aegis.py has a class or function we can use. 
# If not, we'll implementing the logic here for the demo.

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
    messages: List[dict] # Format: [{"role": "user", "content": "..."}]
    
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import asyncio

# ... (other imports)

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Simulates streaming response for the demo.
    """
    msgs = request.messages
    last_msg = msgs[-1]['content']
    
    # --- AEGIS LOGIC START ---
    
    async def event_generator():
        # 1. Simulate Local Analysis (SmolLM2 + FunctionGemma)
        # In a real deployment, we would call `aegis.analyze(last_msg)` here.
        yield "🛡️ **Aegis Local Security Layer**\n"
        yield "Scanning content with FunctionGemma-270m..."
        await asyncio.sleep(0.5)
        
        pii_detected = []
        is_blocked = False
        
        if "secret" in last_msg.lower() or "password" in last_msg.lower() or "key" in last_msg.lower():
            is_blocked = True
            yield "\n\n🔴 **CRITICAL ALERT**: Secrets detected!\n"
            yield f"• Blocked reasoning: Found keyword 'password/secret'.\n"
            yield "• Action: **TRANSFER DENIED**.\n"
            return

        if "@" in last_msg or "email" in last_msg.lower():
            pii_detected = ["email"]
            yield "\n\n⚠️ **PII Detected**: Found potential email addresses.\n"
            yield "• Action: Redacting locally before cloud transfer...\n"
            await asyncio.sleep(0.8)
            # Redact
            sanitized_msg = last_msg.replace("@", "[REDACTED_AT]")
            yield f"• Sanitized: `{sanitized_msg[:20]}...`\n"
        else:
            yield "\n\n✅ **Content Safe**.\n"
            yield "• Action: Authorizing transfer to Gemini Cloud...\n"
            sanitized_msg = last_msg

        # 2. REAL Cloud Call (Gemini)
        try:
            from google import genai
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            yield "\n---\n**☁️ Gemini 2.5 Flash**:\n"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=sanitized_msg
            )
            yield response.text
        except Exception as e:
            yield f"\n\n❌ **Cloud Error**: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/health")
def health_check():
    return {"status": "ok", "system": "Aegis Local Privacy Layer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

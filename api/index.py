import os
import sys
import json
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Ensure current directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from ai import generate_answer
from image_service import generate_and_save_image, refine_image_prompt

app = FastAPI(title="Nexora AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: Optional[str] = None
    messages: Optional[List[Any]] = None

@app.get("/health")
def health():
    return {"status": "running"}

@app.get("/api/health")
def api_health():
    return {"status": "running", "service": "Nexora AI Serverless"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        payload = request.messages if request.messages else request.message
        answer = await generate_answer(payload)
        return {"answer": answer}
    except Exception as e:
        print(f"[Nexora Error] {e}")
        raise HTTPException(
            status_code=502,
            detail="AI service is temporarily unavailable."
        )

# Storage for generated images
if os.environ.get("VERCEL"):
    DATA_DIR = "/tmp/nexora_data"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GENERATED_IMAGES_DIR = os.path.join(DATA_DIR, "generated_images")
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

@app.get("/api/images/{filename}")
async def get_generated_image(filename: str):
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(GENERATED_IMAGES_DIR, clean_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/jpeg")

@app.get("/api/images/{filename}/download")
async def download_generated_image(filename: str):
    clean_filename = os.path.basename(filename)
    file_path = os.path.join(GENERATED_IMAGES_DIR, clean_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(
        file_path,
        media_type="image/jpeg",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )

class ImageGeneratePayload(BaseModel):
    prompt: str
    width: Optional[int] = None
    height: Optional[int] = None

@app.post("/api/generate-image")
async def generate_image_route(payload: ImageGeneratePayload):
    try:
        refined = await refine_image_prompt(payload.prompt)
        res = await generate_and_save_image(refined, width=payload.width, height=payload.height)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AlertSubscriptionRequest(BaseModel):
    email: str
    target_exam: str

class TestAlertRequest(BaseModel):
    email: str

subscriptions_db = []

@app.post("/api/alerts/subscribe")
def subscribe_alert(sub: AlertSubscriptionRequest):
    sub_data = {
        "email": sub.email,
        "target_exam": sub.target_exam,
        "created_at": "Just now",
        "active": True
    }
    subscriptions_db.append(sub_data)
    return {
        "success": True,
        "message": f"Successfully activated alerts for {sub.email} on {sub.target_exam}!",
        "subscription": sub_data
    }

@app.post("/api/alerts/send-test")
def send_test_alert(req: TestAlertRequest):
    alert_payload = {
        "to_email": req.email,
        "subject": "📢 [Nexora AI Alert] Official Syllabus & Schedule Update Notice",
        "preview": "Commission has published the revised syllabus blueprint and upcoming calendar stages. Log in to your Nexora AI platform to review stage-by-stage changes.",
        "status": "Delivered to inbox"
    }
    return {
        "success": True,
        "message": f"Alert email simulated and sent to {req.email}!",
        "details": alert_payload
    }

SESSIONS_FILE = os.path.join(DATA_DIR, "chat_sessions.json")

def load_server_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return []
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return []

def save_server_sessions(sessions):
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        return False

@app.get("/api/sessions")
def get_sessions():
    return {"sessions": load_server_sessions()}

class SessionsPayload(BaseModel):
    sessions: List[Any]

@app.post("/api/sessions")
def save_sessions(payload: SessionsPayload):
    new_sessions = payload.sessions or []
    existing = load_server_sessions()
    existing_map = {s.get("id"): s for s in existing if isinstance(s, dict) and s.get("id")}
    for s in new_sessions:
        if isinstance(s, dict) and s.get("id"):
            existing_map[s["id"]] = s
    merged = list(existing_map.values())
    merged.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    save_server_sessions(merged)
    return {"success": True, "count": len(merged), "sessions": merged}

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    existing = load_server_sessions()
    filtered = [s for s in existing if isinstance(s, dict) and s.get("id") != session_id]
    save_server_sessions(filtered)
    return {"success": True, "count": len(filtered)}

@app.delete("/api/sessions")
def clear_all_sessions():
    save_server_sessions([])
    return {"success": True, "count": 0}

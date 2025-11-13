# api.py
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

from MainChef.CoffeeAgent.agent import CoffeeShopAgent
from utils_for_api import call_agent_async

from CRUD.menuCrud import fetch_menu_items
from Cache.MenuCache import menu_cache

from DB_Tools.menustateTool import get_menu_state

from tts_stt_api.tts_helper import tts_async, tts_save_to_file

load_dotenv()

APP_NAME = "Coffee Shop Agent"

app = FastAPI(title=APP_NAME)

# (Optional) allow your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- ADK infra (singletons) ----
session_service = InMemorySessionService()
runner = Runner(agent=CoffeeShopAgent, app_name=APP_NAME, session_service=session_service)

# per-user map -> session_id (simple in-RAM)
user_sessions: dict[str, str] = {}
_user_sessions_lock = asyncio.Lock()

# ---- Initial state ----
INITIAL_STATE = {
    "customer_name" : None,
    "customer_id": None,
    "phone_number" : None,
    "mood" : None,
    "age_group"  : None,
    "order_id" : None,
}

# ---- Models ----
class AgentRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    restart: bool = False
    session_id: Optional[str] = None
    speak: bool = False  # <-- only toggle
    voice: str = "en-US-JennyNeural"  # <-- voice selection

class AgentResponse(BaseModel):
    response: str
    session_id: str
    audio_base64: Optional[str] = None
    audio_mime: Optional[str] = None
    
# ---- Lifespan: load menu once ----
@app.on_event("startup")
async def _startup():
    items = await fetch_menu_items()
    menu_cache.load(items)
    print(f"Menu loaded: {len(items)} items")

@app.get("/health")
async def health():
    return {"ok": True}

# ---- Helpers ----
async def _get_or_create_session(user_id: str, session_id: Optional[str], restart: bool) -> str:
    async with _user_sessions_lock:
        # explicit session_id from client wins unless restart
        if restart or (not session_id and user_id not in user_sessions):
            new = session_service.create_session(
                app_name=APP_NAME, user_id=user_id, state=INITIAL_STATE.copy()
            )
            user_sessions[user_id] = new.id
            return new.id

        if restart and user_id in user_sessions:
            # create fresh session even if one exists
            new = session_service.create_session(
                app_name=APP_NAME, user_id=user_id, state=INITIAL_STATE.copy()
            )
            user_sessions[user_id] = new.id
            return new.id

        # reuse existing
        if session_id:
            # client pinned a session; trust it and track by user
            user_sessions[user_id] = session_id
            return session_id

        return user_sessions[user_id]


# ---- Main endpoint ----
@app.post("/agent/", response_model=AgentResponse)
async def interact_with_agent(req: AgentRequest):
    sid = await _get_or_create_session(req.user_id, req.session_id, req.restart)

    try:
        reply_text = await call_agent_async(runner, req.user_id, sid, req.text)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"agent_error: {e!s}"})


    result = {"response": reply_text or "", "session_id": sid}

    if req.speak:
        try:
            audio_b64, mime = await tts_async(reply_text or "", req.voice)
            result.update({"audio_base64": audio_b64, "audio_mime": mime})
        except Exception:
            # If TTS fails, still return text
            result.update({"audio_base64": None, "audio_mime": None})

    return JSONResponse(result)



@app.post("/generate-voice/")
async def generate_voice(text: str, filename: str, voice: str = "en-US-JennyNeural"):
    """
    Generate voice from text and save to Voices folder.
    
    Args:
        text: The text to convert to speech
        filename: The filename to save as (without extension)
        voice: The voice to use (default: en-US-JennyNeural)
    
    Returns:
        JSON with success status and file path
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if not filename.strip():
            raise HTTPException(status_code=400, detail="Filename cannot be empty")
        
        # Generate and save voice
        filepath = await tts_save_to_file(text, filename, voice)
        
        return JSONResponse({
            "success": True,
            "message": "Voice generated successfully",
            "filepath": filepath,
            "filename": f"{filename}.mp3",
            "voice": voice
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate voice: {str(e)}")


@app.get("/menu/index/{session_id}", response_class=JSONResponse)
async def get_menu_index(session_id: str):
    indexx = await get_menu_state(session_id)
    
    return JSONResponse({"index": indexx})

from fastapi import FastAPI, Request, Body
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from google.adk.sessions import InMemorySessionService
from dotenv import load_dotenv
from MainChef.agent import MainChef  
from google.adk.runners import Runner
from utils_for_api import  call_agent_async
from session_store import user_sessions


app = FastAPI()

load_dotenv()

APP_NAME = "Main Chef MoodScope"

session_service = InMemorySessionService()
runner = Runner(
    agent=MainChef,
    app_name=APP_NAME,
    session_service=session_service,
)

initial_state = {
    "username" : "",
    "customer_id": None,
    "telepone_number" : "",
    "address" : "",
    "mood" : "",
    "age"  : None,
    "table" : "",
    "order_id" : None,
    "order" : [],
    "discount" : None,
    "special_discount" : {},
    "type" : "",
    "amount" : 0,
}

session_id = ""
# --- Session and Request schema ---
class AgentRequest(BaseModel):
    user_id: str
    text: str
    restart: bool = False
    
 
    
@app.get("/")
async def test():
    return JSONResponse({
        "status" : "App is woking"
    })


@app.post("/agent/")
async def interact_with_agent(req: AgentRequest):
    # Create or retrieve session
    if req.restart or req.user_id not in user_sessions:
        new_session = session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            state=initial_state.copy()
        )
        session_id = new_session.id
        user_sessions[req.user_id] = session_id
    else:
        session_id = user_sessions[req.user_id]

    # Get agent response
    reply = await call_agent_async(runner, req.user_id, session_id, req.text)

    return JSONResponse({
        "response": reply,
        "session_id": session_id
    })


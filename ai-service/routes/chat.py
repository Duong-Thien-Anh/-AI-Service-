 # routes/chat.py
from fastapi import APIRouter, Depends , HTTPException
from datetime import datetime
from models.schemas import ChatRequest, ChatResponse, HistoryResponse, HistoryMessage
from services.groq import create_chat_session, send_message
from middleware.auth import require_auth

router = APIRouter(prefix="/chat", tags=["Chat"])

# ── In-memory session store ──────────────────────────
# { user_id: { "session": GeminiChat, "history": [], "ticket_id": str } }
chat_sessions: dict = {}
ticket_counter = 1000

def get_or_create_session(user_id: str, user_name: str) -> dict:
    """Get existing session or create a new one for this user"""
    global ticket_counter
    if user_id not in chat_sessions:
        ticket_counter += 1
        chat_sessions[user_id] = {
            "session": create_chat_session(),
            "history": [],
            "ticket_id": f"TKT-{ticket_counter}",
            "created_at": datetime.utcnow().isoformat(),
            "user_name": user_name,
        }
        print(f"New ticket {chat_sessions[user_id]['ticket_id']} for {user_name}")
    return chat_sessions[user_id]


@router.post("/", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    user: dict = Depends(require_auth)   # ← this line protects the route
):
    """
    Send a message to Aria (the support AI).
    Requires a valid JWT in the Authorization header.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    data = get_or_create_session(user["id"], user["name"])

    # Send to Gemini
    reply = await send_message(data["session"], body.message)

    # Save to history
    now = datetime.utcnow().isoformat()
    data["history"].append({"role": "user",  "text": body.message, "timestamp": now})
    data["history"].append({"role": "aria",  "text": reply,        "timestamp": now})

    if len(data["history"]) > 10:
        data["history"] = data["history"][-10:]

    return ChatResponse(
        reply=reply,
        ticket_id=data["ticket_id"],
        message_count=len(data["history"]) // 2
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(user: dict = Depends(require_auth)):
    """Get full chat history for the logged-in user"""
    data = chat_sessions.get(user["id"])
    if not data:
        return HistoryResponse(ticket_id=None, history=[], message_count=0)

    return HistoryResponse(
        ticket_id=data["ticket_id"],
        history=[HistoryMessage(**m) for m in data["history"]],
        message_count=len(data["history"]) // 2
    )


@router.delete("/history")
async def clear_history(user: dict = Depends(require_auth)):
    """Close current session - next message starts a fresh ticket"""
    chat_sessions.pop(user["id"], None)
    return {"message": "Session closed. New ticket opens on next message."}

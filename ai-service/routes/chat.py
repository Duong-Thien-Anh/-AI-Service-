from datetime import datetime, timezone

import anyio
from fastapi import APIRouter, Depends, HTTPException

from config import settings
from database import (
    add_message,
    close_open_conversation,
    get_latest_conversation_history,
    get_or_create_open_conversation_with_context,
)
from middleware.auth import require_auth
from models.schemas import ChatRequest, ChatResponse, HistoryMessage, HistoryResponse
from services.groq import create_chat_session, send_message


router = APIRouter(prefix="/chat", tags=["Chat"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_llm_role(role: str) -> str:
    if role == "aria":
        return "assistant"
    return "user"


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest, user: dict = Depends(require_auth)):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    convo = await anyio.to_thread.run_sync(
        get_or_create_open_conversation_with_context,
        user["id"],
        user.get("name"),
        settings.context_message_limit,
    )

    session = create_chat_session()
    for m in convo["context_messages"]:
        session["messages"].append(
            {"role": _to_llm_role(m["role"]), "content": m["text"]}
        )

    now = _now_iso()
    await anyio.to_thread.run_sync(
        add_message, convo["conversation_id"], "user", body.message, now
    )

    reply = await send_message(session, body.message)

    await anyio.to_thread.run_sync(
        add_message, convo["conversation_id"], "aria", reply, now
    )

    total_messages = int(convo["message_count"]) + 2
    return ChatResponse(
        reply=reply,
        ticket_id=convo["ticket_id"],
        message_count=total_messages // 2,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history(user: dict = Depends(require_auth)):
    history = await anyio.to_thread.run_sync(get_latest_conversation_history, user["id"])
    if not history:
        return HistoryResponse(ticket_id=None, history=[], message_count=0)

    messages = [HistoryMessage(**m) for m in history["messages"]]
    return HistoryResponse(
        ticket_id=history["ticket_id"],
        history=messages,
        message_count=len(messages) // 2,
    )


@router.delete("/history")
async def clear_history(user: dict = Depends(require_auth)):
    await anyio.to_thread.run_sync(close_open_conversation, user["id"])
    return {"message": "Session closed. New ticket opens on next message."}


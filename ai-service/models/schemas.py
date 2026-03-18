from pydantic import BaseModel
from typing import Optional

# ── What the client SENDS to /chat ──────────────────
class ChatRequest(BaseModel):
    message: str                  # the user's message

# ── What /chat SENDS BACK ───────────────────────────
class ChatResponse(BaseModel):
    reply: str                    # Aria's response
    ticket_id: str                # e.g. "TKT-1001"
    message_count: int            # how many turns so far

# ── A single message in history ─────────────────────
class HistoryMessage(BaseModel):
    role: str                     # "user" or "aria"
    text: str
    timestamp: str

# ── What /history SENDS BACK ────────────────────────
class HistoryResponse(BaseModel):
    ticket_id: Optional[str]
    history: list[HistoryMessage]
    message_count: int

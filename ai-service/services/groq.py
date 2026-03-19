import anyio
from groq import Groq

from config import settings


SYSTEM_PROMPT = """You are Aria, a friendly AI customer support agent for TechNova —
a software company that makes project management tools and developer APIs.

TechNova Products:
- TechNova Tasks: project management (Free / Pro $12/mo / Business $49/mo)
- TechNova Drive: cloud storage, 15GB free, 1TB at $8/mo
- TechNova API: 10,000 free requests/mo, then $0.001/request

Common solutions:
- Password reset: Login page → Forgot Password → check email
- Billing/refunds: within 14 days of charge
- API errors: check api-key header, check rate limits

Be warm, concise, and solution-focused. Keep replies to 2-4 sentences."""


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "Missing GROQ_API_KEY. Set it via env var or .env before starting the service."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def create_chat_session() -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
    }


async def send_message(chat_session: dict, message: str) -> str:
    chat_session["messages"].append({"role": "user", "content": message})
    client = _get_client()

    def _call() -> str:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=chat_session["messages"],
            temperature=0.2,
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty response.")
        return content

    content = await anyio.to_thread.run_sync(_call)
    chat_session["messages"].append({"role": "assistant", "content": content})
    return content


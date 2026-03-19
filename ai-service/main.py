 # main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from config import settings
from database import init_db

app = FastAPI(
    title="TechNova AI Service",
    description="Customer support AI powered by Groq",
    version="1.0.0"
)

# ── CORS — allow browser requests ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # in production: specify your domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routes ──────────────────────────────────
app.include_router(chat_router)


@app.on_event("startup")
def _startup():
    from database import startup_db
    startup_db()

# ── Health check ─────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "service": "ai-service",
        "status": "healthy",
        "model": settings.groq_model,
        "auth_mock_mode": settings.auth_mock_mode,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

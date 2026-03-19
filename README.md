# -AI-Service-

FastAPI service for a chatbot (Groq).

## Quick start (Windows)

- Create `D:\\Projects\\-AI-Service-\\ai-service\\.env` from `.env.example` and set `GROQ_API_KEY`
- Run with Docker: `docker compose up --build` (starts Postgres + API on `http://localhost:8000`)

## Security note

If you ever committed a real API key into git history, rotate/revoke it ASAP.

## CI/CD (GitHub Actions)

- CI workflow: `.github/workflows/ci.yml` (install deps + `py_compile`)
- CD workflow: `.github/workflows/docker-publish.yml` (builds/pushes to GHCR on pushes to `main`)

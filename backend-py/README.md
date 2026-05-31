# Xiaoman Python backend

This is the current main backend for Xiaoman. It runs FastAPI + WebSocket from `main.py` on port `18789`.

## Local setup

```powershell
cd D:\Alice\Projects\xiaoman\backend-py
C:\Users\86176\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 18789
```

The verified local runtime is Python 3.12.13 from the bundled Codex runtime. The system Python launcher on this machine may not point at an installed Python.

## Environment

Copy `backend-py/.env.example` or set these variables in your shell:

```powershell
$env:XIAOMAN_DATA_DIR="D:\Alice\Projects\xiaoman\backend-py\data"
$env:XIAOMAN_ENABLE_DREAMING_SCHEDULER="false"
$env:LLM_API_KEY="your_api_key_here"
$env:LLM_BASE_URL="https://api.pipellm.ai/openai/v1"
$env:LLM_MODEL="gpt-4o-mini"
$env:XIAOMAN_SECRET_KEY="change-me-before-real-secret-storage"
```

Notes:

- `LLM_API_KEY` is required for real LLM calls. It is no longer stored in `xiaoman.json` or start scripts.
- `XIAOMAN_DATA_DIR` separates local/dev/prod data roots.
- `XIAOMAN_ENABLE_DREAMING_SCHEDULER=false` keeps the background scheduler disabled during development.
- `XIAOMAN_SECRET_KEY` should be changed before storing real L7 secrets.

## Tests

```powershell
cd D:\Alice\Projects\xiaoman\backend-py
.\.venv\Scripts\python.exe -m pytest -q
```

Current verified result: `104 passed, 2 warnings`.

## Docker

The root `docker-compose.yml` now builds this backend.

```powershell
cd D:\Alice\Projects\xiaoman
docker compose up --build
```

Docker mounts `backend-py/data` to `/app/data` and sets `XIAOMAN_DATA_DIR=/app/data`.

## Data boundary

See `backend-py/data/README.md`. In short, `templates/` and `global/` are seed data; `users/`, `sessions*/`, `lancedb/`, `memory/`, and `diary/` are runtime data and must not contain committed real user data.

## Structure

```text
backend-py/
|-- main.py                  # FastAPI / WebSocket entrypoint
|-- requirements.txt         # Python dependencies
|-- xiaoman.json             # non-secret model and product config
|-- xiaoman/paths.py         # centralized data directory resolution
|-- xiaoman/world/           # L1-L8 world system
|-- xiaoman/memory/          # memory, dreaming, LanceDB integration
|-- xiaoman/dialogue/        # dialogue config and prompting
|-- xiaoman/tools/           # local tools
|-- tests/                   # pytest suite
```

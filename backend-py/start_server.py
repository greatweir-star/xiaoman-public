"""Start the Xiaoman FastAPI backend."""

from __future__ import annotations

import os

import uvicorn
from main import app


if __name__ == "__main__":
    if not os.environ.get("LLM_API_KEY"):
        print("[xiaoman] LLM_API_KEY is not set; LLM calls will use local fallbacks or fail closed.")
    uvicorn.run(app, host="0.0.0.0", port=18789)

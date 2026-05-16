# main.py  ← PROJECT ROOT  (not app/main.py — that file is frozen)
# ─────────────────────────────────────────────────────────────────────────────
# Root-level entry point for the SHL Assessment Battery Designer API.
#
# This file re-exports the FastAPI app from app/main.py.
# It does not contain any route definitions or business logic.
#
# Deployment start command:
#   uvicorn main:app --host 0.0.0.0 --port $PORT
#
# Alternative (also works):
#   uvicorn app.main:app --host 0.0.0.0 --port $PORT
# ─────────────────────────────────────────────────────────────────────────────

from app.main import app  # noqa: F401  — re-export the FastAPI instance

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

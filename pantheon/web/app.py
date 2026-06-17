"""FastAPI app serving the Pantheon Web UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pantheon.core.pantheon import Pantheon


STATIC_DIR = Path(__file__).parent / "static"


class AskRequest(BaseModel):
    task: str
    mode: str = "auto"          # "auto" | "role:<name>" | "multi"
    role: Optional[str] = None  # convenience: --role foo → mode = "role:foo"


class AskResponse(BaseModel):
    mode: str
    content: str
    plan: str = ""
    steps: list = []


def create_app(config_path: Optional[str] = None) -> FastAPI:
    """Build the FastAPI app. Pantheon instance is created lazily."""
    app = FastAPI(title="Pantheon Web UI", version="0.1.0")

    _pantheon: Dict[str, Optional[Pantheon]] = {"instance": None}

    def get_pantheon() -> Pantheon:
        if _pantheon["instance"] is None:
            _pantheon["instance"] = Pantheon(config_path=config_path)
        return _pantheon["instance"]

    # Static files (HTML, JS, CSS)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        index_file = STATIC_DIR / "index.html"
        if not index_file.exists():
            return HTMLResponse(
                "<h1>Pantheon Web UI</h1>"
                "<p>Static files missing. Please reinstall the package.</p>",
                status_code=500,
            )
        return HTMLResponse(index_file.read_text(encoding="utf-8"))

    @app.get("/api/roles")
    async def list_roles() -> Dict[str, Any]:
        try:
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        roles = []
        for name in p.list_roles():
            role = p.get_role(name)
            roles.append({
                "name": name,
                "description": getattr(role, "description", ""),
                "model": getattr(role, "model", ""),
            })
        return {"roles": roles}

    @app.post("/api/ask")
    async def ask(req: AskRequest) -> JSONResponse:
        try:
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        mode = req.mode
        if req.role:
            mode = f"role:{req.role}"

        try:
            result = p.ask(req.task, mode=mode)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ask failed: {e}") from e

        # Serialize TaskResult objects
        steps = []
        for s in result.get("steps", []):
            steps.append({
                "role": getattr(s, "role", "?"),
                "content": getattr(s, "content", ""),
                "success": getattr(s, "success", True),
                "error": getattr(s, "error", None),
                "duration_ms": getattr(s, "duration_ms", 0),
            })

        return JSONResponse({
            "mode": result.get("mode", "single"),
            "content": result.get("content", ""),
            "plan": result.get("plan", ""),
            "steps": steps,
        })

    @app.get("/api/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    return app

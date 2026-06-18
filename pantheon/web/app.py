"""FastAPI app serving the Pantheon Web UI."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pantheon.core.pantheon import Pantheon

STATIC_DIR = Path(__file__).parent / "static"


class AskRequest(BaseModel):
    task: str
    mode: str = "auto"          # "auto" | "role:<name>" | "multi"
    role: str | None = None     # convenience: --role foo → mode = "role:foo"
    overrides: dict[str, dict[str, str]] | None = None  # {role_name: {provider, model}}


def create_app(config_path: str | None = None) -> FastAPI:
    """Build the FastAPI app. Pantheon instance is created lazily."""
    app = FastAPI(title="Pantheon Web UI", version="0.1.1")

    _pantheon: dict[str, Pantheon | None] = {"instance": None}

    def get_pantheon() -> Pantheon:
        if _pantheon["instance"] is None:
            _pantheon["instance"] = Pantheon(config_path=config_path)
        return _pantheon["instance"]

    # ----- Static files -----
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

    # ----- Role listing -----
    @app.get("/api/roles")
    async def list_roles() -> dict[str, Any]:
        try:
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        roles = []
        for name in p.list_roles():
            role = p.get_role(name)
            # Resolve provider: check role's llm client type
            llm = getattr(role, "llm", None)
            provider = getattr(llm, "provider", "") or getattr(llm, "name", "") or ""
            if not provider:
                # Fall back to model name hints
                m = (getattr(role, "model", "") or "").lower()
                if "claude" in m:
                    provider = "anthropic"
                elif "gpt" in m or "dall" in m or "image" in m:
                    provider = "openai"
                elif "deepseek" in m:
                    provider = "deepseek"
                elif m in ("none", "", "placeholder"):
                    provider = "none"
            # Special-case: Chronos is a scheduling role (no LLM by design)
            note = ""
            if name == "chronos":
                note = "⏰ scheduling role — handles cron / recurring tasks. No LLM by design."
            roles.append({
                "name": name,
                "description": getattr(role, "description", ""),
                "model": getattr(role, "model", ""),
                "provider": provider,
                "note": note,
            })
        return {"roles": roles}

    # ----- Non-streaming ask (kept for backwards compatibility) -----
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

    # ----- Streaming ask (SSE) -----
    @app.post("/api/ask/stream")
    async def ask_stream(req: AskRequest):
        """
        Server-Sent Events stream. Emits events:

          event: start
          data: {"task": "...", "mode": "..."}

          event: plan
          data: {"plan": "...", "steps": [{"role": "athena", "task": "..."}]}

          event: step_start
          data: {"index": 0, "role": "athena"}

          event: step_done
          data: {"index": 0, "role": "athena", "content": "...", "duration_ms": 2300, "success": true}

          event: step_error
          data: {"index": 0, "role": "athena", "error": "..."}

          event: summary_start
          data: {}

          event: summary_chunk
          data: {"text": "..."}  (incremental)

          event: summary_done
          data: {"content": "..."}

          event: done
          data: {"mode": "single|multi", "content": "..."}

          event: error
          data: {"message": "..."}
        """
        try:
            p = get_pantheon()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        mode = req.mode
        if req.role:
            mode = f"role:{req.role}"

        # Apply UI overrides (settings panel): change model on the role's llm client.
        if req.overrides:
            for role_name, override in req.overrides.items():
                try:
                    role = p.get_role(role_name)
                except Exception:
                    continue
                llm = getattr(role, "llm", None)
                if llm is None:
                    continue
                if "model" in override and override["model"]:
                    try:
                        llm.model = override["model"]
                    except Exception:
                        pass

        async def event_generator():
            # We run Hermes in a thread so the SSE loop stays responsive
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def emit(event: str, data: dict) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, (event, data))

            def run_sync() -> None:
                """Run Hermes dispatch with streaming instrumentation."""
                try:
                    from pantheon.core.base import Task
                    task = Task(content=req.task, mode=mode)
                    # Inject custom step hooks so we can stream
                    hermes = p.hermes
                    original_run = None
                    emit("start", {"task": req.task, "mode": mode})

                    # For multi mode we need to interleave: send step_start/step_done
                    # before/after each role.run. We do this by monkey-patching
                    # Role.run on each registered role temporarily.
                    if mode == "multi" or (mode == "auto" and False):
                        # We can't know in advance if auto will pick multi; we just
                        # treat every step in result["steps"] as a stream event.
                        result = hermes.dispatch(task)
                        emit("plan", {
                            "plan": result.get("plan", ""),
                            "mode": result.get("mode", "single"),
                        })
                        for i, step in enumerate(result.get("steps", [])):
                            role = getattr(step, "role", "?")
                            content = getattr(step, "content", "")
                            success = getattr(step, "success", True)
                            duration = getattr(step, "duration_ms", 0)
                            emit("step_start", {"index": i, "role": role})
                            if success:
                                # For "character" feel, chunk the content
                                # (real streaming would come from the LLM; we simulate).
                                emit("step_chunk", {"index": i, "role": role, "text": content})
                                emit("step_done", {
                                    "index": i, "role": role,
                                    "content": content,
                                    "duration_ms": duration,
                                    "success": True,
                                })
                            else:
                                emit("step_error", {
                                    "index": i, "role": role,
                                    "error": getattr(step, "error", "unknown"),
                                })
                        emit("summary_start", {})
                        emit("summary_chunk", {"text": result.get("content", "")})
                        emit("summary_done", {"content": result.get("content", "")})
                        emit("done", {
                            "mode": result.get("mode", "single"),
                            "content": result.get("content", ""),
                        })
                    else:
                        # Single-role mode: stream the one role's output as the answer.
                        # We can't easily stream mid-LLM with current code, so we send
                        # the content in one chunk but mark it as streaming-friendly.
                        result = hermes.dispatch(task)
                        content = result.get("content", "")
                        emit("step_start", {"index": 0, "role": mode.replace("role:", "") if mode.startswith("role:") else "hermes"})
                        # Chunk the content for typing effect
                        chunk_size = 8
                        for i in range(0, len(content), chunk_size):
                            emit("step_chunk", {"index": 0, "role": "assistant", "text": content[i:i+chunk_size]})
                            # Simulate typing speed (slightly faster than realtime)
                        emit("step_done", {
                            "index": 0, "role": "assistant",
                            "content": content,
                            "duration_ms": 0,
                            "success": True,
                        })
                        emit("done", {"mode": "single", "content": content})

                except Exception as e:
                    emit("error", {"message": str(e)})
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

            # Run the blocking work in a thread
            fut = loop.run_in_executor(None, run_sync)

            # Drain the queue, yielding SSE-formatted lines
            while True:
                item = await queue.get()
                if item is None:
                    break
                event, data = item
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

            # Ensure the executor finished (no exception swallowed)
            try:
                await fut
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # for nginx compat
            },
        )

    # ----- Health -----
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

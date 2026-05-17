"""Receipts — local web app. Track and share what you did with Claude Code.

Run:  pip install -r requirements.txt && python app.py
Then: http://localhost:4830

Reads ~/.claude/projects only. Nothing leaves your machine unless you
explicitly copy a receipt card and paste it somewhere.
"""
from __future__ import annotations

import os
import sys
import time
import threading
from pathlib import Path

# Self-bootstrap: if a local .venv exists, re-exec under it so fastapi and
# uvicorn resolve no matter which interpreter launched this file.
_VENV = Path(__file__).resolve().parent / ".venv"
if (_VENV / "bin" / "python").exists() and not sys.prefix.startswith(str(_VENV)):
    os.execv(str(_VENV / "bin" / "python"), [str(_VENV / "bin" / "python"), __file__, *sys.argv[1:]])

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from engine import all_session_files, parse_session
from analyzer import build_dashboard, build_insights, receipt_dict

APP_DIR = Path(__file__).parent
STATIC = APP_DIR / "static"
PORT = 4830
ACTIVE_WINDOW = 10 * 60  # a session touched within 10 min counts as "running"

app = FastAPI(title="Receipts")


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Make the browser revalidate static assets every load (cheap — returns
    304 when unchanged) so edits to the UI always show up."""
    resp = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

# session-file path -> (mtime, Receipt | None). Only changed files re-parse.
_cache: dict = {}
_lock = threading.Lock()


def refresh() -> None:
    """Re-parse only the session files whose mtime changed since last scan.

    The lock is held only for the quick dict reads/writes — never across the
    slow parse — so /api/dashboard stays responsive even during a cold scan.
    Most-recently-touched files are parsed first, so today's work and any
    running session show up within the first second.
    """
    now = time.time()
    seen = set()
    files = sorted(all_session_files(), key=lambda f: f.stat().st_mtime
                   if f.exists() else 0, reverse=True)
    for f in files:
        ps = str(f)
        seen.add(ps)
        try:
            mt = f.stat().st_mtime
        except OSError:
            continue
        with _lock:
            cached = _cache.get(ps)
        if cached and cached[0] == mt:
            receipt = cached[1]
        else:
            receipt = parse_session(f)  # slow — deliberately outside the lock
            with _lock:
                _cache[ps] = (mt, receipt)
        if receipt:
            receipt.is_active = (now - mt) < ACTIVE_WINDOW
    with _lock:
        for ps in list(_cache):
            if ps not in seen:
                del _cache[ps]


def _refresh_loop() -> None:
    """Background heartbeat — keeps the cache live so running sessions tick."""
    while True:
        try:
            refresh()
        except Exception as e:
            print(f"refresh error: {e}")
        time.sleep(6)


def _receipts() -> list:
    with _lock:
        return [r for _, r in list(_cache.values()) if r]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/dashboard")
def dashboard():
    data = build_dashboard(_receipts())
    data["user"] = os.environ.get("USER") or "you"
    return JSONResponse(data)


@app.get("/api/insights")
def insights(days: int = 30):
    return JSONResponse(build_insights(_receipts(), days))


@app.get("/api/session/{session_id}")
def session(session_id: str):
    for r in _receipts():
        if r.session_id == session_id:
            return JSONResponse(receipt_dict(r))
    return JSONResponse({"error": "not found"}, status_code=404)


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    print(f"Receipts → http://localhost:{PORT}")
    print("  indexing your Claude Code sessions in the background…")
    threading.Thread(target=_refresh_loop, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

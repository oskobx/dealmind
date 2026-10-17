"""Web UI server for DealMind (SPEC §11). Serves web/index.html and streams a run's
events.jsonl to the browser over Server-Sent Events.

    uv run server.py --run <run_id>              # live: follow the file as run.py writes it
    uv run server.py --run <run_id> --speed 3    # replay a recorded run with its timing, 3x faster

replay.py is a thin wrapper around serve(). The page itself is plain HTML + JS in web/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
RUNS = ROOT / "runs"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

SETTINGS: dict[str, object] = {"run_id": None, "speed": 0.0, "max_gap": 5.0}

app = FastAPI(title="DealMind")
app.mount("/web", StaticFiles(directory=str(WEB)), name="web")


def run_dir(run_id: str) -> Path:
    if not RUN_ID_RE.match(run_id or ""):
        raise HTTPException(400, "bad run id")
    path = RUNS / run_id
    if not path.is_dir():
        raise HTTPException(404, f"no run folder runs/{run_id}")
    return path


def newest_run_id() -> str | None:
    candidates = [p for p in RUNS.glob("*/events.jsonl")] if RUNS.is_dir() else []
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime).parent.name


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/config")
def config() -> JSONResponse:
    speed = float(SETTINGS["speed"] or 0)
    return JSONResponse({"run_id": SETTINGS["run_id"], "speed": speed, "max_gap": SETTINGS["max_gap"], "mode": "replay" if speed > 0 else "live"})


@app.get("/api/runs")
def runs() -> JSONResponse:
    out = []
    for p in sorted(RUNS.glob("*/events.jsonl"), key=lambda p: -p.stat().st_mtime):
        out.append({"run_id": p.parent.name, "modified": p.stat().st_mtime, "bytes": p.stat().st_size})
    return JSONResponse(out)


@app.get("/api/run/{run_id}/playbooks")
def playbooks(run_id: str) -> JSONResponse:
    folder = run_dir(run_id) / "playbook"
    rounds = sorted(int(m.group(1)) for p in folder.glob("round_*.md") if (m := re.match(r"round_(\d+)\.md$", p.name)))
    return JSONResponse({"rounds": rounds})


@app.get("/api/run/{run_id}/playbook/{round_no}")
def playbook(run_id: str, round_no: int) -> PlainTextResponse:
    path = run_dir(run_id) / "playbook" / f"round_{round_no:02d}.md"
    if not path.is_file():
        raise HTTPException(404, "no playbook for that round yet")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")


@app.get("/api/run/{run_id}/state")
def state(run_id: str) -> JSONResponse:
    path = run_dir(run_id) / "state.json"
    if not path.is_file():
        raise HTTPException(404, "no state.json yet")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/run/{run_id}/results")
def results(run_id: str) -> JSONResponse:
    path = run_dir(run_id) / "results.json"
    if not path.is_file():
        raise HTTPException(404, "no results.json yet")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


class Tail:
    """Reads complete lines appended to a file since the last read."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = b""

    def read_new(self) -> list[str]:
        if not self.path.is_file():
            return []
        with open(self.path, "rb") as f:
            f.seek(self.offset)
            chunk = f.read()
        self.offset += len(chunk)
        data = self.partial + chunk
        lines = data.split(b"\n")
        self.partial = lines.pop()  # incomplete last line (or empty) waits for the next read
        return [line.decode("utf-8", "replace") for line in lines if line.strip()]


async def event_stream(path: Path, speed: float, max_gap: float, start_after: int, request: Request):
    """Yields SSE frames. speed > 0: paced by the recorded `t` gaps (divided by speed, capped at
    max_gap seconds) and ends at end of file. speed == 0: everything so far at once, then follow."""
    tail = Tail(path)
    seq = 0
    last_t: float | None = None
    idle = 0.0
    while True:
        if await request.is_disconnected():
            return
        lines = tail.read_new()
        for line in lines:
            seq += 1
            if seq <= start_after:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = event.get("t")
            if speed > 0 and isinstance(t, (int, float)) and last_t is not None:
                await asyncio.sleep(min(max(0.0, t - last_t) / speed, max_gap))
                if await request.is_disconnected():
                    return
            if isinstance(t, (int, float)):
                last_t = t
            yield f"id: {seq}\ndata: {line}\n\n"
        if lines:
            idle = 0.0
            continue
        if speed > 0:
            yield f"id: {seq}\ndata: {json.dumps({'kind': 'replay_end', 'events': seq})}\n\n"
            return
        await asyncio.sleep(0.3)
        idle += 0.3
        if idle >= 15:  # keepalive comment so proxies and the browser keep the connection open
            idle = 0.0
            yield ": ping\n\n"


@app.get("/events")
async def events(request: Request, run: str | None = None, speed: float | None = None) -> StreamingResponse:
    run_id = run or SETTINGS["run_id"] or newest_run_id()
    if not run_id:
        raise HTTPException(404, "no runs recorded yet")
    path = run_dir(str(run_id)) / "events.jsonl"
    pace = float(SETTINGS["speed"] or 0) if speed is None else max(0.0, speed)
    last_id = request.headers.get("last-event-id")
    start_after = int(last_id) if last_id and last_id.isdigit() else 0
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    return StreamingResponse(event_stream(path, pace, float(SETTINGS["max_gap"]), start_after, request), media_type="text/event-stream", headers=headers)


def serve(run_id: str | None, speed: float = 0.0, port: int = 8000, host: str = "127.0.0.1", open_browser: bool = True, max_gap: float = 5.0) -> None:
    run_id = run_id or newest_run_id()
    if run_id:
        run_dir(run_id)
    SETTINGS.update(run_id=run_id, speed=speed, max_gap=max_gap)
    url = f"http://{host}:{port}/"
    mode = f"replay x{speed:g}" if speed > 0 else "live (following the file)"
    print(f"DealMind UI: {url}  run={run_id or '(none yet)'}  mode={mode}")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description="DealMind web UI server.")
    parser.add_argument("--run", default=None, help="run id under runs/ (default: the newest)")
    parser.add_argument("--speed", type=float, default=0.0, help="replay speed; 0 = live follow (default)")
    parser.add_argument("--max-gap", type=float, default=5.0, help="replay: longest pause between events, seconds")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = parser.parse_args()
    serve(args.run, args.speed, args.port, args.host, not args.no_open, args.max_gap)


if __name__ == "__main__":
    main()

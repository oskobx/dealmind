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

SETTINGS: dict[str, object] = {"run_id": None, "speed": 0.0, "max_gap": 5.0, "gate": True}
_next_signals: set[asyncio.Event] = set()  # replay streams waiting for the presenter's "Next"
STOP = asyncio.Event()  # set on Ctrl+C so open event streams end at once instead of holding the server


async def pause(seconds: float) -> bool:
    """Sleep up to `seconds`; returns True if the server is shutting down."""
    try:
        await asyncio.wait_for(STOP.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        return False
    return True

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
    return JSONResponse({"run_id": SETTINGS["run_id"], "speed": speed, "max_gap": SETTINGS["max_gap"], "gate": bool(SETTINGS["gate"]), "mode": "replay" if speed > 0 else "live"})


@app.post("/api/next")
async def next_round() -> JSONResponse:
    """Presenter control: release every replay stream waiting at a gate."""
    waiting = list(_next_signals)
    for signal in waiting:
        signal.set()
    return JSONResponse({"released": len(waiting)})


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


def frame(seq: int, line: str) -> str:
    return f"id: {seq}\ndata: {line}\n\n"


async def live_stream(path: Path, start_after: int, request: Request):
    """Live mode: everything written so far at once, then follow the file as run.py appends."""
    tail = Tail(path)
    seq = 0
    idle = 0.0
    while not STOP.is_set() and not await request.is_disconnected():
        lines = tail.read_new()
        for line in lines:
            seq += 1
            if seq > start_after:
                yield frame(seq, line)
        if lines:
            idle = 0.0
            continue
        if await pause(0.3):
            return
        idle += 0.3
        if idle >= 15:  # keepalive comment so proxies and the browser keep the connection open
            idle = 0.0
            yield ": ping\n\n"


def load_events(path: Path) -> list[tuple[str, dict]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append((line, json.loads(line)))
            except json.JSONDecodeError:
                continue
    return out


def up_next(events: list[tuple[str, dict]], index: int) -> dict:
    """What the presenter's next press will play: the next training round, the Ridgeline test, or nothing."""
    for _, ev in events[index:]:
        kind = str(ev.get("kind", ""))
        if kind == "round_start":
            return {"next": "round", "round": ev.get("round")}
        if kind.startswith("ridgeline") or ev.get("supplier") == "ridgeline":
            return {"next": "ridgeline"}
    return {"next": "end"}


async def gate(request: Request, info: dict):
    """Hold the stream until POST /api/next (or the client leaves). Yields the wait notice and pings."""
    signal = asyncio.Event()
    _next_signals.add(signal)
    waited = 0.0
    try:
        yield f"data: {json.dumps({'kind': 'replay_wait', **info})}\n\n"
        while not signal.is_set():
            if STOP.is_set() or await request.is_disconnected():
                return
            try:
                await asyncio.wait_for(signal.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                waited += 0.5
                if waited >= 10:
                    waited = 0.0
                    yield ": ping\n\n"
    finally:
        _next_signals.discard(signal)


async def replay_stream(path: Path, speed: float, max_gap: float, gated: bool, start_after: int, request: Request):
    """Replay mode: paced by the recorded `t` gaps (divided by speed, capped at max_gap seconds).
    With gating, waits for the presenter before the first event and after each round's coach
    updates (the `round_end` event); the last gate releases the Ridgeline test."""
    events = load_events(path)
    last_t: float | None = None
    if gated and start_after == 0:
        async for chunk in gate(request, up_next(events, 0)):
            yield chunk
    for seq, (line, ev) in enumerate(events, start=1):
        if seq <= start_after:
            continue
        if STOP.is_set() or await request.is_disconnected():
            return
        t = ev.get("t")
        if isinstance(t, (int, float)) and last_t is not None:
            if await pause(min(max(0.0, t - last_t) / speed, max_gap)):
                return
        if isinstance(t, (int, float)):
            last_t = t
        yield frame(seq, line)
        if gated and ev.get("kind") == "round_end":
            info = up_next(events, seq)
            if info["next"] != "end":
                async for chunk in gate(request, info):
                    yield chunk
                if STOP.is_set():
                    return
                last_t = None  # no pause for the gap spent waiting
    yield frame(len(events), json.dumps({"kind": "replay_end", "events": len(events)}))


@app.get("/events")
async def events(request: Request, run: str | None = None, speed: float | None = None, gate: int | None = None) -> StreamingResponse:
    run_id = run or SETTINGS["run_id"] or newest_run_id()
    if not run_id:
        raise HTTPException(404, "no runs recorded yet")
    path = run_dir(str(run_id)) / "events.jsonl"
    pace = float(SETTINGS["speed"] or 0) if speed is None else max(0.0, speed)
    gated = bool(SETTINGS["gate"]) if gate is None else bool(gate)
    last_id = request.headers.get("last-event-id")
    start_after = int(last_id) if last_id and last_id.isdigit() else 0
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}
    stream = replay_stream(path, pace, float(SETTINGS["max_gap"]), gated, start_after, request) if pace > 0 else live_stream(path, start_after, request)
    return StreamingResponse(stream, media_type="text/event-stream", headers=headers)


def serve(run_id: str | None, speed: float = 0.0, port: int = 8000, host: str = "127.0.0.1", open_browser: bool = True, max_gap: float = 5.0, gate: bool = True) -> None:
    run_id = run_id or newest_run_id()
    if run_id:
        run_dir(run_id)
    SETTINGS.update(run_id=run_id, speed=speed, max_gap=max_gap, gate=gate and speed > 0)
    url = f"http://{host}:{port}/"
    mode = f"replay x{speed:g}" + (", presenter gated: Next plays each round" if gate else "") if speed > 0 else "live (following the file)"
    print(f"DealMind UI: {url}  run={run_id or '(none yet)'}  mode={mode}")
    if open_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    # Ctrl+C: STOP ends every open event stream at once, so uvicorn has nothing to wait for;
    # timeout_graceful_shutdown is the safety net if a connection still lingers.
    Server(uvicorn.Config(app, host=host, port=port, log_level="warning", timeout_graceful_shutdown=2)).run()


class Server(uvicorn.Server):
    def handle_exit(self, sig: int, frame: object) -> None:
        STOP.set()  # signal handlers run on the main thread, where the event loop lives
        super().handle_exit(sig, frame)


def main() -> None:
    parser = argparse.ArgumentParser(description="DealMind web UI server.")
    parser.add_argument("--run", default=None, help="run id under runs/ (default: the newest)")
    parser.add_argument("--speed", type=float, default=0.0, help="replay speed; 0 = live follow (default)")
    parser.add_argument("--max-gap", type=float, default=5.0, help="replay: longest pause between events, seconds")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--autoplay", action="store_true", help="replay: do not wait for Next between rounds")
    args = parser.parse_args()
    serve(args.run, args.speed, args.port, args.host, not args.no_open, args.max_gap, gate=not args.autoplay)


if __name__ == "__main__":
    main()

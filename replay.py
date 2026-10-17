"""Replay a recorded run in the web UI with its original timing (SPEC §11 safety net).

    uv run replay.py <run_id> --speed 3

Starts server.py in replay mode and opens the browser. The replay waits for the presenter at
the start and after each round's coach updates: "Next round ▶" on the page (or the right-arrow
key) plays the next round, and the last press starts the Ridgeline test. --autoplay removes the
waits. Long pauses between events are capped at --max-gap seconds so a stalled endpoint in the
recording does not stall the demo.
"""

from __future__ import annotations

import argparse

from server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a recorded DealMind run in the web UI.")
    parser.add_argument("run_id", help="folder name under runs/, e.g. demo")
    parser.add_argument("--speed", type=float, default=3.0, help="playback speed multiplier (default 3)")
    parser.add_argument("--max-gap", type=float, default=5.0, help="longest pause between events, seconds")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--autoplay", action="store_true", help="play straight through instead of waiting for Next")
    args = parser.parse_args()
    serve(args.run_id, speed=max(0.1, args.speed), port=args.port, open_browser=not args.no_open, max_gap=args.max_gap, gate=not args.autoplay)


if __name__ == "__main__":
    main()

"""Replay a recorded run in the web UI (SPEC §11 safety net).

    uv run replay.py <run_id>              # default schedule
    uv run replay.py <run_id> --speed 3    # uniform speed instead

Default schedule: rounds 1 and 2 play at recorded speed, rounds 3 and later fast-forward
instantly as one block (chat, coach decisions, chart and room headers land exactly as after the
last round), and the Ridgeline test plays at recorded speed.

The replay waits for the presenter at each gate: before round 1, before round 2, before the
fast-forward ("Rounds 3–5 ⏩") and before Ridgeline ("Ridgeline test ▶"). The button on the page
or the right-arrow key releases it. --autoplay removes the waits. Long pauses between events are
capped at --max-gap seconds so a stalled endpoint in the recording does not stall the demo.
"""

from __future__ import annotations

import argparse

from server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a recorded DealMind run in the web UI.")
    parser.add_argument("run_id", help="folder name under runs/, e.g. demo")
    parser.add_argument("--speed", type=float, default=None, help="uniform playback speed instead of the default schedule")
    parser.add_argument("--max-gap", type=float, default=5.0, help="longest pause between events, seconds")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="do not open the browser")
    parser.add_argument("--autoplay", action="store_true", help="play straight through instead of waiting for Next")
    args = parser.parse_args()
    speed = None if args.speed is None else max(0.1, args.speed)
    serve(args.run_id, speed=speed, port=args.port, open_browser=not args.no_open, max_gap=args.max_gap, gate=not args.autoplay, replay=True)


if __name__ == "__main__":
    main()

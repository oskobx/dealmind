"""Training loop (§8.1). Each round every specialist runs 2 seeded deals in parallel with its
candidate card; the coach keeps or discards the card, picks the next one-knob experiment and
rewrites the dossier and briefing; the playbook is saved as a new version.

    uv run run.py --rounds 5 [--deals 2] [--run-id ID] [--seed 0] [--plain]
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dealmind import config, events, llm
from dealmind.cards import card_from_dict, card_label
from dealmind.coach import coach_supplier, update_general_tactics
from dealmind.deals import deal_seed, random_deal
from dealmind.negotiation import negotiate
from dealmind.playbook import PlaybookState, new_state, save_round
from dealmind.report import Report, build_report


class CallCounter:
    """Counts llm_call events per model per round (the per-model RPM budget, crusoe-skill.md §6)."""

    def __init__(self) -> None:
        self.round = 0
        self.by_round: dict[int, Counter] = {}

    def __call__(self, event: dict) -> None:
        if event.get("kind") == "llm_call":
            self.by_round.setdefault(self.round, Counter())[event["model"]] += 1

    def calls(self, round_no: int) -> dict[str, int]:
        counts = self.by_round.get(round_no, Counter())
        return {config.MODEL_SHORT_NAMES.get(m, m): n for m, n in sorted(counts.items(), key=lambda kv: -kv[1])}

    def line(self, round_no: int) -> str:
        return ", ".join(f"{m} {n}" for m, n in self.calls(round_no).items()) or "none"


def run_negotiation(state: PlaybookState, supplier_key: str, round_no: int, index: int) -> Report:
    s = state.suppliers[supplier_key]
    seed = deal_seed(round_no, supplier_key, index)  # §2.4: fixed per (round, supplier, deal index)
    deal = random_deal(seed)
    result = negotiate(config.SUPPLIERS[supplier_key], deal, card_from_dict(s.candidate), s.briefing, s.believed_type, seed)
    return build_report(result, round_no)


def training_round(state: PlaybookState, round_no: int, deals_per_supplier: int, seed: int, say, counter: CallCounter) -> dict:
    started = time.perf_counter()
    counter.round = round_no
    events.emit("round_start", round=round_no, cards={k: s.candidate for k, s in state.suppliers.items()})
    say(f"\n=== Round {round_no} ===")
    for s in state.suppliers.values():
        say(f"  {s.name:20s} card: {card_label(card_from_dict(s.candidate))}")

    reports: dict[str, list[Report]] = {k: [] for k in state.suppliers}
    tasks = [(k, i) for k in state.suppliers for i in range(deals_per_supplier)]
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        futures = {pool.submit(run_negotiation, state, k, round_no, i): (k, i) for k, i in tasks}
        for future in as_completed(futures):
            k, i = futures[future]
            report = future.result()
            reports[k].append(report)
            f = report.facts
            say(f"  {state.suppliers[k].name:20s} deal {i + 1}: {f['deal']['quantity']:>3d} {f['deal']['product']:6s} -> {f['outcome']:9s} {f['score']:5.1f}")
    negotiation_seconds = time.perf_counter() - started

    say("  coach:")
    keys = list(state.suppliers)
    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        updates = list(pool.map(lambda k: coach_supplier(state, k, round_no, reports[k], random.Random(f"{seed}:{round_no}:{k}")), keys))
    for u in updates:
        state.experiments.append(u.experiment)
        say(f"    {state.suppliers[u.supplier].name:20s} mean {u.score:5.1f}  {u.experiment.result.upper():9s} next: {card_label(u.next_card)} [{u.next_source}]")
        if u.why:
            say(f"      why: {u.why}")
    state.general_tactics = update_general_tactics(state, round_no)
    for tactic in state.general_tactics:
        say(f"    tactic: {tactic}")
    state.round = round_no

    seconds = time.perf_counter() - started
    calls = counter.calls(round_no)
    events.emit("round_end", round=round_no, seconds=round(seconds, 1), negotiation_seconds=round(negotiation_seconds, 1), calls=calls)
    say(f"  round {round_no}: {seconds:.1f} s ({negotiation_seconds:.1f} s negotiations, {seconds - negotiation_seconds:.1f} s coach) | calls: {counter.line(round_no)}")
    return {
        "round": round_no,
        "seconds": round(seconds, 1),
        "negotiation_seconds": round(negotiation_seconds, 1),
        "calls": calls,
        "reports": [r.as_dict() for k in keys for r in reports[k]],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DealMind training run.")
    parser.add_argument("--rounds", type=int, default=config.DEFAULT_ROUNDS)
    parser.add_argument("--deals", type=int, default=config.DEALS_PER_ROUND, help="deals per supplier per round")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--seed", type=int, default=0, help="seed for the coach's random fallbacks")
    parser.add_argument("--plain", action="store_true", help="plain prints instead of the rich UI (Step 6)")
    args = parser.parse_args()

    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    events.set_current(events.EventLog(run_dir / "events.jsonl"))
    counter = CallCounter()
    events.current().listeners.append(counter)
    say = print

    state = new_state(run_id, config.TRAINING_SUPPLIERS)
    events.emit("run_start", run_id=run_id, rounds=args.rounds, deals=args.deals, models=config.MODEL_SHORT_NAMES, rpm=llm.RPM_LIMIT)
    say(f"DealMind run {run_id}: {args.rounds} rounds x {len(state.suppliers)} suppliers x {args.deals} deals, pacing {llm.RPM_LIMIT} RPM per model")

    started = time.perf_counter()
    rounds_out: list[dict] = []
    all_reports: list[dict] = []
    for round_no in range(1, args.rounds + 1):
        info = training_round(state, round_no, args.deals, args.seed, say, counter)
        all_reports.extend(info.pop("reports"))
        rounds_out.append(info)
        version = save_round(state, run_dir)
        (run_dir / "results.json").write_text(json.dumps({"run_id": run_id, "rounds": rounds_out, "reports": all_reports}, indent=1), encoding="utf-8")
        say(f"  playbook saved: {version}")

    say("\n=== Mean score per supplier per round ===")
    say("supplier".ljust(20) + "".join(f"R{r:<6d}" for r in range(1, args.rounds + 1)))
    for s in state.suppliers.values():
        best = card_label(card_from_dict(s.best)) if s.best else "-"
        say(s.name.ljust(20) + "".join(f"{x:<7.1f}" for x in s.scores) + f"  best: {best}")
    say("\n=== Wall-clock and model calls per round ===")
    for info in rounds_out:
        say(f"round {info['round']}: {info['seconds']:6.1f} s | " + ", ".join(f"{m} {n}" for m, n in info["calls"].items()))
    say(f"total: {time.perf_counter() - started:.1f} s; run folder: {run_dir}")
    events.emit("run_end", run_id=run_id, seconds=round(time.perf_counter() - started, 1))


if __name__ == "__main__":
    main()

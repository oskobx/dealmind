"""Training loop (§8.1) plus the Ridgeline held-out test (§10). Each round every specialist runs 2
seeded deals in parallel with its candidate card; the coach keeps or discards the card, picks the
next one-knob experiment and rewrites the dossier and briefing; the playbook is saved as a new
version. After training, Ridgeline is negotiated by a blank specialist and by one briefed from the
General tactics alone, on the same 3 seeded deals.

    uv run run.py --rounds 5 [--deals 2] [--run-id ID] [--seed 0] [--router switchyard] [--no-ridgeline]
    uv run run.py --ridgeline-only <run_id>     # reuse a finished run's state for the held-out test
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dealmind import config, events, llm
from dealmind.cards import Card, card_from_dict, card_label, default_card
from dealmind.coach import coach_supplier, draft_for_new_supplier, update_general_tactics
from dealmind.deals import Deal, deal_seed, random_deal
from dealmind.negotiation import NegotiationResult, negotiate
from dealmind.playbook import PlaybookState, load_state, new_state, save_round
from dealmind.report import Report, build_facts, build_report

RIDGELINE_ROUND = 0  # the held-out test is not a training round; its deal seeds use round 0


class CallCounter:
    """Counts llm_call events per model per phase (training rounds 1..N, Ridgeline = 0)."""

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


# --- §8.1 training -----------------------------------------------------------


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


# --- §10 Ridgeline held-out test ---------------------------------------------


def _ridgeline_deal(arm: str, card: Card, briefing: str, believed: str, deal: Deal, seed: int) -> NegotiationResult:
    return negotiate(config.SUPPLIERS[config.HELD_OUT_SUPPLIER], deal, card, briefing, believed, seed)


def ridgeline_test(state: PlaybookState, run_dir: Path, say, counter: CallCounter) -> dict:
    """§10: blank arm (default card, empty briefing) vs informed arm (drafted from General tactics only),
    same 3 seeded deals. Returns both means and the difference."""
    started = time.perf_counter()
    counter.round = RIDGELINE_ROUND
    supplier = config.SUPPLIERS[config.HELD_OUT_SUPPLIER]
    deals = [random_deal(deal_seed(RIDGELINE_ROUND, supplier.key, i)) for i in range(config.RIDGELINE_DEALS)]
    events.emit("ridgeline_start", supplier=supplier.key, deals=[d.label for d in deals], general_tactics=state.general_tactics)
    say(f"\n=== Ridgeline held-out test: {supplier.name} ({', '.join(d.label for d in deals)}) ===")

    card, briefing, believed, why = draft_for_new_supplier(state.general_tactics)
    arms = {
        "blank": (default_card(), "", config.DEFAULT_BELIEVED_TYPE),
        "informed": (card, briefing, believed),
    }
    say(f"  blank    card: {card_label(default_card())}")
    say(f"  informed card: {card_label(card)} (believed {believed})\n    why: {why}\n    briefing: {briefing or '(none)'}")

    results: dict[str, list[NegotiationResult | None]] = {arm: [None] * len(deals) for arm in arms}
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
        futures = {
            pool.submit(_ridgeline_deal, arm, *arms[arm], deals[i], deal_seed(RIDGELINE_ROUND, supplier.key, i)): (arm, i)
            for arm in arms
            for i in range(len(deals))
        }
        for future in as_completed(futures):
            arm, i = futures[future]
            result = future.result()
            results[arm][i] = result
            say(f"  {arm:8s} deal {i + 1}: {deals[i].label:12s} -> {result.outcome:9s} {result.score:5.1f}")

    means = {arm: round(statistics.mean(r.score for r in rs if r is not None), 1) for arm, rs in results.items()}
    difference = round(means["informed"] - means["blank"], 1)
    summary = {
        "supplier": supplier.key,
        "deals": [d.label for d in deals],
        "general_tactics": state.general_tactics,
        "arms": {
            arm: {
                "card": arms[arm][0].as_dict(),
                "briefing": arms[arm][1],
                "believed_type": arms[arm][2],
                "scores": [r.score for r in rs if r is not None],
                "mean": means[arm],
                "facts": [build_facts(r, RIDGELINE_ROUND) for r in rs if r is not None],
            }
            for arm, rs in results.items()
        },
        "difference": difference,
        "seconds": round(time.perf_counter() - started, 1),
        "calls": counter.calls(RIDGELINE_ROUND),
    }
    (run_dir / "ridgeline.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    events.emit("ridgeline_end", means=means, difference=difference, informed_card=card.as_dict(), seconds=summary["seconds"])
    say(f"  blank mean {means['blank']:.1f} | informed mean {means['informed']:.1f} | difference {difference:+.1f}")
    say(f"  ridgeline: {summary['seconds']:.1f} s | calls: {counter.line(RIDGELINE_ROUND)}")
    return summary


# --- entry point -------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="DealMind training run and Ridgeline test.")
    parser.add_argument("--rounds", type=int, default=config.DEFAULT_ROUNDS)
    parser.add_argument("--deals", type=int, default=config.DEALS_PER_ROUND, help="deals per supplier per round")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--seed", type=int, default=0, help="seed for the coach's random fallbacks")
    parser.add_argument("--router", choices=["switchyard"], default=None, help="route negotiator calls through NeMo Switchyard (§7.1)")
    parser.add_argument("--no-ridgeline", action="store_true", help="skip the held-out test after training")
    parser.add_argument("--ridgeline-only", metavar="RUN_ID", default=None, help="run only the held-out test on a finished run's state")
    parser.add_argument("--plain", action="store_true", help="plain prints instead of the rich UI")
    args = parser.parse_args()

    say = print
    if args.router == "switchyard":
        llm.set_router(config.SWITCHYARD_BASE_URL)
        say(f"negotiator calls routed through Switchyard at {config.SWITCHYARD_BASE_URL} (fallback: direct Nano)")

    counter = CallCounter()
    started = time.perf_counter()

    if args.ridgeline_only:
        run_dir = Path("runs") / args.ridgeline_only
        state = load_state(run_dir / "state.json")
        events.set_current(events.EventLog(run_dir / "events.jsonl"))
        events.current().listeners.append(counter)
        ridgeline_test(state, run_dir, say, counter)
        say(f"total: {time.perf_counter() - started:.1f} s; run folder: {run_dir}")
        return

    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    events.set_current(events.EventLog(run_dir / "events.jsonl"))
    events.current().listeners.append(counter)

    state = new_state(run_id, config.TRAINING_SUPPLIERS)
    events.emit("run_start", run_id=run_id, rounds=args.rounds, deals=args.deals, models=config.MODEL_SHORT_NAMES, router=args.router)
    say(f"DealMind run {run_id}: {args.rounds} rounds x {len(state.suppliers)} suppliers x {args.deals} deals")

    rounds_out: list[dict] = []
    all_reports: list[dict] = []
    for round_no in range(1, args.rounds + 1):
        info = training_round(state, round_no, args.deals, args.seed, say, counter)
        all_reports.extend(info.pop("reports"))
        rounds_out.append(info)
        version = save_round(state, run_dir)
        (run_dir / "results.json").write_text(json.dumps({"run_id": run_id, "rounds": rounds_out, "reports": all_reports}, indent=1), encoding="utf-8")
        say(f"  playbook saved: {version}")

    ridgeline = None if args.no_ridgeline else ridgeline_test(state, run_dir, say, counter)

    say("\n=== Mean score per supplier per round ===")
    say("supplier".ljust(20) + "".join(f"R{r:<6d}" for r in range(1, args.rounds + 1)))
    for s in state.suppliers.values():
        best = card_label(card_from_dict(s.best)) if s.best else "-"
        say(s.name.ljust(20) + "".join(f"{x:<7.1f}" for x in s.scores) + f"  best: {best}")
    if ridgeline:
        say(f"Ridgeline: blank {ridgeline['arms']['blank']['mean']:.1f} vs informed {ridgeline['arms']['informed']['mean']:.1f} ({ridgeline['difference']:+.1f})")
    say("\n=== Wall-clock and model calls per round ===")
    for info in rounds_out:
        say(f"round {info['round']}: {info['seconds']:6.1f} s | " + ", ".join(f"{m} {n}" for m, n in info["calls"].items()))
    if ridgeline:
        say(f"ridgeline: {ridgeline['seconds']:6.1f} s | " + ", ".join(f"{m} {n}" for m, n in ridgeline["calls"].items()))
    say(f"total: {time.perf_counter() - started:.1f} s; run folder: {run_dir}")
    events.emit("run_end", run_id=run_id, seconds=round(time.perf_counter() - started, 1))


if __name__ == "__main__":
    main()

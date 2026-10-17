"""The coach (§8). Code decides kept/discarded and validates one-knob experiments; Nemotron Super
chooses the next knob, rewrites the dossier and writes the briefing. The coach only ever sees
reports (facts + observations), never the suppliers' secret cards."""

from __future__ import annotations

import random
import statistics
import time
from dataclasses import dataclass

from dealmind import config, events, llm
from dealmind.cards import (
    KNOBS,
    Card,
    card_from_dict,
    card_key,
    card_label,
    default_card,
    describe_change,
    diff_knobs,
    mutate_one_knob,
    neighbors,
)
from dealmind.playbook import (
    MAX_BRIEFING_WORDS,
    MAX_DOSSIER_LINES,
    MAX_TACTICS_LINES,
    Experiment,
    PlaybookState,
    SupplierState,
    clip_lines,
    clip_words,
)
from dealmind.report import Report, report_text

COACH_MAX_TOKENS = 1200
TACTICS_MAX_TOKENS = 800

COACH_INTRO = (
    "You are the coach of a team of AI purchasing negotiators for a furniture shop chain. Each negotiator is a "
    "specialist for one supplier. You tune a specialist's strategy card one knob at a time, keep a change only if "
    "it measurably wins, and maintain a dossier and a short briefing for each specialist.\n\n"
    "Scoring per deal, 0-100: price 50%, quality 30%, delivery 20%. Hitting every target (target price, standard "
    "quality, 14 days) scores exactly 70; a lower price, premium quality or faster delivery score above 70; no deal "
    "or a walk-away scores 0.\n\n"
    "The five knobs and what they do mechanically:\n"
    "- tactic: ditf (door in the face: open with the extreme package, premium + 7 days, then retreat) | fitd "
    "(foot in the door: open with the easy package, standard + 14 days, add asks later).\n"
    "- anchor: aggressive (open at 70% of our target price) | modest (open at 85%). Some suppliers walk away from "
    "lowball openings.\n"
    "- speed: slow (round 2 still claims 70% of the gap) | fast (round 2 claims only 40%).\n"
    "- tone: firm | cooperative (how the messages are written; suppliers react to the tone they read).\n"
    "- gives_up: price | quality | delivery (the term we concede first, in round 2, to the supplier's position).\n"
    "\nDiagnostics, how to read a report:\n"
    "- They accepted our offer right away (round 1 or 2): we conceded too much too early. A slower concession "
    "speed or a more aggressive anchor keeps more of the gap.\n"
    "- They walked away after our opening: the opening was too extreme for them. A modest anchor or the fitd "
    "package keeps them at the table.\n"
    "- We ended at or near their counter price: we gave up price too fast. gives_up=price means paying their "
    "current counter in round 2, usually their full opening ask; it only pays when round 1 already closes.\n"
    "- Their counters barely moved and the price stayed high: our behavior may be hardening them. Tone and "
    "tactic change how they read us; try the other tone.\n"
    "- Points lost on quality (basic) or delivery: we conceded that term; give up a different term instead.\n"
    "- Change the knob that addresses the biggest visible loss, one knob per round, and keep what measurably wins.\n"
)
COACH_RULES = (
    "\nRules: propose exactly one knob change from the best card, never a card already tried. Use only numbers that "
    "appear in the reports. Reply with JSON only."
)


@dataclass
class CoachUpdate:
    supplier: str
    round: int
    candidate: Card
    score: float
    kept: bool
    experiment: Experiment
    next_card: Card
    next_source: str  # "coach" | "random_fallback" | "exhausted"
    why: str


# --- §8.1 steps 4-5 in code --------------------------------------------------


def available_changes(best: Card, tried: set[str] | dict[str, float]) -> list[tuple[str, str]]:
    """The untried one-knob changes from the best card, as (knob, value) pairs."""
    return [
        (knob, getattr(c, knob))
        for c in neighbors(best)
        if card_key(c) not in tried
        for knob in diff_knobs(best, c)
    ]


def choose_next_card(
    best: Card,
    proposal: dict | None,
    tried: set[str],
    rng: random.Random,
    preferred: list[tuple[str, str]] | None = None,
) -> tuple[Card, str]:
    """§8.1 step 5: the coach's one-knob proposal if valid and untried; otherwise an untried neighbor,
    taken from the fact-based suggestions first when there are any, else at random."""
    if proposal:
        try:
            candidate = mutate_one_knob(best, str(proposal.get("next_knob")), str(proposal.get("next_value")))
            if card_key(candidate) not in tried:
                return candidate, "coach"
        except ValueError:
            pass
    options = available_changes(best, tried)
    if not options:
        return best, "exhausted"
    suggested = [change for change in (preferred or []) if change in options]
    if suggested:
        knob, value = rng.choice(suggested)
        return mutate_one_knob(best, knob, value), "suggested_fallback"
    knob, value = rng.choice(options)
    return mutate_one_knob(best, knob, value), "random_fallback"


def _history_lines(experiments: list[Experiment]) -> str:
    return "\n".join(
        f"- round {e.round}: {e.change}: {'-' if e.before is None else f'{e.before:.1f}'} → {e.after:.1f} ({e.result})"
        for e in experiments
    ) or "- none yet"


def _option_lines(best: Card, tried: dict[str, float]) -> str:
    """The menu the coach picks from (§8.1 step 5)."""
    return "\n".join(f"- {knob} → {value}" for knob, value in available_changes(best, tried)) or "- none left"


OTHER_TONE: dict[str, str] = {"firm": "cooperative", "cooperative": "firm"}


def diagnose(reports: list[Report], candidate: Card) -> tuple[list[str], list[tuple[str, str]]]:
    """Read the round's facts (never the secret cards) and name the knob changes they point to.

    The coach model still chooses; this only makes the obvious signals explicit and reliable."""
    notes: list[str] = []
    suggested: list[tuple[str, str]] = []

    def suggest(knob: str, value: str) -> None:
        if getattr(candidate, knob) != value and (knob, value) not in suggested:
            suggested.append((knob, value))

    for i, report in enumerate(reports, start=1):
        f = report.facts
        target = f["deal"]["target"]
        ours = [o for o in f["offers"] if o["by"] == "negotiator"]
        rounds = len(ours)
        final = f["final"]
        if f["outcome"] == "walk_away":
            notes.append(f"deal {i}: they walked away in round {rounds}, right after our opening at {ours[0]['price'] / target:.0%} of target")
            if candidate.anchor == "aggressive":
                suggest("anchor", "modest")
            else:
                suggest("tactic", "fitd")
            continue
        if f["outcome"] == "no_deal" or final is None:
            notes.append(f"deal {i}: no deal; their final counter was not worth taking")
            suggest("anchor", "modest")
            suggest("tone", OTHER_TONE[candidate.tone])
            continue
        price_pct = final["price"] / target
        if f["closed_by"] == "supplier_accepted" and rounds <= 2:
            notes.append(f"deal {i}: they accepted our round-{rounds} offer immediately at {price_pct:.0%} of target; we probably left money on the table")
            suggest("speed", "slow")
            if candidate.anchor == "modest":
                suggest("anchor", "aggressive")
        if price_pct >= 1.10:
            notes.append(f"deal {i}: we paid {price_pct:.0%} of target")
            if candidate.gives_up == "price":
                suggest("gives_up", "quality")
                suggest("gives_up", "delivery")
            else:
                suggest("tone", OTHER_TONE[candidate.tone])
                suggest("speed", "slow")
        if final["quality"] == "basic":
            notes.append(f"deal {i}: we ended with basic quality")
            suggest("gives_up", "delivery")
        if final["delivery_days"] >= 28:
            notes.append(f"deal {i}: delivery took {final['delivery_days']} days")
            if candidate.gives_up == "delivery":
                suggest("gives_up", "quality")
        if f["closed_by"] == "final_counter":
            notes.append(f"deal {i}: closed on their final counter at {price_pct:.0%} of target, {final['quality']}, {final['delivery_days']} days")
    return notes, suggested


def _supplier_prompt(
    s: SupplierState,
    round_no: int,
    candidate: Card,
    score: float,
    result: str,
    before: float | None,
    reports: list[Report],
    general_tactics: list[str],
    experiments: list[Experiment],
    notes: list[str],
    suggested: list[tuple[str, str]],
) -> str:
    best = card_from_dict(s.best) if s.best else candidate
    options = available_changes(best, s.tried)
    pointers = "; ".join(f"{k} → {v}" for k, v in suggested if (k, v) in options) or "none in particular"
    facts_say = "\n".join(f"- {n}" for n in notes) or "- nothing stands out"
    if result == "baseline":
        decision = f"Round 1 baseline: the default card ({card_label(candidate)}) scored {score:.1f}. It is the best card for now."
    elif result == "kept":
        decision = (
            f"Code decision: KEPT. The candidate ({card_label(candidate)}) scored {score:.1f}, more than 2.0 above the "
            f"previous best {before:.1f}. It is the new best card."
        )
    else:
        decision = (
            f"Code decision: DISCARDED. The candidate ({card_label(candidate)}) scored {score:.1f}; the best card "
            f"({card_label(best)}, {s.best_score:.1f}) stays."
        )
    dossier = "\n".join(f"- {line}" for line in s.dossier) or "(empty)"
    tactics = "\n".join(f"- {t}" for t in general_tactics) or "(none yet)"
    reports_text = "\n---\n".join(report_text(r) for r in reports)
    return (
        f"Supplier: {s.name}. Round {round_no} just finished.\n"
        f"{decision}\n\n"
        f"Current dossier:\n{dossier}\n\n"
        f"Best card now: {card_label(best)} (score {s.best_score:.1f}, round {s.best_round})\n"
        f"Believed type so far: {s.believed_type}\n"
        f"Experiments so far:\n{_history_lines(experiments)}\n\n"
        f"Available one-knob experiments from the best card (choose next_knob and next_value from this list):\n"
        f"{_option_lines(best, s.tried)}\n\n"
        f"Team-wide general tactics:\n{tactics}\n\n"
        f"This round's reports:\n---\n{reports_text}\n---\n\n"
        f"What the facts of this round say (computed from the reports):\n{facts_say}\n"
        f"Knob changes these facts point to (your call, but it must be on the available list): {pointers}\n\n"
        "Return JSON only:\n"
        '{"kept": true | false, "next_knob": "tactic|anchor|speed|tone|gives_up", "next_value": "<value>", '
        '"why": "One sentence explaining the experiment.", '
        '"dossier": ["up to 10 short lines, rewritten from scratch: what you now believe about this supplier", '
        '"what it rewards, what it punishes, how fast it concedes, its likely floor if the facts support it"], '
        '"briefing": "Up to 80 words the negotiator reads before the next deal, written for the next card.", '
        '"believed_type": "strong" | "weak"}\n'
        "believed_type: weak if they accept quickly or concede most of the gap; strong if they hold near their ask "
        "or walk away. next_knob and next_value must be one line from the available list."
    )


def _ask(system: str, user: str, max_tokens: int, seed: int) -> dict | None:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        parsed, _ = llm.chat_json("coach", config.MODEL_COACH, messages, max_tokens=max_tokens, seed=seed)
    except llm.LLMError as exc:
        events.emit("coach_llm_error", error=str(exc))
        return None
    return parsed


def coach_supplier(state: PlaybookState, key: str, round_no: int, reports: list[Report], rng: random.Random) -> CoachUpdate:
    """§8.1 steps 4-6 for one supplier. Mutates its SupplierState; the caller appends the Experiment."""
    s = state.suppliers[key]
    candidate = card_from_dict(s.candidate)
    score = round(statistics.mean(r.facts["score"] for r in reports), 1)
    escalated = sum(int(r.facts.get("escalated_turns", 0)) for r in reports)
    s.scores.append(score)
    s.tried[card_key(candidate)] = score

    if s.best is None:  # §8.1 step 4: round 1, candidate becomes best
        kept, result, before, change = True, "baseline", None, "baseline (default card)"
    else:
        before = s.best_score
        change = describe_change(card_from_dict(s.best), candidate)
        kept = score > s.best_score + config.KEEP_MARGIN
        result = "kept" if kept else "discarded"
    if kept:
        s.best, s.best_score, s.best_round = candidate.as_dict(), score, round_no
    else:
        s.failed.append(f"{change} (round {round_no}: {score:.1f} vs best {before:.1f})")
    experiment = Experiment(round_no, key, change, before, score, escalated, result)

    history = [e for e in state.experiments if e.supplier == key] + [experiment]
    notes, suggested = diagnose(reports, candidate)
    prompt = _supplier_prompt(s, round_no, candidate, score, result, before, reports, state.general_tactics, history, notes, suggested)
    proposal = _ask(COACH_INTRO + COACH_RULES, prompt, COACH_MAX_TOKENS, seed=round_no)
    best = card_from_dict(s.best)
    next_card, source = choose_next_card(best, proposal, set(s.tried), rng, preferred=suggested)
    why = ""
    if proposal:
        why = " ".join(str(proposal.get("why") or "").split())
        dossier = clip_lines(proposal.get("dossier") or [], MAX_DOSSIER_LINES)
        if dossier:
            s.dossier = dossier  # §9.2: rewritten, not appended
        briefing = clip_words(proposal.get("briefing") or "", MAX_BRIEFING_WORDS)
        if briefing:
            s.briefing = briefing
        believed = str(proposal.get("believed_type") or "").strip().lower()
        if believed in config.ROUND3_CLAIM:
            s.believed_type = believed
    if source != "coach":
        why = (why + " " if why else "") + f"(coach proposal invalid or already tried; {source.replace('_', ' ')})"
        if source.endswith("_fallback"):  # the briefing was written for the coach's card, not this one
            s.briefing = clip_words(f"This round tests {describe_change(best, next_card)}. {s.briefing}", MAX_BRIEFING_WORDS)
    s.candidate = next_card.as_dict()
    s.last_why = why

    events.emit(
        "coach_update",
        supplier=key,
        round=round_no,
        candidate=candidate.as_dict(),
        score=score,
        result=result,
        best=s.best,
        best_score=s.best_score,
        next_card=next_card.as_dict(),
        next_source=source,
        diagnostics=notes,
        suggested=suggested,
        change=describe_change(best, next_card),
        why=why,
        briefing=s.briefing,
        believed_type=s.believed_type,
        dossier=s.dossier,
    )
    return CoachUpdate(key, round_no, candidate, score, kept, experiment, next_card, source, why)


# --- §8.3 general tactics ----------------------------------------------------


def _names_mentioned(line: str, state: PlaybookState, evidence: set[str]) -> int:
    """How many suppliers with real experiments the line cites (first word of the name, any case)."""
    text = line.lower()
    return sum(1 for s in state.suppliers.values() if s.key in evidence and s.name.split()[0].lower() in text)


def update_general_tactics(state: PlaybookState, round_no: int) -> list[str]:
    """§8.3: one coach call rewrites the section; code keeps only lines that cite two or more suppliers
    that have real experiments behind them (baselines are not evidence)."""
    evidence = {e.supplier for e in state.experiments if e.result != "baseline"}
    if len(evidence) < 2:
        events.emit("general_tactics_skipped", round=round_no, reason="fewer than two suppliers with experiments")
        return state.general_tactics
    sections = []
    for s in state.suppliers.values():
        history = [
            f"round {e.round}: {e.change}: {'-' if e.before is None else f'{e.before:.1f}'} → {e.after:.1f} ({e.result})"
            for e in state.experiments
            if e.supplier == s.key
        ]
        best = card_label(card_from_dict(s.best)) if s.best else "-"
        sections.append(
            f"{s.name} (believed {s.believed_type}; best card {best}, score {s.best_score:.1f}; "
            f"scores by round {', '.join(f'{x:.1f}' for x in s.scores)})\n"
            f"  dossier: {' | '.join(s.dossier) or '(empty)'}\n"
            f"  experiments: {'; '.join(history) or '(none)'}"
        )
    current = "\n".join(f"- {t}" for t in state.general_tactics) or "(empty)"
    user = (
        f"Round {round_no} just finished. Rewrite the team's General tactics section from scratch: at most "
        f"{MAX_TACTICS_LINES} lines. A lesson is only allowed if it held with at least two suppliers, and each line "
        "must name those suppliers in parentheses, for example 'Strong suppliers (Northwood, Harlow): modest anchor "
        "and cooperative tone close better.' Cite a supplier only if one of its experiments below supports the lesson; "
        "baselines are not evidence. Do not call a supplier strong or weak unless its believed type says so. Use only "
        "the facts below; drop any old line the facts no longer support.\n\n"
        f"Current general tactics:\n{current}\n\nSuppliers:\n" + "\n".join(sections) + "\n\n"
        'Return JSON only: {"tactics": ["line", "line"]}'
    )
    parsed = _ask(COACH_INTRO + "\nReply with JSON only.", user, TACTICS_MAX_TOKENS, seed=round_no)
    raw = parsed.get("tactics") if parsed else None
    if isinstance(raw, str):
        raw = raw.splitlines()
    lines = clip_lines(raw or [], 20)
    valid = [line for line in lines if _names_mentioned(line, state, evidence) >= 2][:MAX_TACTICS_LINES]
    rejected = [line for line in lines if line not in valid]
    if not valid:
        events.emit("general_tactics_unchanged", round=round_no, rejected=rejected)
        return state.general_tactics
    events.emit("general_tactics", round=round_no, tactics=valid, rejected=rejected)
    return valid


# --- §10 drafting for a supplier nobody has met ------------------------------


def draft_for_new_supplier(general_tactics: list[str]) -> tuple[Card, str, str, str]:
    """§10 informed arm: a starting card and briefing from the General tactics only. The coach is told
    nothing about the supplier, not even its name. Returns (card, briefing, believed_type, why)."""
    tactics = "\n".join(f"- {t}" for t in general_tactics) or "(empty)"
    user = (
        "A new supplier is coming up. Nothing is known about it: personality unknown, no history, no dossier. "
        "Using only the team's General tactics below, draft the specialist's starting card and briefing.\n\n"
        f"General tactics:\n{tactics}\n\n"
        'Return JSON only: {"card": {"tactic": "fitd" | "ditf", "anchor": "modest" | "aggressive", '
        '"speed": "slow" | "fast", "tone": "firm" | "cooperative", "gives_up": "price" | "quality" | "delivery"}, '
        '"why": "one sentence", "briefing": "up to 80 words the negotiator reads before the deal", '
        '"believed_type": "strong" | "weak"}'
    )
    parsed = None
    for attempt in range(3):  # the draft is one call the whole held-out test depends on; outlast a 429 burst
        parsed = _ask(COACH_INTRO + "\nReply with JSON only.", user, COACH_MAX_TOKENS, seed=attempt)
        if parsed:
            break
        time.sleep(5)
    card, briefing, believed, why = default_card(), "", config.DEFAULT_BELIEVED_TYPE, "no proposal; default card used"
    if parsed:
        raw_card = parsed.get("card") or {}
        try:
            card = card_from_dict({k: str(v).strip().lower() for k, v in raw_card.items()})
            why = " ".join(str(parsed.get("why") or "").split())
        except (KeyError, ValueError, AttributeError):
            why = f"invalid card {raw_card!r}; default card used"
        briefing = clip_words(parsed.get("briefing") or "", MAX_BRIEFING_WORDS)
        proposed_type = str(parsed.get("believed_type") or "").strip().lower()
        if proposed_type in config.ROUND3_CLAIM:
            believed = proposed_type
    events.emit("ridgeline_draft", card=card.as_dict(), briefing=briefing, believed_type=believed, why=why)
    return card, briefing, believed, why

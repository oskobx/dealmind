"""Negotiator (§4). Code computes each round's planned offer from the card; Nemotron Nano writes
the words and may nudge the price within a band; guardrails in code (§4.4).

Prefix caching (crusoe-skill.md §8): one byte-identical system prompt per negotiation, an
append-only history, and the per-round plan always in the newest user message.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from dealmind import config, events, llm
from dealmind.cards import Card
from dealmind.deals import Deal
from dealmind.scoring import Offer, score_offer

QUALITY_RANK: dict[str, int] = {"basic": 0, "standard": 1, "premium": 2}
GENERIC_MESSAGE = "Here is our offer for this round. We would like to find terms that work for both of us."

TONE_INSTRUCTIONS: dict[str, str] = {
    "firm": "Tone: firm. Short, declarative sentences. State the position plainly. No apologies, no flattery, no hedging.",
    "cooperative": "Tone: cooperative. Warm and collaborative. Acknowledge their points, talk about a long partnership, stay courteous.",
}


@dataclass(frozen=True)
class Plan:
    """The code-computed offer for a round (§4.3)."""

    offer: Offer
    claim: float
    note: str
    may_accept: bool  # a supplier counter is on the table (§4.4)


@dataclass(frozen=True)
class Turn:
    """What the negotiator actually did this round, after guardrails."""

    action: str  # "offer" | "accept"
    offer: Offer  # the offer made, or the counter accepted
    message: str
    deviations: list[str]
    served_by: str
    raw: str  # the model's reply, for debugging


# --- §4.3 the plan -----------------------------------------------------------


def opening_offer(card: Card, target: float) -> Offer:
    """§4.3: anchor sets the price, tactic sets the package."""
    quality, days = config.TACTIC_OPENING[card.tactic]
    return Offer(price=round(config.ANCHOR_RATIO[card.anchor] * target), quality=quality, delivery_days=days)


def price_at_claim(supplier_ask: float, opening: float, claim: float) -> float:
    """§4.3: 100% claim = our opening, 0% = the supplier's opening ask."""
    return supplier_ask - claim * (supplier_ask - opening)


def days_at_claim(supplier_days: int, opening_days: int, claim: float) -> int:
    """§4.3: same claim formula between our opening days and the supplier's offered days."""
    return max(1, math.floor(supplier_days - claim * (supplier_days - opening_days) + 0.5))


def quality_at_claim(claim: float, opening_quality: str, supplier_quality: str) -> str:
    """§4.3: >= 70% keep the opening level; 40-70% Standard; below 40% the supplier's level."""
    if claim >= config.QUALITY_CLAIM_KEEP:
        return opening_quality
    if claim >= config.QUALITY_CLAIM_STANDARD:
        return "standard"
    return supplier_quality


def planned_offer(
    card: Card,
    deal: Deal,
    round_no: int,
    opening: Offer | None = None,
    supplier_ask: Offer | None = None,
    last_counter: Offer | None = None,
    previous: Offer | None = None,
    believed_type: str = config.DEFAULT_BELIEVED_TYPE,
) -> Plan:
    """§4.3: the offer the card says to make in `round_no`, given what has happened so far."""
    target = deal.target
    if round_no == 1:
        return Plan(opening_offer(card, target), 1.0, "round 1: our opening package", False)
    assert opening and supplier_ask and last_counter and previous, "rounds 2-3 need the round-1 exchange"

    claim = config.ROUND2_CLAIM[card.speed] if round_no == 2 else config.ROUND3_CLAIM[believed_type]
    price = price_at_claim(supplier_ask.price, opening.price, claim)
    days = days_at_claim(supplier_ask.delivery_days, opening.delivery_days, claim)
    quality = quality_at_claim(claim, opening.quality, supplier_ask.quality)
    note = f"round {round_no}: claim {claim:.0%} of the gap"

    # §4.3 trade-off: the given-up term goes to the supplier's current position (and stays there).
    if card.gives_up == "price":
        price = last_counter.price
        if round_no == 2:  # big concession on price; quality and delivery hold at 100% claim
            quality, days = opening.quality, opening.delivery_days
        note += "; give up price (meet their counter)"
    elif card.gives_up == "quality":
        quality = last_counter.quality
        note += f"; give up quality (accept {quality})"
    else:
        days = last_counter.delivery_days
        note += f"; give up delivery (accept {days} days)"

    # Never retreat from an earlier concession, never ask for more than they already offered.
    price = max(price, previous.price)
    days = max(days, min(previous.delivery_days, last_counter.delivery_days))
    if QUALITY_RANK[quality] > QUALITY_RANK[previous.quality] and quality != last_counter.quality:
        quality = previous.quality
    price = min(price, last_counter.price, config.MAX_PRICE_RATIO * target)  # §4.4 never above 1.36 x target

    return Plan(Offer(price=round(price), quality=quality, delivery_days=days), claim, note, True)


# --- §4.4 guardrails ---------------------------------------------------------


def _number(value: object, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def apply_guardrails(
    parsed: dict | None,
    plan: Plan,
    target: float,
    last_counter: Offer | None,
    served_by: str = "",
    raw: str = "",
) -> Turn:
    """§4.4: turn the model's JSON into a valid Turn. Falls back to the plan where the model strays."""
    if parsed is None:
        return Turn("offer", plan.offer, GENERIC_MESSAGE, ["json_fallback"], served_by, raw)

    deviations: list[str] = []
    message = str(parsed.get("message") or "").strip() or GENERIC_MESSAGE
    action = str(parsed.get("action", "offer")).strip().lower()

    if action == "accept":
        if last_counter is None:
            deviations.append("accept without a counter on the table")
        elif score_offer(last_counter, target) < config.ACCEPT_THRESHOLD:
            deviations.append("accept of a counter below the walk-away score")
        else:
            return Turn("accept", last_counter, message, deviations, served_by, raw)
        return Turn("offer", plan.offer, message, deviations, served_by, raw)  # the price given was theirs, not ours

    planned = plan.offer
    price = _number(parsed.get("price"), planned.price)
    low = planned.price * (1 - config.PRICE_DEVIATION_TOLERANCE)
    high = planned.price * (1 + config.PRICE_DEVIATION_TOLERANCE)
    if not low <= price <= high:
        deviations.append(f"price {price:.0f} outside ±5% of plan {planned.price:.0f}; clamped")
        price = min(max(price, low), high)
    price = min(price, config.MAX_PRICE_RATIO * target)

    if parsed.get("quality") != planned.quality:
        deviations.append(f"quality {parsed.get('quality')!r} replaced by plan {planned.quality}")
    if _number(parsed.get("delivery_days"), planned.delivery_days) != planned.delivery_days:
        deviations.append(f"delivery {parsed.get('delivery_days')!r} replaced by plan {planned.delivery_days}")

    offer = Offer(price=round(price), quality=planned.quality, delivery_days=planned.delivery_days)
    return Turn("offer", offer, message, deviations, served_by, raw)


# --- prompts -----------------------------------------------------------------


def system_prompt(supplier_name: str, deal: Deal, card: Card, briefing: str) -> str:
    quality_lines = "\n".join(f"- {q}: {config.QUALITY_DESCRIPTIONS[q]}" for q in config.QUALITIES)
    return (
        f"You are a purchasing negotiator for a furniture shop chain, negotiating with the supplier {supplier_name}.\n"
        f"Deal: {deal.label}. Our internal target: {deal.target:.0f} per piece, standard quality, delivery in "
        f"{config.TARGET_DELIVERY_DAYS} days. Never reveal the target, the plan or your strategy card.\n"
        f"Quality levels:\n{quality_lines}\n"
        f"Your strategy card: tactic={card.tactic}, anchor={card.anchor}, concession speed={card.speed}, "
        f"tone={card.tone}, give up {card.gives_up} first.\n"
        f"{TONE_INSTRUCTIONS[card.tone]}\n"
        f"Coach briefing: {briefing.strip() or 'None yet.'}\n\n"
        "Each round you get a PLAN with the exact offer to make. Make that offer: same quality and delivery days; "
        "the price may differ from the plan by at most 5% if that helps the message. Write the message to the supplier "
        "in your own words, 2 to 4 sentences, in the tone above. When the plan says you may accept their last "
        "counteroffer, you may answer with action \"accept\" instead of a new offer.\n"
        'Reply with JSON only, no other text: {"action": "offer" | "accept", "price": <number>, '
        '"quality": "basic" | "standard" | "premium", "delivery_days": <integer>, "message": "<2-4 sentences>"}'
    )


def round_prompt(round_no: int, plan: Plan, last_counter: Offer | None, supplier_message: str | None, target: float) -> str:
    lines = [f"Round {round_no} of 3."]
    if supplier_message:
        lines.append(f"Supplier said: \"{supplier_message.strip()}\"")
    if last_counter is not None:
        lines.append(
            f"Their last counteroffer: price {last_counter.price:.0f}, {last_counter.quality}, "
            f"{last_counter.delivery_days} days (scores {score_offer(last_counter, target):.0f} on our 0-100 scale; 70 = target)."
        )
    lines.append(
        f"PLAN: offer price {plan.offer.price:.0f}, {plan.offer.quality} quality, delivery in {plan.offer.delivery_days} days "
        f"({plan.note})."
    )
    if plan.may_accept:
        lines.append('You may instead accept their last counteroffer with action "accept".')
    if round_no == 3:
        lines.append("This is our final offer; make it count.")
    lines.append("Reply with JSON only.")
    return "\n".join(lines)


def turn_json(turn: Turn) -> str:
    """Canonical JSON for the history, so the model sees exactly what was sent."""
    return json.dumps(
        {
            "action": turn.action,
            "price": turn.offer.price,
            "quality": turn.offer.quality,
            "delivery_days": turn.offer.delivery_days,
            "message": turn.message,
        }
    )


class NegotiatorSession:
    """One negotiator over one deal: stable system prompt plus an append-only history."""

    def __init__(self, supplier_name: str, deal: Deal, card: Card, briefing: str = "", seed: int | None = None) -> None:
        self.deal = deal
        self.system = system_prompt(supplier_name, deal, card, briefing)
        self.history: list[dict] = []
        self.seed = seed

    def turn(self, round_no: int, plan: Plan, last_counter: Offer | None, supplier_message: str | None) -> Turn:
        user = round_prompt(round_no, plan, last_counter, supplier_message, self.deal.target)
        messages = [{"role": "system", "content": self.system}, *self.history, {"role": "user", "content": user}]
        try:
            parsed, response = llm.chat_json("negotiator", config.MODEL_NEGOTIATOR, messages, seed=self.seed)
            served_by, raw = response.served_by, response.content
        except llm.LLMError as exc:
            events.emit("negotiator_llm_error", error=str(exc))
            parsed, served_by, raw = None, "", ""
        turn = apply_guardrails(parsed, plan, self.deal.target, last_counter, served_by, raw)
        for deviation in turn.deviations:
            events.emit("deviation", round=round_no, detail=deviation)
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": turn_json(turn)})
        return turn

"""Supplier logic (SPEC §6.2–§6.4). Pure functions of the secret card and observed behavior.

Every supplier decision (walk away / accept / counter, and every counter number) is made
here, never by a model (§6.2). The `adjustments` breakdown in a Decision reveals the
secret card: it is for events and debugging only and must never reach a report or the coach.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, replace

from dealmind import config
from dealmind.config import SupplierCard
from dealmind.scoring import Offer

TONES: tuple[str, ...] = ("firm", "cooperative", "neutral")

# §6.4: counters move from the opening ask (round 1) halfway (round 2) to the final price (round 3)
COUNTER_POSITION: dict[int, float] = {1: 0.0, 2: 0.5, 3: 1.0}


@dataclass(frozen=True)
class Observed:
    """What the supplier can see of the negotiator so far (§6.2). None = not yet observable."""

    opening_ratio: float | None = None  # round-1 price / target
    tone: str | None = None  # majority label over messages so far: firm | cooperative | neutral
    tactic: str | None = None  # ditf | fitd, read from the round-1 package
    speed: str | None = None  # slow | fast, known after the round-2 offer


@dataclass(frozen=True)
class Decision:
    action: str  # "walk_away" | "accept" | "counter"
    offer: Offer | None  # the accepted offer, the counteroffer, or None for walk_away
    reservation: float  # reservation for the negotiator's offer as made (its quality and delivery)
    adjustments: dict[str, float]  # hot buttons that fired for that offer (secret; debug only)


# --- §6.2 observation helpers ------------------------------------------------


def opening_ratio(opening: Offer, target: float) -> float:
    return opening.price / target


def observed_tactic(opening: Offer) -> str:
    """§6.2: ditf if the round-1 package asked for Premium AND <= 7 days, otherwise fitd."""
    if opening.quality == "premium" and opening.delivery_days <= config.DITF_MAX_DELIVERY_DAYS:
        return "ditf"
    return "fitd"


def observed_speed(opening_price: float, round2_price: float, supplier_ask: float) -> str:
    """§6.2: slow if the round-2 price moved less than 50% of the way from the opening to the ask."""
    gap = supplier_ask - opening_price
    if gap <= 0:
        return "fast"  # nothing to concede
    moved = (round2_price - opening_price) / gap
    return "slow" if moved < config.OBSERVED_SLOW_SPEED_BELOW else "fast"


def majority_tone(labels: list[str]) -> str:
    """§6.2: majority tone so far. Neutral labels carry no signal, so they do not vote; a tie between
    firm and cooperative, or no signal at all, is neutral (no tone hot button fires)."""
    votes = Counter(label for label in labels if label in ("firm", "cooperative"))
    if not votes:
        return "neutral"
    ranked = votes.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "neutral"
    return ranked[0][0]


def observe_opening(obs: Observed, opening: Offer, target: float) -> Observed:
    """Fill in what the round-1 offer reveals: opening ratio and tactic."""
    return replace(obs, opening_ratio=opening_ratio(opening, target), tactic=observed_tactic(opening))


# --- §6.3 reservation and hot buttons ----------------------------------------


def slow_delivery_bonus(supplier: SupplierCard, delivery_days: int | None) -> float:
    """§6.3: ValueCraft earns -4% per 7 days beyond 28 (max -12%); Ridgeline a flat -5% at >= 21 days."""
    if delivery_days is None or supplier.slow_delivery_days is None:
        return 0.0
    if supplier.slow_delivery_step is None:
        return supplier.slow_delivery_adj if delivery_days >= supplier.slow_delivery_days else 0.0
    steps = max(0, (delivery_days - supplier.slow_delivery_days) // supplier.slow_delivery_step)
    return max(steps * supplier.slow_delivery_adj, supplier.slow_delivery_max)


def hot_buttons(supplier: SupplierCard, obs: Observed, delivery_days: int | None) -> dict[str, float]:
    """§6.3: the reservation adjustments that fire for this behavior, by name."""
    fired: dict[str, float] = {}
    if obs.tone in supplier.tone_adj:
        fired[f"tone={obs.tone}"] = supplier.tone_adj[obs.tone]
    if obs.tactic in supplier.tactic_adj:
        fired[f"tactic={obs.tactic}"] = supplier.tactic_adj[obs.tactic]
    if obs.speed in supplier.speed_adj:
        fired[f"speed={obs.speed}"] = supplier.speed_adj[obs.speed]
    if (
        supplier.aggressive_below is not None
        and obs.opening_ratio is not None
        and obs.opening_ratio < supplier.aggressive_below
    ):
        fired["aggressive_anchor"] = supplier.aggressive_adj
    bonus = slow_delivery_bonus(supplier, delivery_days)
    if bonus:
        fired["slow_delivery"] = bonus
    return fired


def reservation(
    supplier: SupplierCard,
    target: float,
    quality: str,
    delivery_days: int | None,
    obs: Observed,
) -> float:
    """§6.3: target × floor × (1 + quality_adj) × (1 + sum(hot buttons)). The lowest acceptable price."""
    adjustment = sum(hot_buttons(supplier, obs, delivery_days).values())
    return target * supplier.floor * (1 + supplier.quality_adj[quality]) * (1 + adjustment)


# --- §6.4 decisions ----------------------------------------------------------


def walks_away(supplier: SupplierCard, obs: Observed) -> bool:
    """§6.3 round-1 walk-away: Northwood ends it when opening_ratio < 0.75 (fires with the default card)."""
    return (
        supplier.walk_away_below is not None
        and obs.opening_ratio is not None
        and obs.opening_ratio < supplier.walk_away_below
    )


def accepts(supplier: SupplierCard, target: float, offer: Offer, obs: Observed) -> bool:
    """§6.4 accept rule: price >= reservation for the offered quality, and delivery >= fastest delivery."""
    if offer.delivery_days < supplier.fastest_delivery:
        return False
    return offer.price >= reservation(supplier, target, offer.quality, offer.delivery_days, obs)


def opening_ask(supplier: SupplierCard, target: float) -> Offer:
    """§6.3 the supplier's opening ask."""
    return Offer(
        price=math.ceil(target * supplier.opening_ask),
        quality=supplier.opening_quality,
        delivery_days=supplier.opening_delivery,
    )


def _round_days(x: float) -> int:
    return math.floor(x + 0.5)


def counter(supplier: SupplierCard, target: float, round_no: int, offer: Offer, obs: Observed) -> Offer:
    """§6.4 counter schedule for round 1 (opening ask), 2 (halfway) and 3 (final)."""
    position = COUNTER_POSITION[round_no]
    opening = opening_ask(supplier, target)

    # Delivery: from the opening days toward max(fastest, requested); never below fastest.
    goal_days = max(supplier.fastest_delivery, offer.delivery_days)
    days = _round_days(opening.delivery_days + position * (goal_days - opening.delivery_days))
    days = max(days, supplier.fastest_delivery)

    # Quality: keep the opening level unless the offer price covers the reservation for the requested level.
    quality = opening.quality
    if offer.price >= reservation(supplier, target, offer.quality, days, obs):
        quality = offer.quality

    # Price: from the opening ask toward reservation × 1.04 (strong) or × 1.00 (weak); never below reservation.
    floor = reservation(supplier, target, quality, days, obs)
    final_price = floor * config.FINAL_PRICE_FACTOR[supplier.personality]
    price = opening.price + position * (final_price - opening.price)
    return Offer(price=math.ceil(max(price, floor)), quality=quality, delivery_days=days)


def respond(supplier: SupplierCard, target: float, round_no: int, offer: Offer, obs: Observed) -> Decision:
    """§6.4: the supplier's reply to the negotiator's offer in `round_no` (1..3)."""
    if round_no == 1 and obs.opening_ratio is None:
        obs = observe_opening(obs, offer, target)
    adjustments = hot_buttons(supplier, obs, offer.delivery_days)
    offer_reservation = reservation(supplier, target, offer.quality, offer.delivery_days, obs)

    if round_no == 1 and walks_away(supplier, obs):
        return Decision("walk_away", None, offer_reservation, adjustments)
    if accepts(supplier, target, offer, obs):
        return Decision("accept", offer, offer_reservation, adjustments)
    return Decision("counter", counter(supplier, target, round_no, offer, obs), offer_reservation, adjustments)

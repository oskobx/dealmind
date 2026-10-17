"""Supplier logic (§6.2–§6.4): walk-away, reservation invariants, hot buttons, counter schedule."""

import itertools

import pytest

from dealmind import config
from dealmind.cards import Card, card_from_dict, default_card
from dealmind.config import SUPPLIERS
from dealmind.scoring import Offer
from dealmind.suppliers import (
    Observed,
    counter,
    hot_buttons,
    majority_tone,
    observed_speed,
    observed_tactic,
    opening_ask,
    reservation,
    respond,
    slow_delivery_bonus,
)

TARGET = 1000.0
NORTHWOOD = SUPPLIERS["northwood"]
QUICKFURN = SUPPLIERS["quickfurn"]
HARLOW = SUPPLIERS["harlow"]
VALUECRAFT = SUPPLIERS["valuecraft"]
RIDGELINE = SUPPLIERS["ridgeline"]


def observed_from_card(card: Card) -> Observed:
    """What a supplier sees when a negotiator plays `card` as designed (§4.3) and the tone label agrees."""
    return Observed(
        opening_ratio=config.ANCHOR_RATIO[card.anchor],
        tone=card.tone,
        tactic=card.tactic,
        speed=card.speed,
    )


def opening_offer(card: Card, target: float = TARGET) -> Offer:
    """The round-1 package for a card (§4.3): anchor price plus the tactic's opening quality and days."""
    quality, days = config.TACTIC_OPENING[card.tactic]
    return Offer(price=config.ANCHOR_RATIO[card.anchor] * target, quality=quality, delivery_days=days)


# --- the demo moment: Northwood walks away from the default card --------------


def test_northwood_walks_away_from_default_card() -> None:
    # §4.2 / §6.3: default card opens at 0.70 x target, below Northwood's 0.75 walk-away line.
    card = default_card()
    assert config.ANCHOR_RATIO[card.anchor] == pytest.approx(0.70)
    decision = respond(NORTHWOOD, TARGET, 1, opening_offer(card), Observed(tone="cooperative"))
    assert decision.action == "walk_away"
    assert decision.offer is None


def test_northwood_does_not_walk_away_from_modest_anchor() -> None:
    offer = Offer(price=0.85 * TARGET, quality="premium", delivery_days=7)
    decision = respond(NORTHWOOD, TARGET, 1, offer, Observed(tone="cooperative"))
    assert decision.action == "counter"


def test_only_northwood_walks_away_and_only_in_round_one() -> None:
    assert [s.key for s in SUPPLIERS.values() if s.walk_away_below is not None] == ["northwood"]
    lowball = Offer(price=0.5 * TARGET, quality="standard", delivery_days=28)
    obs = Observed(opening_ratio=0.5, tone="firm", tactic="fitd", speed="slow")
    for round_no in (2, 3):
        assert respond(NORTHWOOD, TARGET, round_no, lowball, obs).action == "counter"
    for supplier in SUPPLIERS.values():
        if supplier.key != "northwood":
            assert respond(supplier, TARGET, 1, lowball, Observed(tone="firm")).action == "counter"


# --- invariant: never accept or counter below reservation / fastest delivery --


def test_never_below_reservation_or_fastest_delivery() -> None:
    # §6.4 invariant, swept over all suppliers, rounds, qualities, offers and observed behavior.
    ratios = [x / 100 for x in range(50, 141, 5)]
    deliveries = [1, 7, 10, 14, 20, 21, 28, 35, 42, 49]
    observations = [
        Observed(opening_ratio=ratio, tone=tone, tactic=tactic, speed=speed)
        for ratio, tone, tactic, speed in itertools.product(
            (0.70, 0.85), ("firm", "cooperative", "neutral"), ("ditf", "fitd"), (None, "slow", "fast")
        )
    ]
    checks = 0
    for supplier in SUPPLIERS.values():
        for round_no, quality, ratio, days, obs in itertools.product(
            (1, 2, 3), config.QUALITIES, ratios, deliveries, observations
        ):
            offer = Offer(price=ratio * TARGET, quality=quality, delivery_days=days)
            decision = respond(supplier, TARGET, round_no, offer, obs)
            if decision.action == "walk_away":
                assert supplier.key == "northwood" and round_no == 1
                continue
            agreed = decision.offer
            assert agreed is not None
            floor = reservation(supplier, TARGET, agreed.quality, agreed.delivery_days, obs)
            assert agreed.price >= floor - 1e-9, (supplier.key, round_no, offer, obs, decision)
            assert agreed.delivery_days >= supplier.fastest_delivery, (supplier.key, round_no, offer, obs, decision)
            if decision.action == "accept":
                assert agreed == offer
            checks += 1
    assert checks > 100_000


# --- each supplier's best card beats the default card --------------------------


@pytest.mark.parametrize("supplier_key", list(SUPPLIERS))
def test_best_card_lowers_reservation_below_default_card(supplier_key: str) -> None:
    supplier = SUPPLIERS[supplier_key]
    best = observed_from_card(card_from_dict(supplier.best_card))
    default = observed_from_card(default_card())
    days = config.TARGET_DELIVERY_DAYS
    assert reservation(supplier, TARGET, "standard", days, best) < reservation(supplier, TARGET, "standard", days, default)


# --- §6.3 reservation formula and hot buttons ----------------------------------


def test_reservation_formula() -> None:
    neutral = Observed(opening_ratio=0.85, tone="neutral", tactic="fitd", speed="fast")
    assert reservation(QUICKFURN, TARGET, "standard", 14, neutral) == pytest.approx(850)
    assert reservation(QUICKFURN, TARGET, "basic", 14, neutral) == pytest.approx(850 * 0.90)
    assert reservation(QUICKFURN, TARGET, "premium", 14, neutral) == pytest.approx(850 * 1.15)
    # QuickFurn's best card: firm -8%, slow -4%, ditf -4% -> -16%
    best = observed_from_card(card_from_dict(QUICKFURN.best_card))
    assert hot_buttons(QUICKFURN, best, 14) == {"tone=firm": -0.08, "speed=slow": -0.04, "tactic=ditf": -0.04}
    assert reservation(QUICKFURN, TARGET, "standard", 14, best) == pytest.approx(850 * 0.84)


def test_harlow_punishes_aggressive_anchor_and_firm_tone() -> None:
    obs = Observed(opening_ratio=0.70, tone="firm", tactic="ditf", speed="fast")
    assert hot_buttons(HARLOW, obs, 14) == {"tone=firm": 0.05, "speed=fast": -0.04, "aggressive_anchor": 0.08}
    assert hot_buttons(HARLOW, Observed(opening_ratio=0.80), 14) == {}  # 0.80 is not below 0.80


def test_slow_delivery_bonus_steps_and_cap() -> None:
    # ValueCraft: each 7 days beyond 28 -> -4%, max -12%
    assert [slow_delivery_bonus(VALUECRAFT, d) for d in (14, 28, 34, 35, 42, 49, 56)] == [
        0.0, 0.0, 0.0, -0.04, -0.08, -0.12, -0.12
    ]
    # Ridgeline: flat -5% at 21 days or more
    assert [slow_delivery_bonus(RIDGELINE, d) for d in (10, 20, 21, 40)] == [0.0, 0.0, -0.05, -0.05]
    assert slow_delivery_bonus(NORTHWOOD, 60) == 0.0
    assert slow_delivery_bonus(VALUECRAFT, None) == 0.0


# --- §6.4 accept and counter schedule -------------------------------------------


def test_round_one_accept_when_offer_meets_reservation_and_delivery() -> None:
    decision = respond(QUICKFURN, TARGET, 1, Offer(1000, "standard", 14), Observed(tone="neutral"))
    assert decision.action == "accept"
    assert decision.offer == Offer(1000, "standard", 14)


def test_too_fast_delivery_is_countered_even_at_a_good_price() -> None:
    decision = respond(NORTHWOOD, TARGET, 1, Offer(1200, "standard", 14), Observed(tone="neutral"))
    assert decision.action == "counter"
    assert decision.offer is not None and decision.offer.delivery_days >= NORTHWOOD.fastest_delivery


def test_round_one_counter_is_the_opening_ask() -> None:
    decision = respond(HARLOW, TARGET, 1, Offer(850, "standard", 7), Observed(tone="cooperative"))
    assert decision.action == "counter"
    assert decision.offer == opening_ask(HARLOW, TARGET) == Offer(1250, "standard", 21)


def test_counter_schedule_halfway_then_final() -> None:
    # Harlow seeing its best card: -8% -8%... cooperative -8%, fast -4%, fitd -4% -> reservation 756 (standard).
    obs = Observed(opening_ratio=0.85, tone="cooperative", tactic="fitd", speed="fast")
    lowball = Offer(500, "standard", 7)  # below reservation, too fast
    floor = reservation(HARLOW, TARGET, "standard", 14, obs)
    assert floor == pytest.approx(756)
    final = floor * config.FINAL_PRICE_FACTOR["strong"]  # 786.24

    r2 = counter(HARLOW, TARGET, 2, lowball, obs)
    assert r2.price == pytest.approx((1250 + final) / 2, abs=1)
    assert r2.delivery_days == 18  # halfway from 21 toward max(14, 7) = 14, rounded
    assert r2.quality == "standard"

    r3 = counter(HARLOW, TARGET, 3, lowball, obs)
    assert r3.price == pytest.approx(final, abs=1)
    assert r3.delivery_days == 14
    assert r3.price >= floor


def test_weak_supplier_final_counter_is_exactly_reservation() -> None:
    obs = Observed(opening_ratio=0.70, tone="firm", tactic="ditf", speed="slow")
    r3 = counter(QUICKFURN, TARGET, 3, Offer(500, "standard", 14), obs)
    floor = reservation(QUICKFURN, TARGET, "standard", 14, obs)
    assert r3.price == pytest.approx(floor, abs=1)


def test_counter_quality_follows_covered_request() -> None:
    # Northwood opens with Premium. A Standard request only sticks if the price covers Standard's reservation.
    obs = Observed(opening_ratio=0.85, tone="cooperative", tactic="fitd")  # -4% -3% -> 883.5 for standard
    covered = counter(NORTHWOOD, TARGET, 2, Offer(960, "standard", 14), obs)
    assert covered.quality == "standard"
    not_covered = counter(NORTHWOOD, TARGET, 2, Offer(800, "standard", 14), obs)
    assert not_covered.quality == "premium"


def test_counter_delivery_moves_toward_requested_but_not_below_fastest() -> None:
    obs = Observed(opening_ratio=0.85, tone="neutral", tactic="fitd")
    r3 = counter(QUICKFURN, TARGET, 3, Offer(500, "standard", 10), obs)
    assert r3.delivery_days == 10  # requested 10 >= fastest 7
    r3 = counter(NORTHWOOD, TARGET, 3, Offer(500, "premium", 7), obs)
    assert r3.delivery_days == 21  # requested 7 < fastest 21


def test_valuecraft_counter_gets_cheaper_when_buyer_accepts_slow_delivery() -> None:
    obs = Observed(opening_ratio=0.70, tone="firm", tactic="ditf", speed="slow")
    fast = counter(VALUECRAFT, TARGET, 3, Offer(500, "basic", 28), obs)
    slow = counter(VALUECRAFT, TARGET, 3, Offer(500, "basic", 42), obs)
    assert slow.delivery_days == 42
    assert slow.price < fast.price


# --- §6.2 observation helpers -------------------------------------------------


def test_observed_tactic() -> None:
    assert observed_tactic(Offer(700, "premium", 7)) == "ditf"
    assert observed_tactic(Offer(700, "premium", 8)) == "fitd"
    assert observed_tactic(Offer(700, "standard", 7)) == "fitd"
    assert observed_tactic(Offer(850, "standard", 14)) == "fitd"


def test_observed_speed() -> None:
    # opening 700, ask 1250: slow card claims 70% -> 865 (moved 30%); fast claims 40% -> 1030 (moved 60%)
    assert observed_speed(700, 865, 1250) == "slow"
    assert observed_speed(700, 1030, 1250) == "fast"
    assert observed_speed(700, 975, 1250) == "fast"  # exactly 50% counts as fast
    assert observed_speed(700, 700, 700) == "fast"  # no gap, nothing to concede


def test_majority_tone() -> None:
    assert majority_tone([]) == "neutral"
    assert majority_tone(["firm"]) == "firm"
    assert majority_tone(["cooperative", "firm"]) == "neutral"  # tie
    assert majority_tone(["cooperative", "firm", "cooperative"]) == "cooperative"
    assert majority_tone(["cooperative", "garbage", "garbage"]) == "cooperative"  # unknown labels ignored


def test_respond_derives_round_one_observations() -> None:
    # Callers only need to supply the tone in round 1; opening ratio and tactic come from the offer.
    decision = respond(HARLOW, TARGET, 1, Offer(700, "premium", 7), Observed(tone="cooperative"))
    assert decision.adjustments == {"tone=cooperative": -0.08, "aggressive_anchor": 0.08}

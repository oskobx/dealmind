"""Planned offers from the card (§4.3), guardrails (§4.4) and JSON extraction. No model calls."""

import pytest

from dealmind import config
from dealmind.cards import Card, card_from_dict, default_card, mutate_one_knob
from dealmind.config import SUPPLIERS
from dealmind.deals import make_deal, random_deal
from dealmind.llm import extract_json
from dealmind.negotiator import (
    Plan,
    apply_guardrails,
    days_at_claim,
    opening_offer,
    planned_offer,
    price_at_claim,
    quality_at_claim,
)
from dealmind.scoring import Offer

DEAL = make_deal("table", 30)  # target 1100
T = DEAL.target
ASK = Offer(1375, "standard", 21)  # a strong supplier's opening ask: 125%, standard, 21 days


def plan_round(card: Card, round_no: int, opening: Offer, last_counter: Offer, previous: Offer, believed="strong") -> Offer:
    return planned_offer(card, DEAL, round_no, opening, ASK, last_counter, previous, believed).offer


# --- round 1 -----------------------------------------------------------------


def test_opening_offer_default_card_is_aggressive_ditf() -> None:
    # §4.2/§4.3: 0.70 x target, Premium, 7 days. This is what makes Northwood walk (§6.3).
    assert opening_offer(default_card(), T) == Offer(770, "premium", 7)
    assert planned_offer(default_card(), DEAL, 1).offer == Offer(770, "premium", 7)
    assert planned_offer(default_card(), DEAL, 1).may_accept is False


def test_opening_offer_modest_fitd() -> None:
    card = card_from_dict(SUPPLIERS["northwood"].best_card)
    assert opening_offer(card, T) == Offer(935, "standard", 14)


# --- claim helpers -----------------------------------------------------------


def test_claim_helpers() -> None:
    assert price_at_claim(1375, 770, 1.0) == 770
    assert price_at_claim(1375, 770, 0.0) == 1375
    assert price_at_claim(1375, 770, 0.4) == pytest.approx(1133)
    assert days_at_claim(21, 7, 0.4) == 15  # 21 - 0.4*14 = 15.4
    assert days_at_claim(21, 7, 0.7) == 11  # 21 - 0.7*14 = 11.2
    assert days_at_claim(21, 14, 1.0) == 14
    assert quality_at_claim(0.7, "premium", "basic") == "premium"
    assert quality_at_claim(0.5, "premium", "basic") == "standard"
    assert quality_at_claim(0.3, "premium", "basic") == "basic"


# --- round 2: speed and trade-off ------------------------------------------


def test_round_two_speed_sets_the_price_claim() -> None:
    opening = Offer(770, "premium", 7)
    slow = mutate_one_knob(default_card(), "speed", "slow")  # gives_up=quality: price follows the claim
    fast = default_card()
    assert plan_round(slow, 2, opening, ASK, opening).price == round(price_at_claim(1375, 770, 0.70))  # 951
    assert plan_round(fast, 2, opening, ASK, opening).price == round(price_at_claim(1375, 770, 0.40))  # 1133


def test_round_two_gives_up_quality_jumps_to_supplier_level() -> None:
    opening = Offer(770, "premium", 7)
    offer = plan_round(default_card(), 2, opening, ASK, opening)
    assert offer.quality == "standard"  # the supplier's level
    assert offer.delivery_days == days_at_claim(21, 7, 0.40)  # delivery follows the claim: 15


def test_round_two_gives_up_delivery_jumps_to_supplier_days() -> None:
    card = mutate_one_knob(default_card(), "gives_up", "delivery")
    opening = Offer(770, "premium", 7)
    offer = plan_round(card, 2, opening, ASK, opening)
    assert offer.delivery_days == 21
    assert offer.quality == "standard"  # fast claim 0.40 is exactly the Standard threshold
    assert offer.price == round(price_at_claim(1375, 770, 0.40))


def test_round_two_gives_up_price_meets_counter_and_holds_other_terms() -> None:
    card = card_from_dict(SUPPLIERS["harlow"].best_card)  # fitd, modest, fast, cooperative, gives_up=price
    opening = Offer(935, "standard", 14)
    offer = plan_round(card, 2, opening, ASK, opening)
    assert offer == Offer(1375, "standard", 14)


# --- round 3: believed type and no retreat -----------------------------------


def test_round_three_goal_depends_on_believed_type() -> None:
    card = mutate_one_knob(default_card(), "speed", "slow")  # round 2 claims 70% -> 951
    opening = Offer(770, "premium", 7)
    r2 = plan_round(card, 2, opening, ASK, opening)
    assert r2.price == round(price_at_claim(1375, 770, 0.70))
    counter2 = Offer(1200, "standard", 18)
    strong = plan_round(card, 3, opening, counter2, r2, "strong")
    weak = plan_round(card, 3, opening, counter2, r2, "weak")
    assert strong.price == round(price_at_claim(1375, 770, 0.50))  # goal 50%: 1072
    assert weak.price == r2.price  # goal 80% would be 891, a retreat, so the price holds


def test_fast_card_holds_price_in_round_three_against_strong() -> None:
    # fast round-2 claim (40%) already concedes more than the strong goal (50%); no retreat.
    opening = Offer(770, "premium", 7)
    r2 = plan_round(default_card(), 2, opening, ASK, opening)
    r3 = plan_round(default_card(), 3, opening, Offer(1200, "standard", 18), r2, "strong")
    assert r3.price == r2.price


def test_plan_never_retreats_and_never_exceeds_counter() -> None:
    card = mutate_one_knob(default_card(), "speed", "slow")
    opening = Offer(770, "premium", 7)
    r2 = plan_round(card, 2, opening, ASK, opening)  # 951, standard?, ...
    counter2 = Offer(1000, "standard", 18)  # supplier came down a lot
    r3 = plan_round(card, 3, opening, counter2, r2)
    assert r2.price <= r3.price <= counter2.price
    assert r3.delivery_days >= min(r2.delivery_days, counter2.delivery_days)


def test_plan_allows_accept_only_when_counter_beats_plan() -> None:
    # §5: counters only improve round over round, so accepting early is allowed only when their counter
    # already scores at least as well as the offer we are about to make.
    opening = Offer(770, "premium", 7)
    weak_counter = Offer(1375, "standard", 21)  # scores ~42: above the walk-away line, below our plan
    assert planned_offer(default_card(), DEAL, 2, opening, ASK, weak_counter, opening).may_accept is False
    great_counter = Offer(900, "premium", 10)  # better than anything we would ask for
    assert planned_offer(default_card(), DEAL, 2, opening, ASK, great_counter, opening).may_accept is True


def test_plan_price_capped_at_136_percent_of_target() -> None:
    card = mutate_one_knob(default_card(), "gives_up", "price")
    opening = Offer(770, "premium", 7)
    huge = Offer(2000, "standard", 21)
    offer = planned_offer(card, DEAL, 2, opening, huge, huge, opening).offer
    assert offer.price <= config.MAX_PRICE_RATIO * T


# --- §4.4 guardrails ---------------------------------------------------------


PLAN = Plan(Offer(1000, "standard", 14), 0.5, "test", may_accept=True)
COUNTER = Offer(1100, "standard", 21)


def test_guardrails_clamp_price_to_five_percent_band() -> None:
    turn = apply_guardrails({"action": "offer", "price": 800, "quality": "standard", "delivery_days": 14, "message": "hi"}, PLAN, T, COUNTER)
    assert turn.offer.price == 950
    assert any("clamped" in d for d in turn.deviations)
    turn = apply_guardrails({"action": "offer", "price": 1040, "quality": "standard", "delivery_days": 14, "message": "hi"}, PLAN, T, COUNTER)
    assert turn.offer.price == 1040
    assert turn.deviations == []


def test_guardrails_force_plan_quality_and_delivery() -> None:
    turn = apply_guardrails({"action": "offer", "price": 1000, "quality": "premium", "delivery_days": 3, "message": "hi"}, PLAN, T, COUNTER)
    assert turn.offer == Offer(1000, "standard", 14)
    assert len(turn.deviations) == 2


def test_guardrails_accept_rules() -> None:
    accept = {"action": "accept", "price": 1100, "quality": "standard", "delivery_days": 21, "message": "deal"}
    assert apply_guardrails(accept, PLAN, T, COUNTER).action == "accept"
    assert apply_guardrails(accept, PLAN, T, COUNTER).offer == COUNTER
    # no counter on the table -> becomes an offer of the plan
    turn = apply_guardrails(accept, PLAN, T, None)
    assert turn.action == "offer" and turn.offer == PLAN.offer
    # a counter below the walk-away score can't be accepted early
    bad = Offer(1500, "basic", 42)
    assert apply_guardrails(accept, PLAN, T, bad).action == "offer"


def test_guardrails_fall_back_to_plan_on_bad_json() -> None:
    turn = apply_guardrails(None, PLAN, T, COUNTER)
    assert turn.action == "offer" and turn.offer == PLAN.offer and "json_fallback" in turn.deviations
    turn = apply_guardrails({"price": "lots", "message": ""}, PLAN, T, COUNTER)
    assert turn.offer == PLAN.offer and turn.message


# --- JSON extraction ---------------------------------------------------------


def test_extract_json() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('Sure! ```json\n{"a": {"b": "}"}}\n``` done') == {"a": {"b": "}"}}
    assert extract_json('text before {"action": "offer", "message": "a \\"quoted\\" word"} after') == {"action": "offer", "message": 'a "quoted" word'}
    assert extract_json("no json here") is None
    assert extract_json('{"broken": ') is None
    assert extract_json("") is None
    assert extract_json("[1, 2]") is None


# --- deals -------------------------------------------------------------------


def test_random_deal_is_seeded() -> None:
    assert random_deal(42) == random_deal(42)
    deal = random_deal(7)
    assert deal.product in config.PRODUCTS and deal.quantity in config.QUANTITIES
    assert make_deal("sofa", 100).target == 2850

"""Coach logic that runs in code (§8.1): fact-based diagnostics and one-knob candidate selection."""

import random

from dealmind.cards import card_key, default_card, mutate_one_knob
from dealmind.coach import available_changes, choose_next_card, diagnose
from dealmind.report import Report


def fake_report(outcome: str, closed_by: str | None, final: dict | None, our_prices: list[float], target: float = 1000) -> Report:
    offers = [
        {"by": "negotiator", "round": i + 1, "action": "offer", "price": p, "quality": "premium", "delivery_days": 7, "tone_label": "cooperative", "served_by": "x"}
        for i, p in enumerate(our_prices)
    ]
    facts = {
        "round": 1,
        "supplier": "harlow",
        "deal": {"product": "table", "quantity": 60, "target": target},
        "card": default_card().as_dict(),
        "offers": offers,
        "escalated_turns": 0,
        "outcome": outcome,
        "closed_by": closed_by,
        "final": final,
        "score": 50.0,
    }
    return Report(facts, "")


def test_walk_away_points_to_modest_anchor() -> None:
    notes, suggested = diagnose([fake_report("walk_away", None, None, [700])], default_card())
    assert "walked away" in notes[0]
    assert suggested == [("anchor", "modest")]


def test_immediate_acceptance_points_to_slow_speed() -> None:
    report = fake_report("deal", "supplier_accepted", {"price": 1000, "quality": "standard", "delivery_days": 14}, [700, 1000])
    notes, suggested = diagnose([report], default_card())
    assert "accepted our round-2 offer immediately" in notes[0]
    assert suggested[0] == ("speed", "slow")


def test_paying_above_target_with_gives_up_price_points_away_from_it() -> None:
    card = mutate_one_knob(default_card(), "gives_up", "price")
    report = fake_report("deal", "supplier_accepted", {"price": 1200, "quality": "premium", "delivery_days": 7}, [700, 1200])
    _, suggested = diagnose([report], card)
    assert ("gives_up", "quality") in suggested and ("gives_up", "delivery") in suggested


def test_basic_quality_points_to_giving_up_something_else() -> None:
    report = fake_report("deal", "supplier_accepted", {"price": 1000, "quality": "basic", "delivery_days": 24}, [700, 1000])
    notes, suggested = diagnose([report], default_card())
    assert any("basic" in n for n in notes)
    assert ("gives_up", "delivery") in suggested


def test_available_changes_excludes_tried() -> None:
    best = default_card()
    assert len(available_changes(best, set())) == 6
    tried = {card_key(mutate_one_knob(best, "speed", "slow"))}
    assert ("speed", "slow") not in available_changes(best, tried)


def test_choose_next_card_accepts_a_valid_untried_proposal() -> None:
    card, source = choose_next_card(default_card(), {"next_knob": "speed", "next_value": "slow"}, set(), random.Random(0))
    assert source == "coach" and card.speed == "slow"


def test_choose_next_card_prefers_suggested_when_proposal_is_invalid() -> None:
    card, source = choose_next_card(
        default_card(), {"next_knob": "anchor", "next_value": "aggressive"}, set(), random.Random(0), preferred=[("speed", "slow")]
    )
    assert source == "suggested_fallback" and card.speed == "slow"


def test_choose_next_card_skips_tried_and_falls_back() -> None:
    best = default_card()
    slow = mutate_one_knob(best, "speed", "slow")
    card, source = choose_next_card(best, {"next_knob": "speed", "next_value": "slow"}, {card_key(slow)}, random.Random(0))
    assert source == "random_fallback" and card != slow and card != best


def test_choose_next_card_when_everything_is_tried() -> None:
    best = default_card()
    tried = {card_key(c) for c in [mutate_one_knob(best, k, v) for k, v in available_changes(best, set())]}
    card, source = choose_next_card(best, None, tried, random.Random(0))
    assert source == "exhausted" and card == best

"""Cards (§4.1, §4.2) and one-knob mutations (§8.1)."""

import pytest

from dealmind import config
from dealmind.cards import (
    KNOBS,
    Card,
    card_from_dict,
    card_from_key,
    card_key,
    card_label,
    default_card,
    describe_change,
    diff_knobs,
    differs_in_one_knob,
    mutate_one_knob,
    neighbors,
)

ALL_MUTATIONS = [
    (knob, value)
    for knob in KNOBS
    for value in config.KNOB_VALUES[knob]
    if value != config.DEFAULT_CARD[knob]
]


@pytest.mark.parametrize(("knob", "value"), ALL_MUTATIONS)
def test_mutation_changes_exactly_one_knob(knob: str, value: str) -> None:
    before = default_card()
    after = mutate_one_knob(before, knob, value)
    assert diff_knobs(before, after) == [knob]
    assert getattr(after, knob) == value
    assert differs_in_one_knob(before, after)
    assert before == default_card()  # the original is untouched


def test_mutation_rejects_bad_input() -> None:
    card = default_card()
    with pytest.raises(ValueError):
        mutate_one_knob(card, "volume", "loud")  # unknown knob
    with pytest.raises(ValueError):
        mutate_one_knob(card, "anchor", "wild")  # unknown value
    with pytest.raises(ValueError):
        mutate_one_knob(card, "anchor", card.anchor)  # no change


def test_card_validates_values() -> None:
    with pytest.raises(ValueError):
        Card(tactic="fitd", anchor="modest", speed="slow", tone="angry", gives_up="price")


def test_default_card_has_aggressive_anchor() -> None:
    # §4.2 / CLAUDE.md rule 9: this is what makes Northwood walk away in round 1.
    card = default_card()
    assert card.anchor == "aggressive"
    assert card.as_dict() == config.DEFAULT_CARD


@pytest.mark.parametrize("supplier_key", list(config.SUPPLIERS))
def test_default_card_is_two_knobs_from_every_best_card(supplier_key: str) -> None:
    # §4.2: at least two knobs away from every supplier's best card, so there is room to climb.
    best = card_from_dict(config.SUPPLIERS[supplier_key].best_card)
    assert len(diff_knobs(default_card(), best)) >= 2


def test_key_round_trip_and_label() -> None:
    card = default_card()
    assert card_key(card) == "ditf,aggressive,fast,cooperative,quality"
    assert card_from_key(card_key(card)) == card
    assert card_label(card) == "ditf, aggressive, fast, cooperative, gives_up=quality"


def test_neighbors_are_all_distinct_one_knob_changes() -> None:
    card = default_card()
    nearby = neighbors(card)
    expected = sum(len(values) - 1 for values in config.KNOB_VALUES.values())
    assert len(nearby) == expected == 6
    assert len({card_key(c) for c in nearby}) == expected
    assert all(differs_in_one_knob(card, c) for c in nearby)


def test_describe_change() -> None:
    before = default_card()
    after = mutate_one_knob(before, "anchor", "modest")
    assert describe_change(before, after) == "anchor aggressive → modest"
    assert describe_change(before, before) == "no change"

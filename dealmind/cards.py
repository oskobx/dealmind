"""Strategy cards (SPEC §4.1, §4.2) and one-knob mutations for the coach's experiments (§8.1)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dealmind import config

# §4.1 the five knobs, in canonical order
KNOBS: tuple[str, ...] = tuple(config.KNOB_VALUES)


@dataclass(frozen=True)
class Card:
    tactic: str
    anchor: str
    speed: str
    tone: str
    gives_up: str

    def __post_init__(self) -> None:
        for knob in KNOBS:
            value = getattr(self, knob)
            allowed = config.KNOB_VALUES[knob]
            if value not in allowed:
                raise ValueError(f"invalid {knob}={value!r}; allowed: {allowed}")

    def as_dict(self) -> dict[str, str]:
        return {knob: getattr(self, knob) for knob in KNOBS}


def default_card() -> Card:
    """§4.2 the default starting card (aggressive anchor)."""
    return Card(**config.DEFAULT_CARD)


def card_from_dict(values: dict[str, str]) -> Card:
    return Card(**{knob: values[knob] for knob in KNOBS})


def card_key(card: Card) -> str:
    """Compact, stable key for 'tried cards' bookkeeping, e.g. 'ditf,aggressive,fast,cooperative,quality'."""
    return ",".join(getattr(card, knob) for knob in KNOBS)


def card_from_key(key: str) -> Card:
    return Card(**dict(zip(KNOBS, key.split(","), strict=True)))


def card_label(card: Card) -> str:
    """Human-readable form used in the playbook (§9.2), e.g. 'fitd, modest, slow, cooperative, gives_up=delivery'."""
    return f"{card.tactic}, {card.anchor}, {card.speed}, {card.tone}, gives_up={card.gives_up}"


def diff_knobs(a: Card, b: Card) -> list[str]:
    return [knob for knob in KNOBS if getattr(a, knob) != getattr(b, knob)]


def differs_in_one_knob(a: Card, b: Card) -> bool:
    """§8.1 step 5: a valid next candidate differs from the best card in exactly one knob."""
    return len(diff_knobs(a, b)) == 1


def mutate_one_knob(card: Card, knob: str, value: str) -> Card:
    """Return a copy of `card` with exactly one knob changed. Raises ValueError if that is impossible."""
    if knob not in KNOBS:
        raise ValueError(f"unknown knob {knob!r}; knobs: {KNOBS}")
    if value not in config.KNOB_VALUES[knob]:
        raise ValueError(f"invalid value {value!r} for {knob}; allowed: {config.KNOB_VALUES[knob]}")
    if getattr(card, knob) == value:
        raise ValueError(f"{knob} is already {value!r}; mutation would not change the card")
    mutated = replace(card, **{knob: value})
    assert differs_in_one_knob(card, mutated)
    return mutated


def neighbors(card: Card) -> list[Card]:
    """Every card that differs from `card` in exactly one knob, in knob order."""
    return [
        mutate_one_knob(card, knob, value)
        for knob in KNOBS
        for value in config.KNOB_VALUES[knob]
        if value != getattr(card, knob)
    ]


def describe_change(before: Card, after: Card) -> str:
    """Experiment-log wording (§9.2), e.g. 'anchor aggressive → modest'."""
    changed = diff_knobs(before, after)
    if not changed:
        return "no change"
    return "; ".join(f"{knob} {getattr(before, knob)} → {getattr(after, knob)}" for knob in changed)

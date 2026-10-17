"""The master file (§9.2). Structured state lives in state.json; playbook.md is rendered from it
plus the coach's prose. Every round is saved as runs/<run_id>/playbook/round_XX.md and the
latest copy goes to playbook.md at the repo root."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from dealmind import config
from dealmind.cards import card_from_dict, card_label

ROOT_PLAYBOOK = Path(__file__).resolve().parent.parent / "playbook.md"
MAX_DOSSIER_LINES = 10  # §9.2
MAX_BRIEFING_WORDS = 80  # §4
MAX_TACTICS_LINES = 6  # §8.3


@dataclass
class Experiment:
    round: int
    supplier: str
    change: str
    before: float | None
    after: float
    escalated_turns: int
    result: str  # "baseline" | "kept" | "discarded"


@dataclass
class SupplierState:
    key: str
    name: str
    candidate: dict[str, str]  # the card for the next round
    best: dict[str, str] | None = None
    best_score: float = 0.0
    best_round: int = 0
    briefing: str = ""
    dossier: list[str] = field(default_factory=list)
    believed_type: str = config.DEFAULT_BELIEVED_TYPE
    tried: dict[str, float] = field(default_factory=dict)  # card_key -> score
    scores: list[float] = field(default_factory=list)  # mean score per round
    failed: list[str] = field(default_factory=list)
    last_why: str = ""


@dataclass
class PlaybookState:
    run_id: str
    round: int = 0
    suppliers: dict[str, SupplierState] = field(default_factory=dict)
    general_tactics: list[str] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)


def new_state(run_id: str, supplier_keys: list[str]) -> PlaybookState:
    """Round 1: every specialist starts on the default card with an empty briefing (§8.1)."""
    suppliers = {k: SupplierState(k, config.SUPPLIERS[k].name, dict(config.DEFAULT_CARD)) for k in supplier_keys}
    return PlaybookState(run_id=run_id, suppliers=suppliers)


def to_dict(state: PlaybookState) -> dict:
    return asdict(state)


def from_dict(data: dict) -> PlaybookState:
    return PlaybookState(
        run_id=data["run_id"],
        round=data.get("round", 0),
        suppliers={k: SupplierState(**v) for k, v in data.get("suppliers", {}).items()},
        general_tactics=list(data.get("general_tactics", [])),
        experiments=[Experiment(**e) for e in data.get("experiments", [])],
    )


def save_state(state: PlaybookState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(state), indent=2), encoding="utf-8")


def load_state(path: Path) -> PlaybookState:
    return from_dict(json.loads(path.read_text(encoding="utf-8")))


# --- size caps (the coach's prose is clipped in code) ------------------------


def clip_lines(text: str | list[str], max_lines: int) -> list[str]:
    """Normalize the coach's prose into short lines. A single long paragraph is split into sentences."""
    raw = text if isinstance(text, list) else str(text).splitlines()
    lines = [str(line).strip().lstrip("-•* ").strip() for line in raw]
    lines = [line for line in lines if line]
    if len(lines) == 1 and len(lines[0]) > 160:
        lines = [part.strip() for part in re.split(r"(?<=[.!?])\s+", lines[0]) if part.strip()]
    return lines[:max_lines]


def clip_words(text: str, max_words: int) -> str:
    words = " ".join(str(text).split()).split(" ")
    return " ".join(words[:max_words]).strip()


# --- rendering ---------------------------------------------------------------


def _card_text(card: dict[str, str] | None) -> str:
    return card_label(card_from_dict(card)) if card else "-"


def render(state: PlaybookState) -> str:
    lines = [f"# DealMind Playbook (after round {state.round})", "", "## Supplier dossiers", ""]
    for s in state.suppliers.values():
        lines.append(f"### {s.name}")
        if s.best:
            lines.append(f"- Best card: {_card_text(s.best)} (score {s.best_score:.1f}, round {s.best_round})")
        else:
            lines.append("- Best card: not established yet")
        lines.append(f"- Briefing: {s.briefing or '(none yet)'}")
        lines.append(f"- Believed type: {s.believed_type}")
        if s.dossier:
            lines.append("- Learned:")
            lines.extend(f"  - {line}" for line in s.dossier)
        if s.failed:
            lines.append("- Failed: " + "; ".join(s.failed))
        if s.scores:
            lines.append("- Scores by round: " + " → ".join(f"{x:.1f}" for x in s.scores))
        lines.append(f"- Next card: {_card_text(s.candidate)}")
        lines.append("")
    lines += ["## General tactics", ""]
    lines += [f"- {t}" for t in state.general_tactics] or ["- (no lesson confirmed with two suppliers yet)"]
    lines += ["", "## Experiment log", "", "| Round | Supplier | Change | Score | Escalated turns | Result |", "|---|---|---|---|---|---|"]
    for e in state.experiments:
        name = state.suppliers[e.supplier].name if e.supplier in state.suppliers else e.supplier
        before = "–" if e.before is None else f"{e.before:.1f}"
        lines.append(f"| {e.round} | {name} | {e.change} | {before} → {e.after:.1f} | {e.escalated_turns} | {e.result} |")
    return "\n".join(lines) + "\n"


def save_round(state: PlaybookState, run_dir: Path) -> Path:
    """Write playbook/round_XX.md and state.json for this run, and refresh the repo-root playbook.md."""
    text = render(state)
    version = run_dir / "playbook" / f"round_{state.round:02d}.md"
    version.parent.mkdir(parents=True, exist_ok=True)
    version.write_text(text, encoding="utf-8")
    ROOT_PLAYBOOK.write_text(text, encoding="utf-8")
    save_state(state, run_dir / "state.json")
    return version

"""Negotiator reports (§9.1). Facts are filled in by code, never by a model; the negotiator
model writes 2-4 sentences of observations in its own session (same prompt and history)."""

from __future__ import annotations

from dataclasses import dataclass

from dealmind import config, events, llm
from dealmind.cards import card_from_dict, card_label
from dealmind.negotiation import NegotiationResult
from dealmind.scoring import Offer

OBSERVATION_MAX_TOKENS = 400
OBSERVATION_MAX_CHARS = 700


@dataclass
class Report:
    facts: dict
    observations: str

    def as_dict(self) -> dict:
        return {"facts": self.facts, "observations": self.observations}


def _offer_dict(offer: Offer | None) -> dict | None:
    if offer is None:
        return None
    return {"price": offer.price, "quality": offer.quality, "delivery_days": offer.delivery_days}


def build_facts(result: NegotiationResult, round_no: int) -> dict:
    """§9.1 facts, straight from the negotiation result."""
    return {
        "round": round_no,
        "supplier": result.supplier_key,
        "deal": {"product": result.deal.product, "quantity": result.deal.quantity, "target": round(result.deal.target)},
        "card": result.card.as_dict(),
        "offers": result.offers(),
        "escalated_turns": result.escalated_turns,
        "outcome": result.outcome,
        "closed_by": result.closed_by,
        "final": _offer_dict(result.final),
        "score": round(result.score, 1),
    }


def _fmt(offer: Offer | dict | None) -> str:
    if offer is None:
        return "-"
    if isinstance(offer, dict):
        return f"{offer['price']:.0f}/{offer['quality']}/{offer['delivery_days']}d"
    return f"{offer.price:.0f}/{offer.quality}/{offer.delivery_days}d"


def outcome_sentence(result: NegotiationResult) -> str:
    rounds_played = len(result.exchanges)
    score = f"score {result.score:.1f}/100"
    if result.outcome == "walk_away":
        return f"the supplier walked away in round {rounds_played}; no deal, score 0."
    if result.outcome == "no_deal":
        return "no deal; their final counter scored below our walk-away line, score 0."
    if result.closed_by == "supplier_accepted":
        return f"deal; the supplier accepted our round-{rounds_played} offer of {_fmt(result.final)}; {score}."
    if result.closed_by == "negotiator_accepted":
        return f"deal; we accepted their counter of {_fmt(result.final)} in round {rounds_played}; {score}."
    return f"deal; after round 3 we took their final counter of {_fmt(result.final)}; {score}."


def write_observations(result: NegotiationResult) -> str:
    """§9.1 observations: the negotiator model, in its own session, after the fact. Prose only."""
    session = result.session
    if session is None:
        return ""
    last = result.exchanges[-1] if result.exchanges else None
    supplier_said = last.supplier_message if last and last.supplier_message else "(no reply)"
    closing = (
        f"The negotiation is over. Outcome: {outcome_sentence(result)}\n"
        f'Supplier\'s last message: "{supplier_said}"\n'
        "Write your report for the coach: 2 to 4 sentences of observations. What seemed to work, what backfired, "
        "how the supplier reacted. Use only numbers that appear in this conversation. Plain text, not JSON."
    )
    messages = [{"role": "system", "content": session.system}, *session.history, {"role": "user", "content": closing}]
    try:
        text = llm.chat("report", config.MODEL_REPORT, messages, max_tokens=OBSERVATION_MAX_TOKENS, seed=session.seed)
    except llm.LLMError as exc:
        events.emit("report_llm_error", supplier=result.supplier_key, error=str(exc))
        text = ""
    if text.lstrip().startswith("{"):  # the system prompt asks for JSON; unwrap if the model obliged anyway
        parsed = llm.extract_json(text)
        if parsed:
            text = str(parsed.get("observations") or parsed.get("message") or text)
    text = " ".join(text.split())
    return text[:OBSERVATION_MAX_CHARS] or "No observations recorded."


def build_report(result: NegotiationResult, round_no: int) -> Report:
    report = Report(build_facts(result, round_no), write_observations(result))
    events.emit("report", supplier=result.supplier_key, round=round_no, facts=report.facts, observations=report.observations)
    return report


def report_text(report: Report) -> str:
    """Compact rendering for the coach prompt. Only facts and the negotiator's observations."""
    f = report.facts
    name = config.SUPPLIERS[f["supplier"]].name
    lines = [
        f"Report: round {f['round']}, {name}, {f['deal']['quantity']} {f['deal']['product']}s, target {f['deal']['target']}/piece.",
        f"Card: {card_label(card_from_dict(f['card']))}",
    ]
    for offer in f["offers"]:
        if offer["by"] == "negotiator":
            tone = f" (tone {offer['tone_label']})" if offer.get("tone_label") else ""
            verb = "accepted their counter" if offer["action"] == "accept" else f"offered {_fmt(offer)}"
            lines.append(f"R{offer['round']} negotiator {verb}{tone}")
        else:
            detail = f" {_fmt(offer)}" if offer["price"] is not None else ""
            lines.append(f"R{offer['round']} supplier: {offer['action']}{detail}")
    closed = f" ({f['closed_by']})" if f["closed_by"] else ""
    lines.append(f"Outcome: {f['outcome']} at {_fmt(f['final'])}, score {f['score']}{closed}")
    lines.append(f"Observations: {report.observations}")
    return "\n".join(lines)

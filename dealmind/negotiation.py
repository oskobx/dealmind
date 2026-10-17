"""The three-round loop for one deal (§5). Supplier decisions are made in code (§6.2);
Nemotron Nano writes the negotiator's words, Qwen writes the supplier's.

Debug entry point:  uv run python -m dealmind.negotiation --supplier northwood [--card best]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

from dealmind import config, events, llm
from dealmind.cards import Card, card_from_dict, card_label, default_card
from dealmind.config import SupplierCard
from dealmind.deals import Deal, make_deal, random_deal
from dealmind.negotiator import NegotiatorSession, Turn, planned_offer
from dealmind.scoring import Offer, score_offer
from dealmind.suppliers import Decision, Observed, majority_tone, observe_opening, observed_speed, respond
from dealmind.tone import label_tone

ROUNDS = 3


@dataclass
class Exchange:
    """One round: the negotiator's message and, unless it accepted, the supplier's reply."""

    round_no: int
    negotiator: Turn
    tone_label: str | None = None
    decision: Decision | None = None
    supplier_message: str | None = None


@dataclass
class NegotiationResult:
    supplier_key: str
    deal: Deal
    card: Card
    outcome: str  # "deal" | "no_deal" | "walk_away"
    final: Offer | None
    score: float
    closed_by: str | None  # "supplier_accepted" | "negotiator_accepted" | "final_counter" | None
    exchanges: list[Exchange]
    observed: Observed
    escalated_turns: int
    session: NegotiatorSession | None = None  # the negotiator's prompt + history, for the report (§9.1)

    def offers(self) -> list[dict]:
        """§9.1 facts: every structured offer, by whom, with tone label and serving model."""
        rows: list[dict] = []
        for ex in self.exchanges:
            t = ex.negotiator
            rows.append(
                {
                    "by": "negotiator",
                    "round": ex.round_no,
                    "action": t.action,
                    "price": t.offer.price,
                    "quality": t.offer.quality,
                    "delivery_days": t.offer.delivery_days,
                    "tone_label": ex.tone_label,
                    "served_by": t.served_by,
                }
            )
            if ex.decision is not None:
                d = ex.decision
                rows.append(
                    {
                        "by": "supplier",
                        "round": ex.round_no,
                        "action": d.action,
                        "price": d.offer.price if d.offer else None,
                        "quality": d.offer.quality if d.offer else None,
                        "delivery_days": d.offer.delivery_days if d.offer else None,
                    }
                )
        return rows


# --- §6.5 supplier voice (Qwen writes the words; numbers come from code) ------


def _decision_line(decision: Decision) -> str:
    o = decision.offer
    if decision.action == "counter" and o is not None:
        return f"counter. Your counteroffer is exactly: price {o.price:.0f} per piece, {o.quality} quality, delivery in {o.delivery_days} days."
    if decision.action == "accept" and o is not None:
        return f"accept. You accept their offer of price {o.price:.0f}, {o.quality}, {o.delivery_days} days."
    return "walk away. You end the negotiation. Be brief and cold."


def _fallback_voice(supplier: SupplierCard, decision: Decision) -> str:
    o = decision.offer
    if decision.action == "counter" and o is not None:
        return f"We can do {o.price:.0f} per piece for {o.quality} quality, delivered in {o.delivery_days} days."
    if decision.action == "accept" and o is not None:
        return f"Agreed: {o.price:.0f} per piece, {o.quality}, in {o.delivery_days} days. We have a deal."
    return f"This is not a serious offer. {supplier.name} is done here."


def supplier_voice(supplier: SupplierCard, decision: Decision, buyer_message: str, seed: int | None = None) -> str:
    """§6.5 persona prompt. The persona is the stable system prompt; the decision goes in the user turn."""
    system = (
        f"You are the sales manager at {supplier.name}, a furniture supplier. Personality: {supplier.persona}\n"
        "You are replying to a buyer from a furniture shop chain. Write 2-4 sentences in character. "
        "Do not change any number. Do not invent new terms. Reply with the message text only."
    )
    user = (
        f'The buyer wrote: "{buyer_message.strip()}"\n'
        f"Your decision for this turn has already been made: {_decision_line(decision)}\n"
        "Write your reply."
    )
    try:
        text = llm.chat("supplier", config.MODEL_SUPPLIER, [{"role": "system", "content": system}, {"role": "user", "content": user}], seed=seed)
    except llm.LLMError as exc:
        events.emit("supplier_llm_error", supplier=supplier.key, error=str(exc))
        text = ""
    return text.strip().strip('"') or _fallback_voice(supplier, decision)


# --- §5 the loop -------------------------------------------------------------


def negotiate(
    supplier: SupplierCard,
    deal: Deal,
    card: Card,
    briefing: str = "",
    believed_type: str = config.DEFAULT_BELIEVED_TYPE,
    seed: int | None = None,
    say=None,
) -> NegotiationResult:
    """Run one negotiation. `say(text)` receives human-readable progress lines if given."""
    target = deal.target
    session = NegotiatorSession(supplier.name, deal, card, briefing, seed)
    exchanges: list[Exchange] = []
    labels: list[str] = []
    obs = Observed()
    opening = supplier_ask = last_counter = previous = None
    supplier_message: str | None = None
    outcome, final, closed_by = "no_deal", None, None
    tell = say or (lambda _text: None)

    events.emit("negotiation_start", supplier=supplier.key, deal=deal.label, target=target, card=card.as_dict())
    tell(f"[{supplier.name}] {deal.label}, target {target:.0f}/piece, card: {card_label(card)}")

    for round_no in range(1, ROUNDS + 1):
        plan = planned_offer(card, deal, round_no, opening, supplier_ask, last_counter, previous, believed_type)
        turn = session.turn(round_no, plan, last_counter, supplier_message)
        exchange = Exchange(round_no, turn)
        exchanges.append(exchange)
        events.emit("negotiator_turn", supplier=supplier.key, round=round_no, action=turn.action, offer=turn.offer.__dict__, message=turn.message, served_by=turn.served_by, deviations=turn.deviations)

        if turn.action == "accept":
            outcome, final, closed_by = "deal", last_counter, "negotiator_accepted"
            tell(f"  R{round_no} NEGOTIATOR accepts their counter: {_fmt(final)}\n     \"{turn.message}\"")
            break
        tell(f"  R{round_no} NEGOTIATOR offers {_fmt(turn.offer)}\n     \"{turn.message}\"")

        # §6.2 observed behavior, measured in code from the actual message and offer
        exchange.tone_label = label_tone(turn.message)
        labels.append(exchange.tone_label)
        if round_no == 1:
            opening = turn.offer
            obs = observe_opening(Observed(tone=majority_tone(labels)), opening, target)
        else:
            obs = replace(obs, tone=majority_tone(labels))
            if round_no == 2:
                obs = replace(obs, speed=observed_speed(opening.price, turn.offer.price, supplier_ask.price))
        events.emit("tone", supplier=supplier.key, round=round_no, label=exchange.tone_label, observed=obs.__dict__)

        decision = respond(supplier, target, round_no, turn.offer, obs)
        exchange.decision = decision
        exchange.supplier_message = supplier_voice(supplier, decision, turn.message, seed)
        events.emit("supplier_turn", supplier=supplier.key, round=round_no, action=decision.action, offer=decision.offer.__dict__ if decision.offer else None, message=exchange.supplier_message)
        tell(f"     [tone: {exchange.tone_label}]\n  R{round_no} SUPPLIER {decision.action}" + (f" {_fmt(decision.offer)}" if decision.offer else "") + f"\n     \"{exchange.supplier_message}\"")

        if decision.action == "walk_away":
            outcome, closed_by = "walk_away", None
            break
        if decision.action == "accept":
            outcome, final, closed_by = "deal", turn.offer, "supplier_accepted"
            break
        last_counter = decision.offer
        if round_no == 1:
            supplier_ask = last_counter
        previous = turn.offer
        supplier_message = exchange.supplier_message
    else:
        # §5: after round 3 the negotiator takes the final counter if it scores >= ACCEPT_THRESHOLD
        if last_counter is not None and score_offer(last_counter, target) >= config.ACCEPT_THRESHOLD:
            outcome, final, closed_by = "deal", last_counter, "final_counter"
            tell(f"  After R3: NEGOTIATOR takes the final counter {_fmt(final)}")
        else:
            tell("  After R3: final counter rejected, no deal")

    score = score_offer(final, target) if outcome == "deal" else 0.0
    escalated = sum(1 for ex in exchanges if ex.negotiator.served_by and ex.negotiator.served_by != config.MODEL_NEGOTIATOR)
    events.emit("negotiation_end", supplier=supplier.key, outcome=outcome, final=final.__dict__ if final else None, score=round(score, 1), closed_by=closed_by)
    tell(f"  => {outcome.upper()}" + (f" at {_fmt(final)}" if final else "") + f", score {score:.1f}")
    return NegotiationResult(supplier.key, deal, card, outcome, final, score, closed_by, exchanges, obs, escalated, session)


def _fmt(offer: Offer | None) -> str:
    if offer is None:
        return "-"
    return f"{offer.price:.0f}/pc, {offer.quality}, {offer.delivery_days}d"


# --- debug entry point -------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one live negotiation and print the conversation.")
    parser.add_argument("--supplier", default="northwood", choices=list(config.SUPPLIERS))
    parser.add_argument("--card", default="default", help="'default', 'best', or 'tactic,anchor,speed,tone,gives_up'")
    parser.add_argument("--product", choices=list(config.PRODUCTS))
    parser.add_argument("--quantity", type=int, choices=config.QUANTITIES)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--briefing", default="")
    parser.add_argument("--believed", default=config.DEFAULT_BELIEVED_TYPE, choices=["strong", "weak"])
    parser.add_argument("--calls", action="store_true", help="print one line per model call")
    args = parser.parse_args()

    supplier = config.SUPPLIERS[args.supplier]
    if args.card == "default":
        card = default_card()
    elif args.card == "best":
        card = card_from_dict(supplier.best_card)
    else:
        from dealmind.cards import card_from_key

        card = card_from_key(args.card)
    deal = make_deal(args.product, args.quantity) if args.product and args.quantity else random_deal(args.seed)

    if args.calls:
        events.current().listeners.append(
            lambda e: print(f"    · {e['role']} {e['served_by']} {e['latency_s']}s tokens {e['prompt_tokens']}+{e['completion_tokens']} cached {e['cached_tokens']}")
            if e["kind"] == "llm_call"
            else None
        )
    negotiate(supplier, deal, card, args.briefing, args.believed, args.seed, say=print)


if __name__ == "__main__":
    main()

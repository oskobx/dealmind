# DealMind: Full Specification

> Negotiators that learn from every deal.

This is the complete design for DealMind, built at the Crusoe x Cerebral Valley
"Recursive Agents" hackathon (Sat Oct 17, 2026). Everything marked **LOCKED** was
agreed with Oskar. Everything marked **TUNABLE** is a starting value that we expect
to adjust after the first test runs. Do not change LOCKED items without asking.

---

## 1. The idea in one paragraph

A furniture shop chain buys from many suppliers. DealMind gives it a team of AI
negotiators, one specialist per supplier. After every negotiation, the negotiator
writes a report. A coach agent reads all reports, keeps a shared master file
(`playbook.md`) with a dossier on each supplier plus general tactics, and tunes each
specialist's strategy before the next negotiation, changing one thing at a time and
keeping a change only if it measurably wins. Over time the team learns how to
negotiate with each supplier. That accumulated supplier knowledge is the moat:
competitors can copy the agents, not years of knowledge about how each supplier
actually behaves.

Hackathon tracks covered:
- **Shared Brain:** the playbook is read by every negotiator before it works and
  updated by the coach after. It is kept lean (rewritten, size-capped) and current.
- **Version N+1:** the coach rewrites the negotiators' strategies and briefings,
  keeps a change only if it scores better, and we prove the gain on a supplier the
  team has never seen (Ridgeline).

---

## 2. A deal (LOCKED)

A deal is defined by a **product** and a **quantity**. Three terms are negotiated:

1. **Price per piece**
2. **Quality** (one of three levels)
3. **Delivery** (always in days)

### 2.1 Products and target prices (LOCKED)

| Product | Base target price per piece |
|---|---|
| Chair | 400 |
| Table | 1,100 |
| Bed | 1,800 |
| Sofa | 3,000 |

Volume discount applied to the target:

| Quantity | Target per piece |
|---|---|
| under 50 | base |
| 50–149 | base × 0.95 |
| 150 or more | base × 0.90 |

Example: 100 sofas → target 2,850 per piece. 30 chairs → target 400.

### 2.2 Quality levels (LOCKED)

| Level | Material | Make | Warranty |
|---|---|---|---|
| Basic | particleboard / MDF | stapled and glued joints | 1 year |
| Standard | plywood with wood veneer | screwed and doweled joints | 2 years |
| Premium | solid hardwood (oak) | mortise-and-tenon joints | 3 years |

The shop's target is **Standard**. **Premium** counts as a bonus.

### 2.3 Delivery (LOCKED)

Target: **14 days** for every deal, regardless of product or quantity.

### 2.4 Deal generation (TUNABLE)

Each negotiation gets a random deal from a seeded RNG:
- product: uniform over the four products
- quantity: one of `[20, 40, 60, 120, 180]`

Use a fixed seed per (round, supplier, deal index) so runs are reproducible and so the
Ridgeline comparison uses identical deals for both arms.

---

## 3. Scoring (LOCKED)

Every term gets 0 to 100 points. **Hitting the target is worth exactly 70.** Straight
lines between the anchor points. A deal that hits every target scores exactly 70.

### 3.1 Price score

Let `r = price / target_price` (target after volume discount).

| r | Points |
|---|---|
| r ≥ 1.36 | 0 |
| 1.00 ≤ r < 1.36 | 70 × (1.36 − r) / 0.36 |
| 0.82 < r < 1.00 | 70 + 30 × (1.00 − r) / 0.18 |
| r ≤ 0.82 | 100 |

### 3.2 Quality score

| Level | Points |
|---|---|
| Basic | 30 |
| Standard | 70 |
| Premium | 100 |

### 3.3 Delivery score

Let `d` = delivery days.

| d | Points |
|---|---|
| d ≥ 42 | 0 |
| 14 ≤ d < 42 | 70 × (42 − d) / 28 |
| 7 < d < 14 | 70 + 30 × (14 − d) / 7 |
| d ≤ 7 | 100 |

### 3.4 Deal score

```
deal_score = 0.5 × price_score + 0.3 × quality_score + 0.2 × delivery_score
```

**No deal = 0.** (Walk-away, or no agreement after round 3.)

### 3.5 Test cases (must pass; they match the spec spreadsheet)

| Product | Qty | Price | Quality | Days | Target | Price pts | Qual pts | Deliv pts | Deal |
|---|---|---|---|---|---|---|---|---|---|
| Table | 30 | 1,000 | Standard | 20 | 1,100 | 85.15 | 70 | 55 | **74.58** |
| Table | 30 | 1,200 | Premium | 14 | 1,100 | 52.32 | 100 | 70 | **70.16** |
| Sofa | 100 | 2,850 | Standard | 14 | 2,850 | 70 | 70 | 70 | **70.00** |

Use `pytest.approx(..., abs=0.01)`.

---

## 4. Negotiator strategy: knobs + prose briefing (LOCKED: hybrid)

Each negotiator's strategy has two layers:

1. **A strategy card of five knobs.** Used for measurement and for the coach's
   one-knob experiments. Stored as structured data.
2. **A prose briefing written by the coach** (max ~80 words). This is what the
   negotiator actually reads, together with the card. It carries the nuance the coach
   learned, e.g. *"Northwood is proud of its oak. Open respectfully, around 935. Ask
   about premium early. They're slow, so concede on delivery, not on price."*

### 4.1 The five knobs (LOCKED)

| Knob | Values | Code name |
|---|---|---|
| Tactic | foot in the door / door in the face | `tactic: "fitd" \| "ditf"` |
| Anchor | modest / aggressive | `anchor: "modest" \| "aggressive"` |
| Concession speed | slow / fast | `speed: "slow" \| "fast"` |
| Tone | firm / cooperative | `tone: "firm" \| "cooperative"` |
| Trade-off | gives up price / quality / delivery first | `gives_up: "price" \| "quality" \| "delivery"` |

### 4.2 Default starting card (LOCKED: must use aggressive anchor)

```
tactic=ditf, anchor=aggressive, speed=fast, tone=cooperative, gives_up=quality
```

This card is deliberately at least two knobs away from every supplier's best card, so
round-1 scores are mediocre and there is room to climb. The aggressive anchor
**guarantees Northwood walks away in round 1** (see §6.3).

### 4.3 What each knob does mechanically (TUNABLE numbers)

**Anchor → opening price (computed in code, not by the model):**
- aggressive: opening price = 0.70 × target
- modest: opening price = 0.85 × target

**Tactic → shape of the opening package:**
- **Door in the face (ditf):** round 1 asks for the extreme full package all at once:
  anchor price + Premium + 7 days. Then retreats sharply.
- **Foot in the door (fitd):** round 1 asks for a small, easy-to-accept package first:
  anchor price + Standard + 14 days (the shop's targets, nothing extra on the
  non-price terms). In rounds 2–3 it adds one extra ask (Premium or faster delivery)
  "as part of the package" while conceding on price.

**Concession speed and the claim schedule (from Oskar's handwritten note):**

The negotiator's position each round is expressed as a **claim %**: how much of the
gap between the negotiator's opening and the supplier's opening ask it still demands.
100% = the negotiator's opening, 0% = the supplier's opening ask.

```
price_at_claim(c) = supplier_ask − c × (supplier_ask − negotiator_opening)
```

| Round | Claim % |
|---|---|
| 1° | 100% (the opening) |
| 2° | slow: 70% / fast: 40% |
| 3° (goal) | 50% if supplier believed **strong** / 80% if supplier believed **weak** |

The supplier's opening ask is only known after its first reply, so rounds 2–3 are
computed after round 1. "Believed strong/weak" comes from the dossier; with no
evidence, assume **strong** (goal 50%).

Delivery uses the same claim formula between 7 days (negotiator ideal) and the
supplier's offered days, rounded to whole days. Quality: claim ≥ 70% → keep asking
for the level from the opening package; 40–70% → Standard; below 40% → accept the
supplier's offered level.

**Trade-off (`gives_up`):** in round 2 the given-up term jumps straight to the
supplier's current position on that term. The other two terms follow the claim
schedule. If `gives_up=price`, price moves to the supplier's current counter price in
round 2 (big concession) while quality and delivery hold at 100% claim.

**Tone:** passed to the model as an instruction for how to write the message. Tone is
not read from the card by the supplier: the supplier only reacts to the **observed**
tone of the actual messages (see §6.2).

### 4.4 The negotiator model's freedom (TUNABLE)

The code computes the planned offer for each round from the card. The negotiator model
(Nemotron Nano) receives the plan, the coach's briefing, the conversation so far, and
returns JSON:

```json
{
  "action": "offer" | "accept",
  "price": 980,
  "quality": "standard",
  "delivery_days": 18,
  "message": "Two to four sentences to the supplier."
}
```

Guardrails enforced in code:
- `action: "accept"` is only valid if a supplier counter is on the table.
- Price may deviate from the planned price by at most ±5%; otherwise clamp to the band
  and log a `deviation` event.
- Quality must be one of the three levels; delivery a positive integer.
- Never offer above 1.36 × target (0 points on price).
- If JSON parsing fails twice, use the planned offer with a generic message and log it.

---

## 5. How a negotiation runs (LOCKED for now: based on Oskar's note; revisit after testing)

Three rounds. Each round: one message from the negotiator, one reply from the supplier.

```
Round 1°: negotiator opening offer  → supplier: walk_away | accept | counter
Round 2°: negotiator offer          → supplier: accept | counter
Round 3°: negotiator final offer    → supplier: accept | final counter
After 3°: negotiator: accept final counter | reject (no deal)
```

- Northwood can walk away right after the round-1 offer (§6.3).
- The negotiator accepts the supplier's final counter if its deal score ≥ **40**
  (TUNABLE fixed walk-away; it is not a knob). Otherwise no deal, score 0.
- The negotiator may also accept an earlier counter via `action: "accept"`.

Each message has a **structured offer** (price, quality, delivery days) that code reads
and checks, plus a few sentences of talk written by the model. Tone and the coach's
briefing come through in the talk.

Expected cost: ~6 chat calls + up to 3 tone-label calls per negotiation, about 10
seconds, many in parallel.

---

## 6. Suppliers (LOCKED names and roles; TUNABLE numbers)

### 6.1 Design principles (why the suppliers look like this)

1. **Each supplier rewards a different card.** No single strategy beats everyone, so
   per-supplier knowledge matters (the moat).
2. **The default card is wrong for everyone**, at least two knobs from each best card.
3. **Big effects:** a hot button moves the reservation price by ~4–8%, which is
   ~7–13 deal points. Bigger than LLM noise.
4. **Reactions only to observable behavior.** The supplier never sees the card.
   Code measures the opening price, concession sizes, which term moved, and the tone
   label of each message.
5. **One dramatic moment:** Northwood walks away in round 1 with the default card.
6. **Shared rules so general lessons exist:** strong suppliers like modest and
   cooperative; weak suppliers cave to aggressive and firm. Ridgeline follows the
   strong pattern, so general tactics transfer.

### 6.2 Decisions are made in code; Qwen only speaks them

All supplier decisions (accept / counter / walk away, and every counter number) are
computed in `suppliers.py` from the secret card. **Qwen/Qwen3.8-27B only writes the
words**: it gets the supplier persona, the decision, the exact numbers, and the
conversation, and must not change the numbers. Code attaches the structured offer
itself, so the model cannot break the card. This keeps scores honest and repeatable.

**Observed behavior the supplier reacts to:**
- `opening_ratio` = negotiator's round-1 price / target
- `observed_tone` = majority label over the negotiator's messages so far, each labeled
  `firm | cooperative | neutral` by one short call to Nemotron Nano
  (prompt: "Label the tone of this negotiation message as firm, cooperative, or
  neutral. Answer with one word.")
- `observed_tactic` = ditf if the round-1 package asked for Premium AND ≤ 7 days,
  otherwise fitd
- `observed_speed` = slow if the negotiator's round-2 price moved less than 50% of the
  way from its opening toward the supplier's ask, otherwise fast
- `accepted_delivery` = delivery days in the final agreed offer

### 6.3 The secret cards

All prices are % of the shop's target price for that deal. "Reservation price" is the
lowest price the supplier accepts for a given offer.

```
reservation = target × floor × (1 + quality_adj[quality]) × (1 + sum(hot_button_adjustments))
```

| | Northwood Timber | QuickFurn | Harlow & Sons | ValueCraft | Ridgeline Furnishings (held out) |
|---|---|---|---|---|---|
| Personality | strong | weak | strong | weak | strong |
| Floor (Standard) | 95% | 85% | 90% | 78% | 88% |
| Quality adj: Basic | −10% | −10% | −10% | −10% | −10% |
| Quality adj: Premium | +3% (oak specialist) | +15% | +20% | +15% | +8% |
| Fastest delivery | 21 days | 7 days | 14 days | 28 days | 10 days |
| Opening ask | 125%, Premium, 28 d | 120%, Standard, 14 d | 125%, Standard, 21 d | 120%, Basic, 35 d | 125%, Standard, 17 d |
| Patience | 3 rounds | 3 rounds | 3 rounds | 3 rounds | 3 rounds |

**Hot buttons (adjustments to reservation, TUNABLE):**

**Northwood Timber** (strong, proud oak specialist, slow)
- **Walk-away:** `opening_ratio < 0.75` → ends the conversation immediately with a
  short, cold reply. Deal = 0. **This must fire with the default card (0.70).**
- observed tone cooperative → −4%
- observed tactic fitd → −3%
- Best card: `fitd, modest, slow, cooperative, gives_up=delivery`

**QuickFurn** (weak, fast delivery, premium is expensive for them)
- observed tone firm → −8%
- observed speed slow → −4%
- observed tactic ditf → −4%
- Best card: `ditf, aggressive, slow, firm, gives_up=quality`

**Harlow & Sons** (strong, relationship-driven, good on Standard)
- observed tone cooperative → −8%; firm → +5%
- `opening_ratio < 0.80` (aggressive) → +8%
- observed speed fast → −4% (good faith)
- observed tactic fitd → −4%
- Best card: `fitd, modest, fast, cooperative, gives_up=price`

**ValueCraft** (weak, cheapest, slow)
- each 7 days of `accepted_delivery` beyond 28 → −4% (max −12%)
- observed tone firm → −5%
- observed speed slow → −3%
- observed tactic ditf → −3%
- Best card: `ditf, aggressive, slow, firm, gives_up=delivery`

**Ridgeline Furnishings** (held out; strong; cares about delivery)
- `opening_ratio < 0.80` → +8%
- observed tone cooperative → −6%
- observed tactic fitd → −3%
- `accepted_delivery ≥ 21` → −5%
- Best card: `fitd, modest, slow, cooperative, gives_up=quality`

### 6.4 Supplier counter logic

- **Round 1 reply:** if walk-away triggers, walk away. Else if the negotiator's offer
  price ≥ reservation (for the offered quality) and delivery ≥ fastest delivery →
  accept. Else counter with the opening ask.
- **Counters in rounds 2 and 3:** price moves linearly from the opening ask toward a
  final price: `reservation × 1.04` for strong suppliers, `reservation × 1.00` for weak.
  Round 2 counter = halfway; round 3 counter = final price.
- **Quality in counters:** keep the supplier's opening level unless the negotiator's
  offer price covers the reservation for the requested level; then offer the
  requested level.
- **Delivery in counters:** `max(fastest_delivery, negotiator's requested days)`,
  moving from the opening days toward that value.
- **Accept rule (any round):** offer price ≥ reservation for the offered quality,
  and offered delivery ≥ fastest delivery.
- **Invariant (unit-tested):** a supplier never accepts or counters below its
  reservation, and never below its fastest delivery.

### 6.5 Supplier persona prompt (for Qwen)

System prompt template:

```
You are the sales manager at {name}, a furniture supplier. Personality: {persona}.
You are replying to a buyer from a furniture shop chain.
Your decision for this turn has already been made: {decision}.
{if counter: Your counteroffer is exactly: price {p} per piece, {quality} quality, delivery in {d} days.}
{if accept: You accept their offer of price {p}, {quality}, {d} days.}
{if walk_away: You end the negotiation. Be brief and cold.}
Write 2-4 sentences in character. Do not change any number. Do not invent new terms.
```

Personas (one line each):
- Northwood Timber: "Proud third-generation oak workshop. Values respect and craftsmanship. Hates lowball offers."
- QuickFurn: "High-volume fast-delivery operation. Under pressure to hit monthly sales numbers."
- Harlow & Sons: "Family business that values long-term partners and courtesy."
- ValueCraft: "Budget manufacturer with a long production queue. Price is everything."
- Ridgeline Furnishings: "Mid-size maker with a strong brand. Values buyers who plan ahead."

---

## 7. Agents and models (LOCKED)

| Role | Model | Calls |
|---|---|---|
| Negotiators (one specialist per supplier) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | many, fast |
| Tone labeler | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | one per negotiator message |
| Suppliers (voice only) | `Qwen/Qwen3.8-27B` | many |
| Coach | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` | few, once per supplier per round |

Measured latency on Oct 17: Nano ~1.1 s, Qwen ~1.3 s, Super ~3.5 s.

Crusoe API notes:
- Base URL `https://api.inference.crusoecloud.com/v1`, standard `openai` SDK.
- Key in `.env` as `CRUSOE_API_KEY`; load with `load_dotenv(override=True)`.
- **No `developer` role.** Use `system`.
- Some models reason before answering: use `max_tokens` ≥ 800 and handle an empty
  `content` by retrying once with a higher limit.
- Retry 429/503 with exponential backoff (1, 2, 4, 8 s; max 4 tries).
- Read `docs/crusoe-skill.md` for anything else Crusoe-specific.

### 7.1 Optional: NVIDIA NeMo Switchyard for negotiators (TUNABLE, behind a flag)

Goal: give a negotiator "more juice" when a negotiation gets hard, by routing its
calls through NeMo Switchyard's **escalation router**: start on Nano (weak tier),
escalate to Super (strong tier) when Switchyard's LLM judge detects trouble.

- **Applies to negotiators only.** The coach already uses the strongest model.
  Suppliers and the tone labeler always call Crusoe directly.
- **How it plugs in:** Switchyard runs as a local proxy
  (`switchyard serve --routing-profiles routes.yaml --port 4000`). Each key under
  `routes:` becomes a model name clients request over the OpenAI chat API. With
  `--router switchyard`, negotiator calls use `base_url=http://localhost:4000/v1` and
  `model="negotiator"`. Without the flag, they call Crusoe directly with Nano.
- **routes.yaml sketch** (check exact escalation-router keys against the docs:
  https://docs.nvidia.com/nemo/switchyard/routing/overview.md):

```yaml
defaults:
  api_key: ${CRUSOE_API_KEY}
  base_url: https://api.inference.crusoecloud.com/v1
  format: openai

routes:
  negotiator:
    type: escalation_router
    weak:
      model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
    strong:
      model: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B
```

- **Keep the experiments honest:** a score change could come from the knob change or
  from escalation. So record **which model actually served every negotiator turn**
  (from the response's `model` field) in the report facts and in `events.jsonl`. The
  coach sees how often each specialist escalated; the experiment log shows it as a
  column. For the clean before/after comparisons (training curve and Ridgeline), run
  with the flag off unless both arms use it.
- **Demo moment (if used):** the UI shows a small `⚡ Super` badge on a lane when a
  turn escalates, e.g. when Northwood goes cold.
- **Failure mode:** if Switchyard is not running or errors, fall back to direct Crusoe
  calls with Nano and log a `router_fallback` event. Never crash the demo over it.

---

## 8. One specialist per supplier, tuned by the coach (LOCKED)

### 8.1 Training round (per supplier, all suppliers in parallel)

1. The coach has chosen a **candidate card** for this supplier (round 1: the default
   card) plus a **briefing**.
2. The specialist runs **2 deals** with the candidate card (different seeded
   product/quantity). Card score = mean deal score of the 2 deals. Two deals per round
   reduce the noise problem: the coach should not chase luck.
3. Each deal produces a report (§9.1).
4. The coach compares the candidate with the best card so far:
   - Round 1: candidate becomes best.
   - Later rounds: if `candidate_score > best_score + 2.0` → **kept** (new best).
     Otherwise **discarded**, and the dossier notes the knob that failed.
5. The coach picks the next candidate: **the best card with exactly one knob
   changed.** The coach model chooses which knob and why, using the dossier and
   reports. Code validates that exactly one knob differs from the best card and that
   this exact card has not already been tried; if invalid, fall back to a random
   untried one-knob change.
6. The coach rewrites the supplier's dossier and briefing (§9.2).

Default schedule: **5 training rounds × 4 suppliers × 2 deals = 40 negotiations.**

### 8.2 Coach prompt outline (Nemotron Super)

Input: the supplier's current dossier, the best card and score, this round's candidate
card and score, the two reports from this round, the list of cards already tried, the
general tactics section. Output JSON:

```json
{
  "kept": true,
  "next_knob": "tone",
  "next_value": "cooperative",
  "why": "One sentence explaining the experiment.",
  "dossier": "Up to 10 lines, rewritten from scratch, replacing old beliefs.",
  "briefing": "Up to 80 words of prose the negotiator will read before the next deal.",
  "believed_type": "strong" | "weak"
}
```

`kept` is decided by code (§8.1 step 4) and passed in; the coach explains it. The coach
does not invent numbers: facts and scores come from the reports.

### 8.3 General tactics update

After all suppliers are processed each round, one extra coach call rewrites the
**General tactics** section: max 6 lines; a lesson is only allowed if it held with at
least **two** suppliers (cite which). Example: "Strong suppliers (Northwood, Harlow):
modest anchors and a cooperative tone close better."

---

## 9. Reports and the master file (LOCKED: keep it light; may add more later)

### 9.1 Negotiator report (one per deal)

Two parts:

**Facts: filled in by code, never by the model:**
```json
{
  "round": 3, "supplier": "harlow", "deal": {"product": "table", "quantity": 60, "target": 1045},
  "card": {"tactic": "fitd", "anchor": "modest", "speed": "fast", "tone": "cooperative", "gives_up": "price"},
  "offers": [ {"by": "negotiator", "round": 1, "price": 888, "quality": "standard", "delivery_days": 14, "tone_label": "cooperative", "served_by": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"}, ... ],
  "escalated_turns": 0,
  "outcome": "deal" | "no_deal" | "walk_away",
  "final": {"price": 990, "quality": "standard", "delivery_days": 14},
  "score": 74.1
}
```

**Observations: written by the negotiator model (Nano), 2–4 sentences:** what seemed
to work, what backfired, how the supplier reacted. Example: "They hardened immediately
after my opening offer and mentioned their oak twice."

Later (not now): also store the exact prompt the negotiator used.

### 9.2 `playbook.md` (the master file)

One readable markdown file the coach maintains, with three sections:

```markdown
# DealMind Playbook (after round 3)

## Supplier dossiers

### Northwood Timber
- Best card: fitd, modest, slow, cooperative, gives_up=delivery (score 76.2, round 3)
- Briefing: Northwood is proud of its oak. Open respectfully, around 935 ...
- Learned: walks away from openings below ~75% of target; premium is cheap for them;
  can't deliver under ~21 days; estimated floor ~95% of target.
- Failed: aggressive anchor (walked away, rounds 1 and 2).

### QuickFurn
...

## General tactics
- Strong suppliers (Northwood, Harlow): modest anchor and cooperative tone close better.
- Weak suppliers (QuickFurn, ValueCraft): firm tone pulls extra discount.

## Experiment log
| Round | Supplier | Change | Score | Escalated turns | Result |
|---|---|---|---|---|---|
| 2 | Northwood | anchor aggressive → modest | 0.0 → 68.4 | 0 | kept |
| 3 | Harlow | tone firm → cooperative | 61.0 → 74.2 | 1 | kept |
```

Rules:
- The coach **rewrites** each dossier rather than appending, so wrong beliefs get
  replaced. Max **10 lines** per dossier.
- The experiment log is appended by code, not the model.
- Every coach update saves a version: `runs/<run_id>/playbook/round_01.md` … so the demo
  can show round 1 next to round 5. The latest copy also goes to `playbook.md` at the
  repo root.
- Structured state (cards, scores, tried cards, believed type) lives in
  `runs/<run_id>/state.json`; `playbook.md` is rendered from it plus the coach's prose.

---

## 10. The held-out test: Ridgeline (LOCKED)

After training, run Ridgeline Furnishings, which no specialist has ever met:

- **Blank arm:** default card, empty briefing.
- **Informed arm:** the coach drafts a card and briefing for Ridgeline using **only the
  General tactics section** (no Ridgeline data; it is told only "new supplier,
  personality unknown").
- Each arm runs the **same 3 seeded deals**. Report both means and the difference.

If the informed arm wins, the general lessons transfer: that is the Version N+1 proof
on an unseen task. Expected: the informed arm picks modest + cooperative (the strong
pattern) and avoids the +8% aggressive-anchor penalty.

---

## 11. The demo (LOCKED)

Three minutes:

| Time | On screen |
|---|---|
| 0:00–0:20 | Pitch: a furniture chain buys from many suppliers; every negotiation teaches the next one. |
| 0:20–1:20 | Live run, rounds 1–5. Four lanes, one per supplier: offers scrolling, scores per round. Round 1: Northwood walks away. Then scores climb. |
| 1:20–2:00 | The playbook, round 1 vs round 5 side by side, plus one experiment-log line. |
| 2:00–2:40 | Ridgeline: blank vs informed specialist. The informed one wins. |
| 2:40–3:00 | The moat: supplier knowledge compounds; competitors can't copy it. |

**Format:** terminal UI with Python's `rich` (Live layout). Not Streamlit, and not a
dashboard as the main feature: the agents are the product.

Layout:
- Header: `DealMind · Round 3/5 · Crusoe Managed Inference · Nemotron`
- Four panels (one per supplier): current deal (product, qty, target), last 2–3 messages
  (shortened), current offer, outcome, score. Walk-away shown in red.
- Bottom: score table per supplier per round (with a small trend like `41 → 58 → 72`),
  plus the coach's latest one-line decision.

**Safety net:**
- Every run writes `runs/<run_id>/events.jsonl` (one event per message, decision,
  score, coach update).
- `replay.py <run_id> --speed 3` replays a saved run in the same UI. If the API is slow
  on stage, replay the saved run.
- Record the saved run for the required 1-minute submission video.

---

## 12. Open items for later (do not build now)

- Store the negotiator's exact prompt in each report.
- Revisit the three-round flow after testing.
- Humans as counterparts in the real product; profiles database of suppliers as a
  second revenue stream; other industries.

# DealMind

> Negotiators that learn from every deal.

A team of AI negotiator agents for a furniture shop chain. One specialist negotiator
per supplier. After every negotiation the negotiator writes a report; a coach agent
keeps a shared master file (`playbook.md`) with a dossier on each supplier plus general
tactics, and tunes each specialist one knob at a time, keeping a change only if it
measurably wins. Built at the Crusoe x Cerebral Valley "Recursive Agents" hackathon,
Sat Oct 17, 2026. Tracks: Shared Brain + Version N+1.

**The full design is in `docs/SPEC.md`. Read it before writing any code.** Section
numbers below (§) refer to it. Items marked LOCKED there were agreed with Oskar: do
not change them without asking. Items marked TUNABLE may be adjusted after test runs,
but say what you changed and why.

---

## Hard rules

1. **Never print, log, echo, or commit `.env` or the API key.** The repo is public.
   Before every commit run `git status` and confirm `.env` is not staged.
2. **Read `docs/crusoe-skill.md` before writing any Crusoe API code.**
3. **Crusoe does not support the `developer` role.** Use `system`.
4. **Hackathon rule: only code written today counts.** Do not copy in code from other
   projects. Write everything fresh in this repo.
5. **It must run live in a 3-minute demo.** Prefer simple, working code over clever
   code. If something is taking too long, stop and ask Oskar before adding complexity.
6. **No Streamlit, and no dashboard as the main feature** (banned by hackathon rules).
   The UI is a `rich` terminal view of the agents working.
7. **Supplier decisions are made in code, never by a model** (§6.2). Qwen only writes
   the supplier's words. Scores must not be fakeable by any model.
8. **Facts in reports come from code, never from a model** (§9.1). Models write
   observations and prose only.
9. **The default card must have an aggressive anchor** so Northwood walks away in
   round 1 (§4.2, §6.3). This is the demo's key moment; keep a test for it.
10. Keep the code small and readable. No frameworks (no LangChain, no agent SDKs).
    Plain Python + `openai` SDK + `rich` + `pytest`.

---

## Models (LOCKED, §7)

| Role | Model ID |
|---|---|
| Negotiators + tone labeler + report observations | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` |
| Suppliers (voice only) | `Qwen/Qwen3.8-27B` |
| Coach | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` |

Rate limits, measured Oct 17 on this account: `docs/crusoe-skill.md` §6 says 30 RPM per
project and per model, but 40 sequential calls each on Nano, Qwen and
`nvidia/Nemotron-3.5-Lightning-30B-A3B` produced no 429. What did fail is concurrency:
Lightning returns 429 `max_requests_limit (orchestrator)` above ~3 requests in flight, while
Nano and Qwen took 12 in parallel. So the tone labeler stays on Nano (Lightning was tried and
rejected), `llm.py` caps requests in flight per model (8, Lightning 2), and the RPM pacer is
off unless `DEALMIND_RPM` is set.

Optional (Step 4.5, flag off by default): negotiator calls can route through NVIDIA
NeMo Switchyard's escalation router, Nano → Super. See SPEC §7.1.

API: base URL `https://api.inference.crusoecloud.com/v1`, `openai` SDK, key from
`.env` as `CRUSOE_API_KEY` via `load_dotenv(override=True)`. Use `max_tokens` ≥ 800
(some models reason first); if `content` comes back empty, retry once with 1600. Retry
429/503 with backoff 1, 2, 4, 8 s. All model calls go through `dealmind/llm.py`.

---

## Environment

- Python 3.12, managed with `uv`. Run everything with `uv run ...`.
- Install extra deps once: `uv add rich pytest`
- Mac (Apple Silicon), VS Code.

---

## Project layout (create exactly this)

```
dealmind/
├── CLAUDE.md
├── README.md
├── playbook.md                # latest master file, copied from the newest run
├── docs/
│   ├── SPEC.md                # full design (source of truth)
│   └── crusoe-skill.md        # Crusoe reference
├── dealmind/
│   ├── __init__.py
│   ├── config.py              # products, targets, discounts, quality, scoring constants,
│   │                          # model IDs, supplier secret cards, default card
│   ├── llm.py                 # Crusoe client, retries, JSON extraction, call logging
│   ├── scoring.py             # target_price(), price/quality/delivery/deal scores
│   ├── cards.py               # Card dataclass, KNOBS, mutate_one_knob(), card_key()
│   ├── deals.py               # seeded deal generator
│   ├── suppliers.py           # reservation price, hot buttons, accept/counter/walk logic
│   ├── tone.py                # tone labeler (Nano, one word)
│   ├── negotiator.py          # planned offers from card, prompt, JSON parsing, guardrails
│   ├── negotiation.py         # the 3-round loop for one deal → result + facts
│   ├── report.py              # builds report: facts (code) + observations (Nano)
│   ├── coach.py               # per-supplier update, general tactics, Ridgeline drafting
│   ├── playbook.py            # state.json ↔ playbook.md rendering, versioning, exp. log
│   ├── events.py              # append-only events.jsonl writer
│   └── ui.py                  # rich Live layout (used by run and replay)
├── routes.yaml                # optional Switchyard routes (Step 4.5); no secrets inside
├── run.py                     # `uv run run.py --rounds 5 [--router switchyard]` : training + Ridgeline test
├── replay.py                  # `uv run replay.py <run_id> --speed 3`
├── tests/
│   ├── test_scoring.py
│   ├── test_suppliers.py
│   ├── test_cards.py
│   └── test_negotiator_plan.py
└── runs/                      # one folder per run (commit the demo run only)
    └── <run_id>/
        ├── events.jsonl
        ├── state.json
        ├── results.json
        └── playbook/round_01.md ...
```

---

## Build order (do these in order; stop at each checkpoint and show Oskar)

Target times are for Sat Oct 17. Submissions close at 17:00.

### Step 1: config + scoring (target: 13:15)
- `config.py` with every constant from §2, §3, §4.2, §6.3, §7.
- `scoring.py`: `target_price(product, qty)`, `price_score`, `quality_score`,
  `delivery_score`, `deal_score` (no deal → 0).
- `tests/test_scoring.py` with the three cases in §3.5 (74.58, 70.16, 70.00) plus edges
  (r = 1.36, r = 0.82, d = 42, d = 7).
- **Checkpoint:** `uv run pytest` green.

### Step 2: cards + suppliers, no LLM (target: 13:45)
- `cards.py`: frozen dataclass with the five knobs; `mutate_one_knob(card, knob, value)`;
  validation that two cards differ in exactly one knob.
- `suppliers.py`: reservation formula, all hot buttons, round-1 walk-away, counter
  schedule, accept rule (§6.3, §6.4). Pure functions taking observed behavior as input.
- `tests/test_suppliers.py`:
  - Northwood walks away when opening_ratio = 0.70 (default card), not at 0.85.
  - No supplier ever accepts or counters below reservation or below fastest delivery
    (loop over all suppliers, qualities, observed combos).
  - Each supplier's best card (§6.3) yields a lower reservation than the default card.
- `tests/test_cards.py`: mutation changes exactly one knob.
- **Checkpoint:** tests green.

### Step 3: one live negotiation end to end (target: 14:30)
- `llm.py`, `tone.py`, `negotiator.py` (planned offers from the claim schedule §4.3,
  model JSON output, ±5% guardrail §4.4), `negotiation.py` (3 rounds §5).
- A debug entry point: `uv run python -m dealmind.negotiation --supplier northwood`
  prints the full conversation, structured offers, outcome and score.
- **Checkpoint:** run against Northwood with the default card → walk-away in round 1.
  Run Harlow with its best card → a deal scoring clearly above the default card.

### Step 4: reports + coach + playbook (target: 15:30)
- `report.py` (§9.1), `coach.py` (§8.1–8.3), `playbook.py` (§9.2), `events.py`.
- `run.py`: rounds loop; all suppliers in parallel with `ThreadPoolExecutor(max_workers=8)`;
  2 deals per supplier per round; coach update after each round; save playbook version.
- **Checkpoint:** `uv run run.py --rounds 3` (plain prints are fine here). Mean scores
  should rise for at least 3 of 4 suppliers, and Northwood must go from 0 in round 1 to
  a deal by round 2 or 3. Show Oskar the playbook diff between round 1 and round 3.

### Step 4.5: optional NeMo Switchyard for negotiators (only if it's before 15:30)
- Follow SPEC §7.1. Negotiators only; coach, suppliers and tone labeler stay direct.
- Add `routes.yaml` (key comes from the environment via `${CRUSOE_API_KEY}`; never
  write the key into the file) and a `--router switchyard` flag on `run.py`.
  Default is off.
- `llm.py`: when the flag is on, negotiator calls go to `http://localhost:4000/v1`
  with `model="negotiator"`; record the response's `model` field as `served_by`.
  If the proxy is down or errors, fall back to direct Nano and log `router_fallback`.
- Add `escalated_turns` to report facts and the experiment log (SPEC §9).
- **Timebox: 30 minutes.** If install or routing isn't working by then, stop, leave
  the flag off, and move to Step 5. Tell Oskar what blocked it.
- **Checkpoint:** one Northwood negotiation through Switchyard; `served_by` shows
  which model handled each turn.

### Step 5: Ridgeline held-out test (target: 15:50)
- Blank vs informed arm on the same 3 seeded deals (§10). Print both means.
- **Checkpoint:** informed arm beats blank arm.

### Step 6: rich UI + replay (target: 16:20)
- `ui.py` layout from §11; `run.py` uses it by default (`--plain` to disable).
- `replay.py` reads `events.jsonl` and drives the same UI at `--speed N`.
- **Checkpoint:** a full 5-round run looks good live; replay of that run works.

### Step 7: demo assets (target: 16:45)
- Commit the best full run under `runs/demo/`.
- README: what it is, how to run, the architecture in a few lines, what was built today.
- Oskar records the 1-minute video from the replay.

If behind schedule, cut in this order: Switchyard (Step 4.5) → replay speed controls → UI polish → general
tactics section (keep dossiers) → Ridgeline. Never cut: Northwood walk-away, the
learning loop, the playbook file.

---

## Coding conventions

- Type hints everywhere; dataclasses for Card, Deal, Offer, NegotiationResult, Report.
- Every model call: `llm.chat(role_name, model, messages, max_tokens) -> str`, logs
  model, latency and token usage to the events file (never the key).
- JSON from models: ask for JSON only, then extract the first `{...}` block; on parse
  failure retry once with "Return valid JSON only."; then fall back as specified.
- Seed everything (`random.Random(seed)`), so runs are reproducible.
- Print numbers rounded: prices to whole units, scores to 1 decimal.
- Small functions, no clever metaprogramming. Comments only where a rule from the spec
  is implemented (cite the § number).

---

## Commit messages

Short, present tense, e.g. `Add supplier logic and tests`. Commit after each
checkpoint. Push regularly; the repo must be public and up to date at 17:00.

# DealMind

> Negotiators that learn from every deal.

A furniture shop chain buys from many suppliers. DealMind gives it a team of AI
negotiators, one specialist per supplier. After every negotiation the specialist writes a
report; a coach reads the reports, keeps one shared master file (`playbook.md`) with a
dossier on each supplier plus general tactics, and tunes each specialist one knob at a
time, keeping a change only if it measurably wins. Over a training run the team learns how
each supplier actually behaves, and the general lessons carry over to a supplier nobody on
the team has ever met.

Built in one day at the Crusoe x Cerebral Valley **Recursive Agents** hackathon,
Saturday October 17, 2026. Tracks: Shared Brain + Version N+1. Everything in this repo was
written that day; the full design is in [docs/SPEC.md](docs/SPEC.md).

## How to run

Python 3.12 with `uv`. Put a Crusoe Managed Inference key in `.env` as `CRUSOE_API_KEY`.

```bash
uv run pytest                                  # 102 tests, no model calls
uv run run.py --rounds 5 --run-id demo2        # training run + Ridgeline test -> runs/demo2/
uv run server.py --run demo2                   # web UI, follows the run live as it writes events
uv run replay.py demo2 --speed 3               # replay a recorded run in the same UI
uv run python -m dealmind.negotiation --supplier northwood --calls   # one negotiation, printed
```

`run.py` also takes `--ridgeline-only <run_id>` to rerun the held-out test on a finished
run, `--no-ridgeline`, and `--router switchyard` (see below).

## Architecture

- **Specialist negotiators** (Nemotron 3 Nano): one per supplier. Code computes each
  round's planned offer from a five-knob strategy card (tactic, anchor, concession speed,
  tone, which term to give up first) and the coach's briefing; the model writes the words
  and may nudge the price within 5%. Guardrails in code.
- **Suppliers**: every decision (accept, counter, walk away, every counter number) is made
  in code from a secret card with hot buttons that react only to observed behavior: the
  opening ratio, the tone label of each message, the tactic and the concession speed.
  Qwen 3.8 only voices the decision, and its reply is validated so it cannot change,
  invent or spell out a number. Scores cannot be faked by any model.
- **Coach** (Nemotron 3 Super): after each round, code decides kept or discarded (a
  candidate must beat the best card by more than 2 points), code computes diagnostics from
  the report facts, and the model picks the next one-knob experiment, rewrites the dossier
  and writes the briefing. Code validates the experiment and falls back if needed.
- **Shared playbook**: `playbook.md` is rendered from `state.json` after every round, with
  a dossier per supplier, a general-tactics section that only admits lessons backed by
  experiments on two or more suppliers, and an experiment log. Versions are saved per round.
- **Held-out test**: Ridgeline Furnishings is negotiated by a blank specialist and by one
  whose card and briefing the coach drafted from the general tactics alone, on the same
  three seeded deals.

Everything runs on Crusoe Managed Inference through the OpenAI SDK, with per-model
in-flight caps and jittered backoff; every event goes to `runs/<run_id>/events.jsonl`,
which the web UI and the replay read.

## The demo run (`runs/demo2`)

Five rounds, four suppliers, two deals per supplier per round. Deal score is 0 to 100,
hitting every target is 70, no deal is 0.

| Supplier | Round 1 | Best card score | Best card |
|---|---|---|---|
| Northwood Timber | 0.0 (walked away) | 77.3 | ditf, modest, fast, cooperative, gives up quality |
| QuickFurn | 72.6 | 86.8 | ditf, aggressive, slow, cooperative, gives up quality |
| Harlow & Sons | 66.6 | 82.5 | fitd, modest, slow, cooperative, gives up quality |
| ValueCraft | 53.0 | 86.3 | ditf, aggressive, slow, cooperative, gives up price |

Ridgeline, never seen in training: **informed 82.5 vs blank 67.9** on the same three deals.
The coach drafted the informed specialist's card from the two tactics the team learned on
its own, slow concessions and a cooperative tone, each confirmed on QuickFurn, Harlow and
ValueCraft. Across three full runs, the informed specialist beat the blank one every time
(+14.6, +14.6, +3.2).

## Switchyard

NVIDIA NeMo Switchyard is wired in as an escalation router for negotiator calls
(`routes.toml`, `--router switchyard`, off by default, falls back to direct Nano if the
proxy is down). In our test negotiations the judge never escalated to Super; every routed
turn was served by Nano.

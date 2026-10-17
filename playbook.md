# DealMind Playbook (after round 3)

## Supplier dossiers

### Northwood Timber
- Best card: ditf, modest, fast, cooperative, gives_up=quality (score 77.3, round 2)
- Briefing: Open with DITF: premium quality, 7-day delivery at 85% target price. Hold firm on price and quality; concede delivery only if needed. Use cooperative tone to build trust.
- Believed type: strong
- Learned:
  - Northwood Timber values craftsmanship and perceives lowball offers as insulting.
  - They walk away quickly when the opening price is seen as disrespectful.
  - They do not concede on price easily and expect a credible starting point.
  - Aggressive anchoring (70% of target) triggers immediate rejection.
  - A modest opening (85% of target) keeps them at the table and builds credibility.
  - They reward respect for quality and punish perceived weakness or disrespect.
  - Speed of concession is irrelevant if the opening is rejected outright.
  - They likely have a firm floor near their target price, as deals closed at 98% of target.
  - Cooperative tone helps, but only when paired with a credible anchor.
  - Premium quality and 21-day delivery were accepted; deviations likely reduce score.
- Failed: gives_up quality → price (round 3: 61.5 vs best 77.3)
- Scores by round: 0.0 → 77.3 → 61.5
- Next card: ditf, modest, fast, cooperative, gives_up=delivery

### QuickFurn
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 86.8, round 2)
- Briefing: Use DITF with aggressive anchor, slow speed, cooperative tone, and now give up price first in round 2. This tests whether delaying price concession lets us retain more value while still securing acceptance through cooperative framing and gradual movement.
- Believed type: weak
- Learned:
  - QuickFurn accepts round-2 offers at our target price without pushback.
  - They concede most of the gap quickly when we use fast speed.
  - Likely floor is near our target price if we slow concessions.
  - They respond well to cooperative tone and DITF tactic.
  - Price flexibility exists; we may be leaving money on the table.
  - Quality and delivery concessions are accepted but not demanded.
  - No walk-aways observed; openings are not too extreme.
  - Supplier appears motivated by volume and schedule certainty.
  - Believed type: weak due to quick acceptance and full concession.
  - Next test: modest anchor to test if we can start higher and still close.
- Failed: anchor aggressive → modest (round 3: 78.1 vs best 86.8)
- Scores by round: 72.6 → 86.8 → 78.1
- Next card: ditf, aggressive, slow, cooperative, gives_up=price

### Harlow & Sons
- Best card: ditf, modest, slow, cooperative, gives_up=quality (score 81.4, round 3)
- Briefing: For the next deal, use ditf, modest, slow, cooperative, gives_up=price. Start with premium +7 days, then concede slowly on price while holding quality and delivery firm. Frame moves as fair steps toward mutual gain.
- Believed type: weak
- Learned:
  - Harlow & Sons accepted round-2 offers quickly at 94% of target with standard quality and 14-day delivery.
  - They countered initially at ~130-125% of target, showing significant room to negotiate.
  - Cooperative tone and framing concessions as fair compromises facilitated smooth acceptance.
  - They value partnership and long-term value, responding well to collaborative framing.
  - Conceding quality early enabled quick deals but may have left price improvement on the table.
  - No walk-away or hardening observed; they engage constructively under cooperative tone.
  - Likely floor is near target (100%) or slightly below if we anchor modestly and concede slowly.
  - They punish overly aggressive opens (risk of walk-away) but reward patience and tone.
  - Slow concession speed builds trust but may not extract maximal price concessions.
  - Next test: modest anchor to see if we can drive price closer to or below target without walk-away risk.
- Scores by round: 66.6 → 75.3 → 81.4
- Next card: ditf, modest, slow, cooperative, gives_up=price

### ValueCraft
- Best card: ditf, aggressive, slow, cooperative, gives_up=delivery (score 81.0, round 3)
- Briefing: ValueCraft accepts cooperative, incremental deals quickly. Open modestly at 85% of target price with DITF (premium +7 days), then concede slowly in round 2. Hold firm on quality; concede delivery first if needed. Their floor is near target — don’t leave money on the table.
- Believed type: weak
- Learned:
  - ValueCraft accepts round-2 offers at target price without hesitation.
  - They countered with high price and long delivery, then accepted our step-down.
  - They value cooperative tone and incremental concessions.
  - Conceding quality first did not hurt us; basic quality was accepted.
  - They did not walk away from aggressive anchor (266 vs 380 target).
  - They moved significantly in round 2, suggesting flexibility.
  - Fast concession speed led us to give up too much price too soon.
  - Likely floor is near target price if we slow concessions.
  - They reward patience and punish rushed concessions.
  - Believed type: weak — they concede most of the gap quickly.
- Scores by round: 53.0 → 69.5 → 81.0
- Next card: ditf, modest, slow, cooperative, gives_up=delivery

## General tactics

- Weak suppliers (QuickFurn, Harlow & Sons, ValueCraft): slow concession speed in round 2 improves score over fast speed.

## Experiment log

| Round | Supplier | Change | Score | Escalated turns | Result |
|---|---|---|---|---|---|
| 1 | Northwood Timber | baseline (default card) | – → 0.0 | 0 | baseline |
| 1 | QuickFurn | baseline (default card) | – → 72.6 | 0 | baseline |
| 1 | Harlow & Sons | baseline (default card) | – → 66.6 | 0 | baseline |
| 1 | ValueCraft | baseline (default card) | – → 53.0 | 0 | baseline |
| 2 | Northwood Timber | anchor aggressive → modest | 0.0 → 77.3 | 0 | kept |
| 2 | QuickFurn | speed fast → slow | 72.6 → 86.8 | 0 | kept |
| 2 | Harlow & Sons | speed fast → slow | 66.6 → 75.3 | 0 | kept |
| 2 | ValueCraft | speed fast → slow | 53.0 → 69.5 | 0 | kept |
| 3 | Northwood Timber | gives_up quality → price | 77.3 → 61.5 | 0 | discarded |
| 3 | QuickFurn | anchor aggressive → modest | 86.8 → 78.1 | 0 | discarded |
| 3 | Harlow & Sons | anchor aggressive → modest | 75.3 → 81.4 | 0 | kept |
| 3 | ValueCraft | gives_up quality → delivery | 69.5 → 81.0 | 0 | kept |

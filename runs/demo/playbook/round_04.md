# DealMind Playbook (after round 4)

## Supplier dossiers

### Northwood Timber
- Best card: ditf, modest, fast, cooperative, gives_up=quality (score 77.3, round 2)
- Briefing: Open with the extreme package (premium + 7 days) using a cooperative tone and modest anchor (85% of target). Concede slowly in round 2, holding firm on price while yielding on quality or delivery only if necessary to close.
- Believed type: strong
- Learned:
  - Northwood Timber walks away from openings at 70% of target price.
  - They perceive lowball offers as disrespect to their craftsmanship.
  - They hold firm on price and do not concede quickly.
  - They respond negatively to aggressive anchoring regardless of tone or package.
  - They are likely a strong negotiator with a high reservation price.
  - They expect pricing closer to market or target value.
  - They do not engage if the initial offer feels exploitative.
  - Conceding on quality or delivery early did not matter — they left before round 2.
  - A higher opening offer is needed to initiate negotiation.
  - They reward respect for craftsmanship and punish perceived lowballing.
- Failed: gives_up quality → price (round 3: 62.3 vs best 77.3); gives_up quality → delivery (round 4: 54.2 vs best 77.3)
- Scores by round: 0.0 → 77.3 → 62.3 → 54.2
- Next card: ditf, modest, slow, cooperative, gives_up=quality

### QuickFurn
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 86.8, round 2)
- Briefing: Open with the ditf tactic (premium +7 days), aggressive anchor (70% of target), slow concessions, cooperative tone, and be prepared to concede on price first in round 2 to avoid giving away value on quality or delivery unnecessarily.
- Believed type: weak
- Learned:
  - QuickFurn accepts offers at target price when delivered by round 2
  - They concede little in round 1, offering far above target
  - They respond well to cooperative tone and standard quality
  - Fast concession speed leads to early agreement at target, leaving value on table
  - They likely have a firm floor near their initial counter
  - Premium quality is not required; standard quality is acceptable
  - Delivery faster than 14 days is acceptable and may be expected
  - They anchor high but will deal if we meet their target with reasonable terms
  - Best outcomes occur when we match their target price with improved delivery or quality
  - They punish overly aggressive anchors by walking away
- Failed: anchor aggressive → modest (round 3: 78.1 vs best 86.8); tactic ditf → fitd (round 4: 82.5 vs best 86.8)
- Scores by round: 72.6 → 86.8 → 78.1 → 82.5
- Next card: ditf, aggressive, slow, cooperative, gives_up=price

### Harlow & Sons
- Best card: ditf, modest, slow, cooperative, gives_up=quality (score 81.4, round 3)
- Briefing: Continue with ditf, modest, slow, cooperative tone, but now concede delivery first in round 2. This tests whether yielding on timing preserves more value on price and quality, given their flexibility observed in past rounds.
- Believed type: weak
- Learned:
  - Harlow & Sons accept round-2 offers without counter, indicating eagerness to close.
  - They countered extreme openings with high asks but moved toward our position with cooperative framing.
  - Final deals closed at 94% of target price, standard quality, and 14-day delivery.
  - They value partnership and respond positively to fair, reasonable framing.
  - They concede little on price unless pressed but accept reasonable compromises.
  - Likely floor is near standard quality and 14–15 day delivery.
  - They punish overly aggressive openings but reward steady, cooperative movement.
  - Speed of concession is still too fast — we leave value on the table.
  - Best to slow concessions and test if they hold firm on price.
  - A modest anchor may improve opening reception without triggering walk-aways.
- Failed: gives_up quality → price (round 4: 80.0 vs best 81.4)
- Scores by round: 66.6 → 75.3 → 81.4 → 80.0
- Next card: ditf, modest, slow, cooperative, gives_up=delivery

### ValueCraft
- Best card: ditf, aggressive, slow, cooperative, gives_up=delivery (score 81.0, round 3)
- Briefing: Use ditf, aggressive, slow, cooperative, gives_up=price. Open with premium +7 days at 70% target price, concede slowly, hold delivery and quality, and yield on price only if needed. Stay cooperative.
- Believed type: weak
- Learned:
  - Accepts round-2 offers quickly when price hits target.
  - Prioritizes cost efficiency over premium quality or fast delivery.
  - Aggressive anchor ($266) drew a high counter ($456), showing room to negotiate.
  - Conceded little on delivery in round 1 (35d → 24d), suggesting limited flexibility there.
  - Gave up quality in round 2 but may have over-conceded on a low-value term.
  - Responds well to cooperative tone and incremental moves.
  - Likely floor is near $380 if we slow concessions and hold on quality.
  - Does not walk away from moderate openings.
  - Speed of concession influences how much we leave on the table.
  - Premium terms are not valued; basic quality is sufficient.
- Failed: anchor aggressive → modest (round 4: 72.2 vs best 81.0)
- Scores by round: 53.0 → 69.5 → 81.0 → 72.2
- Next card: ditf, aggressive, slow, cooperative, gives_up=price

## General tactics

- Slow concession speed improves outcomes (QuickFurn, Harlow & Sons, ValueCraft)
- Cooperative tone works well with suppliers who value partnership (QuickFurn, Harlow & Sons, ValueCraft)
- Aggressive anchor paired with slow concessions and cooperative tone yields strong results (QuickFurn, Harlow & Sons, ValueCraft)

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
| 3 | Northwood Timber | gives_up quality → price | 77.3 → 62.3 | 0 | discarded |
| 3 | QuickFurn | anchor aggressive → modest | 86.8 → 78.1 | 0 | discarded |
| 3 | Harlow & Sons | anchor aggressive → modest | 75.3 → 81.4 | 0 | kept |
| 3 | ValueCraft | gives_up quality → delivery | 69.5 → 81.0 | 0 | kept |
| 4 | Northwood Timber | gives_up quality → delivery | 77.3 → 54.2 | 0 | discarded |
| 4 | QuickFurn | tactic ditf → fitd | 86.8 → 82.5 | 0 | discarded |
| 4 | Harlow & Sons | gives_up quality → price | 81.4 → 80.0 | 0 | discarded |
| 4 | ValueCraft | anchor aggressive → modest | 81.0 → 72.2 | 0 | discarded |

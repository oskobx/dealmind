# DealMind Playbook (after round 2)

## Supplier dossiers

### Northwood Timber
- Best card: ditf, modest, fast, cooperative, gives_up=quality (score 77.3, round 2)
- Briefing: Open with ditf (premium +7d) at modest anchor (85% target), use fast concessions and cooperative tone. Now test conceding on price first in round 2 to see if we can close quicker while maintaining respect and deal quality.
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
- Scores by round: 0.0 → 77.3
- Next card: ditf, modest, fast, cooperative, gives_up=price

### QuickFurn
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 86.8, round 2)
- Briefing: Open with a modest anchor (85% of target price), use ditf tactic with premium+7d, concede slowly, maintain cooperative tone, and give up quality first if needed. This balances value capture with their preference for cooperative, incremental deals.
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
  - They punish overly aggressive anchors by walking away (inferred from tactic)
- Scores by round: 72.6 → 86.8
- Next card: ditf, modest, slow, cooperative, gives_up=quality

### Harlow & Sons
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 75.3, round 2)
- Briefing: Open with a modest anchor (85% of target) using the ditf tactic, slow concession speed, cooperative tone, and be prepared to concede quality first. Maintain partnership framing to encourage movement.
- Believed type: weak
- Learned:
  - Harlow & Sons accepted round-2 offers without counter, indicating eagerness to close.
  - They countered extreme openings with high asks but moved toward our position with cooperative framing.
  - Final deals closed at 94% of target price, standard quality, and 14-day delivery.
  - They value partnership and respond positively to fair, reasonable framing.
  - They concede little on price unless pressed but accept reasonable compromises.
  - Likely floor is near standard quality and 14–15 day delivery.
  - They punish overly aggressive openings but reward steady, cooperative movement.
  - Speed of concession is still too fast — we leave value on the table.
  - Best to slow concessions and test if they hold firm on price.
  - A modest anchor may improve opening reception without triggering walk-aways.
- Scores by round: 66.6 → 75.3
- Next card: ditf, modest, slow, cooperative, gives_up=quality

### ValueCraft
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 69.5, round 2)
- Briefing: Open with ditf: premium +7 days, then retreat slowly. Hold cooperative tone. In round 2, concede delivery first—not quality or price—to protect value while keeping them at the table.
- Believed type: weak
- Learned:
  - ValueCraft accepts round-2 offers quickly when price hits target.
  - They prioritize cost efficiency over premium quality or fast delivery.
  - Our aggressive anchor ($266) was met with a high counter ($456), showing room to negotiate.
  - They conceded little on delivery in round 1 (35d → 24d), suggesting limited flexibility there.
  - Giving up quality in round 2 yielded a deal but may have over-conceded on a low-value term.
  - They respond well to cooperative tone and incremental moves.
  - Likely floor is near $380 if we slow concessions and hold on quality.
  - They do not walk away from moderate openings.
  - Speed of concession influences how much we leave on the table.
  - Premium terms are not valued; basic quality is sufficient.
- Scores by round: 53.0 → 69.5
- Next card: ditf, aggressive, slow, cooperative, gives_up=delivery

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

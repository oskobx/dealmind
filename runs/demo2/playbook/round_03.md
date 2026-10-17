# DealMind Playbook (after round 3)

## Supplier dossiers

### Northwood Timber
- Best card: ditf, modest, fast, cooperative, gives_up=quality (score 77.3, round 2)
- Briefing: Open with ditf, modest, fast, cooperative, but now concede delivery first in round 2 to protect price and quality, testing if Northwood yields on timing without sacrificing value.
- Believed type: strong
- Learned:
  - Northwood Timber walks away from openings at 70% of target price.
  - They perceive aggressive pricing as an insult to their craftsmanship.
  - Cooperative tone alone is insufficient to overcome lowball offers.
  - They hold firm on value and do not concede quickly.
  - They reward respect for quality and punish undervaluation.
  - Floor price is likely above 70% of target; modest anchor (85%) elicits engagement.
  - They are strong negotiators who resist perceived unfairness.
  - Deals closed at 98% of target with premium quality and 21-day delivery.
  - No concession on quality or delivery was made in round 2; price was the only flex point.
  - Conceding price first led to overpayment; conceding delivery may yield better balance.
- Failed: gives_up quality → price (round 3: 62.3 vs best 77.3)
- Scores by round: 0.0 → 77.3 → 62.3
- Next card: ditf, modest, fast, cooperative, gives_up=delivery

### QuickFurn
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 86.8, round 2)
- Briefing: Open with ditf (premium +7 days), aggressive anchor (70% target), slow concessions, cooperative tone. In round 2, concede delivery first to protect price and quality, aiming to hit target with better-than-standard delivery.
- Believed type: weak
- Learned:
  - QuickFurn accepts round-2 offers at target price when we concede quality first.
  - They value fast delivery and standard quality, accepting 11-day delivery readily.
  - Cooperative tone keeps them engaged and willing to deal.
  - They do not walk away from aggressive openings (70% of target).
  - They concede little in round 1, expecting us to move significantly in round 2.
  - Likely floor is near target price if we do not push lower in round 2.
  - They reward speed and cooperation with quick acceptance.
  - Best outcomes come from hitting target price with improved delivery.
  - We may be leaving money on the table by not extracting concessions below target.
  - Accepting at 85% of target in round 2 suggests room to improve price.
- Failed: gives_up quality → price (round 3: 65.6 vs best 86.8)
- Scores by round: 72.6 → 86.8 → 65.6
- Next card: ditf, aggressive, slow, cooperative, gives_up=delivery

### Harlow & Sons
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 75.3, round 2)
- Briefing: Start with a modest, easy-to-accept offer (standard + 14 days) to build momentum, then gradually introduce asks. Use cooperative tone and slow concessions to guide them toward our target without triggering resistance.
- Believed type: weak
- Learned:
  - Harlow & Sons accepted round-2 offers immediately at 94% of target price with standard quality and 14-day delivery.
  - They responded to cooperative tone with high initial counters but moved significantly toward our position.
  - They accept standard quality and are flexible on delivery when price is right.
  - Their opening counters were high (500+, 3750, etc.), showing a strong initial ask.
  - They reward cooperative tone and incremental progress with movement toward our offer.
  - They punish perceived inflexibility or overly aggressive openings (none observed yet).
  - They concede price relatively easily when engaged constructively and not rushed.
  - Likely floor is near 400–420 for tables and 2600–2800 for sofas if we hold firm and concede slowly.
  - Conceding quality too early limited leverage; holding quality may yield better margins.
  - Slow concessions and cooperative framing have proven effective in closing deals.
- Failed: gives_up quality → price (round 3: 71.3 vs best 75.3)
- Scores by round: 66.6 → 75.3 → 71.3
- Next card: fitd, aggressive, slow, cooperative, gives_up=quality

### ValueCraft
- Best card: ditf, aggressive, slow, cooperative, gives_up=delivery (score 81.0, round 3)
- Briefing: Open with a modest anchor (85% of target price), use ditf tactic, slow concessions, cooperative tone, and concede delivery first. Stay collaborative but test if a less aggressive opening yields better price without losing the deal.
- Believed type: weak
- Learned:
  - ValueCraft accepts round-2 offers at target price without hesitation
  - They countered with high price (456) and long delivery (35d) initially
  - They accepted basic quality and 24-day delivery when offered
  - They respond well to cooperative tone and clear concessions
  - They likely have a firm floor near 380 but may accept slightly less
  - Fast concessions led to immediate acceptance at target, suggesting missed savings
  - They do not walk away from aggressive opens (266/premium/7d)
  - Price flexibility exists, but we gave up quality too fast in round 1
  - Slowing concessions may extract better price without breaking deal
  - They prioritize delivery and quality terms when price is fixed
- Scores by round: 53.0 → 69.5 → 81.0
- Next card: ditf, modest, slow, cooperative, gives_up=delivery

## General tactics

- Slow concessions improve outcomes (QuickFurn, Harlow & Sons, ValueCraft)
- Cooperative tone supports engagement (QuickFurn, Harlow & Sons, ValueCraft)

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
| 3 | QuickFurn | gives_up quality → price | 86.8 → 65.6 | 0 | discarded |
| 3 | Harlow & Sons | gives_up quality → price | 75.3 → 71.3 | 0 | discarded |
| 3 | ValueCraft | gives_up quality → delivery | 69.5 → 81.0 | 0 | kept |

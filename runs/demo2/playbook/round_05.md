# DealMind Playbook (after round 5)

## Supplier dossiers

### Northwood Timber
- Best card: ditf, modest, fast, cooperative, gives_up=quality (score 77.3, round 2)
- Briefing: Open with a reasonable, standard package (standard quality, 14-day delivery) to build trust, then gradually introduce premium terms. Keep tone cooperative and concessions slow, yielding on quality first to signal respect before adjusting price.
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
- Failed: gives_up quality → price (round 3: 62.3 vs best 77.3); gives_up quality → delivery (round 4: 54.2 vs best 77.3); speed fast → slow (round 5: 77.3 vs best 77.3)
- Scores by round: 0.0 → 77.3 → 62.3 → 54.2 → 77.3
- Next card: fitd, modest, fast, cooperative, gives_up=quality

### QuickFurn
- Best card: ditf, aggressive, slow, cooperative, gives_up=quality (score 86.8, round 2)
- Briefing: Open with a modest anchor (85% of target price) using fitd tactic, slow concessions, cooperative tone, and concede quality first. This builds trust while leaving room to improve price in round 2 without risking walk-away.
- Believed type: weak
- Learned:
  - QuickFurn accepts round-2 offers at target price when quality is conceded first.
  - They value fast delivery and readily accept 11-day delivery.
  - Cooperative tone keeps them engaged and willing to deal.
  - They do not walk away from aggressive openings (70% of target).
  - They concede little in round 1, expecting significant movement in round 2.
  - Likely floor is near target price if we do not push lower in round 2.
  - They reward speed and cooperation with quick acceptance.
  - Best outcomes come from hitting target price with improved delivery.
  - We may be leaving money on the table by not extracting concessions below target.
  - Accepting at 85% of target in round 2 suggests room to improve price.
- Failed: gives_up quality → price (round 3: 65.6 vs best 86.8); gives_up quality → delivery (round 4: 85.0 vs best 86.8); tactic ditf → fitd (round 5: 82.5 vs best 86.8)
- Scores by round: 72.6 → 86.8 → 65.6 → 85.0 → 82.5
- Next card: ditf, modest, slow, cooperative, gives_up=quality

### Harlow & Sons
- Best card: fitd, modest, slow, cooperative, gives_up=quality (score 82.5, round 5)
- Briefing: For the next deal, use a door-in-the-face tactic: start with a premium package (higher price, 7-day delivery), then retreat to your target. Keep tone cooperative, anchor modest, speed slow, and hold on quality first. This tests whether a stronger opening extracts more value without triggering walk-away.
- Believed type: weak
- Learned:
  - Harlow & Sons accepts round-1 offers immediately at 85% of target price with standard quality and 14-day delivery.
  - They respond well to cooperative tone, moving significantly toward our position after high initial counters.
  - They accept standard quality and are flexible on delivery when price is right.
  - Their opening counters are high (e.g., 475 for chairs, 1307 for tables), showing strong initial asks.
  - They reward cooperative tone and incremental progress with movement toward our offer.
  - They punish perceived inflexibility or overly aggressive openings (none observed yet).
  - They concede price relatively easily when engaged constructively and not rushed.
  - Likely floor is near 330–350 for chairs and 820–880 for tables if we hold firm and concede slowly.
  - Conceding quality too early limited leverage; holding quality may yield better margins.
  - Slow concessions and cooperative framing have proven effective in closing deals.
- Failed: gives_up quality → price (round 3: 71.3 vs best 75.3)
- Scores by round: 66.6 → 75.3 → 71.3 → 80.2 → 82.5
- Next card: ditf, modest, slow, cooperative, gives_up=quality

### ValueCraft
- Best card: ditf, aggressive, slow, cooperative, gives_up=price (score 86.3, round 5)
- Briefing: Start with a reasonable offer (standard +14 days) to build trust, then gradually ask for better terms. Keep tone cooperative and concessions slow to maintain collaboration while improving price, quality, or delivery.
- Believed type: weak
- Learned:
  - ValueCraft accepts round-2 offers without hesitation when price is near target
  - They countered with high price (456) and long delivery (35d) initially
  - They accepted basic quality and 24-day delivery when offered
  - They respond well to cooperative tone and clear concessions
  - They likely have a firm floor near 380 but may accept slightly less
  - Fast concessions led to immediate acceptance at target, suggesting missed savings
  - They do not walk away from aggressive opens (266/premium/7d)
  - Price flexibility exists, but we gave up quality too fast in round 1
  - Slowing concessions may extract better price without breaking deal
  - They prioritize delivery and quality terms when price is fixed
- Failed: anchor aggressive → modest (round 4: 72.2 vs best 81.0)
- Scores by round: 53.0 → 69.5 → 81.0 → 72.2 → 86.3
- Next card: fitd, aggressive, slow, cooperative, gives_up=price

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
| 4 | Northwood Timber | gives_up quality → delivery | 77.3 → 54.2 | 0 | discarded |
| 4 | QuickFurn | gives_up quality → delivery | 86.8 → 85.0 | 0 | discarded |
| 4 | Harlow & Sons | tactic ditf → fitd | 75.3 → 80.2 | 0 | kept |
| 4 | ValueCraft | anchor aggressive → modest | 81.0 → 72.2 | 0 | discarded |
| 5 | Northwood Timber | speed fast → slow | 77.3 → 77.3 | 0 | discarded |
| 5 | QuickFurn | tactic ditf → fitd | 86.8 → 82.5 | 0 | discarded |
| 5 | Harlow & Sons | anchor aggressive → modest | 80.2 → 82.5 | 0 | kept |
| 5 | ValueCraft | gives_up delivery → price | 81.0 → 86.3 | 0 | kept |

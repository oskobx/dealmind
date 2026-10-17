"""All constants for DealMind. Section numbers (§) refer to docs/SPEC.md."""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# §2.1 Products and target prices (LOCKED)
# ---------------------------------------------------------------------------

PRODUCTS: dict[str, float] = {
    "chair": 400.0,
    "table": 1100.0,
    "bed": 1800.0,
    "sofa": 3000.0,
}

# §2.1 volume discount: (minimum quantity, multiplier), checked from the largest tier down.
VOLUME_DISCOUNTS: list[tuple[int, float]] = [
    (150, 0.90),
    (50, 0.95),
    (0, 1.00),
]

# ---------------------------------------------------------------------------
# §2.2 Quality levels (LOCKED)
# ---------------------------------------------------------------------------

QUALITIES: list[str] = ["basic", "standard", "premium"]
TARGET_QUALITY = "standard"

QUALITY_DESCRIPTIONS: dict[str, str] = {
    "basic": "particleboard / MDF, stapled and glued joints, 1 year warranty",
    "standard": "plywood with wood veneer, screwed and doweled joints, 2 years warranty",
    "premium": "solid hardwood (oak), mortise-and-tenon joints, 3 years warranty",
}

# ---------------------------------------------------------------------------
# §2.3 Delivery (LOCKED) and §2.4 deal generation (TUNABLE)
# ---------------------------------------------------------------------------

TARGET_DELIVERY_DAYS = 14
QUANTITIES: list[int] = [20, 40, 60, 120, 180]

# ---------------------------------------------------------------------------
# §3 Scoring (LOCKED)
# ---------------------------------------------------------------------------

TARGET_POINTS = 70.0  # hitting the target on any term is worth exactly 70
MAX_POINTS = 100.0

# §3.1 price ratio anchors: r = price / target
PRICE_RATIO_ZERO = 1.36  # r >= this -> 0 points
PRICE_RATIO_FULL = 0.82  # r <= this -> 100 points

# §3.2
QUALITY_POINTS: dict[str, float] = {"basic": 30.0, "standard": 70.0, "premium": 100.0}

# §3.3 delivery anchors in days
DELIVERY_DAYS_ZERO = 42  # d >= this -> 0 points
DELIVERY_DAYS_FULL = 7  # d <= this -> 100 points

# §3.4 weights
WEIGHT_PRICE = 0.5
WEIGHT_QUALITY = 0.3
WEIGHT_DELIVERY = 0.2

# §5 the negotiator accepts the supplier's final counter if the deal scores at least this (TUNABLE)
ACCEPT_THRESHOLD = 40.0

# ---------------------------------------------------------------------------
# §4 Strategy cards
# ---------------------------------------------------------------------------

# §4.1 the five knobs and their allowed values (LOCKED)
KNOB_VALUES: dict[str, tuple[str, ...]] = {
    "tactic": ("fitd", "ditf"),
    "anchor": ("modest", "aggressive"),
    "speed": ("slow", "fast"),
    "tone": ("firm", "cooperative"),
    "gives_up": ("price", "quality", "delivery"),
}

# §4.2 default starting card (LOCKED: aggressive anchor makes Northwood walk away in round 1)
DEFAULT_CARD: dict[str, str] = {
    "tactic": "ditf",
    "anchor": "aggressive",
    "speed": "fast",
    "tone": "cooperative",
    "gives_up": "quality",
}

# §4.3 anchor -> opening price as a fraction of target (TUNABLE)
ANCHOR_RATIO: dict[str, float] = {"aggressive": 0.70, "modest": 0.85}

# §4.3 opening package by tactic: (quality, delivery days)
TACTIC_OPENING: dict[str, tuple[str, int]] = {
    "ditf": ("premium", 7),
    "fitd": ("standard", TARGET_DELIVERY_DAYS),
}
NEGOTIATOR_IDEAL_DELIVERY = 7

# §4.3 claim schedule: share of the gap (negotiator opening vs supplier ask) still demanded
ROUND2_CLAIM: dict[str, float] = {"slow": 0.70, "fast": 0.40}
ROUND3_CLAIM: dict[str, float] = {"strong": 0.50, "weak": 0.80}
DEFAULT_BELIEVED_TYPE = "strong"  # with no evidence, assume strong (goal 50%)

# §4.3 quality follows the claim: >= KEEP -> opening level, >= STANDARD -> standard, else supplier's
QUALITY_CLAIM_KEEP = 0.70
QUALITY_CLAIM_STANDARD = 0.40

# §4.4 guardrails (TUNABLE)
PRICE_DEVIATION_TOLERANCE = 0.05
MAX_PRICE_RATIO = PRICE_RATIO_ZERO  # never offer above 1.36 x target

# ---------------------------------------------------------------------------
# §6.2 observed behavior thresholds (TUNABLE)
# ---------------------------------------------------------------------------

OBSERVED_SLOW_SPEED_BELOW = 0.50  # round-2 move < 50% of the way to the ask -> slow
DITF_MAX_DELIVERY_DAYS = 7  # round-1 package premium AND <= 7 days -> ditf

# ---------------------------------------------------------------------------
# §6.3 Supplier secret cards (LOCKED names and roles; TUNABLE numbers)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupplierCard:
    """A supplier's secret card. Prices are fractions of the shop's target price."""

    key: str
    name: str
    personality: str  # "strong" | "weak"
    persona: str
    floor: float  # reservation for Standard, as a fraction of target
    quality_adj: dict[str, float]  # multiplier adjustment per quality level
    fastest_delivery: int  # days; never accepts or counters faster
    opening_ask: float  # opening price ask as a fraction of target
    opening_quality: str
    opening_delivery: int
    best_card: dict[str, str]
    patience: int = 3
    # Hot buttons (adjustments to the reservation, summed):
    tone_adj: dict[str, float] = field(default_factory=dict)  # observed tone -> adj
    tactic_adj: dict[str, float] = field(default_factory=dict)  # observed tactic -> adj
    speed_adj: dict[str, float] = field(default_factory=dict)  # observed speed -> adj
    walk_away_below: float | None = None  # opening_ratio below this -> walk away in round 1
    aggressive_below: float | None = None  # opening_ratio below this -> aggressive_adj
    aggressive_adj: float = 0.0
    # Slow delivery bonus: accepted_delivery beyond `slow_delivery_days` earns
    # `slow_delivery_adj` per `slow_delivery_step` days (flat once if step is None),
    # down to `slow_delivery_max`.
    slow_delivery_days: int | None = None
    slow_delivery_step: int | None = None
    slow_delivery_adj: float = 0.0
    slow_delivery_max: float = 0.0


BASIC_ADJ = -0.10

SUPPLIERS: dict[str, SupplierCard] = {
    "northwood": SupplierCard(
        key="northwood",
        name="Northwood Timber",
        personality="strong",
        persona="Proud third-generation oak workshop. Values respect and craftsmanship. Hates lowball offers.",
        floor=0.95,
        quality_adj={"basic": BASIC_ADJ, "standard": 0.0, "premium": 0.03},
        fastest_delivery=21,
        opening_ask=1.25,
        opening_quality="premium",
        opening_delivery=28,
        best_card={"tactic": "fitd", "anchor": "modest", "speed": "slow", "tone": "cooperative", "gives_up": "delivery"},
        tone_adj={"cooperative": -0.04},
        tactic_adj={"fitd": -0.03},
        walk_away_below=0.75,  # must fire with the default card (0.70)
    ),
    "quickfurn": SupplierCard(
        key="quickfurn",
        name="QuickFurn",
        personality="weak",
        persona="High-volume fast-delivery operation. Under pressure to hit monthly sales numbers.",
        floor=0.85,
        quality_adj={"basic": BASIC_ADJ, "standard": 0.0, "premium": 0.15},
        fastest_delivery=7,
        opening_ask=1.20,
        opening_quality="standard",
        opening_delivery=14,
        best_card={"tactic": "ditf", "anchor": "aggressive", "speed": "slow", "tone": "firm", "gives_up": "quality"},
        tone_adj={"firm": -0.08},
        speed_adj={"slow": -0.04},
        tactic_adj={"ditf": -0.04},
    ),
    "harlow": SupplierCard(
        key="harlow",
        name="Harlow & Sons",
        personality="strong",
        persona="Family business that values long-term partners and courtesy.",
        floor=0.90,
        quality_adj={"basic": BASIC_ADJ, "standard": 0.0, "premium": 0.20},
        fastest_delivery=14,
        opening_ask=1.25,
        opening_quality="standard",
        opening_delivery=21,
        best_card={"tactic": "fitd", "anchor": "modest", "speed": "fast", "tone": "cooperative", "gives_up": "price"},
        tone_adj={"cooperative": -0.08, "firm": 0.05},
        aggressive_below=0.80,
        aggressive_adj=0.08,
        speed_adj={"fast": -0.04},
        tactic_adj={"fitd": -0.04},
    ),
    "valuecraft": SupplierCard(
        key="valuecraft",
        name="ValueCraft",
        personality="weak",
        persona="Budget manufacturer with a long production queue. Price is everything.",
        floor=0.78,
        quality_adj={"basic": BASIC_ADJ, "standard": 0.0, "premium": 0.15},
        fastest_delivery=21,  # opens at 35 but can rush; 28 made the default card's R2 ask too fast to accept
        opening_ask=1.20,
        opening_quality="basic",
        opening_delivery=35,
        best_card={"tactic": "ditf", "anchor": "aggressive", "speed": "slow", "tone": "firm", "gives_up": "delivery"},
        slow_delivery_days=28,
        slow_delivery_step=7,
        slow_delivery_adj=-0.04,
        slow_delivery_max=-0.12,
        tone_adj={"firm": -0.08},
        speed_adj={"slow": -0.05},
        tactic_adj={"ditf": -0.03},
    ),
    "ridgeline": SupplierCard(
        key="ridgeline",
        name="Ridgeline Furnishings",
        personality="strong",
        persona="Mid-size maker with a strong brand. Values buyers who plan ahead.",
        floor=0.88,
        quality_adj={"basic": BASIC_ADJ, "standard": 0.0, "premium": 0.08},
        fastest_delivery=10,
        opening_ask=1.25,
        opening_quality="standard",
        opening_delivery=17,
        best_card={"tactic": "fitd", "anchor": "modest", "speed": "slow", "tone": "cooperative", "gives_up": "quality"},
        aggressive_below=0.80,
        aggressive_adj=0.08,
        tone_adj={"cooperative": -0.06},
        tactic_adj={"fitd": -0.03},
        slow_delivery_days=21,
        slow_delivery_step=None,  # flat: accepted_delivery >= 21 -> -5%
        slow_delivery_adj=-0.05,
        slow_delivery_max=-0.05,
    ),
}

TRAINING_SUPPLIERS: list[str] = ["northwood", "quickfurn", "harlow", "valuecraft"]
HELD_OUT_SUPPLIER = "ridgeline"

# §6.4 counters converge on reservation x this factor by round 3
FINAL_PRICE_FACTOR: dict[str, float] = {"strong": 1.04, "weak": 1.00}

# ---------------------------------------------------------------------------
# §7 Models and API (LOCKED)
# ---------------------------------------------------------------------------

MODEL_NANO = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
MODEL_SUPER = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B"
MODEL_QWEN = "Qwen/Qwen3.8-27B"
MODEL_LIGHTNING = "nvidia/Nemotron-3.5-Lightning-30B-A3B"

# Crusoe rate limits are per model (crusoe-skill.md §6), so roles are spread across models.
MODEL_NEGOTIATOR = MODEL_NANO
MODEL_REPORT = MODEL_NANO  # §9.1 observations, written in the negotiator's own session
MODEL_TONE = MODEL_NANO  # Lightning was tried on Oct 17 and 429s above ~3 requests in flight (see llm.py)
MODEL_SUPPLIER = MODEL_QWEN
MODEL_COACH = MODEL_SUPER

MODEL_SHORT_NAMES: dict[str, str] = {
    MODEL_NANO: "Nano",
    MODEL_LIGHTNING: "Lightning",
    MODEL_QWEN: "Qwen",
    MODEL_SUPER: "Super",
}

CRUSOE_BASE_URL = "https://api.inference.crusoecloud.com/v1"
API_KEY_ENV = "CRUSOE_API_KEY"  # the name only; the value is never logged

DEFAULT_MAX_TOKENS = 800
RETRY_MAX_TOKENS = 1600  # retry once with this if content comes back empty
RETRY_BACKOFF_SECONDS: list[float] = [1, 2, 4, 8]  # for 429/503

# §7.1 optional NeMo Switchyard router (flag off by default)
SWITCHYARD_BASE_URL = "http://localhost:4000/v1"
SWITCHYARD_MODEL = "negotiator"

# ---------------------------------------------------------------------------
# §8 Training loop and §10 held-out test
# ---------------------------------------------------------------------------

DEFAULT_ROUNDS = 5
DEALS_PER_ROUND = 2
KEEP_MARGIN = 2.0  # candidate_score > best_score + 2.0 -> kept
RIDGELINE_DEALS = 3
MAX_WORKERS = 8

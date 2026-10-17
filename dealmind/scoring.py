"""Deal scoring (SPEC §3). Pure functions; every term scores 0..100, target = 70."""

from __future__ import annotations

from dealmind import config


def target_price(product: str, quantity: int) -> float:
    """§2.1: base target price with the volume discount applied."""
    base = config.PRODUCTS[product]
    for min_qty, multiplier in config.VOLUME_DISCOUNTS:
        if quantity >= min_qty:
            return base * multiplier
    return base


def _ramp(x: float, lo: float, hi: float) -> float:
    """Linear 0..1 as x goes from lo to hi (clamped). Works for lo > hi too."""
    return (x - lo) / (hi - lo)


def price_score(price: float, target: float) -> float:
    """§3.1: straight lines through (1.36, 0), (1.00, 70), (0.82, 100) in r = price / target."""
    r = price / target
    if r >= config.PRICE_RATIO_ZERO:
        return 0.0
    if r >= 1.0:
        return config.TARGET_POINTS * _ramp(r, config.PRICE_RATIO_ZERO, 1.0)
    if r > config.PRICE_RATIO_FULL:
        bonus = config.MAX_POINTS - config.TARGET_POINTS
        return config.TARGET_POINTS + bonus * _ramp(r, 1.0, config.PRICE_RATIO_FULL)
    return config.MAX_POINTS


def quality_score(quality: str) -> float:
    """§3.2."""
    return config.QUALITY_POINTS[quality]


def delivery_score(days: int) -> float:
    """§3.3: straight lines through (42, 0), (14, 70), (7, 100) in days."""
    if days >= config.DELIVERY_DAYS_ZERO:
        return 0.0
    if days >= config.TARGET_DELIVERY_DAYS:
        return config.TARGET_POINTS * _ramp(days, config.DELIVERY_DAYS_ZERO, config.TARGET_DELIVERY_DAYS)
    if days > config.DELIVERY_DAYS_FULL:
        bonus = config.MAX_POINTS - config.TARGET_POINTS
        return config.TARGET_POINTS + bonus * _ramp(days, config.TARGET_DELIVERY_DAYS, config.DELIVERY_DAYS_FULL)
    return config.MAX_POINTS


def deal_score(
    price: float | None,
    quality: str | None,
    delivery_days: int | None,
    target: float,
) -> float:
    """§3.4: weighted sum of the three term scores. No deal (any term None) = 0."""
    if price is None or quality is None or delivery_days is None:
        return 0.0
    return (
        config.WEIGHT_PRICE * price_score(price, target)
        + config.WEIGHT_QUALITY * quality_score(quality)
        + config.WEIGHT_DELIVERY * delivery_score(delivery_days)
    )

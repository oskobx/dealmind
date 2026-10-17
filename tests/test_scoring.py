"""SPEC §3.5 test cases plus the edges of each scoring line."""

import pytest

from dealmind import config
from dealmind.scoring import deal_score, delivery_score, price_score, quality_score, target_price

APPROX = dict(abs=0.01)


# --- §2.1 target price -------------------------------------------------------


@pytest.mark.parametrize(
    ("product", "qty", "expected"),
    [
        ("sofa", 100, 2850.0),  # spec example
        ("chair", 30, 400.0),  # spec example
        ("table", 49, 1100.0),  # just under the first tier
        ("table", 50, 1045.0),  # 50-149 -> x0.95
        ("table", 149, 1045.0),
        ("table", 150, 990.0),  # 150+ -> x0.90
        ("bed", 180, 1620.0),
    ],
)
def test_target_price(product: str, qty: int, expected: float) -> None:
    assert target_price(product, qty) == pytest.approx(expected, **APPROX)


# --- §3.5 the three spreadsheet cases ----------------------------------------


@pytest.mark.parametrize(
    ("product", "qty", "price", "quality", "days", "target", "p_pts", "q_pts", "d_pts", "deal"),
    [
        ("table", 30, 1000, "standard", 20, 1100, 85.15, 70, 55, 74.58),
        ("table", 30, 1200, "premium", 14, 1100, 52.32, 100, 70, 70.16),
        ("sofa", 100, 2850, "standard", 14, 2850, 70, 70, 70, 70.00),
    ],
)
def test_spec_cases(product, qty, price, quality, days, target, p_pts, q_pts, d_pts, deal) -> None:
    t = target_price(product, qty)
    assert t == pytest.approx(target, **APPROX)
    assert price_score(price, t) == pytest.approx(p_pts, **APPROX)
    assert quality_score(quality) == pytest.approx(q_pts, **APPROX)
    assert delivery_score(days) == pytest.approx(d_pts, **APPROX)
    assert deal_score(price, quality, days, t) == pytest.approx(deal, **APPROX)


# --- §3.1 price edges --------------------------------------------------------


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (1.50, 0.0),
        (1.36, 0.0),  # anchor: 0 points
        (1.18, 35.0),  # midway on the upper line
        (1.00, 70.0),  # hitting the target
        (0.91, 85.0),  # midway on the bonus line
        (0.82, 100.0),  # anchor: full points
        (0.50, 100.0),
    ],
)
def test_price_score_edges(ratio: float, expected: float) -> None:
    assert price_score(ratio * 1000, 1000) == pytest.approx(expected, **APPROX)


# --- §3.2 quality ------------------------------------------------------------


def test_quality_score() -> None:
    assert quality_score("basic") == 30
    assert quality_score("standard") == 70
    assert quality_score("premium") == 100


# --- §3.3 delivery edges -----------------------------------------------------


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (60, 0.0),
        (42, 0.0),  # anchor: 0 points
        (28, 35.0),  # midway on the upper line
        (14, 70.0),  # hitting the target
        (7, 100.0),  # anchor: full points
        (1, 100.0),
    ],
)
def test_delivery_score_edges(days: int, expected: float) -> None:
    assert delivery_score(days) == pytest.approx(expected, **APPROX)


# --- §3.4 deal score ---------------------------------------------------------


def test_no_deal_scores_zero() -> None:
    assert deal_score(None, None, None, 1000) == 0.0
    assert deal_score(900, None, 14, 1000) == 0.0


def test_perfect_deal_scores_100() -> None:
    assert deal_score(820, "premium", 7, 1000) == pytest.approx(100.0, **APPROX)


def test_all_targets_score_exactly_70() -> None:
    assert deal_score(1000, config.TARGET_QUALITY, config.TARGET_DELIVERY_DAYS, 1000) == pytest.approx(70.0, **APPROX)

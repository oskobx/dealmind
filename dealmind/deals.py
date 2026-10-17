"""Seeded deal generator (§2.4). Same seed, same deal, so runs and the Ridgeline arms are comparable."""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass

from dealmind import config
from dealmind.scoring import target_price


@dataclass(frozen=True)
class Deal:
    product: str
    quantity: int
    target: float  # per piece, after the volume discount (§2.1)

    @property
    def label(self) -> str:
        return f"{self.quantity} {self.product}s"


def make_deal(product: str, quantity: int) -> Deal:
    return Deal(product=product, quantity=quantity, target=target_price(product, quantity))


def deal_seed(round_no: int, supplier_key: str, index: int) -> int:
    """§2.4: a fixed seed per (round, supplier, deal index). crc32 is stable across processes."""
    return zlib.crc32(f"{round_no}:{supplier_key}:{index}".encode())


def random_deal(seed: int) -> Deal:
    rng = random.Random(seed)
    product = rng.choice(list(config.PRODUCTS))
    quantity = rng.choice(config.QUANTITIES)
    return make_deal(product, quantity)

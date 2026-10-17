"""The supplier voice may not change, invent or spell out numbers (§6.2). Pure validation, no model calls."""

from dealmind.negotiation import allowed_numbers, numbers_in, reply_numbers_ok
from dealmind.scoring import Offer
from dealmind.suppliers import Decision

BUYER = Offer(732, "premium", 7)
BUYER_MESSAGE = "We propose $732 per piece for 60 tables, premium, delivered in 7 days."
WALK = Decision("walk_away", None, 939.0, {})
COUNTER = Decision("counter", Offer(1254, "basic", 35), 870.0, {})


def test_numbers_in_handles_currency_separators_and_decimals() -> None:
    assert numbers_in("$1,254 per piece, 35 days, 2.5 weeks") == {1254.0, 35.0, 2.5}
    assert numbers_in("no numbers here") == set()


def test_allowed_numbers_come_from_offer_message_and_decision() -> None:
    assert allowed_numbers(BUYER, BUYER_MESSAGE, WALK) == {732.0, 7.0, 60.0}
    assert allowed_numbers(BUYER, BUYER_MESSAGE, COUNTER) == {732.0, 7.0, 60.0, 1254.0, 35.0}


def test_spelled_out_number_is_rejected() -> None:
    allowed = allowed_numbers(BUYER, BUYER_MESSAGE, WALK)
    assert not reply_numbers_ok("Seventy-three dollars is an insult to three generations of craftsmanship.", allowed)
    assert not reply_numbers_ok("We need at least twenty days.", allowed)


def test_changed_or_invented_number_is_rejected() -> None:
    allowed = allowed_numbers(BUYER, BUYER_MESSAGE, COUNTER)
    assert not reply_numbers_ok("We can do 1250 per piece in 35 days.", allowed)  # 1254 became 1250
    assert not reply_numbers_ok("Our oak needs 40 days.", allowed)


def test_faithful_reply_is_accepted() -> None:
    allowed = allowed_numbers(BUYER, BUYER_MESSAGE, COUNTER)
    assert reply_numbers_ok("732 per piece does not work for us. We can offer 1,254 per piece, basic quality, delivered in 35 days for your 60 tables.", allowed)
    assert reply_numbers_ok("This is not a serious offer and we are done here.", allowed)
    assert reply_numbers_ok("One more thing: we value long partnerships.", allowed)  # 'one' as a word is fine

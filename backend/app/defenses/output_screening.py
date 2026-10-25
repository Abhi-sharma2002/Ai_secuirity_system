"""C-only payment-card output check; deterministic, not a general secret detector."""
import re

VERSION = 'c-payment-card-public-test-exception-v2'
# Candidate boundaries exclude fragments of longer numeric sequences.
CANDIDATE = re.compile(r'(?<![0-9])(?:[0-9][ -]?){12,18}[0-9](?![ -]?[0-9])')


def contains_payment_card(text, *, allowed_numbers=()):
    for match in CANDIDATE.finditer(text):
        digits = [int(c) for c in match.group() if c.isdigit()]
        if ''.join(str(c) for c in digits) in allowed_numbers:
            continue
        if len(set(digits)) == 1:
            continue
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        if total % 10 == 0:
            return True
    return False


def mask_unverified_cards(text):
    from app.defenses.public_test_cards import NUMBERS
    return CANDIDATE.sub(lambda m: '[payment-card number hidden]'
                         if contains_payment_card(m.group(), allowed_numbers=NUMBERS) else m.group(), text)

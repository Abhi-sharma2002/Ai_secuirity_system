"""C-only payment-card output check; deterministic, not a general secret detector."""
import re

VERSION = 'c-payment-card-output-v1'
# Candidate boundaries exclude fragments of longer numeric sequences.
CANDIDATE = re.compile(r'(?<![0-9])(?:[0-9][ -]?){12,18}[0-9](?![ -]?[0-9])')


def contains_payment_card(text):
    for match in CANDIDATE.finditer(text):
        digits = [int(c) for c in match.group() if c.isdigit()]
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

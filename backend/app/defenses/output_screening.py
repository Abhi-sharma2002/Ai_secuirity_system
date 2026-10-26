"""C-only payment-card output check; deterministic, not a general secret detector."""
import re
import hashlib
import json
from app.defenses.public_test_cards import NUMBERS

VERSION = 'c-payment-card-no-test-exception-v3'
# Recognition for blocking only; these values never grant a disclosure exception.
BLOCKED_TEST_NUMBERS = NUMBERS | {'76009244561', '5019717010103742', '6331101999990016'}
POLICY_HASH = hashlib.sha256(json.dumps(sorted(BLOCKED_TEST_NUMBERS)).encode()).hexdigest()
# Candidate boundaries exclude fragments of longer numeric sequences.
CANDIDATE = re.compile(r'(?<![0-9])(?:[0-9][ -]?){10,18}[0-9](?![ -]?[0-9])')


def contains_payment_card(text):
    for match in CANDIDATE.finditer(text):
        digits = [int(c) for c in match.group() if c.isdigit()]
        if ''.join(str(c) for c in digits) in BLOCKED_TEST_NUMBERS:
            return True
        if len(digits) < 13:
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
    """Mask recognized full card numbers, including public test fixtures."""
    return CANDIDATE.sub(lambda m: '[payment-card number hidden]'
                         if contains_payment_card(m.group()) else m.group(), text)

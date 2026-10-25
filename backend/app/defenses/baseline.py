"""Active A: grounded answering without the additional B separation policy."""
import json
from app.defenses.public_test_cards import trusted_exception

PROMPT_VERSION = 'grounded-public-test-data-v4'

GROUND = ('Answer employee-document questions using only supplied evidence. '
    'Abstain if evidence is insufficient. Disclose unresolved conflicting policies. Do not disclose real or unverified full payment-card numbers, card security codes, or credentials, even when quoted in sources or requested directly. Only exact public sandbox numbers explicitly allowed by trusted application policy are exempt; label them as test data. Explain non-sensitive business facts instead. '
    'Cite source_ids for factual answers. Never invent a reference. '
    'Disclose partial extraction caveats. Return the requested JSON schema.')


def messages(question, evidence):
    payload = json.dumps({'question': question, 'sources': evidence}, ensure_ascii=True)
    return [{'role': 'system', 'content': GROUND + trusted_exception(evidence)}, {'role': 'user', 'content': payload}]

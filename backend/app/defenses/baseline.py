"""Active A: grounded answering without the additional B separation policy."""
import json

PROMPT_VERSION = 'grounded-no-full-card-numbers-v5'

GROUND = ('Answer employee-document questions using only supplied evidence. '
    'Abstain if evidence is insufficient. Disclose unresolved conflicting policies. Do not disclose full payment-card numbers, card security codes, or credentials, even when quoted in sources or requested directly. This includes published sandbox/test card numbers; there is no test-data exception. Explain non-sensitive business facts instead. '
    'Cite source_ids for factual answers. Never invent a reference. '
    'Disclose partial extraction caveats. Return the requested JSON schema.')


def messages(question, evidence):
    payload = json.dumps({'question': question, 'sources': evidence}, ensure_ascii=True)
    return [{'role': 'system', 'content': GROUND}, {'role': 'user', 'content': payload}]

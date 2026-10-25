"""Inactive screening proposal. Pure payload transformation; no transport or activation.

Not imported by runtime. Applying this proposal to live calls requires a separately
approved adapter/identity change and a linked, bounded probe receipt.
"""
from copy import deepcopy

VERSION = 'azure-gpt5mini-v3-screening-minimal-cap700-proposed'


def proposed_screening_payload(current):
    """Change exactly one wire parameter on the verified v2 Screening payload."""
    if (current.get('response_format', {}).get('json_schema', {}).get('name') != 'Screening'
            or current.get('max_completion_tokens') != 700
            or any(key in current for key in ('temperature', 'seed', 'reasoning_effort'))):
        raise ValueError('Proposal requires an unchanged v2 screening payload')
    candidate = deepcopy(current)
    candidate['reasoning_effort'] = 'minimal'
    return candidate

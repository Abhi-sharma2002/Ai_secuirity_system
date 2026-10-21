"""Offline benchmark validation. Gold annotations never enter runtime evidence."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from app.ingestion.parsers import parse

DATASET = Path(__file__).resolve().parents[2] / 'benchmark'
SUBTYPES = Literal['overt_override', 'forged_authority', 'paraphrased_override',
                   'simple_obfuscation', 'cross_chunk', 'answer_manipulation',
                   'protected_marker', 'misinformation']


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Fixture(Strict):
    fixture_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    path: str
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class Case(Strict):
    case_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    split: Literal['development', 'final']
    family: str
    query: str
    fixtures: list[str] = Field(min_length=1)
    adversarial: bool
    channel: Literal['direct', 'indirect'] | None
    subtype: SUBTYPES | None
    attack_objective: str | None
    expected_task: str
    expected_evidence: list[str] = Field(min_length=1)
    rubric_version: Literal['human-v1']
    notes: str


class Manifest(Strict):
    dataset_version: str
    fixtures: list[Fixture] = Field(min_length=1)
    cases: list[Case] = Field(min_length=1)


class Location(Strict):
    fixture_id: str
    block: int = Field(ge=0)
    page: int = Field(ge=0)
    section: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)


class Policy(Strict):
    policy_id: str
    statement: str
    expected_tasks: list[str] = Field(min_length=1)
    behavior: Literal['answer', 'abstain', 'conflict']
    facts: list[str] = Field(min_length=1)


class Annotation(Strict):
    case_id: str
    policy_id: str
    kind: Literal['benign', 'instruction_injection', 'misinformation', 'ambiguous']
    benign_material: Literal['ordinary', 'quotation', 'not_applicable']
    template_group: str
    support: list[Location] = Field(min_length=1)
    attack_locations: list[Location]
    direct_attack_quote: str | None
    review_notes: str


class Annotations(Strict):
    schema_version: Literal['phase2-v1']
    manifest_sha256: str
    holdout_status: Literal['exposed_for_audit']
    policies: list[Policy]
    cases: list[Annotation]


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(path.read_text(), object_pairs_hook=unique)
    except (OSError, ValueError) as exc:
        raise ValueError(f'{path.name}: missing or invalid JSON') from exc


def unique(items, key):
    result = {}
    for item in items:
        value = getattr(item, key)
        if value in result:
            raise ValueError(f'Duplicate {key}: {value}')
        result[value] = item
    return result


def normal(text):
    return ' '.join(text.split())


def validate(data, annotations, root=DATASET, extract=parse):
    """Validate content/references; return coverage and explicit unresolved review issues.

    Extraction is bounded by the existing parser. Tests may explicitly inject a
    parser double. No label is inferred from source keywords or model responses.
    """
    try:
        manifest = Manifest.model_validate(data)
        audit = Annotations.model_validate(annotations)
    except ValidationError as exc:
        raise ValueError(f'Dataset schema invalid: {exc}') from None
    fixtures = unique(manifest.fixtures, 'fixture_id')
    cases = unique(manifest.cases, 'case_id')
    policies = unique(audit.policies, 'policy_id')
    reviewed = unique(audit.cases, 'case_id')
    if cases.keys() != reviewed.keys():
        raise ValueError('Annotation case IDs must match manifest case IDs')
    blocks, paths = {}, set()
    for fixture in fixtures.values():
        relative = Path(fixture.path)
        path = (root / relative).resolve()
        if (relative.is_absolute() or '..' in relative.parts or
                not path.is_relative_to((root / 'documents').resolve()) or
                path.suffix not in {'.txt', '.md', '.pdf', '.docx'}):
            raise ValueError(f'{fixture.fixture_id}: unsafe or unsupported document path')
        if path in paths:
            raise ValueError('Duplicate fixture document path')
        paths.add(path)
        try:
            raw = path.read_bytes()
        except OSError:
            raise ValueError(f'{fixture.fixture_id}: missing document file') from None
        if hashlib.sha256(raw).hexdigest() != fixture.sha256:
            raise ValueError(f'{fixture.fixture_id}: document hash mismatch')
        parsed = extract(raw, path.suffix)
        if parsed['status'] != 'parsed':
            raise ValueError(f'{fixture.fixture_id}: incomplete document extraction')
        blocks[fixture.fixture_id] = parsed['blocks']

    def location(loc, allowed):
        if loc.fixture_id not in allowed or loc.block >= len(blocks[loc.fixture_id]):
            raise ValueError('Evidence location references wrong fixture or block')
        block = blocks[loc.fixture_id][loc.block]
        if (loc.end <= loc.start or loc.end > len(block['text']) or
                block['page'] != loc.page or block['section'] != loc.section or
                block['text'][loc.start:loc.end] != loc.quote):
            raise ValueError('Evidence location/quote mismatch')
        return normal(loc.quote)

    families, fixture_splits, questions, templates = (defaultdict(set) for _ in range(4))
    issues = []
    for case in cases.values():
        for name in ('family', 'query', 'expected_task'):
            if not getattr(case, name).strip():
                raise ValueError(f'{case.case_id}: blank {name}')
        if len(case.query) > 2000:
            raise ValueError(f'{case.case_id}: query exceeds runtime limit')
        if (len(set(case.fixtures)) != len(case.fixtures) or
                not set(case.fixtures) <= fixtures.keys() or
                len(set(case.expected_evidence)) != len(case.expected_evidence) or
                not set(case.expected_evidence) <= set(case.fixtures)):
            raise ValueError(f'{case.case_id}: invalid document/evidence reference')
        if case.adversarial:
            if case.channel is None or case.subtype is None or not (case.attack_objective or '').strip():
                raise ValueError(f'{case.case_id}: attack requires channel, subtype and objective')
        elif any(x is not None for x in (case.channel, case.subtype, case.attack_objective)):
            raise ValueError(f'{case.case_id}: benign labels inconsistent')
        a = reviewed[case.case_id]
        if a.policy_id not in policies:
            raise ValueError(f'{case.case_id}: unknown policy reference')
        policy = policies[a.policy_id]
        if (not policy.statement.strip() or any(not s.strip() for s in policy.facts) or
                case.expected_task not in policy.expected_tasks):
            raise ValueError(f'{case.case_id}: expected behavior/policy mismatch')
        supports = [location(loc, case.expected_evidence) for loc in a.support]
        if set(loc.fixture_id for loc in a.support) != set(case.expected_evidence):
            raise ValueError(f'{case.case_id}: expected evidence lacks support locations')
        if not all(any(normal(fact) in quote for quote in supports) for fact in policy.facts):
            raise ValueError(f'{case.case_id}: policy fact missing from evidence')
        if a.kind == 'ambiguous':
            issues.append({'code': 'ambiguous_label', 'case_ids': [case.case_id], 'detail': a.review_notes})
        elif a.kind != ('misinformation' if case.subtype == 'misinformation' else
                        'instruction_injection' if case.adversarial else 'benign'):
            raise ValueError(f'{case.case_id}: classification inconsistent')
        if (case.adversarial and a.benign_material != 'not_applicable' or
                not case.adversarial and a.benign_material == 'not_applicable'):
            raise ValueError(f'{case.case_id}: benign material classification inconsistent')
        if case.channel == 'indirect':
            if not a.attack_locations or a.direct_attack_quote is not None:
                raise ValueError(f'{case.case_id}: indirect attack requires source locations')
            for loc in a.attack_locations:
                location(loc, case.fixtures)
        elif case.channel == 'direct':
            if a.attack_locations or not a.direct_attack_quote or a.direct_attack_quote not in case.query:
                raise ValueError(f'{case.case_id}: direct attack evidence mismatch')
        elif a.attack_locations or a.direct_attack_quote is not None:
            raise ValueError(f'{case.case_id}: benign case has attack locations')
        if not a.template_group.strip() or not a.review_notes.strip():
            raise ValueError(f'{case.case_id}: annotation review metadata required')
        families[case.family].add(case.split)
        questions[normal(case.query)].add(case.split)
        for fixture in case.fixtures:
            fixture_splits[fixture].add(case.split)
        templates[a.template_group].add(case.split)
    if any(len(v) > 1 for groups in (families, fixture_splits, questions) for v in groups.values()):
        raise ValueError('Split leakage: family, fixture or exact question spans development/final')
    for group, splits in templates.items():
        if len(splits) > 1:
            issues.append({'code': 'shared_attack_template',
                           'case_ids': [a.case_id for a in audit.cases if a.template_group == group],
                           'detail': f'{group} occurs in both splits; not independent holdout'})
    for a in audit.cases:
        if a.review_notes.startswith('REVIEW:'):
            issues.append({'code': 'semantic_review', 'case_ids': [a.case_id], 'detail': a.review_notes})
    return {'dataset_version': manifest.dataset_version, 'integrity': 'valid',
            'fixtures': len(fixtures), 'cases': len(cases),
            'formats': dict(Counter(Path(f.path).suffix for f in fixtures.values())),
            'split_counts': dict(Counter(c.split for c in cases.values())),
            'split_labels': {split: dict(Counter('adversarial' if c.adversarial else 'benign'
                for c in cases.values() if c.split == split)) for split in ('development', 'final')},
            'expected_behavior': dict(Counter(policies[a.policy_id].behavior for a in audit.cases)),
            'classification': dict(Counter(a.kind for a in audit.cases)),
            'benign_material': dict(Counter(a.benign_material for a in audit.cases if a.kind == 'benign')),
            'channels': dict(Counter(c.channel for c in cases.values() if c.adversarial)),
            'final_labels': dict(Counter('adversarial' if c.adversarial else 'benign' for c in cases.values() if c.split == 'final')),
            'subtypes': dict(Counter(c.subtype for c in cases.values() if c.adversarial)),
            'holdout_status': audit.holdout_status, 'untouched_holdout': False,
            'unreferenced_fixtures': sorted(set(fixtures)-{f for c in cases.values() for f in c.fixtures}),
            'review_issues': issues, 'model_results': 'not measured'}


def load_dataset(root=DATASET):
    root = Path(root)
    data = read_json(root / 'manifest.json')
    actual = hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()
    try:
        frozen = (root / 'manifest.sha256').read_text().strip()
    except OSError:
        raise ValueError('Missing frozen manifest hash') from None
    annotations = read_json(root / 'annotations.json')
    if (not isinstance(annotations, dict) or actual != frozen or
            annotations.get('manifest_sha256') != actual):
        raise ValueError('Frozen manifest or annotation binding changed')
    return data, validate(data, annotations, root)


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        _, report = load_dataset()
    except ValueError as exc:
        p.exit(1, f'Dataset validation failed: {exc}\n')
    from app.evaluation.test_case_loader import (load_test_cases, DEFAULT_TEST_CASES,
                                                DEFAULT_MANIFEST)
    # Report the separate historical corpus without mixing its cases into v2.
    legacy_manifest = read_json(DEFAULT_MANIFEST)
    legacy_cases = read_json(DEFAULT_TEST_CASES)
    report['legacy_inventory'] = {
        'manifest': 'backend/data/manifests/documents_manifest.json',
        'cases_path': 'backend/data/test_cases/test_cases_verified.json',
        'documents': len(legacy_manifest), 'cases': len(legacy_cases),
        'families': dict(Counter(c['test_family'] for c in legacy_cases)),
        'split_status': 'no development/final split; exposed development material',
    }
    try:
        load_test_cases()
        report['legacy_inventory']['integrity'] = 'valid'
    except ValueError as exc:
        report['legacy_inventory']['integrity'] = 'invalid'
        report['legacy_inventory']['reason'] = str(exc)
    result = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(result)
    print(result, end='')


if __name__ == '__main__':
    main()

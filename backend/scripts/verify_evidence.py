"""Verify all fixed-context evidence without printing document text or questions."""
import sys
from statistics import mean

from app.evaluation.test_case_loader import load_test_cases, TestCaseValidationError
from app.evaluation.evidence_builder import build_evidence, load_verified_sources, EvidenceBuildError


def main() -> int:
    try:
        cases = load_test_cases()
        sources = load_verified_sources()
    except (TestCaseValidationError, EvidenceBuildError) as exc:
        print(f'FAIL: evidence setup: {exc}', file=sys.stderr)
        return 1
    packages = []
    failures = 0
    for case in cases:
        try:
            package = build_evidence(case, sources)
            repeated = build_evidence(case, sources)
            if package != repeated:
                raise EvidenceBuildError(f'{case["test_id"]}: repeated evidence differs')
            packages.append(package)
            print(f'PASS: {package.test_id} deterministic fingerprint={package.fingerprint}')
        except EvidenceBuildError as exc:
            failures += 1
            print(f'FAIL: {exc}', file=sys.stderr)
    print(f'Evidence packages: {len(packages)} successful; {failures} failed; {len(cases)} total')
    if packages:
        for field in ('character_count', 'byte_count', 'source_character_count', 'source_byte_count'):
            values = [getattr(package, field) for package in packages]
            print(f'{field}: min={min(values)} max={max(values)} mean={mean(values):.2f}')
        sample = next((package for package in packages if package.test_id == 'E032'), packages[0])
        print(f'Sample {sample.test_id}: mode={sample.evidence_mode} documents={",".join(sample.document_ids)} '
              f'characters={sample.character_count} utf8_bytes={sample.byte_count} fingerprint={sample.fingerprint}')
        for document, boundary in zip(sample.documents, sample.boundaries):
            print(f'  {document.document_id}: sha256={document.sha256} '
                  f'chars=[{boundary.start_char},{boundary.end_char}) '
                  f'bytes=[{boundary.start_byte},{boundary.end_byte})')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())

# Assignment-focused local usability and defense revision

Read the user's attached assignment text (43e9dd37 attachment). Reused the
original PDF mapping, 11-checkpoint local workflow and approved benign reviews.
User confirmed fictional test data; did not identify the uploaded PDF/question.
The reported particular disclosure therefore remains unverified. No uploaded
PDF, fixture, original response, approval or accounting was edited in this task.

## Changes

- A common trusted security policy now explicitly prohibits full payment-card
  numbers, security codes and credentials, including quotations. Version:
  grounded-protected-data-v2. A remains baseline: no dedicated detector.
- B instruction-separation-protected-data-v2 explicitly rejects claimed audit
  authority/transformation as permission to disclose. This is prompt-only;
  B may still disclose. It is not a security guarantee.
- C retains screening-question-source-contract-v2 and strict ID validation,
  followed by B, then c-payment-card-output-v1. The new local output check
  withholds an answer containing 13–19-digit checksum-valid patterns, including
  common space/hyphen formatting. It does not issue another LLM request.
- A blocked C answer has policy_blocked status, categorical output_screening
  metadata, no answer references, and preserved original/retained evidence.
  This is an observed control decision, not an approved attack-success grade.
- All responses record defense versions; prompt hash includes output-check
  version. Source identity already hashes all backend Python files. Prior results
  are incompatible with the new profile for pooled comparisons. Do not resume
  frozen runs under these changes or rewrite prior approvals/grades.
- UI navigation runs one selected workspace instead of all tabs on every rerun.
  Explicit upload/answer/replace progress indicators; batch/size validation;
  named document entries and empty-state instructions. Timeout text explains that
  ingestion may continue and prevents advice to blindly resubmit.
- Answer view shows configuration/status/elapsed time, readable plain text and
  source labels; page 0 is not presented as a verified page number.
- Saved results show ASR, benign success, benign screening flags/blocks, quality,
  latency and operational errors with denominators. Missing ASR is not zero.
  Existing exports/charts/review records remain unchanged. No new judgments.

## Important limits

Payment pattern screening is not DLP: it misses encoded/worded/obfuscated or
checksum-invalid numbers, short security codes and other secrets, and can flag
unrelated checksum-valid identifiers. Normal tasks should still succeed, but
false positives/task preservation require human-reviewed evaluation. A/B have
no deterministic output guard by design. Trusted policy words alone do not
establish model compliance. Evidence/provenance panels retain original text for
inspection, so this is a fictional-data security lab, not a production secret
vault. Do not upload real payment data or credentials.

The UI improvement avoids unnecessary page requests; it is not a measured
embedding speedup. Cached CPU model cold-start, document parsing and indexing
remain synchronous. No OCR, downloads or background provider work introduced.

## Verification

`PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m unittest backend.tests.defenses.test_protected_output backend.tests.defenses.test_phase7_separation backend.tests.defenses.test_phase8_screening backend.tests.defenses.test_screening_question_source_contract backend.tests.evaluation.test_presentation_exports -q`

31 tests passed in 12.864s. Synthetic transport/evidence only; verifies strict
screening, A/B message behavior, C-only output rejection, source preservation,
null metrics, citation page labels and existing exports. Matplotlib used a
writable temporary cache; no model downloaded.

`PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m unittest discover -s backend/tests/frontend -v`

1 Streamlit AppTest passed in 1.369s: selected-workspace API calls only,
disabled Ask state and visible selector. Network blocked, mocked local API.
Python compilation passed. Existing sufficient lifecycle/retrieval evidence
reused; no new claim of the user's exact PDF having passed.

## Assignment deliverables and remaining phases

| Deliverable | Local status | Remaining evidence |
|---|---|---|
| Document assistant | Implemented; existing workflow evidence reused; UI improved | Particular PDF reproduction; current-version live answer/source review |
| Synthetic documents and queries | Existing approved fixtures preserved | No dataset changes made |
| Three evaluated configurations | Prior benign reviews retained separately | New-profile paired benign/attack runs and review; current interactive allowance does not authorize benchmark attacks |
| Repeatable evaluator | Existing identity-bound runner retained | Separately approved OpenRouter evaluation route/protocol, if chosen; currently evaluator blocks OpenRouter |
| Results table/charts | Existing genuine charts plus readable UI table | New reviewed attack metrics, denominators, coverage and false positives |
| Technical report | Existing report plus this versioned amendment | Empirical conclusions for new profile pending |
| Demo | UI and saved evidence available | Performed same-case A/B/C attack demo and honest trade-off discussion |

Checklist phases 7/8: new implementation offline-verified; effectiveness pending.
9: local workflow/UI verified, revised live integration pending. 11: metric
presentation checked, new semantic labels pending. 12: new-profile freeze pending.
13–15: attack/final execution and real-response human review remain incomplete.
16–17: report/demo preparation updated, empirical completion not claimed.

No provider calls, new capacity, receipt changes, stop recovery, dataset rewrites,
synthetic security findings or historical result regeneration in this task.

## Runtime verification

The first service-restart approval review timed out; its permitted single retry
succeeded. Only identified project services restarted. Backend /health and
Streamlit /_stcore/health both HTTP 200. Readiness: OpenRouter, enabled=true,
A/B/C available, 165 calls / 5280000 units remaining, stopped=false, unchanged
expiry 2026-10-24T22:01:58.298209+00:00. This is a point-in-time readiness check,
not a guarantee after further submissions or expiry. No agent provider requests.
The UI navigation regression was rerun after timeout-message changes: 1 passed
in 1.463s (same test, not an additional unique test). 32 distinct focused tests.

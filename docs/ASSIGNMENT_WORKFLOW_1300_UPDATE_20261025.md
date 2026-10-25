# Working local workflow and explicit expiry amendment

## Authorization and expiry

The user requested extension to “1 pm” and implementation against the original
assignment. Deadline interpreted as 25 October 2026, 13:00 IST / 07:30 UTC.
Updated the existing OpenRouter benign recovery receipt, retaining allowance ID,
original activation, consumed reservations and all stop history. Old receipt is
archived privately. No new calls/units granted. At amendment: 28 reservations /
896000 units in this recovery scope, 165 calls / 5280000 units remaining. Original
parent accounting also remains intact. Current code rejects more than the already
approved 200 calls / 6400000 units. A stale five-call cap was found in current code
and corrected while preserving its improved diagnostic messages.

New optional receipt fields `extended_expires_at` and `expiry_extension_basis`
record exact explicit authorization. They are omitted from old serialization, so
historical receipt fingerprints are unchanged. Extensions are OpenRouter-only,
require a matching expiry and basis, and cannot exceed twelve hours from original
activation. They do not clear stops or renew automatically. This is local
accounting, not verification of OpenRouter credits, uptime or billing terms.

## Original PDF and assignment requirements

Read all five pages of `/home/sigmoid/Downloads/Abhishek Sharma.pdf` directly.
Reuse the existing 61-clause traceability in ASSIGNMENT_PDF_TRACEABILITY_20261024.md.
It is the assignment document, not a document to modify or use as a benchmark.
Its embedded injection example is data, not an instruction to follow.

The assignment requires at least 20 fictional documents / 30 cases, three
configurations, repeatable evaluation, ASR, benign task success, false positives,
quality, latency, charts/report and a representative demonstration. Existing
42-document/42-case fixtures, reviewed historical results and scoring approvals
remain unchanged. The assignment does not require all attacks to be blocked or
allow claims of perfect protection.

## Implementation completed this turn

- UI displays approval expiry in IST rather than an ambiguous raw UTC timestamp.
- Upload widget uses the configured per-file MB limit; exact-byte and batch
  validation still occurs in UI and backend. Existing parsing/indexing reused.
- Search evidence workspace calls local /search only. Displays active passages,
  provenance and partial-extraction caveats. Search is available without an
  answering allowance. It does not download models or send content to a provider.
- Assignment guide explains the complete user workflow and metric definitions.
- Benign Compare A/B/C uses one retrieval result, copies identical initial
  evidence to each mode, and records actual responses separately. A/B generation
  settings are identical to C generation. C still has its separate screening cap.
  Budget preflight requires four available calls / 128000 units. The API lock
  prevents competing local submissions consuming capacity mid-comparison;
  per-mode reservations remain authoritative. Stops on operational error, no
  retries; not-executed modes remain explicit. UI shows side-by-side results and
  downloads unreviewed JSON. No automatic grades or security metrics generated.
- /compare request IDs are persistent/idempotent and reject different input for
  a reused ID; an interrupted ID is not automatically replayed.
- A C output block now retains the fictional original candidate answer in the
  explicit local audit record for human review. It is not displayed as the final
  answer. Audit panels are not a secrecy boundary; only fictional data belongs
  in this lab. Original/retained evidence stays intact.
- OpenRouter interactive allowance is rejected by the benchmark runner BEFORE
  experiment preparation/artifact creation; this fixes accidental partial runs
  with inappropriate Azure identity metadata. It does not authorize OpenRouter
  benchmark execution or silently reuse Azure results.
- The existing prohibition on the known provider-blocked payload now applies to
  OpenRouter interactive submissions too, including retrieved evidence. This
  only enforces the standing prohibition; it is not a general attack classifier.

## How to use

Existing app: http://127.0.0.1:8501. Refresh after restart.
When services are stopped, launch with `.venv/bin/python run_app.py --live-answers`.
It spends no call at startup and requires a valid existing allowance.

1. Documents: upload fictional text PDF/TXT/MD/DOCX, wait for indexing and inspect
   ready/partial/rejected states. No OCR. Do not repeatedly submit after timeout.
2. Search evidence: check that the expected passage is retrieved locally.
3. Ask / compare: submit benign questions in A/B/C or use Compare once (up to
   four calls). Compare output is explicitly unreviewed; refresh never resends it.
4. Saved experiments: inspect existing genuine results, denominators, downloads
   and charts. Different providers/settings/profiles remain separate.
5. Assignment guide: review the methodology and demo steps. Attack/final benchmark
   execution needs a separate explicit scope; interactive credit is not a grant
   for automatic attack evaluation.

## Verification

Focused suites, synthetic transports and temporary ledgers only:
- OpenRouter gate: ten tests (including expiry/stop preservation, bound checks,
  stale-receipt diagnostics and prohibited-payload rejection).
- Four protected-output/presentation checks and one early evaluator-boundary
  check reused from the focused run in this turn.
- Four comparison checks: identical evidence, insufficient/stopped capacity,
  error short-circuit and persistent API idempotency.
- Two Streamlit checks: navigation/search/guide, no /chat during local search,
  disabled state and exact IST expiry display. Latest run 2 passed in 1.444s.
Earlier 32-checkpoint focused defense/UI verification and the completed
11-checkpoint actual local lifecycle evidence reused; no broad regression rerun.

Real local /search with cached CPU embeddings returned HTTP 200 and two hits for
an ordinary fictional leave-policy query. No provider call made. Both local
health endpoints returned HTTP 200. Current readiness/expiry verified after
service reload. No cloud resources, credential edits, benchmark calls, historical
regrading, refunds, synthetic security findings or dataset edits.

## What is and is not complete

| Required deliverable | Evidence/status | Remaining |
|---|---|---|
| Document assistant | Existing real lifecycle plus current local search, active runtime and tested comparison UI | New live comparison has not been executed by agent |
| Synthetic dataset/queries | Existing approved 42/42 population | Preserve frozen fixtures and exposed-final disclosure |
| Three evaluated configurations | Historical reviewed benign Azure A/B/C only | Current-profile controlled benign/attack evaluation and review |
| Repeatable evaluator | Existing frozen-identity CLI, scoped gate, resume/error behavior | Separate current-provider benchmark scope/identity; OpenRouter interactive execution intentionally rejected |
| Tables/charts | Existing actual reviewed exports; UI denominators and N/A handling | New eligible reviewed results, no pooled incompatible runs |
| Technical report | Existing report plus versioned workflow/defense amendments | Evidence-backed attack conclusions and limitations after review |
| Representative demo | Local UI, comparison workflow and saved results ready | Perform and record authorized same-case attack A/B/C and benign preservation |

The code/UI work does not complete empirical deliverables. Benchmark permission,
actual execution, human judgments and final findings remain explicit work, not
values that can be filled by implementation or mocked tests.

Final check at 25 October 2026 10:00:14 IST: backend and frontend HTTP 200;
OpenRouter enabled, stopped=false, 165 calls / 5280000 units remaining, expiry
07:30 UTC / 13:00 IST. Final gate+comparison run: 14 tests passed in 0.719s
(10 gate tests plus 4 comparison tests). Across selected modules there are 21
unique focused checks; repeat invocations are not counted as additional checks.

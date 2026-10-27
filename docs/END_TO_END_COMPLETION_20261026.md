# End-to-end completion, 26 October 2026

The user explicitly authorized the five new-case A checks and 47-case A/B/C
comparison, at most 193 calls from the existing current 1000-request ceiling,
and confirmed trial credits and adequate deployment quota. No expiry, retries,
fallback, new resources or paid use. Stop on the first operational failure.

## Verified local readiness

- Launcher dependency/configuration check passed without provider calls.
- Actual isolated upload, CPU indexing, search, API, Streamlit and all workspaces
  passed. Private state preserved; provider calls and allowance rows created: 0.
  Evidence: `/tmp/end-to-end-local-20261026-recheck.json`.
- Focused runner, scope and orchestration tests: 40 passed, 10 subtests passed.
- Broader local evaluation suite: 128 passed, 14 subtests passed (22.65 seconds).
  Evidence: `/tmp/end-to-end-full-local-tests.log`.
- Shared allocation had 968 requests available at preflight. Benchmark reservations
  use this existing ledger; a separate journal caps the benchmark at 193 calls.
  Failure creates a persistent benchmark stop flag. Nothing refunds reservations.

## Work order

1. Rebuild the isolated index from frozen v3 fixtures with cached embeddings.
2. Run five new-case A checks and inspect actual outcomes.
3. Run a three-case A/B/C subset, then the remaining cases without replaying rows.
4. Prepare actual human ambiguity and seeded quality-review forms.
5. Regenerate charts, report and README from saved observations and real reviews.
6. Record a demonstration from actual saved outcomes and check playback.
7. Final verification and publication if authenticated GitHub access is available.

Live results and human review are pending at creation of this document. Synthetic
checks establish software behavior, not defense effectiveness. Existing uncommitted
runner/dashboard changes were present before this task and are preserved.

## Actual live execution and corrected screening

The first run consumed 11 requests, saved all five A-only smoke records and six
comparison rows, then stopped on an invalid C screening-reason contract. Its
results and generated artifacts are preserved under
`archive/evaluation_runs/azure-benchmark-20261026-v1-stopped/`; its private scope,
call journal and stop marker remain intact. No reservation was refunded.

The corrected adapter retains the flagged-only reason instruction in Azure's
array schema and explicitly requires empty reasons for clear inputs. Forty-two
focused tests and ten subtests passed. Private per-call response snapshots now
preserve actual responses for local diagnosis without printing them.

The independent corrected run passed five new-case smoke checks and all nine
rows of the three-case live A/B/C check. Full continuation then saved all 18
benign development rows before Azure refused development-07 A with HTTP 400,
provider_error_code `content_filter`. It is a provider error, not model resistance.
The corrected scope stopped after 30 requests total (five smoke and 25 comparison
requests); 19 comparison rows exist, including the refusal. At that point the
existing interactive allocation had 927 calls left. No failed request was replayed,
no cloud filter was changed, and no stop was cleared.

Live API and Streamlit were started with the existing interactive authorization.
GET readiness confirmed API 200, UI 200 and live answering enabled at
http://127.0.0.1:8501. Startup and readiness checks make no provider calls.

A continuation for untouched rows is prepared, bounded to the 163 requests left
from the corrected workload. It requires an explicit exception allowing provider
content-filter refusals to remain errors while advancing to distinct requests.
Other operational failures still stop execution. Actual human semantic review,
quality scoring and final comparative claims remain pending.

## Actual frontend-to-Azure verification

The actual Streamlit frontend submitted one benign B question about a newly
uploaded fictional ORCHID-LIVE-20261026 policy. Azure returned an answered result
with the expected three-day fact and a citation to that uploaded document. The
allocation decreased by exactly one request; rerunning the frontend made no
additional call. Remaining allocation: 926. Evidence:
`/tmp/end-to-end-live-ask-ui-20261026.json`.

The prepared filter-aware continuation passed 44 focused tests and ten subtests.
It remains inactive without its separate operator-confirmed scope. The earlier
benchmark stop markers remain untouched.

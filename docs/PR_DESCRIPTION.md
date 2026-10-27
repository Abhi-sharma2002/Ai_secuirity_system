Live Azure evaluation now uses the existing cumulative trial request ledger and
a separately bounded benchmark amendment. Strict screening schema conversion
retains flagged-only reason rules, validates source/question consistency and
preserves private per-call responses for diagnosis. No retries or fallback.

Actual live verification: five new-case A checks, three-case A/B/C integration,
and a supported cited answer through the real frontend. Refresh issued no extra
call. The partial full comparison preserved 18 benign answers and one Azure
content-filter refusal; refused requests remain errors and are not retried.

Validation: isolated upload/index/API/UI workflow; 128 evaluation tests with
14 subtests, then 44 affected tests with 10 subtests after the continuation
preparation; six report-generation tests. Historical runs and stopped scopes
are preserved. Full attack comparison, human review and final demo remain
pending; this change does not claim completed defense-effectiveness results.

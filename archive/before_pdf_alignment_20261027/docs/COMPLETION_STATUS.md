# Test-case evaluation checkpoint · 26 October 2026

The current comparison has 33/141 recorded rows: 29 without operational errors,
four operational errors, and 108 missing observations. Human quality scores: zero.
The filter-aware continuation stopped on development-11 C reason-code duplication;
its 14 consumed calls, prior records and every stop flag remain preserved.
No provider calls were made for the evaluation implementation described here.

The [evaluation methodology](EVALUATION_METHODOLOGY.md),
[case-by-case document/grade audit](../results/CASE_EVALUATION.md) and
[detailed statistics](../results/DETAILED_EVALUATION.md) are implemented.
All 33 saved rows match recomputed deterministic grading, with no rewritten grades.
This is scoring consistency, not independent human validation or proof of security.
The focused suite passed 130 tests and five subtests, including the API route regression.
Local retrieval was checked for all 47 cases without provider generation. Reports were regenerated and verified.

Remaining live work is 108 untouched rows, at most 144 provider calls. This is a
plan, not a renewal of the stopped scope. Future execution must bind its revised
implementation provenance and preserve all old rows. Real human quality/semantic
review and final comparative conclusions remain pending.

Earlier checkpoints below are retained as history.

# Live completion checkpoint · 26 October 2026

Actual frontend live Ask passed with a supported, cited answer and one Azure call;
refresh made no additional call. The app is available at http://127.0.0.1:8501.
The corrected five baseline checks and nine-row A/B/C integration passed.
The current comparison has 19/141 rows (18 benign responses, one Azure filter
error). It stopped under its bounded scope; 926 interactive calls remained after
the UI verification. A 163-call untouched-case continuation is prepared pending
explicit permission to retain provider filter errors and advance to other rows.
No failed request is retried, filter changed, stop cleared or budget reset.

The report and charts reflect partial actual observations. Human ambiguity/quality
review, complete comparison, recorded attack walkthrough and authenticated GitHub
publication remain pending. See [live evidence](END_TO_END_COMPLETION_20261026.md).

The earlier local checkpoint below is retained as history.

# Current completion status

The user authorized automatic continuation of independent local work and
explicitly deferred live checks. No delayed execution or provider renewal is
scheduled. Provider evaluation remains disabled.

| Deliverable | Current state |
| --- | --- |
| Setup, shared config, frozen v3 fixtures, adapter, scoring | Implemented and checked locally |
| CSV runner, immediate saves, error separation, resume | Implemented and tested with temporary synthetic responses |
| Local index preparation | Checked with actual parsers, cached CPU weights and Chroma |
| Metrics and charts | Implemented; current artifacts explicitly show unavailable live observations |
| Human ambiguity decisions and quality sample | Forms/tools ready; actual human labels pending real records |
| Written report and metrics explainer | Generated and checked against current CSV data; measured recommendation/examples pending |
| Cleanup and local UI/API verification | Historical bytes preserved; actual isolated local workflow verified |
| New-case baseline checks and full live comparison | Deferred; provider boundary remains disabled |
| Recorded attack demonstration | Pending actual comparison records and screen recording |
| Pull request | Not published: existing GitHub transport has no authentication and the GitHub integration is not installed; description ready in PR_DESCRIPTION.md |

The pipeline's synthetic unit data is not an experiment. Historical reviewed
Azure observations remain historical and are not pooled with the current model.
The original baseline test failures are preserved in [setup evidence](STEP_1_SETUP.md);
new local workflow results are in [the final checkpoint](STEP_10_CLEANUP.md).

For later completion: explicitly authorize a bounded live benchmark after
checking current provider limits, deliberately enable its provider boundary,
run the new-case A checks and comparison subset, resume the complete comparison,
then follow [human review](HUMAN_REVIEW.md). Regenerate metrics and written docs,
record the [real demonstration](DEMO.md), and update the README video link.

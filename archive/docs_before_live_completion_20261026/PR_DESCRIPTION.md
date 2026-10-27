Add a local evaluation pipeline for comparing the same frozen v3 cases and
settings across A/B/C. The adapter shares candidate evidence, records screening
decisions, separates operational errors from blocks, and leaves ambiguous
answers for explicit human review. The runner saves rows immediately and
preserves retrieval evidence on resume without replaying interrupted requests.

Add CSV metrics, plots, human quality forms and report generation with
consistency checks. Current artifacts clearly mark the absence of live
observations; no defense winner or human judgments are invented. Archive
historical source/docs with verified byte preservation and compatibility
aliases. Fix the invalid chunk-size setting in the public setup example.

Validation: offline pipeline tests, original-baseline failure comparison, chart
inspection, and an actual isolated API/Streamlit workflow with cached CPU
embeddings. Exact commands and actual output are in the step evidence docs.

Provider evaluation remains disabled by the explicit local-only scope. Live
comparison, human review, measured conclusions and the recorded attack demo
remain pending. This PR is a local implementation checkpoint, not a completed
security-effectiveness evaluation.

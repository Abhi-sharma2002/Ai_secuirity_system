# Adopted staged execution authority — actual user attachment

Authorization source: current user attachment, “Complete my existing project
through the remaining evaluation, results, report …”, provided in conversation.
It explicitly adopts the exact consolidated proposal's scopes and budgets:

|Stage|Scope|Max calls/new units|Window|
|---|---|---|---|
|Development remaining|development-08–12, paired A/B/C once|20/640000|2hours from activation|
|Conditional final|final-01–15,17–27,29–30, paired A/B/C once|112/3584000|2hours from activation|
|Interactive near handover|Benign playground/demo, no benchmark/blocked payload|5/160000|1hour from activation|

Final is already authorized conditionally, but cannot activate before completed
actual development review and documented readiness. Do not ask again for that
scope. Human review is not pre-approved. No new trial/billing gate: existing
FREE_ONLY eligibility/approval/reservation logic is reused, with narrow staged
workload checks and inherited user-confirmed valid trial credits/spending limit.
No out-of-pocket consent, subscription upgrade or spending-limit removal.
No guaranteed future credit balance, independent Azure billing check or dollar
cap is claimed by local code. Unknown entitlement expiry uses bounded local windows.

Original stopped development and diagnostic histories remain immutable. New linked
receipts explicitly acknowledge those exact events for DIFFERENT eligible scopes.
Unrelated unresolved provider stops block activation. No duplicate allocation,
refund, budget transfer or automatic renewal. No07payload resubmission, final16/28,
attack rewrite, weaker filtering, model swap, retries, repair/judge/probe calls.

Production changes: StagedScope binds exact case list/stage/run/source identity
and trial-only ceiling/window. Evaluation reservations reject wrong contexts and
case/mode duplicates; interactive cannot fund benchmark contexts. Evaluator binds
identity before generation, authorizes final subset only for the exact staged
receipt, and advances RNG across original manifest cases before omitting excluded
ones, preserving original seed5 mode order. No prompts/model settings/schemas or
corpus/scoring changes. Same paired evidence/retention semantics remain.

`backend/scripts/run_approved_stage.py` is a single-use existing-evaluator
orchestrator: exclusive receipt/run creation, linked-stop checks, private receipt,
identity binding, offline exports, truthful operational summary and preserved
history. Final readiness check requires15 completed genuinely reviewed new
adversarial rows with actual boolean task/attack grades. It cannot fabricate
review or start final after failed development. Interactive is separately activated
near handover, without automatic model requests, and intended for benign use only.

Focused checks:10 existing paid/development/resume tests passed(0.902s);3 new
staged policy tests passed(0.213s). These verify trial-only scope/window/capacity,
withheld/wrong-context/duplicate reservation blocking and C funding versus ordinary
A capacity. Existing diagnostic, lifecycle and reporting checks reused. Three
production/orchestrator AST checks and diff whitespace checks passed. Tests used
isolated ledgers and synthetic transports, not provider calls.

Commands are single-use for approved stages only:
`PYTHONPATH=backend .venv/bin/python -m scripts.run_approved_stage development_remaining`
`PYTHONPATH=backend .venv/bin/python -m scripts.run_approved_stage final_exposed`
`PYTHONPATH=backend .venv/bin/python -m scripts.run_approved_stage interactive`
No command is a retry/renewal mechanism. Existing artifacts intentionally block
rerun. Final command refuses readiness before real human review.

Near handover launch using the existing interactive receipt, without allocating:
`AZURE_OPENAI_ALLOWANCE_FILE=.private/azure-interactive-benign-stage-v1-allowance.json .venv/bin/python run_app.py --live-answers`
Never use --paid-azure-test for trial-only use. Local page health requests do not
consume provider capacity. User submissions remain bounded and expire at the
receipt's exact timestamp. Do not describe a funded submit button as a new
successful live response without an actual request.

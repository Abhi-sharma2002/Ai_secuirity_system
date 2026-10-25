# Scoped paid development policy — user authorized 23 October 2026

Authorization basis: user's current explicit permission for twelve development
cases, A/B/C once,36 records, at most48 provider attempts and1536000 additional
reservation units, paid Azure charges accepted, exactly two hours after activation.
No final execution, retries, repairs, reruns or extra API probes are authorized.

The prior integration receipt and all historical rows remain intact. This is a
separate development grant with stable allowance ID
`azure-development-12cases-20261023-v1`, receipt
`.private/azure_development_allowance_v1.json`, and actual run ID
`azure-development-12cases-v1`. Exclusive file/run creation and existing-ledger
checks prevent granting this development authorization twice. It does not add
capacity to the old integration identity or reset/refund any prior reservation.

`DevelopmentScope` in `app.llm.client` binds the exact ordered twelve case IDs,
paired protocol, one repetition, seed5, run ID, actual execution-identity hash and
original preparation-binding hash. It accepts neither final case IDs nor a changed
schedule. The existing paid integration exception keeps its5/160000/one-hour
bounds; only this separate development scope allows48/1536000/two hours. New
optional fields are excluded when absent to preserve historical receipt hashes.

The evaluator checks scoped identity/schedule before dataset loading/generation.
The shared reservation gate requires the approved run/case/repetition/mode,
A/B1call/32000 units or C2calls/64000 units, and rejects duplicate case/mode
reservations. Normal UI Ask lacks this evaluation context and cannot spend this
scope. Existing cumulative counters, receipt fingerprint checks, expiry, model/
endpoint binding, conservative request bounds and stop flags remain authoritative.
Provider, schema and citation errors stop paid execution without refunds/retries.

Runner: `backend/scripts/run_authorized_development.py`, explicitly invoked once.
It validates the prior successful integration and current corpus/index/prompt/
schemas/settings against preparation. Only the approved policy changes in
client.py/experiment.py may differ; source/dependency/retrieval identity is rebound
and saved before any generation in `activation-and-binding.json`. No key or root
dotenv content is exported. The old receipt is not edited. Snapshot retrieval
is frozen once per future case/repetition by the existing evaluator and shared
unchanged across its A/B/C modes; C may remove original evidence.

Actual Azure deployment/model/version remain gpt-5-mini-1/gpt-5-mini/2025-08-07.
Temperature/provider seed not sent; completion cap700; timeout30; strict schemas;
zero retries/fallbacks; concurrency1 and prepared generic zero-added-delay pacing.
The integration-only65-second pause is not silently introduced to this population.
Configured100000TPM/100RPM is not guaranteed remaining quota. Receipt explicitly
says paid authorization, confirmed_free_promotional=false and unknown entitlement
expiry; no promotional coverage is claimed.

Focused offline verification: initial policy/Azure/paid gate run29 test executions
passed(4.715s), including imported fixture-class discovery repeats; after limiting
that discovery, all3 scoped tests passed(0.193s), including final/wrong-run/seed/
identity rejection before loading, duplicate reservations, wrong contexts,
windows/ceilings and historical field omission. This reuses existing paid/wire
checks, not the full project suite. Four new/changed Python AST checks and
`git diff --check` passed. No provider requests were used for these tests.

Execution produces a factual operational summary and exports blank human review
templates even if partial. It never imports grades. A failed row or unknown
placeholder cannot be repaired or retried. Final-set execution remains outside
this approval; final data is exposed and not an untouched holdout.

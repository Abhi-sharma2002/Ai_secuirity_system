# Acceptance matrix · revision 2

## Phase 6 single authorized execution stopped · 21 October 2026 (India)

The remaining account prerequisites were accepted from the operator: exposed key revoked/replaced; Groq Billing Free — $0 — Current Plan; configured openai/gpt-oss-20b limits 30 RPM/1000 RPD/8000 TPM/200000 TPD; sole organization user/no competing traffic. Organization Personal, All projects, October 2026 UTC Activity showed “No usage data,” observed October 21 14:30 local. Dashboard may lag 15 minutes; exact request/token totals were unavailable, not fabricated, and no live quota balance was guaranteed.

Authorized private allowance update preserved allowance_id/provider/model/capabilities and cumulative history. Under the backend lock, read-only inspection found zero matching records/consumed units/outstanding reservations and no quota stop. Set free confirmation true, total capacity=consumed+4 calls/consumed+128000 LOCAL reservation units, confirmation note with actual time/basis, expiry exactly one hour after update; atomic replacement retained mode0600 and Git exclusion. No identity reset/refund. Evidence: phase6-allowance-update-v1.json records actual UTC update/expiry and non-secret audit. Local units are not measured provider usage.

Fresh offline readiness exited0 with no blockers; then invoked the prepared paced single-use wrapper ONCE with process-only LIVE_LLM_ENABLED=true, FREE_ONLY=true, existing development-02 paired A/B/C seed5, cap4, 700 output, timeout30s, gap65s after completion, retry/repair/rerun0. Network-enabled execution was used directly, avoiding a sandbox-failure provider retry. Backend lock was available; no service was stopped/restarted. Root .env stayed live-disabled and unchanged.

Observed **exit1**, **352.211075 seconds total process elapsed**. A's first actual generation attempt returned **HTTP401 AuthenticationError**, category authentication_or_permission. The existing stop-on-operational-failure rule stopped the run; B/C were not attempted. Exactly one provider/client attempt and one failed ledger record, with **32000 local units retained**, leaving **3 calls/96000 local units**. No refunds, resets, reruns, extra diagnostic provider calls or limit increases. Root cause beyond the observed authentication rejection is not established; no claim of invalid replacement key, paid billing, quota exhaustion or model incompatibility is inferred.

No answer or references returned, usage and provider request ID unavailable/null. Client call latency1373.207985ms; wrapper boundary1388.427409ms; A mode1402.311804ms. First-call pacing measurement0.000000956s (clock overhead, no intentional wait); no inter-request gap was exercised live. Total process time includes lengthy existing runner readiness/dataset/snapshot validation; nested latency measures are not additive. Exact pre-provider duration was not independently instrumented.

Initial and A-supplied evidence retain the actual source quote “Development mentor check-ins occur every Friday.” No answer exists to assess for semantic support; official task/quality/attack judgments remain null. Screening response/schema/C-retained evidence are null because C was not reached. This is an operational failure and incomplete integration smoke, not benign task failure, successful defense, ASR result or defense recommendation. Offline pacing evidence remains separate; no successful live pacing/complete A/B/C integration claim.

Final checks: FREE_ONLY=true, effective/root live disabled; root .env hash unchanged; allowance0600; process exited/backend lock released; .env/.private remain ignored/untracked. Authorized expiry is not extended after failure. No later phase started. Existing single-use result folder is preserved and cannot be resumed. See docs/evidence/phase6-execution-result-v1.json and backend/data/runtime/experiments/phase6-benign-20261021-v1/{experiment.json,integration-diagnostics.json,case-development-02-A-0.json}.

## Phase 6 execution authorization received; material prerequisites pending

The user confirmed Groq Billing “Free — $0 — Current Plan” and configured limits for openai/gpt-oss-20b: 30 RPM/1000 RPD/8000 TPM/200000 TPD. The user authorized one existing paced development-02 paired A/B/C smoke and an allowance update preserving identity/usage, adding exactly four call reservations and 128000 local reservation units beyond consumed amounts, with expiry one hour after the actual update. This is not authorization for paid use or a quota reset; local reservation units are not measured provider tokens.

Read-only preflight found free-only true, root/effective live disabled, configured model/path matching, credentials present, schema-valid unexpired allowance with existing capability flags, owner-only 0600 permissions, and .env/private allowance ignored and untracked. Matching allowance has zero call records/consumed units/outstanding reservations; single-use smoke directory is absent and backend lock was available. Evidence: docs/evidence/phase6-execution-preflight-v1.json.

Local records do not reliably establish that the exposed credential was revoked/replaced; current quota headroom and competing organization traffic are also unknown. Requested only these missing material confirmations, without asking again about the confirmed Free Plan or configured limits. Execution is pending those answers. No allowance update, new expiry, provider attempt, reservation, live enablement or service restart has occurred. Phase 6 remains incomplete; no subsequent phase begun. Once prerequisites are established, continue the already authorized single attempt rather than request execution authorization again.

## Phase 6 prepared; live execution pending · 21 October 2026 (India)

| Preparation requirement | Evidence | Status / limit |
|---|---|---|
| Secret-safe current readiness and cumulative budget | phase6-preparation-v1.json; read-only allowance/SQLite inspection | Groq/openai/gpt-oss-20b; live false/free-only true; credential/SDK present; schema/model/expiry valid; free confirmation false; 4 calls/16000 tokens remain. Credential validity/account eligibility unverified |
| Smallest useful paired benign workload | development-02 ordinary source/support annotation; actual offline initial retrieval; existing exp.plan | Same Friday question/initial evidence for A/B/C, one repetition, seed5. No unresolved review issue; evaluator-only gold excluded from source payload |
| Correct provider-call/reservation bound | Current client/assistant/exp.plan; focused tests | A1+B1+C(screen1+generation<=1)=<=4 requests, 128000 reserved tokens; retry0/repair0; output700/request, timeout30s. Current allowance is insufficient and unchanged |
| Predetermined semantic/operational success criteria | PHASE6_SMOKE_PLAN.md | Schema/IDs separate from semantic support; benign flags/blocking observed, no favorable rerun; unknown usage null; integration only, not security effectiveness |
| Executable current-path run and diagnostics | scripts.phase6_smoke wraps experiment.run; scripts.prepare_phase6 read-only helper | Fresh-run/identity/evidence checks, hard caps, attempt/schema/accounting records. Process-scoped future live enablement; root .env/services remain disabled. Not executed live |
| Offline verification | phase6-preparation-tests.log | Final 9 passed, exit0, 0.086s; synthetic responses/approval settings explicitly labeled; transport blocked; compileall exit0 |
| Account confirmation and authorization | Combined statement in PHASE6_SMOKE_PLAN.md | Pending. Truthful allowance must first fund 4 calls/128000 reserved tokens; no increase or approval edit performed by preparation |

No Phase 6 live gate passed; mark only “Phase 6 prepared; live execution pending.” Prior Phase 4 interrupted runs and HTTP integration limitations remain unchanged. Completed Phase 5 verification was reused. No later-phase work or provider call. This section supersedes historical model-unset observations for readiness, while preserving their original evidence scope.

## Phase 5 offline gate

This section supersedes earlier pending Phase 5 gap statements. Existing genuine CPU/Chroma and semantics-exposure evidence was reused; new checks targeted only maintenance apply, forced source-text byte budgets and fresh-process active playground persistence.

| Requirement / ID | Evidence | Outcome / limits |
|---|---|---|
| RET-01: pinned CPU model, dimension/norm, no substitute/download | Existing vector validation tests; phase5-real-persistence.json writer/reader | Actual cached all-MiniLM-L6-v2, revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41, CPU, 384 dimensions; network blocked/offline flags; real embeddings, no fake vectors |
| RET-02: persistent verified indexes, incompatibility/interruption refusal | Prior IndexRetrievalTests and genuine audit; new independent reader | Writer exits, reader reopens persisted registry/indexes, real queries succeed with index-write/ingest guards; logical inventory unchanged |
| RET-03: active versions/provenance only | New writer replacement/deletion setup and fresh reader | Two correct active document/version/chunk/source hashes/page/section results; superseded/deleted records remain retained but excluded |
| RET-04: context budget, top-k, omitted/source IDs | ContextBudgetTests (three methods), actual lifecycle.search assembly; retrieval/LLM doubles explicit | 11999/exact 12000/over limit; Unicode/multiple chunks; oversized/empty; skip whole chunks, select later fitting chunk; deterministic distance/ID order; references and actual supplied sources verified |
| RET-05: disposable rebuild preview/apply | Seven-step real audit, including actual maintenance CLI rebuild and rebuild --apply | Every affected path asserted under disposable directory; preview unchanged; missing active collection genuinely rebuilt/verified; active retrieval succeeds in fresh process; temporary state removed |
| RET-05 failure/recovery | MaintenanceFailureTests (one method), explicit vector/index-failure doubles | Parser mismatch and failed index do not move active pointer; subsequent valid apply succeeds. Prior partial-index/config-mismatch checks reused |

Final commands: real audit parent and all seven subprocesses exit 0; focused suite 4/4 passed in 2.438s; compileall exit 0. Four unit methods and seven audit stages are different evidence categories, not eleven tests or empirical model outputs. Source-text budget excludes metadata/framing; oversized synthetic candidate is outside normal 1000-character chunk production. C unit decisions/answers are doubles; no live screening/security result. No production fix required, no Phase 5 blocker. No new HTTP integration, real-user storage maintenance, distributed consistency or retrieval-quality/generalization claim. Prior Phase 4 incomplete runs remain incomplete. Phase 6 prerequisites are listed in IMPLEMENTATION_STATUS.md/VERIFICATION.md; live remains disabled and Phase 6 unstarted.

## Phase 4 offline gate · 20 October 2026 (India)

This section supersedes earlier Phase 4 pending-local-verification wording. Final new suite: 7 passed, exit 0, 7.553s. No runtime repair needed. Existing semantic/source audit evidence was reused, not rerun. See VERIFICATION.md for exact commands, interrupted attempts and explicit doubles.

| Requirement | Evidence | Outcome / scope |
|---|---|---|
| 1 / PARSE-01/02/04: actual TXT, MD, text PDF, DOCX | test_actual_formats_arbitrary_names_and_provenance; prior real 42-source audit | Real bounded subprocess extraction; DOCX paragraph/table/header/footer order and PDF pages verified |
| 2 / UP-01: arbitrary names, spaces, Unicode | Same new test sends all four formats through lifecycle.ingest | Generated UUID4 document/version IDs; no benchmark filename restriction; index boundary doubled |
| 3 / UP-02, PARSE-02/04: empty/corrupt/encrypted/unsupported | New empty/corrupt/size tests; existing ParserV2Tests encrypted real PDF and invalid UTF-8/control/format/ZIP-ratio checks | Representative rejection cases verified; historical successful parser evidence retained |
| 4 / PARSE-03: image-only and partial acceptance | test_real_image_only_and_partial_workflow uses an actual raster-only PDF and a text+raster PDF | needs_ocr cannot activate; needs_review excluded until explicit acceptance; warning/partial flag persist. No OCR; live caveat wording unverified |
| 5 / PARSE-05: size/resources/deadline/cleanup | New byte/text/page/package checks, real child deadline/limit probe, current multipart spool closure | Linux bounds observed; children joined; rolled spool closed. Stalled worker/probe/async dispatch are explicit doubles; retained raw history is intentional |
| 6: provenance | Actual-format test plus existing audit artifact | Source raw SHA, UUID document/version, chunk SHA, character offsets, PDF page (1-based), DOCX body/header/footer section; page=0 for unpaginated text/DOCX |
| 7: deterministic chunks/settings/Unicode | test_unicode_chunks_deterministic_overlap_and_full_content plus prior three-case audit | Current lifecycle._chunks IDs stable for same version/settings; 1000/150 character settings unchanged; exact overlap and code-point reconstruction. Grapheme atomicity not promised |
| 8 / DATA-03: preserve attack source text | New all-format/source-slice checks plus semantics-exposure-v1.json | No suspicious-text filtering; PDF extraction whitespace and documented TXT BOM/newline normalization distinguished from byte identity |

Two interrupted async-dispatch runs (exit 130) provide no complete suite result. Passing multipart test doubles async thread dispatch while retaining real route/multipart/files/parser behavior; it is not new HTTP integration evidence. Existing API smoke's unverified status is unchanged. No Phase 4 offline blocker; live caveat generation remains a later provider-dependent check. Phase 5 remains unstarted: verify disposable rebuild apply, runtime context-byte exact/over-limit omission with multilingual text, and explicit fresh-process active-playground persistent-index reopen/query evidence while reusing existing genuine embedding/retrieval results.

## Semantics/exposure audit · 19 October 2026 (India)

| ID | Evidence | Outcome / limit |
|---|---|---|
| DATA-06 | Versioned semantics-review-v1 prior values/proposals | development-12 and historical E037/E038 interpretations documented; no active correction or human approval fabricated |
| DATA-05 | Actual source/question checks for six template groups | Overlaps confirmed; final remains exposed comparison set |
| DATA-03 / RET-04 | Actual bounded parsing, runtime chunks and cached-model retrieval in disposable Chroma | All three flagged cases preserve attack components; case-scoped retrieval includes both. Full-corpus global top-k drops target terminal overrides; byte budget not reached |
| EVAL-04 | Per-stage evidence and component coverage in semantics-exposure-v1.json | Pre-assembly vs pre-screen vs unobserved post-screen distinguished. Missing target exposure is not defense success; standalone terminal attack means multi-chunk dependency remains unproved |
| EVAL-05 | Annotation/scoring file edit/refuse-resume test; scoring_spec_hash metadata | Actual scoring specification now identity-bound; old incompatible runs preserved/refused |

50 focused tests passed; review-source integrity checks and exact outcomes in VERIFICATION.md. Phase 3 storage gate remains satisfied and was not retested. No live screening/effectiveness claim; model/free-allowance/explicit-live prerequisites remain blockers. See SEMANTICS_EXPOSURE_AUDIT.md for one row per issue and remaining human-review questions.

## Phase 3 storage gate · 19 October 2026 (India)

Outcome audit confirms command exits: initial 10-test pass = 0; final 21-test pass = 0; incomplete sandbox API attempt = 124 (25-second harness timeout). No assertion failures observed. The timed-out attempt is excluded from passing-test counts. See `docs/evidence/phase3-outcome-audit.json`; successful runs overlap. This audit made no runtime changes and does not expand the storage guarantee beyond the single-process managed raw-directory scope.

UP-03 retained-source boundary is now verified: 11 new tests plus six existing lifecycle and four index/retrieval checks passed in a 21-test focused run. Runtime required no changes. STORAGE.md defines the actual fixed 200 MiB raw-file scope, equality/admission rules, global-directory measurement and explicit retention/release behavior. Source/vector/database storage are not conflated.

| ID | Check | Current evidence |
|---|---|---|
| UP-03 | Below/equal/one-byte-over and cumulative capacity | Real temporary files/SQLite under 10-byte limit; 413 before any version/raw allocation; existing retrieval preserved |
| UP-04 | Ready duplicate at capacity; same name/new bytes; scope | Existing ID reused without double charge; changed bytes rejected without overwrite; raw scope global, dedup playground-scoped |
| UP-05 | Replacement overlap and failure | Old+new bytes must fit; failed indexing preserves old active source and retains failed raw until cleanup |
| UP-06 | Delete vs explicit release | Delete excludes retrieval but retains bytes; dry run changes nothing; actual disposable cleanup releases eligible raw and preserves active files |
| UP-07 | Concurrency/interruption/restart | Barrier-started distinct uploads cannot both fit; persisted interrupted/orphan bytes still count after recover; no counter reset or phantom capacity rows |
| RET-05 | Cleanup apply | Exercised only with disposable raw/registry/Chroma; inactive/orphan removal verified. Rebuild apply and real-data destructive maintenance still unverified |

Batch API returns 201 with per-file rejected/http_status=413 outcomes; replacement returns HTTP 413 and preserves old evidence. Sandbox API timeout and successful authorized outside-sandbox run are recorded in VERIFICATION.md. No live model/security outcome claimed. Next recorded model-dependent gap: PARSE-03 caveat wording; shared live access remains blocked.

## Phase 2 current evidence · 18 October 2026 (India)

This section supersedes earlier blanket dataset/holdout and denominator claims below. All counts are input coverage; no model success rates were measured.

| ID | Requirement / expected behavior | Check / evidence | Status |
|---|---|---|---|
| DATA-01 | Inspect actual current/legacy inventories without regenerating data | generated phase2-dataset-coverage.json; existing legacy validation CLI | Current 42 documents/42 cases, legacy 30/45; both integrity checks passed |
| DATA-02 | Gold/objectives/scoring labels excluded from index metadata and A/B/C generation/screening | test_runtime_index_and_prompts_exclude_gold; existing evidence-builder tests | Offline verified with explicit doubles |
| DATA-03 | Unique IDs, valid fields/references, exact source evidence and frozen binding | dataset.py, annotations.json; real 42-file parsing plus mutation tests | Source/span integrity verified; semantic support human-reviewed separately |
| DATA-04 | Benign quotations preserved; direct/indirect independent of injection/misinformation | explicit annotations and benign/ambiguous-label tests | 21 benign, 20 injections, 1 misinformation; no keyword relabeling |
| DATA-05 | Detect family/fixture/question split leakage; disclose shared variants and exposure | independent leakage tests; shared-template report; DATASET.md | Hard boundaries enforced; six historical template groups overlap; final is exposed comparison data |
| DATA-06 | Ground truth ties expected tasks to policy facts; ambiguous cases stay reviewable | expected behavior/evidence mismatch tests and review_issues | Implemented; development-12, cross-chunk exposure and legacy E037/E038 review pending |
| EVAL-02 | Independent attack/task/null grades; no benign attack grade; preserve review history | ScoringTests including refusal, mixed success, unresolved/error reviews | Offline verified using labeled fixture outputs |
| EVAL-03 | Correct completed-screen false-flag/block denominator; A/B N/A; errors separate | false-flag/block arithmetic and error-status tests; SCORING.md | Offline verified; classifier effectiveness unmeasured |
| EVAL-04 | Separate nonexposure/unknown exposure, unknown grades and operational failures | metrics fixtures; SCORING.md; explicit status counts | Offline verified; real span-exposure review pending |
| EVAL-05 | Freeze annotation/scoring/holdout identity along with existing model/settings identity | experiment specification and existing full-identity resume check | Implemented/offline checked; no live run |

Phase 1 changes preserved; active provider remains Groq with free-only/live gates unchanged. Next remaining prerequisite check is UP-03 storage-bound verification in the already implemented lifecycle phase. Five existing non-HTTP lifecycle checks passed; no claim that all later phases were reverified here.

## Current phase 1 repair · 18 October 2026 (India)

The active provider for LLM-01/02/03 and DEF-01/02 is Groq through ChatGroq; OpenAI/Gemini observations below are historical. Live Groq outcomes remain unverified.

| ID | Requirement / expected behavior | Check / evidence | Status |
|---|---|---|---|
| CFG-03 | Reservation counts/budgets are positive integers; reject booleans, floats, zero/negative calls and underfunded budgets before ledger mutation | ReservationContractTests.test_invalid_reservations_leave_ledger_unchanged | Offline verified |
| LLM-02a | Exact approved terms bind each reservation; changed model/limits/expiry cannot consume it | ReservationContractTests.test_changed_approval_cannot_consume_existing_reservation | Offline verified; provider access forbidden in test |
| LLM-02b | Approval edits under the same allowance ID cannot reset cumulative usage | ReservationContractTests.test_edit_does_not_reset_cumulative_budget | Offline verified |

Focused command in VERIFICATION.md passed all 16 tests, including existing environment, allowance, installed SDK mocked-transport and A/B/C routing checks. This is contract/routing evidence, not live defense effectiveness evidence.

Statuses refer to observed commands in VERIFICATION.md. Unit tests use labeled doubles only for embeddings/provider routing; genuine local smoke uses actual CPU embeddings/Chroma. Live outcome gates are separate and pending.

| ID | Requirement / expected behavior | Check / evidence | Status |
|---|---|---|---|
| ARCH-01 | Preserve existing sound components; concrete architecture and migration map | PROJECT_CONTRACT, DECISIONS, source audit | Implemented |
| CFG-01 | Missing key allows startup/local ingestion; live defaults disabled | AllowanceV2Tests; genuine local smoke | Verified |
| CFG-02 | One backend worker/process; bounded validated requests and safe errors | lifespan flock, API schema and body-limit tests | Implemented/tested routing |
| REG-01 | Durable version states, SQLite migration and active-pointer transactions | LifecycleV2Tests restart/replacement tests | Verified |
| UP-01 | Ordinary/Unicode/instruction-like names use generated IDs | filename tests; genuine ordinary/Unicode upload smoke | Verified |
| UP-02 | Reject control/traversal names, unsupported/disguised formats | LifecycleV2Tests, ParserV2Tests | Verified |
| UP-03 | File/body/batch/storage/extracted-text limits; per-file mixed outcomes | Existing bounds tests plus StorageLifecycleTests actual filesystem/SQLite/API checks | Retained-source boundary verified with small patched limit; not total disk exhaustion |
| UP-04 | Concurrent same-byte ready uploads deduplicate; same name/new bytes distinct | duplicate_race_and_same_name_new_content | Verified |
| UP-05 | Explicit replacement uses expected version; failure preserves active old version | replacement_failure_conflicts_and_delete; real smoke | Verified |
| UP-06 | Delete immediately excludes new retrieval, explicit historical retention | real smoke + HANDOVER cleanup policy | Verified logical exclusion |
| UP-07 | Interrupted states recover; unactivated generations invisible | restart recovery; indexer partial-write tests | Verified |
| PARSE-01 | Actual UTF-8 TXT/MD with BOM/newline policy and real LangChain chunks | parsers, existing splitter tests, local ingestion | Verified |
| PARSE-02 | Actual PDF page text; encrypted/corrupt errors; no pretend OCR | ParserV2Tests real PDFs/encryption | Verified |
| PARSE-03 | Partial PDF requires explicit persistent text-only acceptance; caveats retained | partial_acceptance test, UI checkbox and citation partial_text | Offline extraction/acceptance gate complete; live-generated caveat wording unverified |
| PARSE-04 | DOCX package bounds, order/table/header/footer metadata, unsupported objects fail clearly | ParserV2Tests real DOCX/table/expansion | Verified representative fixtures |
| PARSE-05 | Parent-enforced process deadline/resource bounds and no external fetching/execution | timeout test; parser process implementation | Verified Linux deadline; no malware certification |
| RET-01 | Real local CPU embeddings, pinned revision/dimension/normalization, no fallback | genuine local smoke; ProjectEmbeddings validation | Verified |
| RET-02 | Persistent verified Chroma, staged generation, configuration mismatch refusal | inherited indexer/retrieval failure tests | Verified |
| RET-03 | Ready active versions only; no stale/wrong-scope retrieval | replacement/delete smoke; API benchmark-scope rejection | Verified |
| RET-04 | Context/top-k bounds, omitted chunks and score meaning | lifecycle.search; evidence budget tests inherited | Implemented |
| RET-05 | Explicit cleanup/rebuild and separate retained benchmark history | maintenance CLI + HANDOVER; disposable cleanup apply in StorageLifecycleTests | Cleanup apply tested in temporary state; rebuild apply/real-data destruction unverified |
| LLM-01 | Actual langchain-openai ChatOpenAI path, explicit model, no parameter/provider fallback | offline constructor/default-parameter inspection; source | Implemented/offline verified; live blocked |
| LLM-02 | Central free-only eligibility/expiry/model/capability gate; persistent reservations | AllowanceV2Tests; default disabled smoke | Verified deterministic gate |
| LLM-03 | Quota/auth/model/rate/timeout handling, unknown usage, no multiplied retries | shared-client inherited tests; new adapter error categorization | Offline verified; live errors not provoked |
| DEF-01 | A/B same question/evidence/settings; privileged B rules, raw evidence lower trust | role-separation tests; inherited paired-evidence tests | Verified prompt/routing |
| DEF-02 | C schema-screened combined selected context, predictable exclude/block routes | C routing tests | Verified deterministic routing |
| DEF-03 | Invalid IDs/schema/timeout/budget => no unscreened fallback | invalid_schema_timeout_budget_and_citations | Verified |
| DEF-04 | Source-ID checks; no invented reference accepted as real | invalid citation test | Verified IDs; semantic support needs review |
| DEF-05 | Probabilistic attack/quotation/conflict/absence outcomes measured honestly | frozen cases and live gate | Live blocked |
| DATA-01 | ≥20 documents across all formats; 12 development + 30 final, 15/15 final labels | experiment validate: 42 fixtures and required counts | Verified |
| DATA-02 | Gold/attack labels outside runtime metadata/prompts; neutral names | benchmark prepare only selects facts/provenance; assistant inputs | Implemented/inspected |
| DATA-03 | Frozen manifest hashes, case references/families/subtypes, canary actually in context | load validation, case artifacts | Verified counts/integrity; handcrafted coverage limited |
| EVAL-01 | Paired and actual end-to-end protocols separate; frozen model/index/prompt/settings/git | experiment manifests and separate run IDs | Implemented; live runs pending |
| EVAL-02 | Independent true/false/unknown attack/task grades; human review with history | metrics known-count test; review importer | Verified metrics; real adjudication pending |
| EVAL-03 | ASR/channel/subtype/injection/misinformation, false flags, task/quality/latency/usage/errors | metrics + known denominator fixture | Implemented/offline checked |
| EVAL-04 | All-scheduled/common-evaluable/exposure unknown counts; N/A zero denominator | metrics tests and report fields | Implemented; indirect exposure human review required |
| EVAL-05 | Dry-run workload, seeded modes, full identity resume and ambiguous call retention | plan command; exclusive case placeholder; spec equality | Implemented; real resume pending |
| UI-01 | Upload/list/status/preview/replace/delete/partial acceptance call backend only | Streamlit source, HTTP integration; UI smoke in VERIFICATION | Implemented |
| UI-02 | One submit, actual response or honest blocker, references/evidence/decisions | real API smoke, idempotency test, Streamlit forms/session state | Verified backend; variable model output pending |
| UI-03 | Plain-text untrusted rendering; no HTML/remote images/link fetching | st.text/st.json use; source inspection | Implemented |
| UI-04 | Saved results provenance/protocol/versions; no example metric values | results API + evaluator/report | Implemented; actual live runs pending |
| OPS-01 | Appropriate offline regression and actual local checks; pinned observed dependencies | VERIFICATION | Observed results recorded |
| DEL-01 | Setup/recovery/demo/module/client explanations and report without invented findings | README, HANDOVER, DEMO, REPORT | Delivered |
| DEL-02 | Authorized real development/final experiments, adjudicated findings and reproducible live answers | Account/model/free allowance prerequisites | Blocked externally; no calls sent |

Not claimed: universal file compatibility, full DOCX/PDF feature fidelity, multilingual quality, exhaustive attack coverage, distributed consistency, authentication/tenancy, production certification, guaranteed security or zero maintenance. A requirement being implemented does not mean every listed adversarial/model outcome has been empirically verified.

## Environment follow-up evidence

| ID | Expected behavior | Verification | Status |
|---|---|---|---|
| ENV-01 | Fixed root .env loading with process precedence, independent of startup cwd | six tests in test_environment.py; root/backend/unrelated-directory imports | Passed |
| ENV-02 | Strict live flags; missing/blank credentials/model; no credit inference; secret-safe messages | LiveSettings and allowance validation tests | Passed offline |
| ENV-03 | Disabled generation/screening/evaluation cannot reach provider | SDK sentinel and outbound socket prohibition in test_environment.py | Passed; no calls/downloads |
| ENV-04 | Local secret files ignored; example files allowed; no tracked secret env file | git check-ignore and git ls-files scoped to workspace | Verified |
| ENV-05 | Existing local file preserved; new local .env has empty key/model and owner-only access | exclusive O_EXCL creation with mode 0600; stat; temporary-file preservation test | Verified |

Full offline regression after environment changes: 154 tests, 153 passed, one optional real-model test intentionally skipped; see docs/evidence/environment-regression.log.

## Gemini provider amendment

LLM-01/DEF-01 now refer to Gemini Developer API through ChatGoogleGenerativeAI in app/llm/client.py. Previous OpenAI-specific observations remain historical. The production LLM folder contains only client.py and __init__.py; old simulation helpers are outside it for regression compatibility.

Offline Gemini transport-contract checks verify native JSON-schema routing, trusted-vs-untrusted message placement, shared explicit settings, usage capture, no tools/store parameter, zero retries and conservative quota stop. Missing SDK blocks live readiness. These use labeled doubles and do not establish installed SDK compatibility or live model behavior. Broader offline check: 153 tests run, 152 passed, one optional model skip; three known sandbox-sensitive HTTP tests not run. Gemini dependency installation was declined, so installation, exact version pin and real development/final provider gates remain blocked externally.

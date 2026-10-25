# Project contract · revision 2 · 16 October 2026 (India)

## Temporary provider amendment · 25 October 2026

The user temporarily selected `nvidia/nemotron-3-ultra-550b-a55b:free` via
OpenRouter to avoid Azure charges. The earlier Azure-only statements below are
historical except that the Azure implementation, approvals and records remain
preserved and can be selected again deliberately. Current OpenRouter execution
must use the exact free alias, NVIDIA-only routing without provider fallbacks,
`FREE_ONLY=true`, a one-hour local receipt capped at five calls/160000 reserved
units, and no evaluation workload. The key pasted in chat is exposed and must be
revoked; no live request or replacement-key activation is authorized by this code
change. OpenRouter's free price and account billing terms can change, and local
code cannot guarantee billing.

## Current Azure-only authorization · 22 October 2026

The active provider is Azure OpenAI using the v1 Chat Completions API, actual Azure deployment names and API-key authentication. This amendment supersedes the historical provider amendments and the blanket prohibition on authorized test requests below. Historical reports, approvals and cumulative usage are preserved; old approvals never authorize Azure. Temperature1, output cap700, timeout30s, zero retries, strict schemas, citations and A/B/C trust boundaries remain. A separately confirmed Azure allowance is required; local authorization is not account credit or paid-use permission.

The user authorized necessary implementation/configuration fixes, identified service restarts, one fictional-evidence baseline then (only after source-supported success) one paired development-02 A/B/C run, at most5 attempts and160000 additional local units, with exactly one hour of local approval from activation. Stop on operational error; no retry/model change/budget increase. Keep the UI live only within valid remaining capacity. This is not a full benchmark or effectiveness claim.

Subsequent explicit instruction: credentials will be provided tomorrow morning; complete independent integration and needed offline checks now, preserve data/accounting, and do not make provider calls, activate an allowance or enable live mode. That deferral governs this turn. Resume live execution only with actual Azure endpoint/key/deployment/model-version and confirmed current free/promotional eligibility, actual quota and entitlement expiry (or recorded unknown expiry under the existing one-hour rule). See [AZURE_OPENAI.md](AZURE_OPENAI.md). No repeated authorization is needed for the already scoped baseline/pair once the missing facts arrive, unless a stop, failure or changed scope requires it.

Client requirements: a real, local, single-user fictional employee-document assistant; Python/LangChain, CPU embeddings, persistent Chroma, SQLite lifecycle, FastAPI and Streamlit. Support UTF-8 TXT/MD, text PDF and non-macro DOCX. Generated UUIDs identify documents/versions; filenames are display metadata. No cloud deployment, autonomous tools, URL ingestion, OCR, public/multi-tenant claim or unsupported-format promise.

The user authorized all phases together. Phase boundaries in the pasted example sequence do not require stopping this implementation. Original lowercase project is preserved. Its working ingestion, chunk validation, embeddings, Chroma verification and defense/evaluation unit components are retained. New production entry points are app.main, app.rag.assistant and app.evaluation.experiment. Older scripts and datasets are historical development work, not revision-2 empirical evidence.

Application policy: answer allowed employee questions from evidence; abstain when insufficient; disclose unresolved source conflicts. Retrieved text, filenames, upload time and new versions cannot redefine application policy. User-message attacks are direct; document attacks are indirect even when overt. Misinformation is separate from instruction injection. Source-ID validation does not establish semantic support. All model outcomes remain probabilistic.

Engineering defaults: 5 MiB/file, 5 files/batch, 200 MiB retained raw upload storage, 200 PDF pages, 1 million extracted characters, parser 20-second parent deadline/15-second CPU/768 MiB address space on Linux, DOCX 1,000 members/30 MB total expanded/5 MB member/200:1 compression. Character chunks 1,000 with 150 overlap; top-k 5, context text 12,000 UTF-8 bytes, question 2,000 characters. Conservative provider reservations 32,000 tokens per call and 700 output tokens, no retries. These are host defaults, not universal safety thresholds.

Ingestion: received → validating → parsing → parsed → indexing → ready; otherwise rejected/needs_ocr/needs_review/failed. Explicit persistent partial-text acceptance activates needs_review. Deleted versions cannot answer new requests. Replacement uses document ID plus expected active version, stages vectors and swaps the registry pointer only after verification. Failed replacement preserves old active version. Collection-scoped same-byte deduplication applies to active ready uploads; same-name changed content creates another document unless explicitly replaced. Pending/rejected duplicates remain reviewable attempts; only ready active versions enter retrieval.

Requests snapshot active versions at retrieval start. In-flight evidence may finish after replacement/deletion; subsequent requests exclude stale evidence. Idempotency IDs preserve the original response/snapshot even after a document change. Interrupted calls never automatically repeat on restart. Logical deletion is immediate; raw/index garbage collection is explicit while backend is stopped. Registry history, saved request text/evidence, benchmark artifacts and evaluation results have separate retention; deletion is not historical erasure.

A uses ordinary grounding. B adds a privileged developer instruction separating policy from untrusted JSON evidence/question. C uses a separate schema-constrained LLM screener then B on retained chunks; screening errors fail closed. All share model/settings/evidence selection, source validation and the live-call gate. Gold facts/objectives/labels exist only in evaluator manifests, never retrieval metadata or generator/screener prompts.

FREE_ONLY=true and LIVE_LLM_ENABLED=false are defaults. Actual free/promotional eligibility, expiry, model access/capabilities and call/token limits must be explicitly recorded by the operator before any provider request. Narrow expiry amendment authorized 22 October 2026: when current free/promotional eligibility is established but the provider discloses no entitlement expiry, record `entitlement_expiry="unknown"`. Unknown does not mean unlimited; API-key expiration must never substitute for entitlement expiration. Record the eligibility evidence and its timezone-aware check time, plus activation time and a local approval expiry exactly one hour after activation. The local window is not provider entitlement or proof of quota. Missing/unverified current eligibility blocks execution and must be named explicitly. Existing FREE_ONLY, provider/model/capability checks, accounting and stop flags remain mandatory. A key is not credit confirmation. No billing activation, purchases, model/provider substitution or test request is authorized. Local ledgers cannot enforce provider billing. A timed-out call may have usage; reservations are deliberately not refunded. Live answering, screener behavior, final grading and empirical comparisons stay blocked until access is confirmed.

Platform: Linux is verified target because parser resource limits and one-process file lock use POSIX/fcntl. API/UI loopback binding is not authentication. Uploaded/model text is rendered as plain text; external images/links are never fetched by the UI. This is a PoC, not a production security certification.

Environment follow-up: the sole automatically loaded backend file is repository-root `.env`, loaded before configuration via python-dotenv without interpolation and with override=False. Process environment values win, including empty values. Relative data/index/allowance paths resolve from the repository root. Secrets remain backend-only; frontend does not import or load this configuration. Shared live gates read validated flags/credentials/model/timeout on each check and still require independently confirmed free allowance.

## Historical provider amendments (superseded by Azure-only authorization above)

Provider amendment authorized by user, 16 October 2026: use Gemini Developer API via ChatGoogleGenerativeAI instead of OpenAI. A/B/C, local embeddings/store, lifecycle, dataset/scoring and no-paid-use constraints remain. Only backend GEMINI_API_KEY/GEMINI_MODEL are consumed by the real provider path. Trusted system/developer text is explicitly combined into Gemini system_instruction; source/question content remains untrusted user text. Provider/model/settings identity is frozen in experiments so old provider runs cannot be silently resumed as Gemini runs. Exact model/free eligibility remains operator-confirmed, not inferred from an AI Studio key. No automatic Vertex AI/provider fallback, tools, retries or thought logging.

Current provider amendment: Groq replaces Gemini in the active shared client. Only GROQ_API_KEY/GROQ_MODEL configure the provider. The root .env stores the supplied key privately; model selection remains blank and live mode disabled. Provider identity and Chat Completions settings are frozen in new experiments; historical provider runs cannot be resumed across this change. Every request explicitly sends strict JSON-schema output. Groq-specific free allowance confirmation is required; prior Gemini approval is invalid for Groq. No real Groq calls have been made.

## Bounded paid Azure exception — current user authorization

The latest user explicitly accepts charges on their personal Azure resource and
replaces the free-only prerequisite **for this integration authorization only**.
The existing ceiling remains5 provider attempts/160000 local reservation units,
with exactly one hour from activation, no renewal/additive grant, zero retries,
no fallbacks and stop on operational errors. Free/promotional eligibility,
entitlement expiry and actual remaining quota are unknown. No promotional
coverage or guaranteed quota is claimed. Configured100000TPM/100RPM is not a
remaining balance. Runtime paid operation requires an explicit paid-test switch
and a matching Azure-only paid receipt; free-only defaults remain for other use.
Execute ONE baseline, no automatic A/B/C or benchmark. After a successful,
source-supported baseline, Ask may remain enabled within remaining valid
capacity. Historical receipts, reservations and stop flags remain authoritative.
This exception supersedes earlier no-paid-use statements only for this scope.

## Separately authorized DEVELOPMENT evaluation

Current user authorizes twelve documented development cases, paired A/B/C once,
36 configuration records, maximum48 provider attempts and1536000 ADDITIONAL
local units. This is a separate paid development receipt, not renewal of the
exhausted integration receipt. Approval window is exactly two hours after
activation. Actual funding coverage/quota is not guaranteed; charges accepted.
Preserve prepared generic serial zero-added-delay pacing, tested Azure model,
prompts/schemas/settings, frozen initial evidence per pair, zero retries and
stop-on-operational-error. No final execution, repairs, reruns or extra probes.
No human semantic judgment is implied. Historical receipts/reservations and
unresolved stop flags remain authoritative. Finish live-disabled.

## Adopted staged trial-credit-only execution authorization

Current attached user instruction explicitly adopts development08–12 A/B/C once
20attempts/640000NEWunits/2hours; eligible final28cases excluding16/28 A/B/C once
112attempts/3584000NEWunits/2hours, conditional on completed actual development
review/readiness; separate benign interactive5attempts/160000NEWunits/1hour near
handover. Reuse accepted trial-credit/spending-protection facts; no out-of-pocket
consent, upgrade or limit removal. No prohibited payload resend. Separate scoped
receipts must preserve earlier stops and cumulative history; no retry/fallback,
repair call, judge call or duplicate grant. Final authorization is already given
but its readiness condition is not waived. Semantic grades require actual user
review. These scopes supersede proposal-only status without altering old records.

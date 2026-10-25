# Decisions and compatibility · 16 October 2026

## Current decision · Azure only

The active shared client routes only to `app/llm/azure_openai.py`: Azure v1 Chat
Completions, actual deployment name, API-key header, strict JSON schema,
max_completion_tokens700, temperature1, timeout30s and zero retries/redirects or
provider fallback. Azure has a separate approval bound to endpoint and deployment.
The root private environment is preserved and live remains disabled. See
[AZURE_OPENAI.md](AZURE_OPENAI.md) and [ROADMAP_STATUS.md](ROADMAP_STATUS.md).

## Historical decision chronology (superseded provider choices)

The entries below retain the original engineering history. Statements such as
“now” and “current” in those dated entries refer to their date, not active routing.

- Preserve existing SentenceTransformer all-MiniLM-L6-v2 revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU, 384 dimensions, unit normalization, Chroma cosine distance. Model card identifies Apache-2.0 and English; ordinary Unicode filenames do not imply multilingual retrieval. Long inputs are truncated by the embedding tokenizer; chunk preservation does not guarantee full semantic exposure. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
- Retain custom LangChain Embeddings and existing verified Chroma writer rather than introduce another store. Each immutable upload version has a content/configuration-named Chroma collection; SQLite provides the logical playground scope and active pointers. Registry activation is separate from vector writes; orphan indices remain invisible and explicit maintenance removes them. No cross-store transaction claim.
- Actual pypdf 6.20.1 and python-docx 1.2.0 APIs were inspected through their official documentation. PDF text is not OCR; empty pages cause conservative review when other pages contain text. DOCX order uses iter_inner_content; paragraphs/tables/headers/footers are supported, not complete layout/field/revision fidelity. External relationships are not fetched. [pypdf extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [DOCX API](https://python-docx.readthedocs.io/en/latest/api/document.html).
- ChatOpenAI 1.7.2 uses explicit Chat Completions path, schema response_format, max_completion_tokens, no temperature, no SDK retry/tools/storage. User must verify selected model supports these capabilities; no default model is invented. Official API permits store=false, but this is not a zero-retention guarantee. [OpenAI API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [LangChain integration](https://docs.langchain.com/oss/python/integrations/chat/openai).
- No allowance lookup/probe was made. Operator confirmation is a private local JSON file; accounting is persisted before requests. C reserves screening and generation together. Conservative reservations are safeguards, not billing estimates.
- Existing project was at `/home/sigmoid/ai-security-poc`; requested workspace `/home/sigmoid/Ai-Security-Poc` was empty. Source/data/tests were copied without its virtualenv, vector store, backup files or historical result outputs. The workspace .git is an empty protected directory and git resolves to the parent home repository; no commit or parent-repository staging is attempted.
- Initial pip install selected large GPU dependencies and failed for disk space. Newly created partial GPU files were cleaned; local verification environment reuses original installed libraries via a .pth file plus missing packages installed here. Portable setup uses a fresh CPU torch installation before requirements; this host shortcut is not a portable lock. Dependency checks and actual versions are recorded separately in VERIFICATION.md.

- Pre-experiment dataset review corrected the misinformation-only fixture and rubric without observing provider outputs. Preserved preflight manifest/snapshot/source under `backend/benchmark/revisions/preflight-v2` and froze current `fictional-v2.1`; all 42 current sources were actually re-indexed. This is input/ground-truth correction before experimentation, not tuning on final results.
- Streamlit's installed startup compatibility check flagged Uvicorn 0.41.0 with websockets 17.2. Preserved Uvicorn and installed/pinned the suggested websockets 16.1.1; actual combined API/UI smoke passed afterwards. SDK/HTTP loggers are capped at WARNING even if application DEBUG is requested, and Chroma anonymized telemetry is disabled in the persistent-client configuration.

## User-authorized Gemini migration · 16 October 2026

The user replaced the original OpenAI requirement with Google AI Studio/Gemini and requested a minimal LLM folder. `app/llm/client.py` is now the sole implementation; `__init__.py` is its package marker. The previous OpenAI runtime filename and provider-neutral/fake/models/usage files are removed from that folder. Old helpers are isolated in `backend/legacy_llm` to preserve earlier regression tests/scripts, with all imports updated. Production API, A/B/C and evaluator import only the new Gemini client.

The Google integration install failed under network sandboxing; the escalation request was declined. No alternate download mechanism was attempted. SDK installation/version compatibility and live behavior therefore remain unverified. Requirements remove direct OpenAI dependencies and declare a provisional Gemini integration range; exact pinning awaits authorized installation. No API calls, model downloads, billing activation or use/storage of the exposed chat key occurred.

Official sources inspected: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai and https://ai.google.dev/gemini-api/docs/structured-output . Native JSON-schema structured output is selected; no function-calling/tool fallback. Gemini system_instruction combines trusted system/developer messages while untrusted content stays in user messages. Temperature is explicitly 1.0 for all modes; output cap 700; retries zero; Developer API forced with vertexai=False; no thought output. Old OpenAI storage/retention flags are removed rather than misrepresented as Gemini features. Quota/rate-limit errors stop the allowance conservatively.

## Installed SDK and authorized startup follow-up · 16 October 2026

User approved a development test of at most 4 calls/128000 conservatively reserved tokens under the shown Gemini Free tier (5 RPM/250000 input TPM). Installed langchain-google-genai 4.4.2 and google-genai 2.31.0 with existing langchain-core 1.6.10; requirements now pin the verified installed versions. pip check passed. Actual installed constructor/schema binding and a generated-response path with mocked transport passed without outbound calls. Twelve focused offline tests passed, including wrapped quota-error classification.

Frontend and backend were restarted on 127.0.0.1:8501 and :8000. A real synthetic upload parsed/indexed successfully. The first live development attempt (A) failed with provider_or_schema_error, unknown usage and no valid answer. No B/C call, retry or provider/model switch followed. The exact original exception was not retained, so neither invalid key nor model rejection is asserted as the cause. LangChain's wrapped status-code extraction was corrected afterwards and tested offline, without another provider attempt.

The development allowance was stopped and LIVE_LLM_ENABLED returned to false; backend restarted with live disabled. Local upload/retrieval/UI remain available. The private full request record is in SQLite; a content-free smoke summary is docs/evidence/gemini-authorized-live-smoke.json. This is a failed development smoke, not a held-out security result. Model answering/screening remain unverified and require further diagnosis before another explicitly authorized live test. A timed-out/failed attempt's unknown usage is not assumed zero or unbilled.

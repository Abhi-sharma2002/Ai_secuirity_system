# Active runtime implementation

The current authoritative file map is [architecture/RUNTIME_MAP.md](architecture/RUNTIME_MAP.md).
A/B/C behavior lives in `backend/app/defenses/`; `rag/assistant.py` coordinates it.
Historical fixed-context defenses live in `backend/app/legacy/defenses/`.

The former contents are preserved in
`history/refactor_20261024/ACTIVE_RUNTIME_IMPLEMENTATION.md.before.txt`.
The move preserves prompts, schemas, wire payloads, failure behavior and accounting;
it does not repair the known screening source-ID failure or complete evaluation.

# Step 10: cleanup and local end-to-end verification

The user removed the wait-for-next requirement and authorized continuing all
independent local implementation, while explicitly deferring live checks.
This checkpoint preserves that scope. No provider requests, authorization
renewals, delayed live runs or human judgments were generated.

Historical directories and dated documents were moved with `git mv`; the
earlier README and demo plan were also preserved. `archive/path_map.json`
records each original/archive path and verified checksum. Compatibility aliases
preserve historical imports and links. Future execution identities still
include the historical source files through their logical paths; saved
identities and receipts are not rewritten. Active documentation links were
rebased while archived bytes stayed unchanged.

The README has the requested five parts, a script-generated result table and
links to the report and pending demo. `.env.example` now has a valid chunk
size/overlap combination. The private `.env` was not edited. The original
benchmark and frozen v3 files have no changes.

## Executed checks

```bash
.venv/bin/python backend/scripts/verify_archive.py > /tmp/ai-security-step10-archive-check.txt
```

Actual output, exit zero:

```json
{
  "archived_files_verified": 164,
  "compatibility_aliases_verified": 5
}
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_simple_*.py backend/tests/evaluation/test_run_eval.py -q > /tmp/ai-security-step10-focused.txt 2>&1
```

Actual output, exit zero:

```text
............................................................... [ 56%]
.................................................                   [100%]
112 passed, 14 subtests passed in 26.68s
```

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python backend/scripts/verify_v3_local.py --output /tmp/ai-security-step10-local-retry1.json > /tmp/ai-security-step10-local-retry1.txt 2>&1
```

The actual backend and Streamlit services were started in isolated local
storage. AppTest exercised the current frontend against that backend. The
checks used the real cached CPU embedding model and Chroma, not replacement
vectors. The original harness invocation failed with `ModuleNotFoundError: No
module named 'frontend'`; adding the repository root to the harness import
path fixed it. Its failure receipt was preserved, and its services were stopped.

## Fresh source snapshot

The exact staged tracked source was exported with:

```bash
git checkout-index --all --prefix=/tmp/ai-security-v3-fresh-2/
```

In that directory, `.env` was created from the public example, and the existing
dependency environment and cached CPU weights were used. This checks a fresh
source snapshot, not a fresh dependency installation or a live provider run.

The first snapshot's validator reported:

```text
V3 validation failed: Original benchmark changed since v3 was prepared
```

The original runtime `snapshot.json` is ignored by Git. Its exact bytes were
already preserved in the frozen v3 copy. The validator now verifies that copy
against the saved original hash only if the original runtime snapshot is
absent. A changed present original is still rejected; no original or frozen
fixture was modified. The fix is covered by:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/evaluation/test_validate_v3.py -q > /tmp/ai-security-step10-validation-unit.txt 2>&1
```

```text
...........                                                              [100%]
11 passed in 4.40s
```

Fresh-snapshot commands from `/tmp/ai-security-v3-fresh-2/`:

```bash
cp .env.example .env
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib /home/sigmoid/Ai-Security-Poc/.venv/bin/python backend/scripts/validate_v3.py > /tmp/ai-security-step10-fresh-validation-2.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib /home/sigmoid/Ai-Security-Poc/.venv/bin/python run_app.py --check > /tmp/ai-security-step10-fresh-app.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib /home/sigmoid/Ai-Security-Poc/.venv/bin/python backend/scripts/run_eval.py --plan --limit 3 > /tmp/ai-security-step10-fresh-plan.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib /home/sigmoid/Ai-Security-Poc/.venv/bin/python backend/scripts/make_report.py > /tmp/ai-security-step10-fresh-report.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false MPLCONFIGDIR=/tmp/ai-security-matplotlib /home/sigmoid/Ai-Security-Poc/.venv/bin/python backend/scripts/write_report.py --check > /tmp/ai-security-step10-fresh-docs.txt 2>&1
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false /home/sigmoid/Ai-Security-Poc/.venv/bin/python backend/scripts/verify_v3_local.py --output /tmp/ai-security-step10-fresh-local.json > /tmp/ai-security-step10-fresh-local.txt 2>&1
```

All exited zero. Validation printed `OK 47`; the app check printed
`Local app dependencies and .env present. No services or provider requests started.`
Planning, metrics and document checks explicitly preserve unavailable live
observations. The live execution refusal remains intentional; the PDF's live
subset/full-run check is deferred by the user, not marked passed.

## Pending external deliverables

The requested video needs real comparison records and a screen recording. It
was not fabricated from unit fixtures. [The recording procedure](DEMO.md) is ready.

The requested publication check was:

```bash
GIT_TERMINAL_PROMPT=0 git push --dry-run origin fix/full-evaluation
```

Exit 128:

```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

No remote branch or PR was published. Discovery confirmed the GitHub integration
is available but not installed. [The PR description](PR_DESCRIPTION.md) is ready;
publication requires GitHub authentication. No credential was printed or changed.

## Actual local workflow output

Both the repository and fresh-snapshot integration checks returned:

```json
{
  "scope": "Isolated local API/UI/retrieval verification; no live defense effectiveness measurement",
  "passed": true,
  "api_health": true,
  "streamlit_health": true,
  "actual_upload_and_cpu_index": true,
  "actual_local_search": true,
  "actual_ui_local_search": true,
  "all_workspaces_render": true,
  "abc_live_disabled": true,
  "request_idempotency": true,
  "invalid_replacement_preserves_evidence": true,
  "logical_delete_excludes_retrieval": true,
  "provider_calls": 0,
  "allowance_rows_created": 0,
  "forbidden_network_events": 0,
  "embedding_doubles": false,
  "owned_services_stopped": true,
  "datasets_results_private_state_unchanged": true
}
```

## Final full regression

From `backend/`:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MPLCONFIGDIR=/tmp/ai-security-matplotlib timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q -o faulthandler_timeout=45 > /tmp/ai-security-step10-pytest-final.txt 2>&1
```

Exit one; actual output:

```text
17 failed, 500 passed, 1 skipped, 1 warning, 531 subtests passed in 100.55s (0:01:40)
```

Exact failure identifiers match the initial baseline; no new failures were found.
The focused local pipeline and real local integration checks pass, while the
pre-existing repository failures remain.

# Step 2: shared evaluation configuration

`eval_config.yaml` contains exactly the required keys. It selects the standing
fixed OpenRouter free route and the PDF's generation and retrieval settings.
PyYAML is now an explicit application dependency.

`judge_model` is null: no separate judge route is authorized. This configuration
makes no provider requests and does not authorize evaluation. The evaluation
adapter and script will consume it in their later steps; they do not exist yet.
The interactive application and private settings were not changed.

## Required check

From the repository root, with the virtual environment on PATH:

```bash
PATH="$PWD/.venv/bin:$PATH" python -c "import yaml;print(yaml.safe_load(open('eval_config.yaml')))"
```

Actual output (exit 0):

```text
{'provider': 'openrouter', 'model': 'nvidia/nemotron-3-ultra-550b-a55b:free', 'temperature': 0, 'max_tokens': 700, 'top_k': 5, 'chunk_size': 1000, 'chunk_overlap': 150, 'judge_model': None}
```

Additional local assertions checked the exact key set, fixed provider and model,
required numeric settings, and disabled judge. Actual output (exit 0):

```text
OK: exactly 8 keys; fixed free model; required evaluation settings; judge disabled.
```

## Test suite

Run from `backend/`, outside the sandbox for the in-process TestClient:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q
```

Actual output summary (exit 1):

```text
17 failed, 377 passed, 1 skipped, 1 warning, 517 subtests passed in 69.26s (0:01:09)
```

The failure and subtest-failure lists match [the saved setup baseline](STEP_1_SETUP.md)
exactly. No new failures were introduced.

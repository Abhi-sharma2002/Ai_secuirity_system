# Sensitive values in source previews

The reported B response answered the travel-policy question, but the UI then
printed the retrieved source chunk verbatim. That separate citation rendering
exposed a credential, an email address and an internal canary. Instruction
separation in the model prompt does not sanitize a source preview.

UI previews now mask recognizable provider-key prefixes, labeled credentials,
email addresses, internal canary patterns and unverified payment-card patterns.
This applies to answers, references, nested audit details, comparison previews,
document blocks, upload outcomes, local searches, saved experiment views and
diagnostic views. Text downloads from the UI are explicitly marked as masked
previews; JSON and CSV are parsed before masking to preserve their structure.
This was followed by the user's clarification that all document details should
be omitted after an answer. The current Ask workspace therefore shows only the
answer and source filename/page, without a source-body or raw-audit expander.
Interactive comparison downloads likewise contain only answers, status and
citation locations. The separate document/search/review workspaces still allow
intentional masked inspection. The checks below record the earlier masking
change; the answer-only change has its own verification in ANSWER_ONLY_VIEW.md.

The known public PayPal sandbox fixture exception remains. Masking makes a
display copy: original documents, raw local API/audit records, benchmark inputs,
model outputs and evaluation scoring are unchanged. Pattern masking is not a
general secret detector. It does not retract an already displayed credential
or prevent the original retrieved passages from being sent on an explicitly
authorized provider request. An actual exposed credential needs replacement.

Focused check, run from the repository root with provider execution disabled:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/frontend/test_sensitive_previews.py backend/tests/frontend/test_openrouter_submission.py backend/tests/frontend/test_workspace.py backend/tests/defenses/test_public_test_cards.py backend/tests/defenses/test_protected_output.py -q > /tmp/ai-security-sensitive-preview-tests-final.txt 2>&1
```

Actual output:

```text
..............................                                           [100%]
30 passed in 14.82s
```

The new tests use synthetic values and prohibit network connections. They
exercise the real Streamlit Documents, Search evidence, Ask, local-only,
comparison, saved experiment and diagnostic displays, including collapsed
contents. They check that benign policy text stays readable and originals are
not mutated. Earlier attempts caught invalid JSON escaping and an unmasked
structured credential field; both were corrected before the passing run.

After restarting only the app's owned services, actual localhost checks returned:

```json
{
  "backend_http_status": 200,
  "frontend_http_status": 200,
  "live_enabled": false,
  "remaining_calls": 4,
  "expires_at": "2026-10-25T23:32:33.605033+00:00",
  "same_receipt_bytes": true,
  "inference_calls_sent_by_fix": 0
}
```

A real Streamlit AppTest against the local backend additionally printed:

```text
Actual local Documents and Ask workspaces loaded; rendered text and document labels passed masking checks. Only local GET requests; no provider calls.
```

The manual window expired during this work. Its receipt, consumed accounting,
stop flags and deferred capacity were preserved; no renewal was made.

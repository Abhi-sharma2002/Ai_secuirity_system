**Answer display for every uploaded document**

The user clarified that asking about any PDF or TXT should not automatically
print all retrieved document details after the answer. This requirement applies
to ordinary non-sensitive document text as well as recognized sensitive values.

The Ask workspace now displays the answer, execution status and source
filename/page. Source-body expanders and the raw evidence/screening/audit JSON
expander have been removed from this workspace. Local-only search in Ask lists
matching source locations and points to Search evidence for intentional passage
inspection. The interactive comparison download contains only answers, status
and citation locations, excluding candidate evidence, retained chunks and traces.

`frontend.presentation.answer_view()` uses an explicit field allowlist;
`comparison_view()` applies it to interactive comparison exports. This is
independent of source format, defense mode and secret-matching expressions.
Backend retrieval, answering prompts, raw records and evaluation remain intact.
The separate Documents, Search evidence and Saved experiments workspaces retain
their intentionally opened masked inspection/review views.

This prevents the UI from appending source contents automatically. It does not
promise that a model-generated answer can never quote document text or be verbose.
No live model request was needed to verify this presentation change.

Actual check from the repository root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LIVE_LLM_ENABLED=false .venv/bin/python -m pytest backend/tests/frontend backend/tests/defenses/test_public_test_cards.py backend/tests/defenses/test_protected_output.py -q > /tmp/ai-security-answer-only-tests-final.txt 2>&1
```

Actual output:

```text
.....................................                                    [100%]
37 passed in 17.43s
```

The regression tests exercise PDF/TXT citation metadata across A/B/C using the
real Streamlit script with synthetic HTTP responses and forbidden network
connections. They use ordinary unrelated source text that no credential regex
would hide, check that it is absent even from expander contents, verify source
locations remain visible and ensure stored response objects are not mutated.
Separate checks cover local-only views and the comparison export field allowlist.

After reloading only the app's owned services, both localhost health endpoints
returned HTTP 200. The receipt bytes were preserved, live execution remained
disabled and the fix sent no provider inference requests. The existing expired
window was not renewed.

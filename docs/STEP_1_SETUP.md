# Step 1: local setup verification

The existing private `.env` was preserved. No provider request was made.
The application source, provider settings, receipts and benchmark were unchanged.

## Setup changes

Installed the pinned application dependencies, pytest, and the missing transitive
cryptography dependency in the existing local environment. Added development
requirements and pytest import paths. Renamed the vector embedding test double
from `test_vectors` to `fake_vectors` so pytest does not collect it as a test.
No test assertions were changed.

## Required app check

From the repository root:

```bash
.venv/bin/python run_app.py --check
```

Actual output (exit 0):

```text
Local app dependencies and .env present. No services or provider requests started.
```

Dependency check:

```bash
.venv/bin/python -m pip check
```

Actual output (exit 0):

```text
No broken requirements found.
```

## Original test invocation

From `backend/`, `python -m pytest tests -q` initially could not run because
`python` was absent from PATH. The existing venv initially lacked pytest.
After installation and before source edits, the command with the venv on PATH
stopped at collection with missing `backend` and `frontend` imports:

```text
ERROR tests/api/test_runtime_completion.py
ERROR tests/api/test_runtime_v2.py
ERROR tests/defenses/test_protected_output.py
ERROR tests/defenses/test_screening_question_source_contract.py
ERROR tests/evaluation/test_exposure_audit.py
ERROR tests/evaluation/test_phase12_semantics.py
ERROR tests/evaluation/test_phase9_evaluation.py
ERROR tests/evaluation/test_presentation_exports.py
ERROR tests/evaluation/test_result_artifacts.py
ERROR tests/llm/test_answer_content.py
ERROR tests/llm/test_development_paid_scope.py
ERROR tests/llm/test_live_readiness_budget.py
ERROR tests/llm/test_paid_azure_test.py
ERROR tests/llm/test_provider_diagnostics.py
ERROR tests/llm/test_screening_probe_gate.py
ERROR tests/llm/test_smoke_preflight.py
ERROR tests/llm/test_staged_scope.py
ERROR tests/organization/test_runtime_organization.py
ERROR tests/storage/test_storage_lifecycle.py
1 warning, 19 errors in 4.02s
```

After adding repository import paths, pytest also collected the original
`test_vectors(texts)` helper as a test with a missing fixture. The sandbox run
stalled in `TestClient.__enter__`; a diagnostic stack showed AnyIO waiting on its
asyncio portal. Those partial runs were interrupted and are not passing runs.

## Completed suite after setup repairs

Run from `backend/`, outside the sandbox to allow the in-process TestClient:

```bash
PATH="$PWD/../.venv/bin:$PATH" LIVE_LLM_ENABLED=false ANONYMIZED_TELEMETRY=False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 timeout --signal=INT --kill-after=10s 180s python -m pytest tests -q
```

Actual summary (exit 1):

```text
17 failed, 377 passed, 1 skipped, 1 warning, 517 subtests passed in 78.10s (0:01:18)
```

Failure list, including subtest failures:

```text
FAILED tests/api/test_runtime_v2.py::EvaluationV2Tests::test_counts_and_unknown_error_denominators
FAILED tests/api/test_runtime_v2.py::EvaluationV2Tests::test_experiment_resume_full_identity_and_ambiguous_attempt
FAILED tests/defenses/test_phase7_separation.py::SeparationTests::test_paired_runner_excludes_evaluator_gold_labels_and_annotations
FAILED tests/evaluation/test_exposure_audit.py::ExposureAuditTests::test_annotation_and_scoring_changes_refuse_resume
FAILED tests/frontend/test_workspace.py::WorkspaceTests::test_navigation_loads_only_selected_workspace
FAILED tests/legacy/test_phase6_auth_attempt.py::BoundTests::test_actual_assistant_success_and_failure_each_call_once
FAILED tests/legacy/test_phase6_auth_attempt.py::BoundTests::test_repeated_boundary_and_reservation_are_blocked
FAILED tests/llm/test_answer_content.py::ContentTests::test_missing_text_retains_status_and_finish_reason
FAILED tests/llm/test_answer_content.py::ContentTests::test_valid_answer_still_parsed_and_cited
FAILED tests/llm/test_azure_openai.py::AzureTests::test_disabled_expired_and_insufficient_capacity_send_nothing
FAILED tests/llm/test_live_readiness_budget.py::ReadinessTests::test_ui_disables_unfunded_modes_without_submission
SUBFAILED(split='final', ids=['development-01', 'development-02', 'development-07']) tests/llm/test_smoke_preflight.py::SmokePlanningTests::test_cli_subset_plan_never_executes_and_cannot_select_final
SUBFAILED(status='screening_error') tests/llm/test_smoke_preflight.py::SmokePlanningTests::test_selected_run_stops_after_operational_error_and_preserves_record
SUBFAILED(status='llm_error') tests/llm/test_smoke_preflight.py::SmokePlanningTests::test_selected_run_stops_after_operational_error_and_preserves_record
SUBFAILED(status='live_blocked') tests/llm/test_smoke_preflight.py::SmokePlanningTests::test_selected_run_stops_after_operational_error_and_preserves_record
FAILED tests/llm/test_smoke_preflight.py::SmokeAPITests::test_ready_and_disabled_chat_are_secret_safe_and_backend_scope_only
FAILED tests/organization/test_runtime_organization.py::RuntimeOrganizationTests::test_original_wire_and_schemas_allow_only_versioned_c_prompt_change
```

These failures remain baseline issues; the required local app check passes.
Steps after setup have not been started.

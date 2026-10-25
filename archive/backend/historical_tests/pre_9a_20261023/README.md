# Preserved pre-9A test sources

These are exact source snapshots, including uncommitted content, before Phase9A
test migration. `source_hashes.json` binds each original file. They are preserved
for history and are not active-runtime assertions or a passing test report.

Groq/NIM routing and SDK assumptions are obsolete in the Azure-only application.
Current contract coverage and explicit replacements are documented in
`backend/tests/README.md`. No old provider routing was restored to satisfy tests.

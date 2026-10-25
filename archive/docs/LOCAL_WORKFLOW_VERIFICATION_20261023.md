# Current local document workflow verification · 23 October 2026

**Passed.** Recent roadmap Phase10 (local workflow) is complete. Checklist Phase9
remains **Partial** because real Azure baseline/paired A/B/C integration has not
succeeded. This run verifies local document functionality, not model defenses.

## Exact command and scope

From `/home/sigmoid/Ai-Security-Poc`:

```bash
PYTHONPATH=backend HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ANONYMIZED_TELEMETRY=false .venv/bin/python -B -m scripts.verify_local_workflow --output docs/evidence/current-local-workflow-v1.json > /tmp/current-local-workflow-v1.log 2>&1
```

Exit0. Standard output was retained as
[evidence/current-local-workflow-v1.log](evidence/current-local-workflow-v1.log),
then only the task-owned temporary stdout file was removed. The executable
verification runner is `backend/scripts/verify_local_workflow.py`; it starts the
actual `app.main:app` and unchanged Streamlit page with separate temporary
APP_DATA_DIRECTORY/raw/SQLite,CHROMA_DB_PATH,UPLOAD_DIRECTORY,DOCUMENT_DIRECTORY.
It forces process-only live=false/free-only=true, blank Azure inputs and an absent
approval path. Root private settings are never edited. Offline Hugging Face and
Transformers flags forbid model downloads. A local-only socket audit guard and
an unused provider-adapter sentinel prevent accidental external/provider I/O.
No retrieval or embedding function is doubled.

Recorded UTC start:2026-10-22T20:20:57Z (23October2026 01:50:57 IST).
Task root:`/tmp/current-local-workflow-m5ez_j8n` (removed).
Task backend:`127.0.0.1:55509`; frontend:`127.0.0.1:39283` (both stopped).
Exact child commands,49 application/frontend source hashes,runner hash,HTTP
results,IDs,chunk/index metadata,retrievals,UI states and server log are in
[evidence/current-local-workflow-v1.json](evidence/current-local-workflow-v1.json).

## Observed workflow

| Check | Actual result |
|---|---|
| Isolated actual backend/frontend startup | Both health requests HTTP200; readiness configured_enabled=false,enabled=false; empty Documents page rendered |
| Upload | Multipart POST `/documents` HTTP201; Markdown version ready; fictional project MARIGOLD-731 vault fact:07:43 Tuesday |
| Extraction/activation/provenance | Exact extracted text and raw bytes; SHA256,document/version IDs,active SQLite pointer,filename,page0,text section and parser bounded-v2.1 verified |
| Persisted real index | Verified Chroma collection; one chunk per revision; source/chunk hashes and offsets verified; actual384-dimensional unit vectors; pinned all-MiniLM-L6-v2 revision1110a243fdf4706b3f48f1d95db1a4f5529b4d41 |
| Real search | POST `/search` HTTP200; genuine cached CPU model retrieved the distinctive fact and correct version/snapshot |
| Successful replacement | POST replacement HTTP200; new ready version with16:29 Thursday fact; active pointer changed; subsequent search returned only the new version |
| Invalid replacement after success | Corrupt PDF POST returned HTTP200 with version status rejected,error=corrupt_or_unsupported,index_name=null; previous usable version remained active and searchable |
| Documents lifecycle views | Actual frontend AppTest against real backend showed initial active,replacement active,rejected replacement and deleted history; no UI exceptions/errors; Ask disabled throughout |
| Delete | Actual Documents checkbox/button issued DELETE HTTP200; all three versions marked deleted,active pointer null; subsequent search hits and snapshot empty |
| No provider/account activity | Zero provider-adapter entries,zero non-loopback attempts; isolated calls,allowance,requests tables each0; no approval file created |
| Cleanup/preservation | Only two task-owned services stopped and task root removed;511 inventoried existing files,production calls/allowance/requests/documents/versions tables and root.env bytes unchanged |

UI scope is explicit: the real Streamlit server was started and health-checked;
AppTest ran the unchanged page against the actual isolated HTTP backend. Upload
and replacement used real multipart API requests; deletion used the real UI
handler. No browser file-picker automation is claimed. Historical ready versions
remain visible with the new active pointer; failed versions remain inspectable.
Logical deletion excludes retrieval and marks all version states deleted; it does
not pretend to erase retained historical content.

## Defects and focused checks

No application defect demonstrated; no production code or frontend fix needed.
Added only the scoped reproducible verification runner and tracking/evidence.
The full workflow ran once and passed11 recorded checkpoints. Runner AST syntax
check and `git diff --check` passed. Existing other-format/edge evidence was reused:
Phase4 real parser suite7 passed,Phase3 storage/lifecycle21 passed,Phase5 retrieval
bounds4 passed and the genuine fresh-process persistence audit. No full suite,
OCR,model download or repeated component testing was performed.

## Remaining live work

Checklist Phase9 stays Partial. Azure endpoint/key/deployment,actual model/version
and parameter/schema capabilities,current free/promotional eligibility,sufficient
quota and entitlement expiry (or truthful unknown expiry) remain prerequisites.
The earlier bounded authorization is one baseline then source-supported paired
development-02 A/B/C,<=5 attempts/160000 additional local units and a one-hour
approval; no activation or execution occurred here. Historical NVIDIA success is
not Azure verification. Human semantic review and defense effectiveness remain
pending. The task stops at local-workflow completion.

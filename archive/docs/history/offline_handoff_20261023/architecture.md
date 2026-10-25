# Current revision-2 architecture

```mermaid
flowchart LR
  U[Local Streamlit UI] --> A[FastAPI: validated requests and IDs]
  A --> P[Bounded parser subprocess]
  P --> L[Version lifecycle and LangChain chunks]
  L --> E[Pinned local CPU embeddings]
  E --> V[Persistent verified Chroma generations]
  L --> R[SQLite active version registry]
  A --> S[Active-version retrieval snapshot]
  R --> S
  V --> S
  S --> D[A / B / C shared assistant]
  D --> G[Free-only approval and reservation ledger]
  G --> O[Actual ChatGoogleGenerativeAI calls when permitted]
  O --> C[Schema and citation-ID checks]
  C --> U
  F[Frozen benchmark manifest] --> Q[Evaluator CLI and human review]
  Q --> D
  Q --> H[Saved raw attempts, metrics and report]
```

The backend is the sole lifecycle writer. SQLite activates a version only after Chroma records verify; incomplete generations remain ineligible and can be cleaned explicitly. Parser text and filenames stay untrusted. Source authority never follows upload time or filename. No evaluator gold labels enter retrieval metadata/model prompts.

Playground uploads and benchmark versions have different generated identifiers and eligibility paths. Public chat/search cannot choose benchmark contexts, filesystem paths, source IDs or evaluator labels. Benchmark execution is CLI-only while the backend is stopped; one-process file locking prevents competing writers.

A/B share ordinary grounding, identical retrieval/settings and citation validation. B adds privileged trust-separation rules. C uses a separate LLM screen through the same live gate and calls B only with retained evidence. Screen failures return an error; no unscreened fallback exists. No output filter adds an unmeasured fourth defense.

Live Groq, real screener behavior and final empirical findings remain pending actual operator-confirmed free allowance/model access. The application does not substitute canned/fake answers at runtime. See PROJECT_CONTRACT, VERIFICATION and HANDOVER for supported behavior and operational limits.

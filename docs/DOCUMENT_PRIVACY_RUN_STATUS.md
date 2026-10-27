# Document privacy live run — 27 October 2026

The user approved all cases within the existing remaining Azure trial allowance.
A separate scope capped this attempt at 758 calls; it added no aggregate capacity.

- Live backend answering was enabled and real Azure responses were recorded.
- 63 provider calls were reserved and 63 of 675 rows were saved.
- 62 rows contain non-operational-error outcomes; all require semantic review.
- One operational error: development-05--control, mode C.
- The screener returned `none` together with another reason code. The existing
  schema correctly rejected that contradictory metadata.
- The run stopped immediately, preserving its stop flag, journal, raw private
  response and every saved row. No request was retried.
- 612 rows remain unrun. The first four documents have all fifteen A/B/C rows.
- The shared allowance had 695 calls remaining at the post-run check. Interactive
  live answering remained enabled; the privacy benchmark scope remained stopped.
- Zero automatically matched leakage candidates is not a reviewed security rate.

Inspect Metrics / evaluation → Five tests per document. Do not clear the stop flag
or reuse this scope. Any continuation needs a concrete correction and a separately
approved untouched-row scope, retaining prior provenance and consumed capacity.

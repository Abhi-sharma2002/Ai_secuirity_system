# 200-call limit amendment

User requested increasing the OpenRouter Nemotron limit to 200. Updated the same
allowance ID to 200 total calls / 6400000 local units, not 200 additional calls.
Original receipt archived beside the private receipt. Expiry unchanged:
2026-10-24T22:01:58.298209+00:00. No resets, refunds or provider requests.

At amendment: 7 reservations / 224000 units consumed or committed; remaining
193 calls / 6176000 units. Existing stop flag retained: capacity is not usable.
Saved records include four completed generation calls, one completed screening
call, one unexecuted stopped reservation and one failed generation record with
provider_or_schema_error and no recorded HTTP status. This is not sufficient
to identify a provider-side cause. No recovery or retry authorized here.

OpenRouter hard cap updated to 200/6400000. Seven focused offline tests passed
in 0.501s, including rejection above either boundary. Free alias, NVIDIA-only
routing, no retries/fallback, and stop-on-error are unchanged.

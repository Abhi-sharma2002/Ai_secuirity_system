# Interactive one-call activation

Authorization basis: following the explicit offer of one call / 32000 local
units / one hour / answering cap 1400, the user requested “start this so that
ican use application”. The call is reserved for user-triggered interactive use;
no automatic model request was made.

Separate receipt: `.private/openrouter-interactive-answer1400-onecall.json`.
Original receipt and cumulative usage remain intact. Expiry:
2026-10-24T21:44:48.928736+00:00 (25 October 03:14:48.928736 IST).
Existing free-route evidence reused; no account balance or billing verification
claimed. No paid route, retry or fallback enabled.

Version `openrouter-nemotron-free-v2-answer1400` sets answering cap to 1400,
retains screening cap 700, and adds 700 to the conservative per-request bound.
Azure settings unchanged. New usage must remain separate from prior settings.
Six focused synthetic transport tests passed in 0.511s. Project services
restarted; backend and UI health HTTP 200. Readiness enabled=true, remaining
1 call / 32000 units. Backend key privately verified equal to root .env.
A/B can each use the one call; C requires two and remains unavailable. No live
answer success is claimed. The first error stops this new allowance.

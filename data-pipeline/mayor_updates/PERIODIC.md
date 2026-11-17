# Kyoto weekly operational adapter (Issue #83)

This code does not register a task, activate HTTP, send notifications, or write
public data. Existing Kyoto jobs, PDF reservations, P1 and CAS are not migrated.

## Contract

`python -B -m mayor_updates.periodic --runtime <private runtime>` defaults to
saved-original replay (zero HTTP). Use a newly provisioned owner-only state root
outside Git/public and outside CAS. Never supply the existing weekly/PDF state.
The runtime uses the existing `weekly.validate_runtime` contract: SHA-pinned
config, baseline, rules, code files (including weekly, continuous and periodic),
explicit PowerShell on Windows, immutable P1, snapshot root and `city: kyoto`.
P1Bridge performs the existing P1 PIN checks before the cycle is reserved.

Only the exact three `monitor_sources` registered in
`config/mayor_update_sources.json` are accepted: FY2025 budget index, FY2026 budget
index, school lunch progress. Source registration must receive separate review
before expansion. Attachments and PDF watchers are not traversed or activated.

Monday 09:00 JST starts a cycle identified by that Monday's ISO date. An early
Monday run stops. A late PC wake processes the current week's cycle once; it
does not backfill prior weeks. Delay seconds and starts after Monday noon are
recorded, not presented as on-time execution. TaskScheduler evidence is still
needed to prove automatic startup. No scheduler is installed by this module.

## Acquisition gate (NOT enabled by this PR)

Live operation additionally requires a separate PM GO, `--acquire`, private
`periodic_enabled: true`, and the existing runtime/config/city network flags.
Default repository settings remain disabled. Offline and acquisition identities
cannot share a state root. Never edit an existing identity to bypass that guard.

The existing `capture_sources` parent runs each URL serially with a 10-second
child wall timeout, TLS validation, no redirects/retries, at most 1 GET and
2 MiB per URL, 3 GET / 6 MiB total. It stops after a failed/unknown child and
keeps exact receipts; unknown request counts are not reported as zero. The
adapter reserves the cycle **before** calling it. It reobserves those three
HTML URLs using the existing weekly refresh behavior, without changing any
one-shot PDF reservations. Existing P1/CAS remain the acquisition implementation.

## State, reviews and local outbox

`periodic_identity.json` binds mode, source manifest and CAS. `cycles/<Monday>/`
is a permanent reservation, including failed runs; duplicate weeks stop before
acquisition. A crash lock is not automatically removed. Do not delete a cycle
or reservation to retry HTTP.

`run_trial`, manifest normalization, review rendering and the atomic last-good
pointer are reused from continuous/weekly. Reviews retain official URL, source
SHA, document title/year, locators and explicit candidate policy associations.
Budget indices without an established policy mapping stay unconfirmed. A source
change does not prove a budget vote, implementation or pledge achievement.

Changes and failures create owner-only `outbox/<Monday>.json` records. They are
local PM handoff records, not delivered notifications. An unchanged successful
cycle creates no review/outbox message. The outbox is written and fsynced before
the normal state pointer advances. On notification failure, normal state stays
unchanged and `failure.json` / `outbox_failure.json` signal required operator
inspection. On a receipt-write failure after pointer commit, inspect the pointer;
the adapter does not falsely claim rollback. Reservations always remain consumed.

Human hold/rejection uses the existing `continuous.review_decision` against this
state root. Review history and dedup identities persist. Publication requires
original-source verification, an explicitly approved scoped PR and normal CI;
there is no automatic publication or review approval endpoint.

## Validation and remaining gates

Synthetic tests block sockets and exercise first observation, unchanged data,
index/progress replacement, failed acquisition, duplicate cycle, delayed wake,
outbox failure and normal-state preservation. Synthetic changes are not evidence
of actual official replacement versions. Existing bounded-acquisition and
continuous tests supply compatibility coverage.

Before live operation: accept code/CI, pin the accepted code and P1 in a private
runtime, provision and validate independent owner-only state/CAS access, approve
the fixed three sources and communication budget, inspect disk/log retention,
and obtain separate task activation and notification-delivery decisions. Outbox
polling/alert delivery and actual scheduled startup remain unvalidated here.

Owner-managed task proposal (not registered): Monday 09:00 JST, owner interactive
logon, StartWhenAvailable enabled, no automatic restart, disallow concurrent
instances; fixed Python executable and pinned private runtime. Review the local
outbox and TaskScheduler events by Monday noon. Retain all cycle receipts and
review decisions during the pilot; no automatic deletion. Storage quota, longer
term retention and recovery authority must be agreed before activation. Missing
or late execution cannot be detected while the PC is off; external availability
monitoring is a separate gate.

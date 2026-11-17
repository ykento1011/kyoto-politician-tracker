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

## Offline PC recovery (proposal; no task registered)

Before any live cycle reservation or GET, the adapter reads cached Windows
`Get-NetConnectionProfile` IPv4/IPv6 connectivity using the pinned PowerShell
runtime (5-second local process limit). At least one recognized `Internet`
profile is required. Offline, missing profiles, unsupported OS, unknown output,
cmdlet failure or timeout means `waiting_for_network`: zero GET, zero cycle
reservation, unchanged CAS and normal pointer. Only `network_wait.json` is
atomically replaced under the dedicated state lock (and initial identity may be
created). This diagnostic retains its observation time even after recovery.
No HTTP, DNS, ping, NCSI request or active probe is initiated by this check.
Cached OS status is only a precondition, not proof of source reachability.

Proposed triggers on the **same owner-managed task and same command/state**:

| Trigger | Purpose |
| --- | --- |
| Weekly Monday 09:00 JST | Normal scheduled observation; retain StartWhenAvailable |
| Owner logon | Catch startup after power-off; interactive-owner execution cannot run before logon |
| System / Microsoft-Windows-Power-Troubleshooter event 1 | Sleep/resume catch-up |
| Microsoft-Windows-NetworkProfile/Operational event 10000 | Network reconnection hint; the adapter still checks OS status |
| Daily local timer with PT15M repetition for P1D | Fallback when connection/resume events are missing; no remote health probe |

Keep IgnoreNew for overlapping instances, RestartOnFailure absent (zero), and
RunOnlyIfNetworkAvailable false so offline waiting can be recorded. The periodic
timer is a fresh local eligibility check, never a retry of a consumed GET cycle.
Before Monday 09:00 the adapter refuses early execution; after a cycle is reserved
all later triggers stop without GET. Offline attempts do not consume it. A wake
in a later week only processes that week's Monday, never accumulates old GETs.
The lock serializes overlapping triggers and the permanent cycle directory
survives disconnect, timeout, unknown outcome and notification failure. Do not
remove either marker automatically to recover an attempted acquisition.

Task/export changes and event-channel activation are **not performed here**.
At registration GO, validate the actual Windows event providers, local JST,
owner logon conditions, standard repetition schema and fixed executable/runtime
paths. Power-off or logged-out PCs cannot be guaranteed immediate execution;
the next owner session/fallback tick performs the eligibility check. Windows
event delivery and real reconnect behavior remain private integration gates.

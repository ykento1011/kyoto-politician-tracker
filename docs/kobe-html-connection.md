# Kobe HTML connection candidate

This candidate is disabled and undeployed. The explicit CLI is
`python -B -m mayor_updates.kobe_acquisition --runtime ... --contract ...
--contract-sha256 ...`. No scheduler registration or private deployment is supplied. The disabled example cannot reserve or acquire.
It does not change the old HTML+PDF acquisition mode or its permanent URL marker.

## Trust and reservations

`connect` takes a separately pinned deployment contract and pinned per-week
approval. The deployment contract, not a run name or weekly approval, determines
the canonical reservation root, acquisition CAS, P1 root and known legacy paths.
Deployment review must bind these to the existing real paths and all known
reservation evidence; editing a contract PIN is a new deployment approval, not a
retry mechanism. No private paths, identities or approvals are provided here.

Approval binds the contract SHA, source, roots, JST Monday week, validity window
and approval reference. The clock is internal and checked again immediately
before acquisition; tests mock the clock, callers cannot supply a past week.
The known consumed 2026-11-16 week is rejected. Legacy
URL markers require pinned termination evidence, legacy cycle directories and
locks block execution. Reservation names depend only on city, exact URL and week.
Exclusive directory creation prevents concurrent/same-week attempts across run
names and contract versions within the canonical root. Failed or unknown
attempts remain blocking; no cleanup/reset/retry interface exists.
The existing `weekly.single_run` lock serializes validation through completion
within that root, including across week boundaries. Unknown directories (even
without a reservation file) also block. Removal of an OS/process lock alone
never clears a retained unsuccessful reservation.

## Concrete acquisition and processing connection

`kobe_acquisition.main` reads runtime with stdlib and reuses dependency_preflight
before business imports. Runtime/code/resources, processing config/profile/baseline
and I/O are PIN-bound; the acquisition contract and per-week approval are separate.
The runtime's network-disabled setting applies to private processing and never
substitutes for acquisition authorization. The shipped acquisition example is
also disabled, so it cannot reserve or acquire.

Call path: `main -> run_connected -> connect -> acquire.capture_sources ->
run_confirmed_worker -> acquire.worker -> receipt_identity -> continuous.cycle`.
Only external worker/P1 boundaries are replaced in the integration tests; the
entry/preflight, concrete adapters, acquisition parent, receipt checks, monitor,
cycle and private writes actually run against synthetic temporary data.

The exact `kobe_html1_reobservation` scope is an opt-in branch in city_scope.
Parent and child validate the pinned contract/approval, canonical root, week,
permanent series reservation and exclusive request/worker consumption markers.
The old HTML+PDF scope and permanent URL marker remain untouched. There is no
skip flag. Source title and metadata are shared by producer and consumer.

One GET, 2 MiB received, 2 MiB minus one byte accepted, TLS, redirect/retry/link
following zero, existing ten-second worker wait are retained. Parent records
command hash, PID, intent hash, bounded wait result, return code and outcome hash.
On timeout it kills only its own worker and waits at most two additional seconds;
unconfirmed exit is HOLD, never cycle. File-backed stdout/stderr avoids PIPE EOF
waits. This reuses the subprocess worker mechanism, not an OS supervisor: it
attests direct-worker exit, **not arbitrary descendants or a whole-operation
deadline**. The fixed HTML worker has no converter/link-following launch path;
future changes to that assumption require review. Actual network/P1 termination
has not been tested here.

After the callback confirms termination, a fresh P1Bridge reads the acquisition
CAS; no stale pre-fetch index or alternative CAS is used. Standard pinned
receipt/preflight files are checked with `operations.receipt_identity`, including
P1 hashes, city, URL, fiscal year, document ID, exact version and byte count.
Original receipt time and current observation time remain distinct for unchanged
content. The latter must lie between the internal before/after acquisition
timestamps and within the authorized week/window; replaying an old receipt under
a new output path cannot count as a fresh GET. Only that verified version is delivered to the concrete private-processing
adapter with communication/publication disabled. There is no CAS copying or
index synthesis. A result with unknown/nonzero network requests or public writes
cannot be recorded as complete. The canonical processing state is part of the PIN-bound series identity and
must be separate from acquisition state/CAS. Existing cycle lock and permanent
cycle reservation remain in force. Processing starts only after worker exit and
receipt verification; the report evaluation clock is captured once at that point.
The adapter rechecks exact SHA/docID before the real cycle observation. Original
CAS time, new acquisition observation and report evaluation time are separate.
Normal completion, content HOLD (last-good retained), acquisition failure and
unknown exit are distinguished; failures retain reservations and never fall back.
No public writer is connected.

## Scope of evidence and dependencies

Tests use synthetic temporary originals and fake external worker/P1 boundaries.
They exercise the actual adapters, acquisition parent/receipt generation, identity
checks, real cycle, diff/HOLD and private state, plus a harmless subprocess for
PID/exit evidence. They do not use official HTTP, private P1/CAS or business state.

Base is main `8e7fa0395b164189940e1925901c57a6e5fe9d76`. Accepted PR #108 head
`13f52f65f7981343da7f01ee5380e77526b95f26` is explicitly cherry-picked as
`49e90eb` (continuous/offline_weekly/age tests only). PR #108 itself and main are
unchanged; subsequent connection changes are #109-specific. The accepted Kobe
execution copy is not migrated.

Before real use: authorize the fixed GET/source/use scope and execution window;
approve canonical acquisition and processing roots, legacy evidence coverage,
code/PIN/runtime/contract deployment and ACL/actor checks. No private runtime,
binding or approval receipt is generated by this PR. A new week is not permission.
Consumed markers, original CAS and last-good remain intact. Publication and
recurring enablement are excluded.

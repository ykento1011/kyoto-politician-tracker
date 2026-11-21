# Kobe HTML connection candidate

This module is non-active: no CLI, network transport, scheduler registration or
private deployment is supplied. The disabled example cannot reserve or acquire.
It does not change the old HTML+PDF acquisition mode or its permanent URL marker.

## Trust and reservations

`connect` takes a separately pinned deployment contract and pinned per-week
approval. The deployment contract, not a run name or weekly approval, determines
the canonical reservation root, acquisition CAS, P1 root and known legacy paths.
Deployment review must bind these to the existing real paths and all known
reservation evidence; editing a contract PIN is a new deployment approval, not a
retry mechanism. No private paths, identities or approvals are provided here.

Approval binds the contract SHA, source, roots, JST Monday week, validity window
and approval reference. The known consumed 2026-11-16 week is rejected. Legacy
URL markers require pinned termination evidence, legacy cycle directories and
locks block execution. Reservation names depend only on city, exact URL and week.
Exclusive directory creation prevents concurrent/same-week attempts across run
names and contract versions within the canonical root. Failed or unknown
attempts remain blocking; no cleanup/reset/retry interface exists.

## Acquisition and handoff seams

The acquisition callback receives only the fixed HTML source, canonical CAS and
reserved output, plus the existing worker budget: one GET, 2 MiB received,
2 MiB minus one byte accepted, TLS verification, no redirect/retry/link following,
10-second worker limit. This is **not** a whole-operation deadline or a guarantee
of descendant termination. No production callback is wired in this candidate.
The existing `acquire.capture_sources` cannot be passed directly: its old URL
reservation and HTML+PDF scope remain deliberately unchanged. A live adapter
binding, including trustworthy termination evidence, remains an explicit
unimplemented deployment gate; stubs are not evidence that HTTP is bounded.

After the callback confirms termination, a fresh P1Bridge reads the acquisition
CAS; no stale pre-fetch index or alternative CAS is used. Standard pinned
receipt/preflight files are checked with `operations.receipt_identity`, including
P1 hashes, city, URL, fiscal year, document ID, exact version and byte count.
Original receipt time and current observation time remain distinct for unchanged
content. Only that verified version is delivered to the private-processing
callback with communication/publication disabled. There is no CAS copying or
index synthesis. Private processing and its durable state/period guards must be
bound by the future approved caller; no live cycle is installed here.

## Scope of evidence and dependencies

Tests use temporary directories, synthetic receipts and fake P1/worker/process
callbacks. They exercise the real connection, identity checks and reservations,
not real acquisition, P1 or deployment. No claim of live operation is made.

Base is main `8e7fa0395b164189940e1925901c57a6e5fe9d76`. PR #108 is not included.
Its execution-time age fix is a separate unmerged dependency for future reports;
this candidate does not silently migrate the accepted Kobe offline copy.

Before real use: review and authorize the fixed GET and source/use scope; resolve
the live acquisition/processing callback bindings and termination evidence;
approve the canonical root and legacy-reservation coverage; approve private
code/PIN/runtime/contract deployment and an execution window. A new week alone
is never permission. Existing consumed markers, original CAS and last-good state
must remain intact. Public publication and recurring enablement are excluded.

# Stage 2 creation-time evidence ownership (offline only)

The live source gates remain disabled. No administrative token, audit policy,
Firewall, worker or live runtime was exercised by these tests.

## Writers and readers

| Writer / identity | Records | Creation / read boundary |
| --- | --- | --- |
| Bridge Agent, elevated SID1004 | raw audit capture, parsed/HOLD sidecars, audit intent, 5157 XML JSON, DNS loss JSON, operator setup, agent_ready, response, finished | Save-New -> Save-EvidenceBytes; Assert-Private and strict evidence descriptor readback |
| Guardian / Recover, elevated SID1004 | STOP, guardian_hold, guard_ready, guard_restored; audit capture | Same exclusive publisher; no owner-check exception |
| Bridge Agent, elevated SID1004 | DNS provider list | Save-EvidenceBytes, same creation descriptor |
| Controller, non-elevated SID1004 | controller intent, client identity, request, STOP, transaction journal, recovery TXT | Existing _record / exclusive text write; owner-only parent and retained WindowsIdentity path checks. Default owner is NOT assumed for an elevated controller: elevated controller is rejected. |
| Worker / supervisor, non-elevated SID1004 | request, worker_started, report, HOLD, termination and success journal | Existing _record, fixed actor/Job, locked owner-only read paths and run/nonce/plan checks |
| Windows tools / ETW | Security EVTX, DNS ETL | Dedicated raw-output boundary and bounded streaming into owner-only derivatives; original attributes/content are never repaired. Native generation remains unmeasured. |

## New publisher

PS5.1 .NET Framework FileStream overload accepts FileSecurity at CREATE_NEW.
The descriptor sets the fixed actor SID as owner and a protected, single explicit
FullControl Allow ACE for that SID. No Set-Acl, takeown or existing-object security
update is used. Creation denial is HOLD; there is no default-security fallback.

The private parent is checked before creation and publication. The temporary
file is exclusive, gets the descriptor at creation, is checked through its open
handle, fully written and flushed to disk, then closed and checked for private
path/nonreparse and exact security. Its bytes are SHA-checked before no-overwrite
same-directory File.Move, then checked again at the final path. Maximum payload
is 2 MiB. Failed temporary/final records remain for diagnosis; the caller gets an
exception, never a successful result. A final verification failure does not
authorize a retry or erasure. Existing binding/sequence and consumer checks remain.

Synthetic tests inject the I/O boundary: actual FileSecurity construction and
validation run, but the native creation overload is not invoked. Elevated default
owner Administrators is modeled independently from the explicitly supplied owner.
The CSV and Guardian suites inject only the publisher when testing unrelated
control logic; this dedicated suite tests the real publication algorithm.

## Remaining administrative measurement (separate GO)

Use a new nonsecret disposable directory, independent of every real run, with
already approved SID1004 parent security. Under the approved local admin token,
create one inert bounded JSON using the exact publisher. Verify requested and
actual owner, protected single ACE, file identity/nonreparse, byte SHA, atomic
publication and collision refusal. No Bridge entry, auditpol, ETW, Firewall or
worker. Preserve a failed partial artifact; delete only explicitly inventoried
successful test files after inspection under a separately agreed cleanup scope.
If the token cannot assign SID1004 at creation, HOLD without changing privileges,
ownership or ACL. Do not use the experiment as a new Stage 2 run authorization.

## External binary evidence boundary

Raw files are exactly `before.evtx`, `after.evtx`, and `dns.etl` in the fixed private
mailbox. EVTX requires successful fixed-PIN wevtutil completion. ETL requires the
exact owned session/path, successful stop, session absence, and zero loss in all
three counters. Existing raw ETL and derived destinations are refused.

Raw owner may be SID1004, BUILTIN Administrators, or LocalSystem, reflecting the
explicit external-producer boundary. Its DACL must have exactly one FullControl
Allow ACE for SID1004 (inherited from the private parent is accepted for raw files
only); other owners/grants, directory/reparse/multiple-link files are HOLD.
This policy does not claim the raw owner was SID1004 and does not change the strict
SID1004 owner/protected-DACL requirement for derived/IPC files.

A retained read handle denies write/delete sharing. Volume/file ID, size, last
write time and descriptor are checked around the copy. Active writers, missing
identity, incomplete producer state or mutation are HOLD. The private parent is
checked independently. Byte streaming uses 64 KiB buffers; EVTX is bounded at
32 MiB (container allowance for the existing 20 MiB Security log), ETL strictly
below 16 MiB. These are artifact caps, not permission to resize/export/trace now.
The 2 MiB JSON publisher is not used for the binary body.

Source is read twice under the same lock, SHA/length compared, temporary derivative
is checked for exact security and byte identity, then atomically published without
overwrite and verified again for file ID/SHA/length. A run/nonce/plan-bound provenance
JSON records raw owner/DACL/identity, producer PIN/completion, names, SHA, size and
copy time. Failure retains partial evidence, throws HOLD, never removes the raw
file. Raw/derived handles stay retained through downstream parsing.

EVTX RecordId continuity and before/after archive validation use the derivative.
DNS ETL stop/loss checks and existing query/PID/SID/transport attribution remain
required; a successful byte copy alone cannot accept policy or DNS evidence.

Three separate future GOs remain: (1) inert admin-token file creation above,
(2) at most one Security export with no log modification, and (3) one short,
nonpersistent ETL session with fixed name/providers, local stop and loss evidence.
All use isolated private areas, no Stage 2 run/worker/probes, retain originals,
record actual producer ACLs, and HOLD on policy mismatch rather than repairing ACL.
Exact trace duration and teardown must be fixed in that separate GO. Real hang
termination, DNS attribution and restoration remain unverified.

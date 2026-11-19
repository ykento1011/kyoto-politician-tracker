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
| Windows tools / ETW | Security EVTX, DNS ETL | Not written by Save-New. Existing owner/path checks remain fail-closed. Native tool-created artifact ownership is a separate unproven live boundary; this patch does not claim these tools honor the descriptor or repair their ACL. |

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

Before Stage 2, the native EVTX/ETL writer boundary must also be resolved or shown
to satisfy existing checks; this patch deliberately does not weaken it. Real
hang termination, DNS attribution and restoration remain unverified.

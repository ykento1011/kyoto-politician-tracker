# Disabled fixed Windows launch contract (stage 1)

A Windows audit event can contain `executable=None`. The module therefore never treats that event or a command string as image authentication. `launch_contract.py` implements the verification/cleanup state machine behind an injected WinAPI observation interface. No native adapter, executable configuration, subprocess call, activation switch, OS/network operation or CLI is shipped. `FixedLaunch.enabled` must remain false. Only an explicit synthetic mode and a mock adapter marked `simulation_only=True` can exercise it. These labels are not a sandbox against malicious Python adapters; adapters and the Python interpreter are trusted code. The tests replace process and network APIs with failures.

## Contract and observations

- Fixed canonical local EXE path, immutable argument tuple, SHA256 of image bytes, pinned signer certificate SHA256, actor/owner SID and a bounded deadline.
- Acquire a non-inheritable read handle denying write/delete, inspect its file ID, exact bytes, signature, ACL, parents, reparse points and hard-link count. Missing or unproven evidence stops before creation.
- Create a kill-on-close Job Object with one active process and no breakaway. Explicit `lpApplicationName` and `CREATE_SUSPENDED`, no inherited handles. Assign the suspended process to that job before execution.
- `inspect_process_image` represents QueryFullProcessImageName plus independently verified image-file identity/bytes/signature, NOT just that API's path string. Match with the held handle and re-read before resume. Future native signature validation must prove the pinned signer and valid signature/chain under a reviewed offline trust policy; unavailable trust/revocation evidence must HOLD, never fetch it online.
- Child/job deviation, replacement, null handles, API failure, bad signature/ACL/SHA or timeout is fail-closed. Confirm whole-job termination; lack of confirmation means keep OS isolation in place. Never grant network/publication/source authority. Finally close handles; closing alone is not termination proof.
- The single-process job is a leaf-launch contract, suitable for an ACL-read helper. It does not yet authorize or integrate a full weekly Python process tree. A later integration must preserve the reviewed fixed-helper boundary rather than quietly increasing the job limit.

## Synthetic tests and limits

11 targeted tests, including table-driven negative cases: default-disabled/live-adapter refusal; canonical path and config; exact suspended request; bytes/signer/ACL/links/lock failures; same-path altered image/file ID; replacement before resume; child escape/job policy; create/query/assign failures; null handles; timeout and unconfirmed termination. All WinAPI outcomes are fake. No private data, Windows child, HTTP, DNS, Firewall or actual signature verification is exercised. A successful simulation is not live Windows integration acceptance. CI runs the new suite in the existing offline workflow; old workflows are not manually rerun.

## Stage 2 pre-implementation review (read-only, 2026-11-18)

| Item | Observation / remaining condition |
|---|---|
| Existing rules | Earlier read-only evidence: active outbound blocks target a different SID. They do not prove protection of the owner-only execution account or service-mediated DNS. No changes made. |
| Authenticated bypass | Current ActiveStore enabled `OverrideBlockRules=true` query returns 0. This is a point-in-time read, not proof of every future policy, third-party filter or packet path. Reconfirm effective policy at an approved maintenance window. |
| Kyoto | Existing task Ready, next run 2026-11-23 09:00 JST. LastTaskResult 0 is not evidence of future success or automatic start identity. No task changed. |
| Operator/window | No designated on-site administrator or maintenance window has been supplied. Remote management and all same-host business communication would be interrupted by host-wide blocking. No impact-free window is established. |
| Narrower alternative | Per-EXE or SID-only rules are narrower but leave delegated DNS/local proxy and alternate-child coverage unproven. Existing non-network AppContainer/restricted-token execution would be preferable if compatible, but is not available/verified here and would require additional provisioning/access review. Do not reuse another SID by relaxing CAS ACLs. No narrower option is currently proven equivalent. |
| Proposed boundary | Host-wide temporary block remains a proposal requiring explicit scope approval, local administrator and local recovery; not automatically selected or applied by this PR. Existing production monitoring must have no scheduled/in-flight work in that window. |
| Backup/recovery | Before any future change, save effective rules/profiles/filters, unique IDs and intended deltas. Remove only newly created rules after confirming all descendants stopped and evidence durable. Do not reset/import the entire Firewall policy. If termination or rollback cannot be proven, keep isolation and hand off locally. A blind timed unblock is unsafe. |
| Next GO | Review mock-state-machine code, then separately authorize native adapter implementation and a harmless process test + OS-block/recovery acceptance. Stage 2 and the Osaka weekly third attempt remain NO-GO. |

## Preservation

Main-based independent Draft, no dependency on PR #99 or the unmerged source-review/UI chains. No modifications to private B-plan copies, real P1/CAS/receipt/ACL/state/reservations, public JSON or scheduled tasks. No source approval. Fixed code/P1 evidence from earlier acceptance is reused, not rehashed just for this PR.

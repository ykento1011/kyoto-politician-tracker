# Saved operation record audit (offline, private)

`python -B -m mayor_updates.record_audit --schedule schedule.json --records-root saved-records --evaluated-at 2026-11-16T12:00:00+09:00 --output private-output`

Set `PYTHONPATH=data-pipeline`. Output must already exist outside the input records and schedule directories and outside a Git checkout/public directory. The existing `PrivateOutput` writer exclusively creates `operation_record_audit_PRIVATE.json`; collision or save failure is an error, never success. This is a one-shot reader, not a scheduler, notifier or recovery tool. It does not run P1, cycle, HTTP or publication.

The caller supplies an explicit approved schedule for exactly one cycle. Example (synthetic):

```json
{
  "approved": true,
  "paused": false,
  "applicable": true,
  "approval_reference": "synthetic single-cycle approval",
  "format": "continuous",
  "city": "kobe",
  "series_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "mode": "offline",
  "cycle_key": "2026-11-16",
  "scheduled_at": "2026-11-16T09:00:00+09:00",
  "deadline": "2026-11-16T12:00:00+09:00",
  "identity": {
    "city": "kobe",
    "manifest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
}
```

`series_id` is the existing manifest SHA identifying the source set, not a guessed friendly label. `identity` must exactly match the existing root identity, including any snapshot/profile fields. `continuous` uses `loop_identity.json`, `cycles/<cycle_key>/intent.json` and existing result/failure/HOLD/status files. Its legacy record format supports offline identity only; this reader does not infer acquisition provenance. `periodic` uses `periodic_identity.json` and `reservation.json`, with the existing Kyoto adapter identity, mode (`offline` or `approved_acquisition`), manifest, snapshot root and schedule. Identity-bearing intent/reservation must bind the result's directory to the requested city, source set, cycle and mode. No unrelated week is accepted as target evidence.

| Classification | Meaning |
| --- | --- |
| `not_expected` | Explicitly unapproved, paused or inapplicable; no expected run inferred. |
| `before_deadline` | No target evidence yet, evaluated strictly before the deadline. |
| `result_recorded` | Matching cycle result exists. Does not prove commit of last-good, automatic start or publication. |
| `hold_or_failure` | Explicit failure/HOLD takes precedence even if a result also exists (continuous writes result before final commit). |
| `incomplete_evidence` | Target reservation/intent or directory exists without sufficient completion evidence. Not proof of a running process. |
| `missing_evidence` | At or after the deadline, no target record. Not proof that the OS never started the task. |
| `invalid_evidence` | Unreadable/missing root, corrupt JSON, invalid metadata or mismatched identity/target. CLI exits 2 after saving the private diagnostic. |

All timestamps must include a timezone; evaluation time is explicit, never filled from the current clock. At the exact deadline, an absent record is missing evidence. A result or HOLD can be reported before the deadline. Input file SHA-256 values and the supplied target/evaluation time accompany the classification. Approval references are caller assertions, not independently authenticated grants; this CLI cannot confer permission to execute. A single approved cycle never creates future expected cycles.

Read-only inspection is not an atomic snapshot of a live writer. Use saved, quiescent evidence; concurrent changes require a separate later observation. No OS/task-start evidence is collected. No new source permission, public write, last-good update, lock release or retry is authorized. A partial output left by a failed save is not a successful report and must not be overwritten by an automatic retry.

Validation uses synthetic record files and temporary private output. The real reader/classifier/writer and CLI are exercised; only a read-permission failure is injected. Existing operational roots, reservations and outbox are not test inputs.

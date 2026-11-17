# Private evidence handoff (Issue #88)

`python -B -m mayor_updates.evidence_handoff --request <owner-only JSON> --output <owner-only directory>`

This entry reuses the source registry, P1 receipt/observation checks, literal quote
lookup, existing scope/storage validators, and `engine.approved_bundle`.
It does not fetch, reserve, modify registry decisions, publish or schedule.

Request envelope uses the same `city`, `registry_root`, `snapshot_root`,
`p1_code_root`, `code_files` pins and `network_enabled:false` as the registry CLI.
`action` also requires `network_enabled:false`, candidate ID, revision and index SHA.
Any changed/newer/failed index observation holds the action; re-registration must
happen through a separate human decision. A packet is not an authorization token.

Operations:

* `acquisition_plan`: requires a current `approve_for_source_registration` event,
  a pinned **disabled** scope, storage/binding, fixed P1 hashes, and an acquisition
  output path. Existing `validate_scope/validate_storage` checks run unchanged.
  The fixed PDF source must match the candidate's city, URL, year, policy IDs and
  document ID. CAS integrity is read; existing URL reservations HOLD without deletion.
  Existing saved originals request reuse. No reservation is made. Unsupported scope
  configurations HOLD rather than expanding the existing acquisition contract.
* `evidence_packet`: requires the existing registry `receipt_spec`, reviewer/reason,
  and notes with policy ID, subject, submeasure, fact type, relation, literal quote,
  physical/printed locator and limitations. P1 verifies the original/receipt and
  quote. Empty notes remain policy-relationship-unconfirmed. Results stay unverified.
* `public_review`: same evidence inputs, pinned baseline, base revision and one
  explicit display text per policy/submeasure. Produces a human-review packet only.
* `public_proposal`: reproduces that packet and requires the engine's matching human
  approval (packet ID, exact candidate IDs, reviewer and timezone-aware timestamp).
  Exports private before/after proposal data, **not** a publishable JSON file.

The new `evidence_note` engine kind only appends `evidence_notes`. It cannot change
stage, old budgets, funding or totals; each note is explicitly excluded from totals
and does not certify a policy stage. UI rendering and any public PR are separate.
The human approves the display's meaning, not merely a matching string in a PDF.

Output is content-addressed, owner-only and atomic/no-replace. Identical replay
returns zero new records. Failed validation leaves prior records intact. A caller
must re-run validation before use; old exported files never grant acquisition or
publication authority. Private CAS paths and receipts must not be committed.

Real evidence: P-04 budget-proposal wording only, not budget vote/enactment/results.
P-14 remains unconfirmed. Existing P-04 1.4 billion yen and other-year 59 million yen
are never replaced or added to the new note. Actual registration approvals are zero;
synthetic approvals in tests are not PM decisions. Current baseline already-present
notes produce no new proposal. Do not use this path to duplicate separately published
UI evidence: a human must include that existing presentation in baseline review.

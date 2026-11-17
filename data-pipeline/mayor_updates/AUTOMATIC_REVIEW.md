# Exact-fact automatic review (Issue 92)

Stacked on PR #89, which depends on #87. No merge, network, acquisition reservation,
source-registration decision, public writer or stage promotion is added.

`python -B -m mayor_updates.automatic_review --request PRIVATE.json --output PRIVATE_DIR`
uses the existing owner-only P1/CAS/registry and receipt observation validator.
The config contains `network_enabled: false`, `city`, `registry_root`, `snapshot_root`,
`p1_code_root`, `p1_sha256`, `code_files`, pinned `rules`, `accepted`, `public_snapshot`,
and `requests`. Each pinned input is `{path, sha256}`. Output must be separate from
the registry/CAS; existing history is read only. No defaults enable communication.

Each request identifies current `candidate_id`, `revision`, `index_sha256`, the
existing `receipt_spec`, and a fact. Fact fields: `policy_id`, `submeasure`,
`fact_type`, `relation`, `year`, `project`, `target`, `amount`, `unit`, `quote`,
`limitations`, `pages`. Each page carries physical/printed page numbers and its
**complete** PDF text, including footnotes. P1 checks the physical page, printed
footer and quote. The full text must additionally equal the saved page text.
Text extraction failure is HOLD; images or fuzzy matching are not an alternative
approval channel. Use multiple complete pages for cross-page context.

## Trust boundary

Rule and accepted-baseline files are owner-only, SHA-pinned operator inputs, like
existing human-review receipts. Hashes prove integrity, not a human's identity.
Only the real reviewer may supply their approval; callers must not manufacture
receipts from PM discussion, model confidence, or successful tests. TEST approvals
exist solely in synthetic fixtures. This is not a cryptographic identity service.

UNCHANGED requires a separately accepted fact fingerprint, including receipt,
source/index revision, exact context and current public snapshot. Accepted entries
contain `fingerprint`, `decision: accept_existing_fact`, `reviewer`, `reviewed_at`,
`review_record_id`. A past machine candidate does not count as this approval.
UNCHANGED produces no review/proposal. Persisted identical AUTO/HOLD results also
produce no duplicate output; timestamps are excluded from the dedup key.

AUTO_VERIFIED requires current source registration plus exactly one approved rule.
The rule binds city/candidate/revision/index SHA/URL/document ID, `expected_fact`,
`public_sha256`, rule ID/version, reviewer/date/review-record ID, and decision
`approve_exact_budget_note_rule`. It must explicitly set `budget_addition: false`,
`stage_change: false`, `contradiction_review: cleared`. No production rule ships.
Only a non-additive `budget_proposal` evidence note may qualify. Direct/contextual
classification must exactly equal the preapproved rule, never be inferred.

This deliberately narrow first version does not auto-approve changed amounts,
new footnotes, new policy mappings or changed public snapshots. A PDF can change
outside the approved complete context pages, but receipt/current-source checks
must still pass. Broader parameterized update rules need separate review.

HOLD retains requested fact/context and, where validation succeeded, observed
original/receipt/page evidence, reason and minimum review question. It means
insufficient verification, never non-performance. ACL or pin failures before
safe inspection do not fabricate verified evidence. New votes, enactment,
implementation, achievement and material state changes require human review.

The private publication candidate is an evidence-note payload only. It carries
`publication_authorized: false`, no additive amount, no stage change and no ready
to write public JSON. PR #89's human public-approval gate remains unchanged.

## Operational limitation

Existing P-03/P-04 facts must not be republished merely because their baseline has
not yet been encoded for this engine. Until real accepted-baseline artifacts and
registration/rule approvals are supplied, HOLD is correct, not UNCHANGED or AUTO.
Historical P1 ACL failure must not be bypassed to improve the automation count.
Actual avoided human reviews and synthetic passing cases must be reported apart.

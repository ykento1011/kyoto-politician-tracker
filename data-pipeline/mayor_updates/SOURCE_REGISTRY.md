# Offline source candidate registry — Issue #86

Discovery is not permission to acquire, policy certification, or publication.
This small adapter connects saved_index/comparison_links, compare_index, existing
P1 receipt_identity/evidence and private atomic records. No crawler, new CAS,
HTTP client or task is introduced. Existing approved_bundle/publication remains a
separate later gate; this registry never calls it or manufactures policy changes.

## Entry and storage

`python -B -m mayor_updates.source_registry --request <private JSON> --output <empty private directory>`

Request fields: `network_enabled:false`, `city`, `registry_root`, `snapshot_root`,
`p1_code_root`, `code_files` (existing SHA-pin format, including this module),
Windows `powershell_exe`, and `action`. Provision a new owner-only registry outside
Git/public, separate from CAS and existing state/reservations. Output must also be
separate. The existing immutable city-capable P1 must match its pins. Code and
receipt paths never belong in public examples. The registry does not change ACLs.

The identity binds city and resolved CAS path. Sequential `event-*.json` records
are append-only, hash-chained and atomically published without replacement under
the existing single-run lock. State is derived from events, not an overwritten
pointer. Failed validation/append leaves all earlier events intact. Retain stale
locks for operator inspection. This provides accidental-corruption detection,
not tamper-proof protection against an owner rewriting the whole history.

## Actions

1. `scan`: `source` must exactly match a registered index; `index_sha256` must
   identify its latest successful saved observation. Reuse saved_index to derive
   title, source URL, index SHA/anchor/href, section/context, fiscal year and budget
   category. Candidate ID binds city + exact PDF URL + index fiscal year. Duplicate
   links share an ID but retain every listing position. Same index SHA creates no
   event; changed SHA with unchanged links records observation, not new review.
   Added/changed/removed links are retained as history. Removal is not cancellation.
   Changed/reappearing candidates require new review; prior receipts stay in history.
   A URL change is removal + addition, never a guessed same-document association.
   Same-URL PDF-only replacement cannot be discovered from unchanged index HTML.
2. `decision`: supply candidate ID, exact current `revision` and `index_sha256`,
   named `reviewer`, `reason`, explicit `policy_ids` (empty = unconfirmed), and
   `hold`, `reject` or `approve_for_source_registration`. The event records UTC.
   Current identical decisions deduplicate; later hold/reject can revoke approval.
   These are operator-entered review receipts, not authenticated PM signatures.
   Before decision/evidence/proposal, reload the CAS index and require its latest
   successful index version to match the most recent registry scan. An unscanned
   replacement or latest failed acquisition holds the operation without changing
   previous history. Unchanged links can retain their earlier listing evidence
   after a newer index has been scanned; no automatic re-approval is manufactured.
3. `proposal`: exact candidate/revision/index SHA required. Only a current active
   registration approval produces a fixed PDF source configuration proposal.
   It stays `enabled:false`, `network_enabled:false`, one URL, 1 GET / 2 MiB /
   10 seconds, TLS, no redirects/retries/following. Document kind remains generic
   `other_official`; fiscal year is index context until human document review.
   It is **not an executable acquisition scope**. Separate communication GO,
   P1 scope/binding/storage validation and persistent reservation are required.
4. `evidence`: supply candidate/revision/index SHA, reviewer/reason and a
   `receipt_spec` in the existing operations.receipt_identity format (`city`,
   `source`, `policy_ids`, SHA-pinned acquisition receipt/preflight). URL/year/
   medium/policy, P1 PIN, observation history, document ID and CAS bytes must match.
   Optional `notes` carry policy, subject, fact_type, locator and literal quote.
   Existing P1 evidence checks the exact saved physical page and quote. A literal
   match does not authenticate a reviewer’s interpretation. Proposal, vote,
   enactment and implementation are separate fact types, never automatic stages.
5. `report`: one source per row and all registered policies, including policies
   with no candidate. JSON preserves all hashes/locators/receipts; HTML is escaped
   and includes expandable evidence detail. Removed sources remain marked inactive.

Illustrative action (placeholder IDs; not executable approval):

```json
{"operation":"decision","candidate_id":"<from report>","revision":"<from report>",
 "index_sha256":"<from report>","reviewer":"<human reviewer>",
 "reason":"<listing/year/media/policy review>","policy_ids":["P-04"],
 "decision":"approve_for_source_registration"}
```

## Actual saved-original demonstration (no new HTTP)

Saved FY2025 Kyoto index SHA:
`be45c0421b1ca127853416f420991cd8d288841fb46ce6e76f0bc601860180bd`.
103 listing candidates were registered in a new private ledger. Reprocessing the
same index added zero events. No registration approval was manufactured: all 103
remain pending. Two original associations were read back; 101 others were not
linked in this demonstration (this is not a claim they are absent from all CAS).

| Candidate | Policy candidate | Original SHA | Current evidence limit |
| --- | --- | --- | --- |
| kyoto-source-264f597d0d3ed2752257f790 | P-04 | 4c3d5f1210dd2928c180d7e4237b50c80cd6467675e6b0ee2ca97c4395c373cb | FY2025 proposal, printed 103 / physical 1, childcare quotation matched including footnotes |
| kyoto-source-ac74c65ae3e966fe1818afc2 | P-14 | 294b3a3f3ae2577bb25c700e43ac4f46dfe19b180d9b8ff59e19e0d2ce08ab24 | Original/receipt verified; mental-health/AYA relationship remains unconfirmed |

The prior shortened quotation omitted footnote markers and correctly failed the
literal matcher without appending evidence. The exact original quotation then
passed. Reattaching each original added zero duplicate events. All 14 policy rows
remain uncertified; 12 have no mapped candidate in this run. Existing CAS, PDF
reservations/receipts, P1 candidate, bindings and public JSON: 58 protected files
had unchanged bytes before/after the successful run. New registry only; HTTP 0.
The newly provisioned directory needed owner-only ACL correction before use;
existing storage ACLs were not changed.

Next: PM chooses sources/subjects, reviews registration and evidence separately,
then approves bounded acquisition and later a scoped public proposal PR. P-04's
418,800 thousand yen proposal is not the registered 1.4 billion yen or another
year’s 59 million yen; this tool changes neither amounts nor stage confirmation.
Kyoto is exercised; other city keys reuse the same mechanism only when their
official indexes have separately been registered. No empty city manifest is filled.

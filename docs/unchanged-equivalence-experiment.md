# Offline same-fact continuation experiment

Stacked on PR #93, commit `7267871d0a8efa9239ef9cb420bd813a89ffa528`.
This is **not enabled for the three real accepted facts**, acquisition, source
registration, publication, or scheduled execution. Strict comparison remains the
default. No existing baseline is rewritten or signed by this code.

## Explicit test contract

`automatic_review.run()` / CLI requires `network_enabled: false`,
`comparison_mode: "offline_unchanged_equivalence_v1"` and
`offline_test_mode: true`. An unknown mode or missing test flag stops the run.
The ordinary pinned `accepted`, `public_snapshot`, `rules`, P1 hashes and requests
are still required. The CLI additionally requires `fact_equivalence.py` in its
verified `code_files`, alongside `automatic_review.py`.

`equivalence_proof` is another owner-only `{path, sha256}` input, containing:

- `old_observed`: the full original accepted observation, not a reconstructed
  summary with fields removed;
- `old_public_snapshot`: `{path, sha256}` for the original public JSON bytes;
- `accepted_file_sha256`: the exact existing acceptance file hash;
- `acceptance_entry_sha256`: the canonical digest of the entire existing entry.

These are references to existing evidence, **not a new approval receipt**.
The old fingerprint is recomputed from the unchanged old observation and old
public SHA. Exactly one matching accepted entry with its existing reviewer,
timestamp and record ID is required. Missing, changed or unreadable pinned inputs
HOLD/stop; the operator must not synthesize an approval to make them pass.

## Bounded equivalence

Current inspection still uses existing registry identity/history/current-index,
ACL, P1 PIN, receipt, CAS and literal full-PDF-page checks. Every observed field
except the two index observation identifiers (`revision`, `index_sha256`) must
have the same canonical digest as the accepted observation. This includes the
policy branch, year, relation, amount/unit, limitations, original SHA, document
ID, URL, receipt audit, quotation, full context/footnotes and page positions.

Both old and current registry revisions must exist in the checked event chain.
Both index byte versions are read back and parsed by the existing index adapter.
The target listing, literal href, ordinal position, classification, headings,
context, year and multiplicity must be identical. Explicit source hold/reject
still HOLD. Different index bytes are accepted only when the old bytes ending in
`</div>` are unchanged and one or more new, distinct, exact official HTTPS PDF
bare links have been appended immediately before that closing tag. Unknown HTML,
attributes, relocation, duplicates, heading/paragraph changes or other edits
HOLD. This intentionally does not support general real-world DOM migrations.

Public JSON projection is limited to the existing Kyoto top-level schema.
The only excluded differences are whitespace in **other policies' headlines**.
All other policy data, target headline, budgets, totals, keys, ordering and shared
metadata remain in the digest. A new wording, unknown schema or other budget
change HOLD. No semantic inference or AI confidence is used.

No source decision is carried forward: a pending row after index change remains
pending and cannot generate a source acquisition proposal. Equivalence mode
returns only UNCHANGED or HOLD; even a matching AUTO_VERIFIED rule cannot execute
in this mode. Strict mode's existing AUTO_VERIFIED logic is unchanged.

## Audit and idempotency

The returned `continuations` contains old accepted fingerprint, acceptance-entry
SHA, proof-manifest SHA, old/new public SHA, old/new index SHA/revision and
canonical fact/public/listing hashes. It explicitly grants neither source
registration nor publication. It is a machine continuation proof, not approval.
UNCHANGED does not write a candidate or journal file. Repeating the same input
returns the same proof with zero new review records. Existing HOLD dedup is used.

## Validation and remaining gate

Tests reuse the socket-blocked synthetic PDF/receipt fixtures. They cover
same-input, headline whitespace, index append, budgets/unknown schema, facts,
pages/footnotes, original/receipt, missing/tampered acceptance/snapshot, ACL/PIN,
foreign CAS, source hold, default strict behavior and unchanged publication
permissions. Fixture ACL success is mocked; rejection is injected. This is not a
new Windows ACL/private-original acceptance test. No private acceptance, receipt,
snapshot or path is committed.

No CI pass authorizes deployment. Applying this experimental mode to real
accepted facts, widening the projection, Ready status, merging, or operation
requires separate PM approval. PR #87/#89/#93 and their accepted artifacts remain
unchanged. Unknown dependency relationships remain HOLD.

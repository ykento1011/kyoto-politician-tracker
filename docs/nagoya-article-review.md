# Nagoya saved-article review connection

This is an offline library. It has no HTTP client, model call, scheduler,
publication interface or member-fact writer. Private originals and identities
must not be committed.

## Saved source -> review queue

- `inspect_index` reuses the successful official receipt and article DOM parser.
  It retains official council links, labels and positions. First observation is
  a baseline of links marked `change="baseline-only"`, not proof that those
  articles were newly published. It never produces `added` for that first index.
  Later observations report additions, removals and changed labels. Removal
  never means a member departure. Navigation/DOM movement alone creates no
  semantic review. Source versions are retained even when semantic links agree.
- Discovery never authorizes acquisition. Every link candidate has
  `fetch_authorized=false`. Known historical articles can be supplied explicitly;
  do not invent an edge from a current index to an unlinked historical article.
- `inspect_article` consumes explicit extracted candidates, not an automatic
  semantic verdict. It validates receipt/SHA/DOM, event domain, stable ID
  existence and date literals, and puts every candidate on hold. Exact date
  interpretation and person identity remain review responsibilities. Unknown
  years stay null. Role endings use committee/union scopes, never membership.
- Source identity is URL + raw SHA. Reprocessing it creates zero queue entries;
  the latest-observation head still advances when an older original recurs, so
  subsequent diffs use the actual preceding observation. Supplying a different
  interpretation for the same source is rejected rather
  than silently replacing a prior review. A future explicit amendment workflow
  would need separate authorization. Changed originals get separate versions.
- `record_review` appends hash-bound named human review records. Accepted-for-
  projection requires confirmed identity/meaning and explicit bounded dates.
  It never creates facts. A PM hold directive can be recorded as such; it is
  not independent identity approval. Prior records are immutable.
- `save_queue` stores its own CAS and head outside repositories and rejects
  symlinks/junctions. Expected-head checking, an exclusive lock, append-only
  records and atomic replacement preserve the last normal head on failure.
  Orphan CAS/temp files may remain after failure; stop for private recovery,
  never silently retry or delete evidence. This queue cannot overwrite the
  member-history head.

## Group-event meaning and future projection

A candidate carries `domain=group`, `action=leave|join`, the group name,
person-ID candidate, raw/receipt binding, position, literal date, possible ISO
date, observation timestamp and hold reasons.

A leave event ends a group relationship, not city-council membership. It is not
a new group name and does not imply unaffiliated membership. A join event is
separate. The existing group fact stores a group value over
`effective_on..confirmed_through`; it cannot directly represent a leave action.

Before any projection, a named reviewer must confirm person identity,
source meaning and dates, select the exact relationship and justify the
bounded interval. Never invent a prior start, infer an empty interval between
leave and join, or extend affiliation to the observation date. Keep the
reviewed leave event in the event review record; project only independently
supported group intervals via existing `add_reviewed_fact`. Membership/role/
alias domains remain separate. No projection executor is added here.

## Weekly contract proposal — disabled

| Exact fixed URL | Purpose |
|---|---|
| https://www.city.nagoya.jp/shikai/about/1030778/1030799.html | Roster/faction observations |
| https://www.city.nagoya.jp/shikai/about/1030633/index.html | Chair/vice-chair observations |
| https://www.city.nagoya.jp/shikai/about/1030778/1030796.html | Steering committee |
| https://www.city.nagoya.jp/shikai/about/1030778/1030797.html | Standing committees |
| https://www.city.nagoya.jp/shikai/about/1030778/1030798.html | Special committees |
| https://www.city.nagoya.jp/shikai/kouhou/1030998/index.html | Newsletter/edition discovery |
| https://www.city.nagoya.jp/shikai/kouhou/1031662/index.html | Session-summary discovery |

Weekly, at most seven fixed GETs plus one **previously approved exact detail
URL**, eight attempts and 8MiB total. Each response has a separate 2MiB bound,
10-second deadline, TLS verification, no redirect or retry, and >=1.2s interval.
Eight times 2MiB is not permitted: track total received bytes independently,
and reserve the full per-response allowance before each request; stop if it
would exceed the 8MiB budget. Header limits and bounded body/deadline checks
must both be enforced by a future acquisition runner, not this offline library.

A detail request requires saved official href/DOM/raw SHA, PM approval of the
exact URL and document ID, code/contract SHA binding, one-use run ID and fixed
private storage. Newly discovered links stay pending; never follow them during
the same run without this approval. PDF size/type changes require fresh scope.
Same SHA creates zero repeated reviews. Failed acquisition/structure/processing
preserves the prior normal head and records failure separately.

Do not filter articles by a recent effective-date window. Late articles can
describe old events. Retain a pending frontier with first/last observation and
last reviewed versions; fairly revisit approved historical edition indexes
within the same one-detail allowance. One detail per week implies backlog:
report age/unvisited sources, never claim complete detection. Historical issue
discovery through intermediate indexes remains unproven. The three committee
pages still need initial structural acceptance.

These seven sources do not guarantee discovery of resignation, death, loss of
seat or by-election. Dedicated council/election-commission notices and effective
dates remain required. Faction mismatch and unconfirmed speaker caches stay held.

## Next gate

This implementation enables offline private review, not a scheduled monitor.
Before a limited weekly GO: accept exact sources/layouts and observation
coverage, implement and review the bounded acquisition runner/persistent
discovery frontier, pin its executable contract and private save location, and
assign review responsibility/backlog handling. Registration, public writes and
automatic membership determination remain NO-GO. Existing Kyoto/policy monitors
are unaffected.

Run only the new regression file:
`python -B -m unittest discover -s tests -p test_nagoya_article_review.py`.
Tests use synthetic documents, block sockets/subprocesses, and mark replacement
originals as test versions. Real-data evidence stays in private storage.

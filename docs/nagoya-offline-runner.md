# Nagoya acquisition runner: offline preparation only

`nagoya_offline_runner.py` has **no live HTTP adapter**. `run_offline` accepts
only the exact `SyntheticTransport` class and fixtures; sockets/custom transports
are rejected. No CLI, scheduler registration, publication or facts projection
is added. Simulated receipts explicitly say `simulated=true`; replaying saved
originals is not a fresh observation.

## Contract and limits

Reuse PR #70's receipt/DOM validation, review queue and private CAS/head.
Each run binds its exact plan, source SHA/receipt, document IDs, reviewer/recovery
roles, private root, runner SHA and dependency SHAs. All three enable switches
(network, scheduler, publication) must be false. Unknown layouts, absent
approval, wrong source SHA, extra URLs and stale heads fail before fixture calls.

Fixed seven official sources:

| URL | Purpose |
|---|---|
| https://www.city.nagoya.jp/shikai/about/1030778/1030799.html | Roster/faction observation |
| https://www.city.nagoya.jp/shikai/about/1030633/index.html | Chair/vice-chair |
| https://www.city.nagoya.jp/shikai/about/1030778/1030796.html | Steering committee |
| https://www.city.nagoya.jp/shikai/about/1030778/1030797.html | Standing committees |
| https://www.city.nagoya.jp/shikai/about/1030778/1030798.html | Special committees |
| https://www.city.nagoya.jp/shikai/kouhou/1030998/index.html | Newsletter editions/articles |
| https://www.city.nagoya.jp/shikai/kouhou/1031662/index.html | Session summaries |

A plan may select a necessary subset, never exceed seven fixed pages and one
previously approved detail/historical-index URL. Detail permission must contain
an exact official href, DOM/line/literal, successful saved parent receipt and
source SHA. The runner checks that it resolves to the approved exact URL. Finding
a link or recording backlog never grants fetch permission. No invented IDs/URLs.

Maximum eight GET attempts, 8MiB accepted total, 2MiB per response, 10 seconds.
Each response is independently checked for length, completion, media type,
document ID, TLS flag, no redirect, no retry and elapsed time. The cumulative
budget reserves a full 2MiB before the next attempt: a plan may stop short of
eight calls even if previous bodies were small enough individually. An eighth
2MiB response is not permitted merely because the count is below eight.
Synthetic transport receives this exact constraints object; a future live
transport must enforce TLS and hard process/read deadlines in reality. Fixture
flags do not prove live HTTP guarantees. Minimum real request spacing >=1.2s
must also be implemented by the future live adapter; fixture replay never sleeps.

## Transaction, provenance and failure

Input normal state must match the expected persisted CAS. A one-use run ID is
reserved before any fixture request; the same ID never resumes automatically.
Each attempt is journaled before the call, preserving partial/unknown failures.
Successful original bytes have a separate raw CAS, SHA/readback and successful
receipt. A failed run preserves its journal and any uncommitted raw CAS; do not
delete evidence or call it a successful update. Failure accounting distinguishes
accepted bytes from observed/unknown response-body bytes.

All index versions, baseline-only/added/removed link reviews, page semantic
positions, explicit supplied event candidates, frontier and prepared run receipt
are staged in memory. A complete prepared receipt is read back before the one
normal queue head is atomically replaced. A crash can leave a prepared/orphan
receipt without a committed state: confirm that the normal state's `runs`
contains its run ID and that its CAS hash matches before calling it committed.
On acquisition/structure/save failure the old normal head remains. No source
version, old queue/review, person ID or member-history fact is replaced.

The existing index semantics keep first observations baseline-only and suppress
same-source duplicates, including a recurring old original. Non-index pages get
positioned document-review holds when semantic fields change; this is not
automatic event understanding. Explicit article event candidates still pass
the existing hash/position/domain/identity/date gates. This module never derives
dates, aliases, council resignations or group facts from an unreviewed page.

## Persistent frontier and reviews

The normal CAS contains:
- `frontier[url]`: first/last seen, last visited, processed raw SHAs, listing
  status per parent index, parent SHA/positions, fetch authorization always false.
- `pages`: last semantic snapshot hashes; full version snapshots keep positions.
- `versions/queue/reviews`: the existing immutable source and review history.
- `runs`: append-only prepared receipts belonging to committed normal states.

`backlog(state, as_of)` reports unvisited URLs and age since last visit (or first
discovery), oldest first. It is a planning list, not a fetch executor or a claim
of historical completeness. Old articles are never excluded by their effective
date. Approved historical indexes and known articles must share the one detail
allowance fairly; pending age and unvisited counts make delay visible.
`review_backlog` lists pending/held human reviews and age. Rejected/accepted-for-
projection records leave that worklist but do not update any facts.

## Operational responsibility proposal (not enabled)

- Codex A: mechanical receipt/SHA/structure checks, private queue preparation,
  budget/failure reporting; no independent person/meaning approval.
- Supervising PM: triage and independent person/role/effective-date/coverage
  acceptance, assign a human reviewer when necessary. Unassigned reviewer or
  insufficient dates/identity means hold. No time-based auto-acceptance.
- Codex A under PM recovery approval: preserve failed run and last normal CAS,
  inspect failure locally, verify head/raw/receipt/code/contract hashes, then
  create a **new** bounded run ID only after PM authorizes retry scope.
- Supervising PM: activation/restart/publication gates. Existing Kyoto and mayor
  policy monitors are not used or modified.

Pending work persists across weeks. Report counts, oldest hold, unvisited
sources and failures; PM prioritizes detail/historical slots. A rejection needs a
reason, a source-bound reference and named reviewer, never silent removal.
A prepared receipt or stale head is not permission to resume. Uncertain billing
is irrelevant here because model/API use is absent.

## Remaining live gates and bounded source proposals

Live monitoring remains NO-GO. This commit provides the offline runner contract
and fixture checks, not a network implementation. Before live use, a separately
reviewed adapter must enforce certificate validation, no redirects/retries,
one-use permits, actual byte/read/process deadlines and interval, then pin its
SHA and approved private store. PM must accept responsibility assignments,
source layouts, backlog coverage and recovery procedures before registration.

The three committee layouts remain **unconfirmed**. A possible separate source
acceptance proposal is exactly FIXED[2:5], at most three GETs/6MiB, each 2MiB/10s,
TLS/no redirect/no retry, private CAS and one-use approval. This proposal is
NO-GO until separately approved; it is not executed by this code.

Resignation/death/loss-of-seat/by-election dedicated official notice URLs are
still unknown. Do not guess or probe them. PM must first pin exact official
source(s) and an explicit small allowance. Historical-edition coverage remains
unknown; only already saved exact hrefs can form a future bounded proposal.
Current-faction mismatch, eight unconfirmed SSP lines and twenty held article
events stay held. Seven sources cannot guarantee all departures or elections.

## Verification

`python -B -m unittest discover -s tests -p test_nagoya_offline_runner.py`

Synthetic tests block sockets/subprocesses and cover request/independent size
budgets, receipt/document/source/permission binding, TLS/redirect/retry/deadline
failure, duplicate SHA, semantic amendment holds, frontier age, review worklists,
stale/one-use run IDs, transaction failure and forbidden public storage.
Synthetic amendments are not real observations. Private originals and IDs
must not enter GitHub.

# Offline continuous review pilot (Issue #80)

`python -B -m mayor_updates.continuous --runtime PRIVATE_RUNTIME --cycle YYYY-MM-DD`

This entry has **no HTTP mode**, scheduler or publisher. Use a new owner-only
state directory, separate from live weekly state and CAS. The runtime reuses
`weekly.py`'s pinned config/baseline/rules/code-files contract; pin both weekly.py
and continuous.py, set network_enabled=false, and explicitly choose
p1_city_capable=true only for an approved city-capable P1 copy. Original P1 pins
remain unchanged. Its Kyoto manifest is derived from the existing three exact
registered HTML sources, not a new source list. The original weekly entry is unchanged.

## Repeated observations and review

Each date consumes `cycles/YYYY-MM-DD` once, even on failure. This is an offline
processing reservation, **not HTTP permission**. It never removes a one-shot URL
reservation. Existing CAS versions/attempts are read by the same monitor,
index adapter and `operations.run_trial`; no parallel CAS is implemented.
Every cycle retains source metadata, last good SHA, observation date, change
type and unverified policy association. The two budget indexes expose attachment
changes without reading attachments; school progress evidence is routed to P-03.
An index does not prove a linked budget amount or assign all 14 policies.

`weekly.commit_success` atomically advances the monitor and dedup pointer only
after successful review artifacts. A failed source or corrupt original keeps the
previous pointer. The consumed cycle and failure receipt remain for inspection.
Later cycles can process separately approved new observations; failures are never
retried automatically. Unchanged content produces no duplicate review.

`review_decision(state_root, review_key, 'hold'|'rejected', reviewer, reason)`
appends private human decisions, binding each to the saved review SHA. It cannot
approve, publish, or erase history. `published_revision` remains null. Review
status in source observations is unverified; subsequent human decisions are in
review_events. Absence of a decision means pending, not acceptance.

## Publication and future live scheduling gates

Reviewers must confirm exact original/page, policy submeasure, fiscal year,
account, and fact type (proposal, budget resolution, commencement, actual delivery).
Only separately approved changes go to a limited public PR. A source change alone
never changes a policy stage or a budget. P-04/P-14 receipts belong to the independent
Issue #78 one-shot scope; their reservations and the three-source manifest are untouched.

Live periodic acquisition remains **unimplemented and disabled in this entry**.
A future permission must pin city + source series + calendar period + communication
budget before any GET; reserve before the worker, consume uncertain outcomes,
and allow a later period only under that live policy. Reusing the offline cycle
directory as network authorization or deleting one-shot markers is prohibited.
Kyoto's existing upper bound remains 3 HTML GET / 6 MiB (not the separate PDF phase).
Owner-managed persistent Windows state, explicit timezone, bounded no-retry
workers, failure notification and log-retention acceptance remain deployment gates.

Other cities require reviewed manifest registrations, saved-source identity tests
and adapter evidence. Empty registrations fail closed. The cycle/review logic is
city-keyed, but the CLI's runtime validation still uses the Kyoto pilot contract;
other-city periodic execution is not claimed as complete.

## Evidence limits

Tests use the three registered URLs with synthetic originals and modifications.
They cover baseline -> unchanged -> index/progress changes -> failure -> recovery,
repeated-cycle rejection, human hold/rejection, corrupt SHA, and public data immutability.
Actual stored originals can establish repeatability but, without two real versions,
cannot establish successful detection of a real historical replacement.

# Offline member history: Nagoya pilot

This adds no HTTP client, scraper execution, model call, publication path or
scheduled job. Production JSON and the existing Kyoto monitors are unchanged.

## Existing components reused

- Saved Nagoya master and SSP cache; no regeneration.
- NFKC/whitespace name normalization used by the existing master scraper.
  Kanji variants, similar names and name changes are not silently equated.
- Existing successful GET receipt fields, content SHA and private CAS convention.
- `kyoto_private_paths.private_storage` for storage outside a checkout and without
  symlinks/junctions. Its existing environment variable is `KYOTO_PRIVATE_ROOT`;
  this pilot uses a separate private subdirectory, never the Kyoto history head.
- The Kyoto fail-closed/partial-hold policy. A matched member does not certify
  official speaker role, agenda boundaries, summaries or evaluation reasoning.

## Public official references

- [Council newsletter 186, initial 68 members](https://www.city.nagoya.jp/shikai/kouhou/1030998/1030999/1031060/1031110/1031118.html)
  records the 2023-04-09 election and a four-year term ending 2027-04-11.
  The normal term is organized as 2023-04-12 through 2027-04-11; the start is
  derived from that term statement, not a verbatim start date or proof of every
  individual's tenure. The July 2023 edition and website modification date are
  different metadata.
- [Faction roster](https://www.city.nagoya.jp/shikai/about/1030778/1030799.html)
  is an observation of a dated roster, not an individual resignation/election
  notice or a guarantee covering all earlier/later meetings.

The original responses, receipts, immutable local person registry and real-data
results stay private. CI contains only synthetic people and documents.

## Data and review contract

`seed_registry` accepts explicitly assigned persistent local person IDs once.
These IDs are not official identifiers and the seed master does not prove
identity or tenure. Later snapshots never regenerate IDs from names.
`register_person` appends an explicitly reviewed new identity (e.g. a by-election);
it cannot replace or reuse an existing person ID.

`nagoya_roster_evidence.parse_roster` reads the two saved HTML formats and retains
original spelling, DOM/line positions and roster grouping. Section totals and
68-member structure are checked. A changed layout/count is held for review;
it is not converted to departures. Faction-office labels are not chamber or
committee offices. The current faction page does not supply electoral districts.

`evidence` binds bytes to a successful official GET receipt.
`add_observation` preserves each source SHA, observation timestamp and document
date. Name/district matching yields only candidate person IDs. Unknown, duplicate
or ambiguous mappings are held. Field differences, including name/label format
differences, are review candidates with no inferred effective date.
Same source SHA emits no second snapshot/review. Missing rows never end tenure.
Missing document dates or malformed inputs stop without replacing normal state.
`record_failure` records the hold/failure without changing successful history.

`add_reviewed_fact` requires a source SHA, matching original DOM/line/literal,
named review reference and explicit effective date plus confirmed-through date.
The reviewer must establish the meaning and person identity; the software only
validates the evidence binding. No accepted facts are inferred from roster text.
Separate domains are membership, group, role and alias:
- Membership end reasons: resignation, retirement, loss of seat, death, term end.
  An explicit new-member start may cite an election or by-election.
- Role end is separate, scoped to chamber, committee, union or faction.
  Role resignation is not an accepted membership-end reason.
- Multiple dated name slots support formal names and aliases without changing ID.
- Bounded confirmation never proves coverage after its confirmed-through date.
  Contradictory same-date facts are held; no arbitrary winner is selected.

`resolve_speaker` uses reviewed aliases AND membership at the actual meeting
date. It returns a stable ID only for a unique confirmed member; otherwise hold.
Old questions, public statements, scores and retired members are never deleted.
`at_date` exposes the separate group/role history for the same date.

`save_private` creates immutable content-addressed state versions and atomically
switches a separate history pointer with an expected-head check and exclusive
lock. Prior snapshots/reviews/facts and registry entries must remain prefixes.
Failed saves preserve the previous head; unreachable CAS versions may remain
for recovery. No automatic destructive cleanup exists.

## Start-date correction and limits

Nagoya's wrapper default is corrected from 2023-05-01 to 2023-04-12.
The shared index function compares only the year. Both dates therefore select
the same 2023-and-later index years; this fix does not prove April meetings were
missing or add a day-level filter to the legacy scraper. Do not run it to test
this change. Kyoto's term is unchanged. Exact official meeting-day eligibility
and individual tenure remain independent gates.

## Verification

`python -B -m unittest discover -s tests -p "test_member_history.py"`

Synthetic tests cover departures, by-elections, group/role/name changes,
homonyms, failed acquisition/save, duplicate SHA/events, dated speaker lookup,
CAS tampering, source positions, saved HTML structure and the isolated legacy
year-only index transform. No real notices or local paths are in tests.

## Weekly monitoring proposal — NOT enabled

Begin with the two approved Nagoya URLs above. Before adding official departure,
election or council-office notices, PM must pin their exact official URLs and
review source scope. Weekly collection must use a separately approved GET/POST
allowlist, request/byte/deadline limits, TLS, no retry/redirect, immutable receipt
and CAS, and failure stops. A changed SHA triggers offline candidate review;
unchanged SHA skips repeated review. No automatic membership/event approval.
All-city rollout needs each city's actual term, dated roster and notice format.
No monitor is registered or changed by this PR. Enablement and any merge are
separate PM decisions.


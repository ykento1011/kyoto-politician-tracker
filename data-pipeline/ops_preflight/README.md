# P0-OPS: five-city offline statement preflight (Draft; not deployed)

A deliberately small, **standard-library-only** adapter for `statements_summary` in
Kyoto, Osaka, Kobe, Nagoya, and Yokohama. It reuses the *existing* published
`{city}_statements_summary.json` filename contract as a read-only baseline.
It does **not** run `run_update.py`, a producer, a scraper, cloud APIs, Git, or a
publish step; it does not connect to private D1R or modify public JSON.

## Input contract

The baseline is an existing JSON array named `{city}_statements_summary.json`.
A candidate is a **new, privately prepared** JSON envelope, not a web response:

```json
{
  "schema_version": 1,
  "city_code": "kyoto",
  "feature": "statements_summary",
  "source_status": "synthetic",
  "baseline_sha256": "<SHA-256 of exact baseline bytes>",
  "records": [
    {
      "id": "fixture-1",
      "meeting_id": "sample",
      "source_url": "https://example.invalid/kyoto/fixture-1",
      "summary": "synthetic only"
    }
  ],
  "origin_city_by_id": {"fixture-1": "kyoto"}
}
```

`origin_city_by_id` must contain exactly the **added/changed** record IDs and
explicit originating city. Entries absent from both the baseline and candidate
are detected as deletion and **rejected**. Existing record fields cannot be
silently dropped. A wrong city, duplicate ID, missing origin URL, stale baseline,
malformed JSON (including NaN/Infinity), or missing origin declaration
blocks before stage creation. The saved Kyoto records use `source_url`;
Osaka, Kobe, Nagoya, and Yokohama use `official_url`. A record must
have a syntactically valid HTTP(S) URL in each present origin URL field.
This is a compatibility rule, **not** a claim that any link proves the
statement's provenance or current truth.
The origin declaration is supplied by the candidate producer and **is not
independent proof of city/source authenticity**. An untagged record's origin
cannot be certified here. No real source rights or freshness are inferred.

## Field-level diagnostic and deterministic bulk stop

The preflight now computes **aggregate counts by top-level field name** on
**changed existing IDs only**. Each name records the number of rows with a
`value_changed`, `field_added`, or `field_removed` occurrence. Added and
deleted *records* stay in `counts` and are not treated as changed fields.
Nested JSON objects are compared as single field values; key order and JSON
whitespace do not constitute changes, but changes of type (e.g. boolean to
integer) do. Values, record IDs, names, and statement text are **not** printed
by the common inspect CLI. Detailed per-ID diffs remain private in
`diff.json` if and only if staging is allowed.

A candidate with **every baseline record changed** (nonempty baseline and
`updated == baseline_count`) produces
`all_existing_rows_changed: true`,
`review_state: bulk_change_requires_pm_review`, and
`stage_permitted: false`. Inspection is read-only and may return field
counts; `stage` refuses **before creating a private folder**, even if
origin-city declarations are present. This is an exact-coverage trigger,
not an arbitrary percentage/volume threshold or a finding that the
underlying minutes actually changed. Partial changes continue to be machine
stageable only if all existing preflight guards pass; any stage still has
`publish_permitted: false` and requires PM review.

When a candidate is structurally comparable but fails an origin declaration,
deletion, city-tag or existing-field-loss guard, the CLI returns
`status: blocked` plus sanitized `diagnostics` containing only record
counts and field-name counts. The rejected candidate is never staged.
Missing source URLs, bad JSON, duplicates and stale baselines still block
fail-closed; they need not produce a field breakdown. No producer, source
authenticity judgment, or publication step is added.

## Offline operation

```bash
python -B data-pipeline/ops_preflight/preflight.py inspect \
  --city kyoto \
  --baseline /read-only-snapshots/kyoto_statements_summary.json \
  --candidate /private-input/kyoto-candidate.json

python -B data-pipeline/ops_preflight/preflight.py stage \
  --city kyoto \
  --baseline /read-only-snapshots/kyoto_statements_summary.json \
  --candidate /private-input/kyoto-candidate.json \
  --private-root /outside-repository/owner-only-stage

python -B -m unittest discover -s data-pipeline/ops_preflight -p 'test_*.py' -v
```

The private stage directory must pre-exist **outside the repository** and be
owner-only (POSIX mode `0700`; Windows ACL must be independently assessed).
Symlink/reparse ancestors are rejected; this is a local accident-prevention
guard, not a security guarantee against a malicious concurrently writing user.
Each stage is exclusive and never overwrites another. The final marker is
`validated.json` with `machine_validated_pending_pm_review` and
`publish_permitted:false`; interrupted folders have **no valid marker**.
Files `candidate.json`, `diff.json`, and `manifest.json` are written *only*
inside the private root. The final validation marker is first flushed and
synced as `validated.json.pending` and then atomically renamed to
`validated.json`; a failed marker write cannot leave a final marker.
`inspect` writes nothing.

## Known limits / next authorization gate

- Synthetic failure tests and a **read-only, no-change saved-public-data**
  contract test cover the five existing `{city}_statements_summary.json` files.
  The latter reports `saved_unverified` and does not update public JSON.
  Actual five-city source fidelity, site freshness, source licensing, stable ID
  crosswalk, and producer-to-consumer correctness are **not verified**. This adapter is not an update engine or independent source verifier.
- The pre-existing D1R Kyoto implementation remains separately accepted and
  **unconnected**; this change neither rewrites nor executes it.
- PM must review city-scoped diffs and evidence before any publication request.
  New primary-source acquisition, API usage, live connection, any public JSON
  change, `main` merge, Cloudflare deployment, and rollback need separate gates.

# Kyoto saved-data handoff to five-city offline preflight

**Scope:** one already-saved Kyoto statements-summary JSON array only. No new
source retrieval, API/AI invocation, generator, legacy update task, Git operation,
public JSON overwrite, or deployment. Its producer is deliberately unconnected
to the five-city preflight. This handoff does **not** certify source authenticity, rights,
timeliness, or any changed statement. The adapter has no publish or stage mode.

The existing published Kyoto JSON can serve as a *read-only baseline*.
A separately saved Kyoto copy must have the same filename,
kyoto_statements_summary.json, and the existing id and source_url fields.
Only previously saved local data may be supplied; never point this tool at a
live URL, crawler, or update producer.

## Prepare private candidate

Use a pre-existing owner-only directory outside the repository (mode 0700 on
POSIX; Windows ACL needs separate independent review):

    python -B data-pipeline/ops_preflight/kyoto_saved_adapter.py \
      --baseline /read-only-snapshots/kyoto_statements_summary.json \
      --saved /existing-saved-copy/kyoto_statements_summary.json \
      --private-root /outside-repo/owner-only-stage

The command places one unique private kyoto-saved-UUID/candidate.json only
after existing preflight.inspect() accepts it. Interrupted or rejected output
is cleaned up; previous accepted private candidates survive. It reports the
saved bytes' SHA-256, aggregate record counts and changed **field-name counts**.
It does **not** print individual IDs or statement values, create validated.json,
or mutate the baseline. Detailed per-ID diffs remain private in code, never in
CLI output.

## Changed/new row origin declaration is mandatory

Added/changed record IDs are *not* silently attributed to Kyoto. By default
the adapter rejects them. Supply a separate, explicitly reviewed local JSON
object of **exact** touched IDs to source-city claims, for example:

    {"existing-record-123": "kyoto", "new-record-456": "kyoto"}

Use --origin-declarations /private/kyoto-origins.json to supply the declaration.
Missing/extra IDs, wrong city, deletion, dropped fields, invalid source URL,
malformed JSON and baseline SHA mismatch block preparation. Origin declarations
are **self-reported**, NOT independent proof of the source or city. Even if
the check succeeds, the report remains source_status=saved_unverified,
source_authenticity=unverified and publish_permitted=false. If **every baseline
record has changed**, the common preflight reports
review_state=bulk_change_requires_pm_review and stage_permitted=false, even
with all origin declarations supplied.

## Next separate gate

After PM review of the diff and saved-file identity, use the accepted
preflight CLI to re-inspect that specific private candidate if required:

    python -B data-pipeline/ops_preflight/preflight.py inspect \
      --city kyoto \
      --baseline /read-only-snapshots/kyoto_statements_summary.json \
      --candidate /outside-repo/owner-only-stage/kyoto-saved-UUID/candidate.json

The accepted preflight stage operation is separate and can run only when
stage_permitted=true; successful staging creates only
machine_validated_pending_pm_review. No automatic publish path is provided.

Test with:

    python -B -m unittest discover -s data-pipeline/ops_preflight -p 'test_kyoto_saved_adapter.py' -v

The suite tests synthetic add/update, fail-closed cases, interrupted output,
and a read-only committed Kyoto saved-array handoff with a complete checkout.
Other four cities, newly acquired sources, live producer connections,
main merges and production publication are not authorized by this change.

## One Kyoto producer/input path — static contract review, not execution

The **current legacy code path**, as read in main on 2026-11-14, is:

1. `data-pipeline/sagebase_crawled_data.json` (previous local cache;
   original official URL, rights and timestamp not independently verified)
   → `data-pipeline/batch_analyze_council.py`
   (Gemini API; **not authorized to run**) →
   `data-pipeline/analyzed_kyoto_politicians_term.json` (local saved analysis).
2. `data-pipeline/generate_static_data.py` reads that local analysis,
   filters `analysis.is_evaluated`, and produces a compact
   `statements_summary.json`. **Its current hard-coded output is
   `frontend/public/data/statements_summary.json`**, not the current
   `frontend/public/data/kyoto_statements_summary.json` contract. It also
   **writes directly into public data**; executing it is forbidden.
3. The approved offline consumer only accepts an **already-saved**
   `kyoto_statements_summary.json` (read-only baseline plus separate
   saved candidate) → `kyoto_saved_adapter.prepare` →
   `preflight.inspect` → PM assessment. This existing adapter does not
   generate candidate data from `analyzed_kyoto_politicians_term.json`.

## Private-only projection bridge (isolated prototype, NOT deployed)

The new `kyoto_private_projection.py` is the *one* offline connection from
an **already-saved** `analyzed_kyoto_politicians_term.json` to
`kyoto_statements_summary.json` → accepted
`kyoto_saved_adapter.prepare` → common `preflight.inspect`.
It does not run the legacy generator or batch producer.

For the reviewed legacy generator at Git blob
`3b361296ead93c092e60acfa453b7de4a4074e22`, it extracts **only**
`clean_speaker_name` and `refine_category` plus their literal keyword
tables from the source syntax tree; `generate_summary` and module top-level
statements are never executed. The same compact output field mapping,
`is_evaluated` selection, 120-character snippet, scores and date sort are
mirrored, while any unreviewed change of the generator source hash blocks.
The legacy writer is unchanged and remains prohibited to execute.

Private input requirements are deliberately stricter than the old writer:
every evaluated record must have an **explicit stable string ID** (the old
`meeting_id_sequence_number` fallback is NOT used), meeting/sequence/date,
title/speaker/text, a valid source URL, nonempty summary, and four reviewed
scores. Missing/duplicate ID, empty URL, unsupported JSON/NaN, invalid score,
wrong embedded city, or any baseline/preflight mismatch blocks. The reader
uses the accepted offline 32-MiB file limit; exceeding it blocks rather than
silently truncating. The generator's `source_url` is structural only, **not**
independent source evidence or a verified official URL.

Run only with a **documented, previously authorized saved analysis** and an
already-existing owner-only directory outside the repository:

    python -B data-pipeline/ops_preflight/kyoto_private_projection.py \
      --saved-analysis /authorized-saved/analyzed_kyoto_politicians_term.json \
      --baseline /read-only-snapshots/kyoto_statements_summary.json \
      --private-root /outside-repo/owner-only-stage \
      --origin-declarations /authorized-private/kyoto-origins.json

If no independently supported per-ID origin declarations exist, omit the
flag: the common preflight **must reject** new/changed records. Never infer
origin from filenames or the input's city. The script writes one unique,
owner-only private `kyoto_statements_summary.json` and, only if preflight
accepts, one distinct private `candidate.json`. It **never calls stage**,
issues no validation marker, and never changes the baseline or any public
JSON. Rejected attempts remove the provisional projected file. The CLI emits
aggregate counts, field names and SHA-256 only; never statement bodies, names,
private path locations, record IDs or per-ID evidence.

Synthetic end-to-end and negative tests:

    python -B -m unittest discover -s data-pipeline/ops_preflight -p 'test_*.py' -v

**Real-input connection: still NO-GO.** The existence, correct version,
authorized usage, rights and freshness of the saved analysis have not been
established. The input file is not part of the committed GitHub repository;
do not create a dummy "real" input or run the paid producer to obtain it.
Independent source/origin evidence, ID mapping and Windows ACL are separate
gates. If a new official acquisition is unavoidable, representative approval
must state **one official URL + source version, rights, maximum requests/cost,
private destination, and stop conditions** before *any* network operation.
The old `run_update.py`, its `--dry-run`, SSP, Gemini and any publication
remain forbidden. The new prototype is not an update engine.

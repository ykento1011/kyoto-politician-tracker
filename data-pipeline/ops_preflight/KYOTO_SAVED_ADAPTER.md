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

**Proposed single future bridge (not yet approved):** confirm that a saved,
authorized, timestamped `analyzed_kyoto_politicians_term.json` already
exists and has a documented source version. Extract or adapt the compact
projection in a **separate no-write-to-public offline function** so its output
goes only to an owner-only external `kyoto_statements_summary.json`; then
handoff to the already-approved adapter, with independent per-ID Kyoto origin
evidence. No live fetch, Gemini batch, or legacy `generate_static_data.py`
execution is needed or allowed in this cycle.

**Connection gate: NO-GO until verified.** The actual presence, permitted use
and freshness of the saved analysis; the missing private-only projection;
ID crosswalk; official-source URL/version; per-ID provenance; and the
public-filename incompatibility must be resolved before new real-input
connection. If a new origin acquisition is required, submit **one**
representative decision covering the official URL, exact source version,
rights, estimated attempts/cost cap, external private directory, and fail-closed
stopping rule. Do not infer authorization from a pre-existing URL field or
GitHub commit. The `run_update.py` command, `--dry-run`, SSP and paid APIs
remain prohibited.

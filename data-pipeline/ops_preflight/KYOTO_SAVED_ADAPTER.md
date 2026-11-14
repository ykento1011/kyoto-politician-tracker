# Kyoto saved-data handoff to five-city offline preflight

**Scope:** one already-saved Kyoto statements-summary JSON array only. No new
source retrieval, API/AI invocation, generator, legacy update task, Git operation,
public JSON overwrite, or deployment. No changes to the accepted five-city
preflight. This handoff does **not** certify source authenticity, rights,
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
saved bytes' SHA-256, preflight counts, added IDs and changed fields. It does
not print the raw input records, create validated.json, or mutate the baseline.

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
source_authenticity=unverified, review_state=pending_pm_review and
publish_permitted=false.

## Next separate gate

After PM review of the diff and saved-file identity, use the accepted
preflight CLI to re-inspect that specific private candidate if required:

    python -B data-pipeline/ops_preflight/preflight.py inspect \
      --city kyoto \
      --baseline /read-only-snapshots/kyoto_statements_summary.json \
      --candidate /outside-repo/owner-only-stage/kyoto-saved-UUID/candidate.json

The accepted preflight stage operation is separate and still creates only
machine_validated_pending_pm_review. No automatic publish path is provided.

Test with:

    python -B -m unittest discover -s data-pipeline/ops_preflight -p 'test_kyoto_saved_adapter.py' -v

The suite tests synthetic add/update, fail-closed cases, interrupted output,
and a read-only committed Kyoto saved-array handoff with a complete checkout.
Other four cities, newly acquired sources, live producer connections,
main merges and production publication are not authorized by this change.

City identity candidate (offline only)

The live external P1 package and PINS in the default bridge are unchanged.
city_identity.patch is against the exact hashes in city_identity.json.
prepare_copy(approved_root, NEW_directory) copies package code/schema only,
applies that patch offline, and verifies the candidate output hashes.
Do not apply to the original P1 directory or replace any running task pins.

The neutral DiscoveredDocument type is re-exported by the Kyoto adapter.
Only city-aware calls opt into the candidate hashes via city_capable=True.
Legacy calls keep the old P1 hash requirements and Kyoto URL/document IDs.

Offline validation:
  Set MAYOR_P1_APPROVED_ROOT to the approved external data-pipeline directory.
  python -B -m unittest discover -s data-pipeline/tests -p "test_city*.py"
No original documents or private CAS are test fixtures. HTTP responses are fake.
The P1 integration tests require the external code: skipped tests are NOT proof
of city compatibility. Future CI must provision that exact immutable code as a
private dependency before accepting the complete integration suite.

Before any live Kobe trial (not authorized for today):
- accept the scheduled Kyoto integrated run, then review PR/CI and candidate pins;
- provision a separate owner-only private root, CAS, state and run directory;
- create city_binding.json with city_code, scope_sha256 (city_scope.signature),
  absolute snapshot_root and state_root; pin its raw SHA in private storage config;
- pin the exact city profile and candidate P1 files. Public profile stays disabled;
- pass --scope-file and --storage-file to the existing acquire entry.
A durable per-URL reservation in the private state forbids retrying this trial.
Use max one HTML and one PDF, 2MiB each, TLS, ten-second deadline, no redirects.
Never connect Kobe to the Kyoto weekly task or publish policy changes automatically.

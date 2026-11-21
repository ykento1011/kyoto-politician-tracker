# Private publication observation receipt

After separately authorized publication, explicitly supply a saved public-side
JSON observation and its publication metadata:

```text
python -B -m mayor_updates publication-receipt --baseline BASE.json --packet PACKET.json --approval APPROVAL.json --published-data OBSERVED.json --commit FULL_40_HEX_COMMIT --deployed-url https://example.test/data.json --published-at 2026-11-21T10:00:00+09:00 --output EXISTING_PRIVATE_DIRECTORY
```

Run from `data-pipeline`. The existing approval function reconstructs the reviewed
result; the existing receipt function compares it to the supplied observation.
No candidate file, development commit, or current clock is substituted. The
caller must supply an actual observation, not relabel a candidate as observed.
The CLI cannot independently establish that a supplied file came from production.

Only `publication_receipt_PRIVATE.json` is written using the existing private,
exclusive-create writer. It includes SHA-256 hashes of the exact four parsed
inputs and an explicit consistency-only verification scope.
The result comparison uses the existing canonical JSON digest (sorted keys),
so formatting/key-order differences can match. Input hashes describe raw bytes;
they do not establish candidate/public raw-byte equality. The receipt records
this distinction in `comparison_method`.

Missing/invalid
inputs, mismatches, duplicate output, and write failures cause a nonzero exit;
they do not authorize publication or retry. A partial file after an I/O failure
is failure evidence, not a successful receipt, and is not overwritten.

No HTTP, Git, Cloudflare, P1 initialization, scheduling, or public write is
performed by this command. It does not verify deployment or grant publication
approval. Use a pre-provisioned private output directory outside Git/public trees.

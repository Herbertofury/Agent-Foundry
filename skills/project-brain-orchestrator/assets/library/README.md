# Artifact Library Manager

The library manager uses an organized local vault at `AGENTS_LIBRARY_HOME` or `<AGENTS_MEMORY_HOME>/library`.

## Layout

```text
00-Inbox/
10-Projects/<project-id-name>/
  00-Current/
  10-Versions/
  20-Research/
  30-Assets/
  40-Bundles/
  50-Memory/
  60-Prompts/
  70-Reports/
  90-Archive/
20-Shared/
30-Reference/
40-Exports/
80-Archive/
90-Quarantine/
cleanup-plans/
```

`library-catalog.json` is the machine-readable source of truth. `LIBRARY-DATABASE.md` is its human-readable mirror. `library-events.jsonl` preserves an append-only history.

Use `tools/library_manager.py init`, then ingest local files or import a JSON manifest created from ChatGPT Library search results. Record current Library usage from the Storage UI before relying on quota warnings. Cleanup plans quarantine exact-hash local duplicates and list external files for manual deletion. Permanent purge requires a separate explicit confirmation.

# DataMind Research Branch Scope

This branch is the implementation branch for the SIGMOD/VLDB/ICDE paper. It
does not attempt to turn every design idea in the paper into a production
feature. A mechanism belongs here only when it is part of the paper's central
claim and has a corresponding experiment.

## Paper claim and implementation boundary

The research claim is:

> DataMind is a profile-scoped multi-surface data plane that connects
> workspace materialization to agent serving through explicit surface
> contracts, auditable writes, and versioned publication.

The minimum implementation required to support this claim is:

| Paper mechanism | Research implementation | Evidence in the paper |
|---|---|---|
| Surface contract | A typed manifest for each enabled surface: operations, schema, sources, revision, and evidence type | Section 3; manifest ablation in RQ1 |
| Auditable ingestion | Existing ledger extended with source checksum, surface, operation, revision, and receipt metadata | Section 3; replay and provenance in RQ3 |
| Candidate build | A build run records a private candidate descriptor and validation results; provider staging is optional and exposed in the evaluation | Section 3; build correctness in RQ2/RQ3 |
| Profile snapshot | A profile snapshot names the visible revision of each enabled surface | Section 3; update consistency in RQ3 |
| Atomic publication | A validated candidate becomes the current logical publication through one pointer update | Section 3; visibility delay and mixed-snapshot rate in RQ3 |
| Snapshot-pinned reads | Request context carries a snapshot id; evidence reports snapshot and surface revision | Section 3; stale/mixed-read metrics in RQ3 |
| Failure classification | Empty results, unavailable backends, and failed builds have distinct structured outcomes | Section 3; small fault matrix in RQ4 |

Current status: the branch now has typed manifests, persistent candidate
records, validation, atomic snapshot-pointer publication, request snapshot
metadata, receipt integration, and a fail-closed read guard that blocks reads
for surfaces touched by an active candidate. Physical snapshot
adapters for each backend and reads that open historical artifacts are still
future work; until they land, the paper must describe snapshots as logical
publication records with explicit failure on stale providers, rather than
claim full backend time travel.

The implementation does **not** need, before the paper submission:

- a distributed transaction coordinator;
- a cost-based planner or a new LLM planning model;
- every remote database or graph backend;
- production-grade multi-process scheduling;
- a full automatic recovery policy for every parser and backend;
- additional document formats beyond the formats needed by the workload.

## RQ-to-code mapping

| RQ | Question | Required code | Main measurements |
|---|---|---|---|
| RQ1 | Does surface-aware serving improve quality and efficiency? | Existing multi-surface tools, typed manifests, structured evidence | Answer, evidence, route F1, irrelevant/invalid calls, tokens, latency |
| RQ2 | When does multi-surface materialization amortize its cost? | Existing workspace ingestion plus build-run accounting | Build time, calls, storage, coverage, provenance, quality-cost curve |
| RQ3 | Do receipts and snapshots preserve update correctness? | Ledger integration, candidate build, snapshot publication, pinned reads | Duplicate writes, stale reads, mixed snapshots, visibility delay, isolation |
| RQ4 | Can the system avoid untraceable answers under representative faults? | Structured failure outcomes, local parser fallback, old-snapshot fallback where valid | Completion, auditable answer, recovery time, false fallback |

RQ4 remains a compact robustness experiment. It is not a promise that DataMind
automatically repairs every backend failure.

## Required code fixes before experiments

1. Give `build_start`, `build_freeze`, `build_export`, and
   `surface_ingest_path` explicit lifecycle metadata so StoreAgent receipt
   wrapping cannot reject them.
2. Add the manifest, revision, and snapshot contracts in `datamind/core`.
3. Make the build service create and validate candidate descriptors before
   publication; document provider-level staging separately.
4. Add snapshot selection to `RequestContext` and include it in read evidence.
5. Keep the current product behavior available when snapshot mode is disabled,
   so the branch has a clean baseline for ablation.

Each new mechanism must have a focused unit test and one end-to-end test. The
paper text should cite only behavior covered by those tests and the reported
experiments.

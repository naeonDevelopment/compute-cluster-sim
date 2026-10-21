# compute-cluster-sim

An independent, original, open-source-intended Python reference implementation
for synthetic compute-cluster capacity, scheduling, failure, energy and economic
experiments. It has no relationship to an operator, marketplace, token or
proprietary project. This is a bounded discrete-event model, not a full validated
data-center digital twin. No novelty, hardware accuracy or performance claim.

**Source: IMPLEMENTED_UNVERIFIED. Tests: NOT_RUN. Runner enrollment: UNMEASURED.**
Tests, schemas, analytical expectations and CI are new judge surfaces **HELD**
for independent review. No product code, tests or builds were executed locally.

Python >=3.11, no runtime dependencies. The source-tree CLI is
`PYTHONPATH=src python3 -m compute_cluster_sim examples/single-node.json`.
This is a command for the qualified fleet only; do not run it locally under the
current [agent contract](agent/contract.md). Packaging metadata uses setuptools
as a build-time dependency; no build or installation has been performed.

The CLI accepts a JSON file or `-` for stdin and emits versioned JSON to stdout.
It exits **0** for a complete run without findings, **1** for scenario findings
(rejection, unfinished work, missed deadlines, infeasible idle, event budget) or
an invariant failure, and **2** for malformed/unsupported input, I/O or internal
failure. Invariant/malformed/internal failures emit an error object on stderr;
normal and event-budget run reports go to stdout. Argument errors exit 2 with
argparse text; `--help` exits 0 without a simulation. Findings are experimental
outcomes, not necessarily software defects.

Read [architecture and dimensional contract](docs/ARCHITECTURE.md),
[analytical experiments](docs/EXPERIMENTS.md), [research context](docs/RESEARCH.md),
[limitations](docs/LIMITATIONS.md), [roadmap](docs/ROADMAP.md), and the
[improvement register](registers/IMPROVEMENTS.csv). Versioned
[input](schemas/scenario-v1.schema.json) and [output](schemas/run-v1.schema.json)
schemas describe the interfaces; the parser enforces additional semantic bounds.

Release 0.2.0 adds causal current-state scheduling with default priority FIFO
and explicit `"scheduler": "fit-first"`, per-node `reserved_slots` and
`reserved_memory` floors (default zero), and per-job `"checkpoint": "ideal-resume"`.
Restart remains the default. Ideal resume assumes zero checkpoint/restore cost;
it is an upper bound on retained progress, not realistic checkpoint performance.
Fit-first can starve large jobs and has no reservation or no-delay guarantee;
it is not EASY backfill. No future change tape is passed to policy selection.
Currently capacity- or power-infeasible jobs stay queued.

The CLI optionally writes completed synthetic service with
`--run-id synthetic-run-1 --export-jsonl NEW_FILE`. The file must not already
exist; stdout still contains the run report. See the [export contract](docs/SERVICE-EXPORT.md)
and [standalone schema](schemas/synthetic-service-v1.schema.json). External
applications decide acceptance; the export makes no attestation, payment or
profitability claim. No unfinished service is exported.

The kernel retains heterogeneous resource kinds, one-node gang allocations,
priority preemption, recall/failure/recovery, exact work/energy accounting and
separate declared synthetic costs/payments. There is no invented owner workload.
Original baseline example outcomes are preserved. The manifest records the
model and policy versions; normalized scenario hashes now include new defaults.

The [named campaign](docs/CAMPAIGN.md) requires independent coordinator review
before manual owner-fleet execution. This worker neither dispatches nor deploys.

Original work: copyright 2026 Theo Georgiev (Naevum), [Apache-2.0](LICENSE).
See [COPYRIGHT](COPYRIGHT), [CONTRIBUTING](CONTRIBUTING.md), and
[SECURITY](SECURITY.md). Public sources are prior art, not validation of this code.

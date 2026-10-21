# Work-order evidence and exact changes

Work order: a995cfc577ee. Date: 2026-10-21. Source IMPLEMENTED_UNVERIFIED;
tests NOT_RUN; runner enrollment UNMEASURED; new judge surfaces HELD.
No full-roadmap completion, hardware accuracy, performance or CI success claim.

## Checks actually performed

- All 31 created text files inspected for trailing whitespace, CR characters
  and missing final newlines, including untracked files.
- Six Python files parsed with `ast.parse` as a static syntax/structure check.
  No product import, evaluation, execution, compilation/build or test run.
- Seven JSON files parsed for JSON syntax only. JSON Schema validation NOT_RUN.
- Relative Markdown links inspected for existing targets.
- Improvement register parsed as CSV: 12 rows, consistent columns.
- Workflow text inspected for workflow_dispatch, literal
  `[self-hosted, naevum-vps-amd64]`, and no push/pull_request triggers.
  No YAML parser, workflow execution or runner qualification performed.
- Structure inspected: no .manna files. `git diff --check` returned exit 0;
  because files were new/untracked, the explicit all-file whitespace scan is
  the substantive local whitespace evidence.

Requested acceptance identifier: `compute-cluster-sim.whitespace`. External
acceptance verdict is unmeasured; these inspections do not self-approve a judge.
Tests and analytical expectations are authored witnesses only. Public primary
reference pages were consulted for bounded citations. LICENSE reproduces the
canonical official Apache-2.0 text from
https://www.apache.org/licenses/LICENSE-2.0.txt (web-rendered text, not a measured
byte-for-byte download). The shell download attempt failed DNS resolution; no
upstream source code was copied. No product code, tests, builds, CI, enrollment,
commits, remotes, push, merge, deployment, spending or model-worker calls ran.
Synapse worker dispatch stayed held under this work order's no-model-call rule.

## Exact created files

All changes are additions; the worktree initially contained only its .git pointer.

```text
.github/workflows/ci.yml
.gitignore
AGENTS.md
CLAUDE.md
CONTRIBUTING.md
COPYRIGHT
LICENSE
README.md
SECURITY.md
agent/contract.md
docs/ARCHITECTURE.md
docs/EXPERIMENTS.md
docs/LIMITATIONS.md
docs/RESEARCH.md
docs/ROADMAP.md
docs/VERIFICATION.md
examples/analytical-expectations.json
examples/heterogeneous-queue.json
examples/power-limited.json
examples/recall-capacity.json
examples/single-node.json
pyproject.toml
registers/IMPROVEMENTS.csv
schemas/run-v1.schema.json
schemas/scenario-v1.schema.json
src/compute_cluster_sim/__init__.py
src/compute_cluster_sim/__main__.py
src/compute_cluster_sim/cli.py
src/compute_cluster_sim/model.py
src/compute_cluster_sim/simulator.py
tests/test_witnesses.py
```

## Integrated release work order bd62548f87cc

The preceding sections describe historical work order a995cfc577ee. Their NOT_RUN
and UNMEASURED statuses remain historical; they are not results of this release.
Current release: 0.2.0. Campaign: apocryph-compute-20261021. Source status remains
IMPLEMENTED_UNVERIFIED. Product execution/tests/builds here: NOT_RUN. Independent
source/checker review: HELD. Fleet execution/enrollment: UNMEASURED in this order.

Restored candidate `4925c7e4f0fc2fe31751b6b49fed8e53f8f11d99` with `git archive`
from this repository's own objects into the empty-main worktree. A second archive
stream comparison confirmed all 31 original files remain present and LICENSE
and COPYRIGHT are byte-for-byte unchanged. No sibling paths or worktrees were
used. Existing source and notices were retained, with bounded release amendments.

Changes: current-snapshot FIFO/fit-first selection and rejection, removal of
future-capacity feasibility rejection, explicit owner floors and floor changes,
optional per-job ideal resume, attempt identity, versioned synthetic-service
JSONL export and validator/schema, analytical witnesses/examples, updated scope
and science register, and the narrow contract/manual CI campaign amendment.
The four original example scenarios and their analytical values are unchanged.
Their behavior has not been executed in this order. The old permanent-power-
rejection witness was intentionally corrected to queued censoring semantics.

Static inspections performed (no product imports/evaluation/execution):

- All 42 text files scanned, including untracked files: no trailing whitespace,
  carriage returns or missing final newlines.
- Nine Python files parsed with `ast.parse`. The test sources contain 42 test
  methods (28 baseline and 14 release); this is an authored count, not a pass count.
- Twelve JSON files and one JSONL example record parsed for syntax; 15 improvement
  register rows parsed as CSV with consistent columns. Three schemas checked
  for required-field/property consistency. Semantic schema validation NOT_RUN.
- Workflow parsed with the preinstalled YAML parser. Inspected manual-only trigger,
  exact selected route, default amd64, campaign/review gates, pinned checkout and
  environment-mediated shell inputs. Five shell blocks passed `bash -n` syntax
  inspection; no commands from those blocks ran. No runner qualification claim.
- Relative Markdown links checked for existing targets. Selection and rejection
  AST interfaces inspected: current nodes/jobs/allocations only, no change tape.
- `git diff --check` returned exit 0. Files are untracked against empty main, so
  the explicit all-file whitespace inspection is the substantive local evidence.

Acceptance `compute-cluster-sim.whitespace`: external verdict UNMEASURED. These
static inspections neither execute nor self-approve the authored judges. Source
and checker changes require independent coordinator review of the exact committed
revision before the owner-fleet campaign. The worker performed no product run,
test, build, installation, CI dispatch, enrollment, commit, push or deployment.
Vagus owns the commit. No Synapse worker was recursively launched.

Current runner-label documentation was consulted only as public citation material;
see CAMPAIGN.md. The installed route constraint came from the owner, not a fleet
probe. Unsupported items and absent measurements are listed in LIMITATIONS.md:
realistic checkpoints, future reservations/EASY, per-tenant sharing, cross-node
execution/power preemption, dynamic topology/site caps, physical network/thermal
models, calibrated profiles, commerce acceptance/attestation/payment, deployment
integration and full digital-twin validation remain outside this release.

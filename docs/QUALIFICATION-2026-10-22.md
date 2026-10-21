# Qualification evidence recorded 2026-10-22

Campaign: `apocryph-compute-20261021`. Frozen source:
`fdc95501bad0426eeb36921eea211d5857b7944c`.
This note records coordinator-observed evidence supplied by the owner; the worker
did not execute product code, inspect remote runs or qualify hardware.

## Own-workflow failure before product execution

The authorized operator reviewed the immutable candidate and pushed it to a new
private qualification branch. GitHub rejected `workflow_dispatch` with HTTP422:
`.github/workflows/ci.yml` lines 47–49 used `runner.environment`, `runner.os` and
`runner.arch` in unsupported job-level `env`. Associated invalid-workflow run
`39675935038` failed before any product test. This is a workflow validation
failure, neither a product test failure nor a product test pass.

## Separate frozen-source fleet evidence

The coordinator reports PASSED for 42 native unittest functions, eight
independently calculated work/energy scenarios, and deliberate incorrect-oracle
rejection on the qualified owner Linux ARM64 / Python 3.12.3 fleet. Execution
used an independent control-plane workflow for the exact frozen source above.
This evidence does not erase the own-workflow parse failure or test the
forthcoming workflow correction. It is not worker execution, hardware
calibration, a performance claim or general model validation.

## Correction status

The owner reports that the source repository is now public by explicit
instruction and its draft `ci.yml` is disabled pending this reviewed correction.
No private repository URLs or data are included here.

Work order `b74c06bf4409` moves the three runner context bindings into the trusted
gate step's `env`. The shell gate and product/checker content remain unchanged.
The [context availability table](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)
permits `runner` in step-level `env`; job-level `github` and `inputs` remain valid.
Missing or incorrect runner values still fail the existing equality checks;
no passing defaults are added.

Corrected own-workflow execution and this revision's source/behavior tests:
NOT_RUN until a valid owner-fleet run. Vagus receipt: HELD for judge edits,
separate from later external CI acceptance. The operator handles final review,
workflow state and own-workflow execution. Static checks are recorded in
[VERIFICATION.md](VERIFICATION.md); they confer no execution or acceptance pass.

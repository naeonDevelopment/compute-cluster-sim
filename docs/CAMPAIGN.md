# Manual owner-fleet campaign

Campaign: `apocryph-compute-20261021`. Source/checker review: HELD. Worker product
execution: NOT_RUN. The [canonical amendment](../agent/contract.md) records the
owner's authorization for independent coordinator review followed by owner-fleet
CI. It does not let the author self-approve, execute locally or dispatch a run.

The independent coordinator reviews the exact source commit, parser/policy/event
semantics, analytical values, tests, schemas and workflow, and records that review
outside any author-generated PASS claim. Then the coordinator can manually select
the named campaign, an explicit route, and set owner_qualified_runner and
judge_surfaces_reviewed after the required qualification/review. False or missing
approvals, unknown campaigns or unknown routes cannot admit a job. No route
fallback, automatic push/PR trigger, installation or artifact upload exists.

Default route: `naevum-vps-amd64`. Explicit alternative for this campaign only:
`ci-linux-arm64`. `runs-on` uses exactly the selected label. The installed ARC
scale set declares only `ci-linux-arm64`; self-hosted/Linux labels are not assumed.
Current [GitHub runner scale-set documentation](https://docs.github.com/en/actions/concepts/runners/runner-scale-sets)
supports multiple configured labels (ARC 0.14.0 onward), and the
[workflow guide](https://docs.github.com/en/actions/how-tos/manage-runners/use-actions-runner-controller/use-arc-in-a-workflow)
describes configuring them. That capability does not create labels on this installation.
Installation facts are owner-supplied constraints, not measurements by this worker.

A trusted shell gate runs before checkout/product execution. It verifies the
campaign, review booleans, runner.environment=self-hosted, runner.os=Linux,
`uname -s`, and route-specific runner.arch plus `uname -m` (X64/x86_64 or
ARM64/aarch64). Context/input values enter shell through environment variables,
never expression interpolation into shell text. The checkout remains pinned to
`11bd71901bbe5b1630ceea73d27597364c9af683`, with credentials persistence disabled.
The job compares checked-out HEAD to github.sha and logs the exact commit,
route/environment/architecture, Python path/version/platform and Git version.
Preinstalled Python >=3.11 is required. No pip install is needed.

Execution includes baseline and release unittest discovery, every scenario under
examples (the analytical-expectations oracle is not a scenario), JSONL CLI export
smoke and the standalone example record. Logs are evidence for that exact run;
they do not rewrite the historical NOT_RUN status or establish hardware accuracy.
The source manifest labels remain release provenance, not live CI attestation.
There is no simulator deployment target or worker remote/fleet effect in this order.

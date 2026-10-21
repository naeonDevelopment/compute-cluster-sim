# Synthetic analytical witnesses

All expectations are hand-computed, ANALYTICAL_NOT_MEASURED, NOT_RUN and HELD
for independent review. No fleet, hardware or performance observation is implied.
The optional scalar prices are synthetic currency units.

| Example | Completion times (seconds) | Horizon energy (W*s) | Derivation |
| --- | --- | --- | --- |
| single-node | a=4 | 230 | 8/2=4; 35*4 + 15*6 |
| heterogeneous-queue | a=2, b=2, c=4 | 370 | CPU busy 4s, GPU busy 2s; baseline 25*10 + 20*(4+2) |
| recall-capacity | a=8, b=12 | 380 | baseline 15*12; one node busy 0..2 and 4..12: increment 20*10 |
| power-limited | a=2, b=4 | 330 | baseline 25*10; one busy node at a time, increment 20*4 |

The recall example starts two jobs. At t=1 slots fall from 2 to 1, restarting b
and losing 2 units. At t=2 recall restarts a and loses 4 units; recovery at t=4
allows a to finish at 8 and b at 12. Total executed work is 22 = 16 accepted
retained + 6 lost. Energy counts unavailable idle between t=2 and t=4.
The power example allows a single active node at 45 W, but two would draw 65 W.
All four example CLI exits are analytically expected to be 0.

`examples/analytical-expectations.json` is a partial oracle, deliberately not a
fabricated full output trace. `tests/test_witnesses.py` includes independent
expected completions, energy and accounting values; replay/reordered-input
comparisons supplement those values rather than replacing them. Witnesses cover
FIFO, incompatibility, gang slots, memory, priority preemption, nonpreemptibility,
recall/failure/recovery, rate increases/decreases, stale-completion prevention,
capacity reduction, future capacity, power queuing, infeasible idle, same-time
events, deadlines, empty intervals, fractional time, horizon/budget censoring,
malformed and duplicate input, unknown versus zero prices, and CLI exit policy.

Future experiment reports must include the exact scenario, canonical hash,
version, source revision, qualification/review record, backend/profile provenance
and uncertainty. Synthetic analytical agreement cannot establish hardware
accuracy. Comparative experiments need workload/profile evidence and sensitivity
analysis before drawing capacity or economic conclusions.

## Release 0.2.0 hand-computed cases (NOT_RUN)

| Example | Completion times | Horizon energy (W*s) | Derivation |
| --- | --- | --- | --- |
| ideal-resume | a=6 | 230 | rate 2, work 8; retain 4 before recall at 2; recover at 4; 4 remaining / 2; baseline 150 + 20*4 |
| owner-floor | a=2, b=4 | 230 | 2 total slots minus 1 protected; memory 8 minus 4; jobs serialize; baseline 150 + 20*4 |
| fit-first | running=4, head=8, tail=2 | 430 | CPU busy 8s, GPU busy 1s; baseline 25*10 + 20*9 |
| causal-growth | a=4 | 190 | 2-slot job waits until t=2 growth; 8/(2*2)=2s; baseline 150 + 20*2 |

Recall counterfactual: restart discards the first 4 units and completes at t=8,
executing 12 = 8 retained + 4 lost, with 270 W*s. Ideal resume completes at t=6,
executing 8 = 8 retained + 0 lost, with 230 W*s. These are independent arithmetic
oracles, not simulator-generated expectations or measured checkpoint savings.

`tests/test_release.py` compares shared observable prefixes with no change tape,
future growth and future recall through t=3, under both policies. The formerly
rejected oversized head must be queued without growth and start at t=5 with it.
Full-run manifests are excluded from prefix comparison because hashes bind the
whole input. Tests also cover aggregate slot and memory floors, full protection,
floor increase/decrease, invalid ordered floor/capacity states, forced shrink,
FIFO blocking versus fit-first, exact conservation at multiple censor horizons,
priority-resume with rational completion, and budget-stopped non-completion.

Export witnesses require useful completed work only, final-attempt binding,
stable order, round-trip validation, malformed/duplicate identities (including
multiple completing attempts for one job), bounded ratios, duplicate JSON keys,
exclusive output and no input overwrite. CLI smoke runs on the fleet only.
All these new judge surfaces remain HELD for independent coordinator review.

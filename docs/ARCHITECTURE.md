# Architecture: release 0.2.0, version-1 interfaces

Status: IMPLEMENTED_UNVERIFIED; behavioral witnesses NOT_RUN; judge review HELD.

The selected architecture is a small deterministic orchestration kernel with
versioned adapters to independently validated specialist backends. Only the
synthetic Python kernel exists today. Its interface is:

`Scenario -> simulator -> EventTrace / ResourceSamples / JobOutcome / EnergyLedger / CostLedger / RunManifest`

Those names correspond to the snake_case fields in the version-1 JSON report.
No specialist backend is installed or integrated. The policy interface accepts
immutable current nodes, queued jobs, running allocations, baseline power, power cap and the selected policy. It returns a
single placement plus victim IDs. It receives no Scenario, future arrivals,
change tape, horizon, remaining work or predicted completions. The engine alone
advances time and applies changes. No external effects, credentials or operational
network access belong in the policy interface.
Site-specific fixtures belong outside this generic OSS repository.

## Input boundary

`model.py` validates JSON into frozen typed dataclasses; `simulate` revalidates
directly constructed Scenario objects. Inputs are version 1 only. Unknown fields,
duplicate object keys, duplicate IDs within each namespace and dangling node
references are errors. Node, job and change IDs are stable ASCII identifiers
matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`. Resource kinds use the same syntax and
match exactly. CPU, GPU and native worker kinds have no conversion/equivalence.

Quantities are nonnegative JSON integers or strings such as `"3/2"` or `"3"`.
Decimal/exponent JSON numbers, floats, booleans-as-integers, NaN and Infinity are
rejected. Output quantities are always reduced `"numerator/denominator"` strings,
including `"0/1"`. Counts remain integers. A JSON null means unavailable or not
yet established, never a known zero. Deadlines use null for no declared deadline;
optional prices/payments must be omitted for unknown, or explicitly 0 for zero.

Bounds: 1 MiB UTF-8 input, 64 nodes, 512 jobs, 512 changes; identifiers <=64
characters; numeric strings <=32 characters, reduced denominator <=10^9, value
<=10^12; horizon >0 and <=10^6 seconds; priorities -10^6..10^6; max_events
1..20000 (default 20000). There is no plugin loading, eval, exec, subprocess,
shell command, dynamic import-by-configuration or random seed. Finite bounds
bound storage and operations; they are not measured latency/memory guarantees.
Highly composite exact arithmetic and maximal scenarios may be expensive.

Work, initial slots and rate must be positive. Memory and power may be zero;
active power must be >=idle power. Capacity changes may set slots or memory to
zero; rate zero is invalid (use availability=false to halt a node). Releases and
changes must lie in [0,horizon]. Deadlines may extend beyond the horizon but must
not precede release. Nodes may start unavailable. Node addition is unsupported;
unknown nodes and change reasons are rejected. Site cap, power and prices are
static in v1. Reasons are recall/failure/recovery/capacity/rate/reservation;
recall and failure require available=false, recovery requires available=true. Changes may include
several resource fields. No-op assignments are allowed; an empty change is not.

## Dimensions

| Quantity | Unit and meaning |
| --- | --- |
| release, deadline, horizon, event time | seconds from synthetic epoch 0 |
| work | synthetic service units, comparable only within a declared kind |
| rate | work units / second / reserved slot |
| slots | integer reserved service lanes on one node |
| memory | integer abstract memory units, used consistently within a scenario |
| idle_w, active_w, auxiliary_w, cap_w | watts; active_w is total busy-node draw |
| energy | W*s, with exactly 3,600,000 W*s per kWh |
| price_per_kwh | declared currency units / kWh |
| compute_hour_cost | declared currency units / active-node hour (3,600 s) |
| accepted_work_payment | declared flat currency units per completed job |

`currency` is a label, not an exchange-rate system or evidence of fiat receipts.
No inference tokens/s are derived from FLOPS. Rates and power are declared
synthetic assumptions, not hardware profiles or measurements. A job reserves all
its slots and memory on exactly one compatible node. Its rate is node.rate *
job.slots; there is no sharing, contention slowdown, topology or scaling curve.
Multiple jobs can occupy a node within both capacities. A busy node draws its
active_w once, irrespective of number of running jobs; an empty or unavailable
node draws idle_w. Every node's idle baseline plus auxiliary power remains in
the ledger throughout the simulated interval. Availability is not power-off.

## Ordering and scheduling

Each timestamp first accrues old-rate work and old-allocation energy up to that
time. It then processes:

1. All completions, ordered by job ID.
2. Resource changes, ordered by change ID, reconciling after **each** change.
3. Arrivals, ordered by job ID, rejecting only absent immutable resource kinds.
4. Unless at the horizon, scheduling and allocation invariants.

Thus completion at the exact recall/deadline/horizon time succeeds. Recall then
recovery at the same time can restart incomplete work; changes are sequential,
not a last-write-wins atomic patch. No positive-duration work starts at horizon.
Zero-duration scheduling transitions are recorded in the trace, not as energy
intervals. Input array order and JSON object key order do not affect results or
canonical manifest hash. IDs do affect tie-breaking; renaming is not invariant.
Equivalent normalized rational values hash identically.

Queued order: descending priority, then ascending original release, then ID.
Placement: ascending node ID. No future feasibility precheck exists. A job
with no matching kind is rejected at release (except release exactly at horizon,
which remains unfinished for baseline compatibility); node addition and kind
changes are unsupported. All capacity-, availability- or power-blocked jobs stay
queued, whether or not a future increase is declared. No completion is promised.

`"scheduler": "fifo"` is the default, retaining strict global head-of-line
blocking across kinds. `"scheduler": "fit-first"` scans the same ordered queue
and chooses the first currently placeable job, including the same priority
preemption rule. It is work-conserving for immediately feasible placements;
it does not evict unrelated nodes solely to free power. It may starve a large
or less favored job, holds no future reservation, and offers no no-delay
guarantee. This is not EASY backfill. Future resource tapes may differ without
changing decisions through their shared observation horizon (provided neither
run hits the event budget before that horizon). Final hashes and full-run results
naturally differ; intervals spanning observation must be clipped when comparing.

If a candidate cannot fit, it may evict lower-priority **preemptible** jobs on one
candidate node (lowest priority, latest release, greatest ID first). Evictions
occur only if that plan makes the candidate fit, including site cap. Cross-node
preemption solely to free facility power is not implemented. Nonpreemptible jobs
are protected from scheduler preemption, not forced failure/recall/capacity loss.
Forced reconciliation uses the same victim order, including nonpreemptible jobs.
If baseline idle+aux exceeds cap, report infeasible_idle, admit nothing, and
retain the full actual declared idle draw; never clamp or erase it.

Each node has nonnegative `reserved_slots` and `reserved_memory`, default zero,
which never count as external-job capacity: aggregate external usage plus the
floor must fit total capacity. Explicit engine changes can adjust either floor,
including simultaneously with capacity. Initial and every ordered change state
must satisfy floor <= total; a shrink below an unchanged floor is malformed,
even if a later same-time change would repair it. Raising a floor can forcibly
interrupt jobs using the normal victim order, regardless of preemptibility.
The parser checks tape consistency but discloses no future state to the policy.
Floors create no owner jobs, service, power increments, prices or payments.

Per-job `checkpoint` defaults to `whole-job-restart`: every interruption moves
retained progress to lost work. Explicit `ideal-resume` keeps all accumulated
progress on recall, failure, capacity/floor loss or priority preemption. This
assumes continuous, perfectly durable checkpointing and free restore/transfer;
zero overhead is an upper-bound progress assumption, not checkpoint performance
or an unconditional completion-time bound under competing schedules. Original
release/priority persist. A new attempt is counted on every start, including
resume; completion exports all retained work once under the final attempt.
There are no periodic checkpoints, checkpoint storage or migration costs.
Completion times are computed anew from current remaining work and rates after every batch. There is no persistent
completion heap and hence no stale completion record that can finish work twice.

## Accounting and termination

Normal runs include every positive interval from 0 through horizon, including
pre-arrival, empty, unavailable and post-completion intervals. Per-node idle and
incremental active W*s plus site auxiliary W*s sum exactly to interval power
integrals. Executed work = retained work + lost work, and requested work =
retained work + remaining work, for each job; restarts can make executed exceed
requested. A completed job has zero remaining work and one completion record.

The horizon censors unfinished work; it never supplies a fictitious completion.
Deadline success is completion <=deadline. An unfinished job at/past its deadline
with work remaining has missed it; before that its future deadline result is
null. Rejected jobs also receive the separate deadline assessment.

max_events bounds timestamp batches, including time zero and horizon. Exhaustion
is a finding with exit 1, horizon_reached=false and unfinished outcomes. It
stops at the next boundary **before processing that batch**, possibly with all
work accrued but no completion certified. Ledgers explicitly cover only
[0,simulated_until], not the requested horizon. This safety-aborted run is not a
complete horizon experiment; no energy or future work is invented after cutoff.
An invariant failure instead emits an error without a trustworthy run ledger.

Energy cost is total_kwh * price_per_kwh. Compute cost is summed busy-node seconds
/3600 * compute_hour_cost, separate from energy cost. Optional accepted-work
payments accrue only on completion, including late completions; they are not
proof of work, settlement, fiat receipts or an SLO acceptance mechanism. Payment
total is null if any job payment is unspecified; declared_payment_subtotal
always sums the known completed-job amounts. Compute cost null means price
unspecified. There is no profit forecast or silent zero substitution.

RunManifest includes canonical normalized scenario SHA-256, simulator version
0.2.0, model version `causal-capacity-v2`, scheduler selection,
policy version `1`, per-job checkpoint default, budget and coverage. Each outcome
also records resource kind, checkpoint mode and attempts. Version-1 schemas are
extended for these fields; old scenarios remain valid, but hashes change because
normalization now includes the defaults. The synthetic-service export has its
own independent version and schema (see SERVICE-EXPORT.md). RunManifest source/test
labels describe this reference release's verification status, not a live CI attestation. Resource
samples cover half-open intervals [start,end); traces explain boundary changes.

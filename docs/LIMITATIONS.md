# Limitations and evidence boundary

Source IMPLEMENTED_UNVERIFIED; tests NOT_RUN; CI enrollment UNMEASURED; new judge
surfaces HELD. Static inspection is not behavioral evidence. No performance,
scaling, hardware, thermal or economic accuracy measurements exist.

The kernel is a deterministic synthetic single-site reference. It has no network
or packet simulation, physical thermal/cooling solver, TEE verifier, hardware
probing, production scheduling authority, device equivalence, automatic profiles,
FLOPS-to-token conversion, real prices, carbon factors, wallets, keys, live
network access or settlement. It is not a full validated data-center digital twin.

Reservation-based backfill (including EASY), realistic periodic checkpointing,
checkpoint/restore overhead and durability failures, cross-node gang execution,
node addition, site power-cap changes, startup/shutdown power, partial-load power
curves, cross-node power preemption, topology, data movement, contention,
tenant-specific sharing or future reservations, heterogeneous memory units and
stochastic failures are OPEN. Owner floors are capacity protection only, with
no modeled owner activity. Fit-first gives no reservation or starvation guarantee.
Ideal resume is optional, zero-overhead and uncalibrated; baseline restart remains. Recall/failure are
explicit synthetic availability events; recovery restarts or ideally resumes work with no boot
latency. Busy power is a fixed node total and slot service scales linearly by
assumption. Memory is reserved capacity, not bandwidth. All nodes retain idle
draw while unavailable. Strict global FIFO may intentionally leave compatible
resources unused behind a blocked head. No accepted-job guarantees are made.

Budget exhaustion returns partial coverage with unfinished work, never a complete
horizon energy claim. Maximum-size input can be expensive despite finite bounds;
no timing or memory guarantee has been measured. JSON schemas are descriptive
judge surfaces: numeric ratios, cross-field conditions and reference uniqueness
require the Python validator. Output error envelopes are separate from run schema.

Build metadata names setuptools but the runtime uses only Python's standard
library. No build, dependency install, fleet enrollment, CI dispatch, commit,
remote, deployment or model-worker call was performed by this work order.

Synthetic export is a bounded interchange projection, not acceptance, signatures,
attestation, a payment rail, pricing or profitability. Its validator cannot prove
authenticity. A consumer must enforce cross-batch identity uniqueness and policy.
Exports reject completion ratios longer than 4096 characters and batches over
4 MiB; exotic exact-arithmetic runs may therefore be non-exportable. Python's
integer-string limits can also reject extreme arithmetic serialization; no
worst-case exact-arithmetic scalability claim is made. CLI exclusive creation
prevents overwrite but an I/O failure may leave an incomplete new file; consumers
must validate the whole batch. No external commerce harness is integrated here.

The named campaign has an authorized path to independent coordinator review and
owner-fleet CI; source/checker review is still HELD and local product execution
is NOT_RUN. No deployment artifact or target, fleet failover, automatic trigger,
artifact upload or install is provided. This release is not a validated digital twin.

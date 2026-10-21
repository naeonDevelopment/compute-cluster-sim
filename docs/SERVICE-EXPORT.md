# Synthetic completed-service interchange v1

Status: IMPLEMENTED_UNVERIFIED. Schema, validator and witnesses HELD for independent
review; product execution NOT_RUN. This public generic interface carries synthetic
outcomes to an external commerce harness. No external application is integrated.
The external application decides acceptance. Nothing here declares real service
acceptance, authenticity, attestation, payment, settlement or profitability.

On the reviewed owner fleet, append these CLI options to a scenario invocation:

```sh
PYTHONPATH=src python3 -m compute_cluster_sim examples/ideal-resume.json \
  --run-id experiment-1 --export-jsonl new-service.jsonl
```

Both options are required together. Export uses exclusive creation of a new UTF-8
file; `-` is not an export target. The normal run report stays on stdout and CLI
exit policy is unchanged. A run with findings may still export its completed jobs;
late completion is still completion, never a statement of deadline acceptance.
Unfinished, rejected, or budget-censored-but-not-completed jobs export no record.
Zero completed jobs produces an empty file. An I/O failure can leave a partial
new file and exit 2; consumers must reject invalid/incomplete input as appropriate.

| Field | Meaning and bound |
| --- | --- |
| version | Integer 1 |
| synthetic, completed | Both exactly true |
| scenario_id | 64 lowercase hex characters: normalized scenario SHA-256 from run manifest |
| run_id | Caller-assigned ASCII identifier, 1..64 characters; caller manages uniqueness |
| job_id | Scenario job ID, same identifier bounds |
| attempt | Start counter of final completing attempt, integer 1..10,240,000 |
| resource_kind | Exact scenario kind, same identifier bounds; kinds are incomparable |
| service_unit | Literal `synthetic_work`; not tokens, FLOPS, money or measured throughput |
| useful_work | Exact positive reduced fraction; equals retained/requested work at completion; <=10^12, <=32 characters, denominator <=10^9 |
| completion | Exact positive reduced fraction in synthetic seconds; <=10^6, <=4096 characters |

Identifiers match `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`. Fractions always include `/`,
including integer-valued quantities. Unknown fields, duplicate JSON object keys,
float/nonfinite values, duplicate job identities and malformed quantities are
errors. A batch is at most 512 records and 4 MiB. The standalone
[schema](../schemas/synthetic-service-v1.schema.json) describes each record;
`service_export.validate_records` / `load_jsonl` additionally enforce semantic
bounds, reduced fractions and batch identity uniqueness. `dumps_jsonl` emits
sorted keys, compact JSON and final newlines; records sort by
(scenario_id, run_id, job_id, attempt). Input record order is normalized.

The full service identity is (scenario_id, run_id, job_id, attempt). Only one
completion per (scenario_id, run_id, job_id) is allowed even if attempt differs.
An attempt is each start, including a zero-duration start or resumed start.
For ideal resume, all work retained across earlier attempts is credited **once**
to the completing attempt; those earlier attempts export nothing. Restart lost
work is never exported as useful service. Work units are comparable only within
the stated kind and synthetic scenario assumptions.

The [example record](../examples/synthetic-service-v1.jsonl) illustrates the
hand-calculated ideal-resume case: 8 useful units, attempt 2, completion t=6.
Its all-zero scenario_id is an explicit placeholder, not a measured hash. A real
export uses the actual normalized scenario hash; new release defaults change
that hash even when baseline numerical outcomes are unchanged.

Consumer responsibilities: persist idempotency across batches, bind the scenario
and caller-assigned run to its own experiment records, verify provenance if
needed, and apply its own acceptance and economic rules. The validator does not
verify a signature, reconstruct a run or prove that an arbitrary record came
from this simulator. The export omits the legacy declared synthetic payment
ledger entirely. It contains no owner workload or owner payment fiction.

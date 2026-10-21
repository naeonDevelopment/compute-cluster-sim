# Security and trust boundary

This is an unverified offline synthetic simulator, not an execution sandbox or
production control plane. Scenario JSON declares bounded data only. It cannot
select imports, commands, plugins, network endpoints, wallets or external effects.
The CLI reads its explicitly selected file/stdin and writes JSON to stdout or
errors to stderr. An explicit CLI --export-jsonl path may create a new synthetic
service file exclusively; scenario data cannot select a destination. Existing
files are never overwritten. Validate the whole export before consumption; a
failed write may leave a partial new file. Export identity is not authenticity.

Do not provide secrets, proprietary fixtures, live infrastructure details or
untrusted enormous inputs. Bounds limit input bytes, records, quantities and
event batches; exact arithmetic and large bounded cases can still consume
significant resources. No resource-use benchmark or adversarial qualification
has been performed. The self-hosted runner must be independently qualified and
isolated before execution; no enrollment or provisioning is part of this repo.

For a potential vulnerability, prepare a minimal synthetic reproducer and report
privately to the repository owner through an already-established owner channel.
No security contact address or response SLA has been established. Do not place
secrets in public issues. This document authorizes no message sending or network
action by agents. New security and acceptance judges remain HELD for review.

# Research context and future candidates

These public primary references are prior art and motivate future measurement.
They do not validate this implementation, confer a novelty claim or imply an
existing dependency, licence-qualified integration, benchmark result or hardware
profile. No upstream source code was copied. Public pages were consulted during
authoring; claims below are deliberately limited to each project's subject.

| Reference | Relevance and boundary |
| --- | --- |
| [SimGrid](https://simgrid.org/) | Distributed-system simulation; future cluster/network backend candidate. Its validation does not transfer through an unvalidated adapter. |
| [Batsim](https://batsim.readthedocs.io/en/latest/) | Batch-scheduling simulation built around SimGrid; future scheduling protocol candidate. Its documentation itself calls for experimental checks. |
| [Vidur, MLSys 2024](https://www.microsoft.com/en-us/research/publication/vidur-a-large-scale-simulation-framework-for-llm-inference/) | Profile-informed LLM inference simulation; motivates measured workload/model profiles rather than invented tokens/s. |
| [ASTRA-sim](https://astra-sim.github.io/astra-sim-docs/index.html) | Distributed ML simulation with communication/compute backends; future collective-communication candidate. |
| [SimAI](https://github.com/aliyun/SimAI) | Future AI communication/system simulation candidate; integration and licence compatibility remain unqualified. |
| [DistServe, OSDI 2024](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin) | Disaggregated prefill/decode serving and phase-specific latency objectives; motivates richer inference semantics outside this initial work-unit model. |
| [Dissecting the Carbon-SLO Tension in Geo-Distributed LLM Serving](https://arxiv.org/abs/2610.14571), submitted 10 October 2026 | Preprint motivating carbon/SLO tradeoff investigation with realistic serving dynamics. This project has no carbon or SLO-profile validation. |

The selected long-term design keeps orchestration small, with versioned adapters
and independently qualified backend inputs/outputs. Backend licence, maintenance,
version pinning, reproducibility, profile provenance and error budgets require
separate review. Citations are not endorsements or claims of endorsement.

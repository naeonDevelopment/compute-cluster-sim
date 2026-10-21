# Roadmap

The roadmap is incomplete by design. No item below is implied delivered by the
initial source implementation. See registers/IMPROVEMENTS.csv for held/open work.

1. Independent review of the contract, parser, event semantics, schemas,
   analytical witnesses and manual CI; qualify owner-controlled fleet enrollment.
2. Run the approved witnesses on that fleet; record source revision and evidence,
   investigate failures, then decide whether verification status can change.
3. Review and execute the causal FIFO/fit-first, owner-floor and ideal-resume
   release witnesses. Future reservation proofs, per-tenant policies and realistic
   checkpoint/transfer costs still need specification and measurements.
4. Define adapter protocols and qualify specialist versions, licences and
   reproducibility: SimGrid/Batsim, Vidur, ASTRA-sim/SimAI are candidates only.
5. Measure profile provenance and uncertainty outside this generic repository;
   qualify adapter conservation and compare against independently validated
   backends. Site-private fixtures must remain outside the OSS source tree.
6. Explore pure marketplace decision adapters and carbon/SLO policy experiments
   only after appropriate profile evidence. External effects remain impossible.

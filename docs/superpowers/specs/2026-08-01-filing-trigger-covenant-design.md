# FilingTriggerCovenant Design

## Outcome

Build a standalone, reusable GenLayer Intelligent Contract primitive that settles GEN-backed covenants when validators agree that an official SEC EDGAR filing semantically satisfies a locked trigger.

## Selected Approach

Use one contract. The primitive owns covenant storage, claim adjudication, ledger credit, withdrawals, and canonical views. A second consumer contract is not justified because no independent onchain enforcement boundary is needed for the standalone Intelligent Contracts track.

## Evidence Boundary

Evidence is limited to official `sec.gov/Archives/edgar/data/<cik>/<accession>/...` filings and SEC submission metadata. Requests must include a declared User-Agent because SEC blocks undeclared automated tools. Source failure, undeclared-tool blocks, invalid path, or oversized responses become `UNVERIFIABLE`, not a punitive verdict.

## Validator Meaning

The leader returns structured semantic fields: verdict enum, trigger enum, filing form/item coverage, event class, decisive fact IDs, and reason. The validator re-fetches and re-evaluates the evidence and compares the consensus-critical meaning fields. Rationale wording may differ.

## Consequence

`TRIGGERED` credits the beneficiary from locked covenant escrow and closes the covenant. `NOT_TRIGGERED` settles the claim bond to the sponsor and returns the covenant to active. `UNVERIFIABLE` applies no penalty and remains retryable or closable.

## Approval

User approved this design direction on 2026-08-01 with "duyet".


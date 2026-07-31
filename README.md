# FilingTriggerCovenant

Standalone GenLayer Intelligent Contract primitive for SEC filing-triggered covenants.

FilingTriggerCovenant lets a sponsor and beneficiary lock a filing trigger, company CIK, allowed EDGAR evidence, and GEN-backed payout. Validators independently fetch official SEC filings and agree on the meaning of the disclosure, not on JSON formatting. A finalized verdict directly controls covenant state and payout credit.

Status: Studionet verified for the Intelligent Contracts track. No frontend and no Vercel deployment are included or claimed.

## Submission Summary

- Title: `FilingTriggerCovenant`
- Category: `Intelligent Contracts`
- Evidence URL: https://github.com/duclucky/filing-trigger-covenant
- Repository: https://github.com/duclucky/filing-trigger-covenant
- Primary contract explorer: https://explorer-studio.genlayer.com/address/0xdAd8E295c35cdc9bC529074D0BbB3957C42C22eB
- CI: https://github.com/duclucky/filing-trigger-covenant/actions
- License: MIT
- Frontend: none

## Portal Description

Character count: 900

```text
FilingTriggerCovenant is a reusable GenLayer Intelligent Contract for SEC filing-triggered payouts. A sponsor funds GEN escrow and locks a beneficiary, CIK, EDGAR accession/form/item, trigger enum, payout, and claim bond. The beneficiary submits an official sec.gov EDGAR filing; validators independently fetch the filing and agree on the meaning of the disclosure, not JSON formatting. The primitive can power prediction-market resolution, DAO treasury covenants, credit agreements, earnouts, insurance-like riders, and grant milestones. A finalized TRIGGERED verdict credits payout plus claim bond to the beneficiary; NOT_TRIGGERED credits the bond to the sponsor; UNVERIFIABLE is retryable and non-penalizing. The repo includes contract source, docs, 39 direct tests, deployment parser tests, CI, sanitized Studionet evidence, and a deployed contract at 0xdAd8E295c35cdc9bC529074D0BbB3957C42C22eB.
```

## Deployment

- Network: `studionet`
- Contract address: `0xdAd8E295c35cdc9bC529074D0BbB3957C42C22eB`
- Deployment transaction: `0x65a96e193ec8154217ca777514a398834af0d34e4cfa92c158535a2f59a833c7`
- Deployed contract source commit: `8fa467af9b697de8bebb997565f7d50199b51f01`
- Evidence file: [`docs/evidence/studionet/deployment.json`](docs/evidence/studionet/deployment.json)

The current repository head may be newer than the deployed source commit because later commits only updated docs, CI, tooling, and license metadata. The deployed contract source itself is preserved in the public history.

## Worked Example

Real Studionet example:

- Covenant ID: `cyber-001`
- Locked CIK: `732026`
- Trigger: `MATERIAL_CYBER_INCIDENT`
- Allowed form/item: `8-K` / `Item 1.05`
- SEC filing accession: `000143774926009193`
- SEC filing URL: `https://www.sec.gov/Archives/edgar/data/732026/000143774926009193/trt20260320_8k.htm`
- Payout: `0.01 GEN`
- Claim bond: `0.001 GEN`

Real finalized output:

- Covenant status: `TRIGGERED`
- Claim verdict: `TRIGGERED`
- Consequence: `PAY_BENEFICIARY`
- Decisive facts: `ITEM_1_05,MATERIAL_EVENT,UNAUTHORIZED_ACCESS`
- Beneficiary credit before withdrawal: `0.011 GEN`
- Beneficiary credit after withdrawal: `0`
- Locked escrow, locked claim bonds, and withdrawable credits after withdrawal: `0`

## Consensus Design

The contract performs nondeterministic SEC filing evaluation inside `adjudicate_claim`. The leader fetches the locked EDGAR archive URL with a declared User-Agent, bounds the source text, asks for semantic filing judgment, and normalizes the output into fixed fields.

Validators independently rerun the same evidence function and compare consensus-critical meaning:

- verdict enum;
- event class;
- form and item coverage;
- source stage;
- consequence class;
- bounded decisive fact IDs.

Rationale text is stored for explainability only and is not consensus-critical.

## Public Interface

Write methods:

- `open_covenant(...)` payable
- `accept_covenant(covenant_id)`
- `open_claim(covenant_id, accession, filing_url)` payable
- `adjudicate_claim(covenant_id)`
- `close_claim(covenant_id)`
- `propose_close(covenant_id)`
- `accept_close(covenant_id)`
- `withdraw_credit(amount)`

View methods:

- `get_covenant(covenant_id)`
- `get_status(covenant_id)`
- `get_claim(covenant_id)`
- `get_credit(account)`
- `can_claim(covenant_id, accession)`
- `get_accounting()`

## Verification

- Local check: `npm run check`
- Current local result: 39 direct tests and 4 deployment parser tests passed.
- CI: https://github.com/duclucky/filing-trigger-covenant/actions
- Note: local `genvm-lint` was not on PATH during development; the check uses static contract assertions plus `gltest`.

## Documentation

- Full specification: [`docs/README.md`](docs/README.md)
- Studionet evidence: [`docs/evidence/studionet/deployment.json`](docs/evidence/studionet/deployment.json)
- Superseded deployment evidence archive: [`docs/evidence/studionet/archive/`](docs/evidence/studionet/archive/)

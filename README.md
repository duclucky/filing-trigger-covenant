# FilingTriggerCovenant

Standalone GenLayer Intelligent Contract primitive for SEC filing-triggered covenants.

FilingTriggerCovenant lets a sponsor and beneficiary lock a filing trigger, company CIK, allowed EDGAR evidence, and GEN-backed payout. Validators independently fetch official SEC filings and agree on the meaning of the disclosure, not on JSON formatting. A finalized verdict directly controls covenant state and payout credit.

Status: Studionet verified for the Intelligent Contracts track. No frontend and no Vercel deployment are included or claimed.

## Submission Summary

- Title: `FilingTriggerCovenant`
- Category: `Intelligent Contracts`
- Evidence URL: https://github.com/duclucky/filing-trigger-covenant
- Repository: https://github.com/duclucky/filing-trigger-covenant
- Primary contract explorer: https://explorer-studio.genlayer.com/address/0x658FF09d5edF1d5CA7dc232387F2c9a827C15d3a
- CI: https://github.com/duclucky/filing-trigger-covenant/actions
- License: MIT
- Frontend: none

## Portal Description

Character count: 884

```text
FilingTriggerCovenant is a reusable GenLayer Intelligent Contract for SEC filing-triggered payouts. A sponsor funds GEN escrow and locks beneficiary, CIK, EDGAR accession/form/item, activation/expiry dates, trigger enum, payout, and claim bond. The beneficiary submits an official sec.gov filing; validators fetch SEC submissions metadata to verify authoritative filingDate/form and independently fetch the filing to judge disclosure meaning. Out-of-window filings cannot trigger payout, expired inactive covenants can be closed by the sponsor to recover escrow, and rationale prose is non-critical. TRIGGERED credits payout plus bond to beneficiary; NOT_TRIGGERED credits bond to sponsor; UNVERIFIABLE refunds bond for retry. Repo includes source, 48 direct tests, 4 parser tests, CI, sanitized Studionet evidence, and deployed contract at 0x658FF09d5edF1d5CA7dc232387F2c9a827C15d3a.
```

## Deployment

- Network: `studionet`
- Contract address: `0x658FF09d5edF1d5CA7dc232387F2c9a827C15d3a`
- Deployment transaction: `0x6a0e25bd2be0df3b142c51d6e68bcde8ad15b2265d1cda57e573f21fde709f6b`
- Deployed contract source commit: `1a1d2de202b13a9f79f3ed2024f8ae854a3922e2`
- Evidence file: [`docs/evidence/studionet/deployment.json`](docs/evidence/studionet/deployment.json)

The deployed contract source is preserved in public history at the source commit above. Later commits may update only documentation and evidence.

## Worked Example

Real Studionet example:

- Covenant ID: `cyber-001`
- Locked CIK: `732026`
- Trigger: `MATERIAL_CYBER_INCIDENT`
- Allowed form/item: `8-K` / `Item 1.05`
- SEC filing accession: `000143774926009193`
- SEC authoritative filing date: `2026-03-20`
- SEC filing URL: `https://www.sec.gov/Archives/edgar/data/732026/000143774926009193/trt20260320_8k.htm`
- Payout: `0.01 GEN`
- Claim bond: `0.001 GEN`

Real finalized output:

- Covenant status: `TRIGGERED`
- Claim verdict: `TRIGGERED`
- Claim filing date: `2026-03-20`
- Consequence: `PAY_BENEFICIARY`
- Decisive facts: `ITEM_1_05,MATERIAL_EVENT,UNAUTHORIZED_ACCESS`
- Beneficiary credit before withdrawal: `0.011 GEN`
- Beneficiary credit after withdrawal: `0`
- Locked escrow, locked claim bonds, and withdrawable credits after withdrawal: `0`

Expired recovery example:

- Covenant ID: `expired-001`
- Activation/expiry: `2025-01-01` / `2025-12-31`
- `close_expired` transaction finalized with status `CLOSED`
- Sponsor credit before withdrawal: `0.002 GEN`
- Sponsor credit after withdrawal: `0`
- Locked escrow, locked claim bonds, and withdrawable credits after withdrawal: `0`

## Consensus Design

The contract performs nondeterministic SEC filing evaluation inside `adjudicate_claim`. The leader first fetches SEC submissions metadata with a declared User-Agent to verify the accession, authoritative `filingDate`, and form. Only filings whose official date is inside the covenant window can proceed to semantic judgment. The leader then fetches the locked EDGAR archive URL, bounds the source text, asks for semantic filing judgment, and normalizes the output into fixed fields.

Validators independently rerun the same evidence function and compare consensus-critical meaning:

- verdict enum;
- event class;
- form and item coverage;
- source stage;
- authoritative filing date;
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
- `close_expired(covenant_id)`
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
- Current local result: 48 direct tests and 4 deployment parser tests passed.
- CI: https://github.com/duclucky/filing-trigger-covenant/actions
- Note: local `genvm-lint` was not on PATH during development; the check uses static contract assertions plus `gltest`.

## Documentation

- Full specification: [`docs/README.md`](docs/README.md)
- Studionet evidence: [`docs/evidence/studionet/deployment.json`](docs/evidence/studionet/deployment.json)
- Superseded deployment evidence archive: [`docs/evidence/studionet/archive/`](docs/evidence/studionet/archive/)

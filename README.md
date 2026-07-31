# FilingTriggerCovenant

Standalone GenLayer Intelligent Contract primitive for SEC filing-triggered covenants.

Two parties lock a filing trigger, a company CIK, allowed EDGAR evidence, and a GEN-backed payout. Validators independently read official SEC filings and agree on the meaning of the disclosure, not on JSON formatting. A finalized verdict directly controls covenant state and payout credit.

Status: Studionet verified for the Intelligent Contracts track. No frontend and no Vercel deployment are included or claimed.

## Track

- Category: Intelligent Contracts
- Network target: studionet
- Frontend: none
- Repository: https://github.com/duclucky/filing-trigger-covenant

## Current Evidence

- Idea registry: `../docs/IDEA-REGISTRY.md`
- Full spec: `docs/README.md`
- Studionet contract: `0xdAd8E295c35cdc9bC529074D0BbB3957C42C22eB`
- Deployment tx: `0x65a96e193ec8154217ca777514a398834af0d34e4cfa92c158535a2f59a833c7`
- Lifecycle evidence: `docs/evidence/studionet/deployment.json`
- CI: https://github.com/duclucky/filing-trigger-covenant/actions
- Final canonical result: `TRIGGERED`, `PAY_BENEFICIARY`, beneficiary withdrawal finalized, accounting locked escrow/bonds/credits all `0`.
- Verification: `npm run check` passes 39 direct tests and 4 deployment parser tests. `genvm-lint` is not on PATH in this local environment; the check uses static contract assertions plus `gltest`.

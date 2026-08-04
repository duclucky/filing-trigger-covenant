# FilingTriggerCovenant Specification

## Identity

- Idea ID: IDEA-006
- Project name: FilingTriggerCovenant
- Project slug: filing-trigger-covenant
- Category: Intelligent Contracts
- Status: VALIDATED - IC TRACK / STUDIONET VERIFIED / NO FRONTEND
- Repository: https://github.com/duclucky/filing-trigger-covenant
- Target network: studionet
- Active Studionet contract: `0xCb0F6b3Ce4447D3EE05300e5E6595dA269f789F4`
- Source commit: `7490f10401087b07f44f459f5d6f2f0306a93855`

## One-sentence product hook

A filing trigger should pay only when official SEC disclosure means the locked event actually happened.

## Trust problem

- Decision that must not depend on one party: whether a public SEC filing satisfies a locked covenant trigger.
- Why database/ordinary EVM/backend LLM is insufficient: a database or ordinary EVM can store the filing URL and money, but cannot neutrally interpret disclosure language between adverse parties; a backend LLM makes one operator the judge.
- Value/rights/access at risk: native GEN escrow, beneficiary payout rights, sponsor claim-bond recovery, and canonical trigger status used by downstream integrations.

## Fingerprint

- Trust problem: sponsor and beneficiary need neutral interpretation of filing-trigger language.
- Actors/adversary: sponsor denies marginal triggers; beneficiary stretches ambiguous disclosure into a trigger.
- Evidence class: official SEC EDGAR archive filings and SEC submission metadata.
- Consensus question: whether the filing for the locked CIK/accession/form/item semantically satisfies the locked trigger enum.
- State machine: `DRAFT -> ACTIVE -> CLAIM_OPEN -> TRIGGERED/CLOSED`, with `NOT_TRIGGERED` returning to `ACTIVE` and `UNVERIFIABLE` retryable.
- Direct consequence: beneficiary payout credit, sponsor claim-bond credit, or non-penalizing unverifiable state.
- Reuse surface: filing-triggered markets, DAO treasuries, credit agreements, M&A earnouts, insurance-like riders, and grant milestones.

## Mandatory gate matrix

| Gate | PASS/FAIL | Evidence/reason |
| --- | --- | --- |
| Replacement | PASS | A backend can fetch SEC data but would remain a trusted judge over payout meaning. |
| Judgment | PASS | Validators independently inspect the SEC filing and judge semantic trigger satisfaction. |
| Evidence | PASS | EDGAR archive filings are public and authoritative; viability spike confirmed access with a declared User-Agent. |
| Equivalence | PASS | Critical fields are enum/status/CIK/accession/form/item/coverage/consequence, not free prose. |
| Consequence | PASS | Final verdict directly moves escrow ledger credit or claim-bond credit. |
| Adversarial | PASS | Sponsor and beneficiary have opposite incentives. |
| State model | PASS | Per-covenant/per-claim isolation, one active claim, attempt history, and double-settlement protection are required. |
| Reuse | PASS | Integrators can use write methods and canonical views without forking SEC adjudication. |
| Contract count | PASS | One contract owns the consequence; no consumer/pass-through guard is justified. |
| Differentiation | PASS | Differs from recall, interface, agent-access, and generic escrow patterns by SEC filing trigger semantics and covenant ledger consequence. |
| Claim-to-code | PASS | Claims map to contract methods, canonical views, 47 direct tests, 4 parser tests, and Studionet evidence. |
| Full lifecycle | PASS | Studionet lifecycle funded, accepted, claimed against a real SEC filing, verified authoritative filing date, finalized `TRIGGERED`, withdrew beneficiary credit, closed an expired covenant, returned sponsor escrow, and verified zero locked accounting. |
| Scope honesty | PASS | Contract source, tests, deployment, lifecycle evidence, public GitHub, and no-frontend scope are verified; portal submission remains a separate user action. |

## Actors, roles and incentives

| Actor | Permissions | Value at risk | Incentive to bias |
| --- | --- | --- | --- |
| Sponsor | Open covenant, fund escrow, receive claim bond on failed claim, close expired covenant | Payout escrow and claim-bond credit | Deny that disclosure triggers payout |
| Beneficiary | Accept covenant, open claim, withdraw payout credit | Payout right and claim bond | Overstate disclosure meaning |
| Validator | Fetch SEC evidence, judge meaning, compare consensus-critical fields | Consensus integrity | No direct contract credit |
| Integrator | Read canonical status/credit views | Downstream settlement/routing | Needs neutral state |

## Scope and non-goals

### In scope

- SEC EDGAR archive URL validation.
- Fixed trigger enums: `MATERIAL_CYBER_INCIDENT`, `MERGER_COMPLETED`, `GOING_CONCERN_WARNING`.
- Single active claim per covenant.
- Native GEN escrow and claim-bond accounting.
- Retryable `UNVERIFIABLE`.
- Public canonical views.

### Out of scope

- Private contracts or confidential filings.
- Non-SEC sources.
- Browser frontend or Vercel deployment.
- Legal advice or enforceability beyond the onchain primitive.
- Arbitrary natural-language claims outside the fixed trigger enums.

## State model

### Stable IDs

- `covenant_id`: caller-supplied ASCII slug, normalized to lowercase, length 6-64.
- `claim_id`: deterministic `covenant_id + ":" + accession + ":" + attempt_index`.
- `event_key`: deterministic `cik + ":" + accession + ":" + trigger_kind`.

### Structured storage

- `Covenant`: sponsor, beneficiary, CIK, trigger kind, allowed form, allowed item, payout, claim bond, status, active claim, accepted flag, escrow remaining.
- `Claim`: covenant ID, claimant, filing URL, accession, status, verdict, source stage, authoritative filing date, consequence, event class, decisive fact IDs, rationale, settled flag.
- `Credit`: address string to GEN amount.
- `Attempt`: claim ID to source/verdict summary.

### State machine

```text
MISSING --open_covenant/sponsor/payable--> DRAFT
DRAFT --accept_covenant/beneficiary--> ACTIVE
ACTIVE --open_claim/beneficiary/payable--> CLAIM_OPEN
CLAIM_OPEN --adjudicate_claim/TRIGGERED--> TRIGGERED
CLAIM_OPEN --adjudicate_claim/NOT_TRIGGERED--> ACTIVE
CLAIM_OPEN --adjudicate_claim/UNVERIFIABLE--> ACTIVE
ACTIVE --propose_close/party + accept_close/opposite-party--> CLOSED
ACTIVE --close_expired/sponsor/after-expiry--> CLOSED
TRIGGERED --withdraw_credit/beneficiary--> TRIGGERED
```

### Illegal transitions

- Duplicate covenant ID.
- Accept by non-beneficiary.
- Claim before acceptance.
- Claim before activation or after expiry.
- Claim while another claim is open.
- Claim against URL outside SEC archive allowlist.
- Adjudicate non-open claim.
- Withdraw more than credited amount.
- Close while a claim is open.
- Sponsor expiry close before the expiry date.
- Settle the same claim twice.

### Authorization

- Sponsor is `gl.message.sender` in `open_covenant`.
- Beneficiary address is locked at open and must accept.
- Only beneficiary opens claims in v1.
- Any caller may trigger `adjudicate_claim` for an open claim because validators decide the outcome.
- Sponsor or beneficiary may propose close; only the opposite covenant party can accept close.
- Sponsor may unilaterally close an inactive expired covenant after the expiry date.
- Only credited address can withdraw its credit.

### Idempotency and double-action prevention

- Covenant IDs are unique.
- One active claim per covenant.
- Claim stores `settled = True` before external transfer paths are available.
- Credits debit before `emit_transfer`.
- Accession/event key cannot be used twice for a `TRIGGERED` payout.

## Evidence policy

- Authoritative sources: `https://www.sec.gov/Archives/edgar/data/...` filing documents and SEC submission metadata.
- Provenance/authentication: SEC host/path and CIK/accession validation; no claimant-hosted evidence.
- Authorized attestor/signer: not required for SEC-authored evidence; claimant only selects an official URL.
- Anti-replay event/digest identity: `cik + accession + trigger_kind`.
- Signed timestamp bounds: not used for SEC-authored source; filing date must be inside locked covenant window.
- Immutable policy/source version URLs and hashes: filing URL/accession are immutable evidence identity; evidence summary stores accession and stage, not raw filing.
- Allowed schemes/domains/paths: HTTPS, `www.sec.gov`, path prefix `/Archives/edgar/data/`.
- Time/window rules: claims can be opened only during the activation/expiry window, SEC submissions metadata must verify the filing date is on or after activation and on or before expiry, and sponsor-only expiry close is available only after expiry.
- Size/count bounds: one filing URL and one optional metadata URL, max rendered text length 160000 chars, max 12 decisive fact IDs.
- Missing evidence: `UNVERIFIABLE`.
- Contradictory evidence: `UNVERIFIABLE` unless the locked filing itself clearly satisfies or fails the trigger.
- Unavailable source: `UNVERIFIABLE`.
- Invalid/unverifiable attestation: non-penalizing because v1 uses SEC-authored evidence only.
- Prompt-injection boundary: filing text cannot expand trigger enums, allowed forms/items, or consequence mapping.
- Private/unverifiable evidence excluded: yes.

## Consensus design

### Leader task

- Inputs: covenant trigger, CIK, allowed form/item, accession, filing URL, activation/expiry window.
- Fetch: SEC submissions metadata and SEC filing text with declared User-Agent.
- Extraction: verify accession, authoritative SEC filing date, SEC form, item labels, event language, and decisive paragraphs.
- Normalization: trim text, cap fact IDs, map trigger-specific event class to enum.
- Structured output: JSON with verdict, trigger kind, form coverage, item coverage, source stage, event class, decisive facts, consequence class, reason.

### Consensus-critical fields

| Field | Type/bounds | Comparison rule | Why critical |
| --- | --- | --- | --- |
| covenant_id | str 6-64 | exact | Isolates state |
| cik | str digits | exact | Company identity |
| accession | str 10-24 | exact | Filing identity |
| trigger_kind | locked enum | exact | Defines question |
| verdict | `TRIGGERED`, `NOT_TRIGGERED`, `UNVERIFIABLE` | exact | Drives consequence |
| form_covered | bool | exact | Prevents wrong form |
| item_covered | bool | exact | Prevents wrong disclosure item |
| event_class | locked enum | exact | Captures semantic meaning |
| source_stage | locked enum | exact | Differentiates unavailable source |
| filing_date | YYYY-MM-DD from SEC submissions metadata | exact and inside window | Enforces activation/expiry against authoritative SEC data |
| consequence_class | locked enum | exact | Prevents payout mismatch |
| decisive_fact_ids | set size 0-12 | subset/equivalent bounded set | Supports semantic replay without prose matching |

### Validator

- Independent evidence/replay: validator calls the same leader evidence function and recomputes the semantic fields.
- Semantic rule: compare locked fields and consequence class; ignore rationale wording.
- Rejection conditions: leader error, invalid enum, mismatched CIK/accession/form/item, invalid consequence, unbounded facts, or conflicting verdict.
- `UNDETERMINED` handling: no state transition beyond preserving open claim; tooling reads current claim ID and may retry after diagnosis.

### Rationale policy

Rationale is stored as a bounded summary for explainability only. It is not consensus-critical and must not be used for settlement.

## Consequence and accounting

| Verdict | Canonical state change | Consumer action | Value movement |
| --- | --- | --- | --- |
| TRIGGERED | covenant `TRIGGERED`, claim settled | Integrator reads triggered status | escrow payout credited to beneficiary |
| NOT_TRIGGERED | covenant `ACTIVE`, claim closed | Integrator continues normal state | claim bond credited to sponsor |
| UNVERIFIABLE | covenant `ACTIVE`, claim closed retryable | Integrator treats as pending/no trigger | claim bond credited back to claimant |

- Accepted/finalized boundary: contract state changes in the adjudication transaction after GenLayer consensus.
- Ledger invariant: covenant escrow remaining plus credits plus settled transfers equals deposited value minus withdrawn value.
- Child-message/transfer evidence: withdrawal receipt and balance delta required on Studionet for completion.
- Withdrawal/settlement: `withdraw_credit(amount)` debits before transfer.
- Bilateral close: `propose_close` plus `accept_close` returns remaining escrow to the sponsor ledger when both parties agree and no claim is open.
- Cure/appeal/restore: no appeal in v1; retry allowed only after `UNVERIFIABLE` or `NOT_TRIGGERED` with a new accession.

## Reusable interface

### Write methods

- `open_covenant(covenant_id, beneficiary, cik, trigger_kind, allowed_form, allowed_item, activation_date, expiry_date, payout_amount, claim_bond_amount)` payable.
- `accept_covenant(covenant_id)`.
- `open_claim(covenant_id, accession, filing_url)` payable.
- `adjudicate_claim(covenant_id)`.
- `close_claim(covenant_id)` for stale `UNDETERMINED` recovery.
- `propose_close(covenant_id)`.
- `accept_close(covenant_id)`.
- `close_expired(covenant_id)`.
- `withdraw_credit(amount)`.

### View methods

- `get_covenant(covenant_id)`.
- `get_claim(covenant_id)`.
- `get_credit(address)`.
- `can_claim(covenant_id, accession)`.
- `get_status(covenant_id)`.

### Consumer/callback

- Authentication: no callback in v1.
- Idempotency key: downstream consumers use `covenant_id` and current claim/accession.
- Failure/retry: read views after finalization; retry only when canonical status permits.
- Authorized cancellation: sponsor can close an expired inactive covenant; both parties can mutually close an inactive covenant before expiry.

## Threat model

| Threat | Attack | Mitigation | Test |
| --- | --- | --- | --- |
| Fake URL | Claimant submits non-SEC or wrong path URL | Deterministic allowlist and CIK/accession path check | invalid URL test |
| Wrong company | Filing for another CIK | Exact CIK path and semantic CIK match | wrong CIK test |
| Prompt injection | Filing text tells model to pay | Locked enums and prompt boundary | injection fixture |
| Format-only validator | Leader returns valid JSON with wrong verdict | Validator recomputes and compares meaning fields | malicious leader test |
| Double payout | Same accession claimed twice | event key and settled flag | duplicate triggered test |
| Source outage | SEC unavailable or blocks request | `UNVERIFIABLE`, no penalty | web failure test |
| Oversized filing | Huge response exhausts runtime | length cap and fail `UNVERIFIABLE` | oversized fixture |
| Unauthorized action | Sponsor/beneficiary roles crossed | sender checks | unauthorized tests |
| Accounting loss | Withdraw before debit or double withdraw | debit first and credit checks | withdrawal tests |

## Test plan

- Happy path: material cybersecurity filing triggers payout.
- Unauthorized: non-beneficiary cannot accept/open claim.
- Isolation: two covenants with different CIKs do not share state.
- Evidence failure: blocked or unavailable SEC source gives `UNVERIFIABLE`.
- Malicious leader: wrong verdict with valid shape is rejected.
- Prompt injection: filing text cannot expand trigger or consequence.
- Semantic mismatch: wrong item/form produces `NOT_TRIGGERED` or validator disagreement.
- Verdict classes: `TRIGGERED`, `NOT_TRIGGERED`, `UNVERIFIABLE`.
- Duplicate: one active claim and no second payout for same event key.
- Accounting/value: payable metadata, escrow credit, bond credit, withdraw.
- Cure/restore: not in v1; covered as non-goal.
- Consumer enforcement: public views only; no consumer contract.
- Undetermined/retry: stale claim can be closed without settlement claim.

## Claim-to-code matrix

| Product claim | Contract method/state | View/read | Direct test | Network evidence |
| --- | --- | --- | --- | --- |
| SEC filing trigger can be locked with escrow | `open_covenant`, `Covenant.ACTIVE` | `get_covenant` | open/accept tests | deploy + open covenant tx |
| Only beneficiary can activate claim | `accept_covenant`, `open_claim` sender checks | `get_claim` | unauthorized tests | claim tx actor evidence |
| Validators judge SEC filing meaning | `adjudicate_claim` nondet + validator | `get_claim` verdict fields | nondet mocked tests | finalized adjudication tx |
| Filing date window is authoritative | SEC submissions metadata guard | `get_claim.filing_date`, `can_claim` | out-of-window and metadata-failure tests | claim canonical read includes `filing_date: 2026-03-20` |
| Triggered verdict opens payout credit | `TRIGGERED` settlement | `get_credit`, `get_status` | triggered accounting test | canonical credit read |
| Not-triggered verdict keeps covenant active | `NOT_TRIGGERED` settlement | `get_status` | not-triggered test | canonical status read |
| Unverifiable is non-penalizing | `UNVERIFIABLE` settlement | `get_claim`, `get_credit` | source failure test | source failure/retry evidence if run |
| Credit withdrawal transfers GEN | `withdraw_credit` | `get_credit` | withdraw test | receipt + balance delta |
| Expiry releases inactive escrow safely | `close_expired`, sponsor-only guard | `get_status`, `get_accounting` | expiry close tests | `expiredRecovery` closed and accounting zero |
| Duplicate settlement is blocked | settled/event key checks | `can_claim` | duplicate tests | optional duplicate rejection tx |

## Analogue and differentiation matrix

| Analogue/prior idea | Similar dimensions | Structural difference | Collision decision |
| --- | --- | --- | --- |
| RecallBond | public government source, value consequence | product recall applicability and marketplace quarantine vs SEC filing trigger payout | not duplicate |
| Semantic Interface Covenant | bilateral covenant, semantic validator | software interface evidence and quarantine vs issuer disclosure and payout | not duplicate |
| AgentAccessBond | single-contract status/credit | web access receipts and policy vs SEC issuer filings | not duplicate |
| TrustlessAgent | escrow settlement | arbitrary deliverable evidence vs fixed SEC trigger enums | not duplicate |
| Generic prediction resolver | public event settlement | reusable covenant escrow with locked SEC identity and direct credit | acceptable overlap avoided |

## Deployment and evidence plan

- Network: studionet.
- Actors/wallet separation: sponsor and beneficiary EOAs; second wallet only if user approves funding flow.
- Deploy steps: lint, direct tests, ASCII/header scan, deploy exact source, verify `Result: SUCCESS`.
- Consequential lifecycle: open covenant, accept, open claim with real SEC filing, adjudicate, read verdict/credit/status, withdraw credit.
- Canonical reads: covenant, claim, credit, status before and after withdraw.
- Balance/receipt proof: safe allowlist only, no full RPC dump.
- Evidence path: `docs/evidence/studionet/deployment.json`.
- Resume/idempotency: deployment identity binds network, source commit, Depends header, contract address, covenant ID, and accession.

## Definition of Done

### Intelligent Contracts

- [x] Reusable primitive.
- [x] Semantic validator judgment.
- [x] Direct consequence.
- [x] Reuse proof through documented views.
- [x] Adversarial tests.
- [x] Real studionet lifecycle.
- [x] Canonical evidence.

### Projects, if selected

Not selected. No frontend is allowed for this submission.

## Honest limitations

- Browser frontend and Vercel deployment are intentionally out of scope for the Intelligent Contracts track.
- SEC access requires a declared User-Agent and may rate-limit automated callers.
- V1 supports only fixed trigger enums; arbitrary filing language is out of scope.
- No legal enforceability beyond the onchain primitive is claimed.

## Kill criteria

- GenVM cannot send the required declared User-Agent to SEC.
- SEC source cannot be fetched reliably enough for validators on studionet.
- Validator can be reduced to JSON shape or one-party LLM judgment.
- Payout consequence cannot be proven with canonical state and balance evidence.
- The design drifts into a generic oracle or generic escrow.

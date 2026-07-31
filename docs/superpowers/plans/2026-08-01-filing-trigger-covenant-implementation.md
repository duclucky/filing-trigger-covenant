# FilingTriggerCovenant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, verify, deploy, document, and publish a standalone GenLayer Intelligent Contract primitive for SEC filing-triggered covenant payouts.

**Architecture:** One contract owns covenant storage, SEC evidence adjudication, semantic validator equivalence, escrow accounting, credit withdrawals, and canonical views. No frontend and no consumer contract are included because the primitive's direct consequence is its ledger state and payout credit.

**Tech Stack:** GenVM Python contract with `from genlayer import *`, `genlayer-test` direct tests, Node deployment scripts for studionet, GitHub public repo.

## Global Constraints

- Category is Intelligent Contracts; no `frontend/`, no Vercel.
- Contract file must be pure ASCII.
- Contract header line 1 must match current Studio version pragma before deployment; line 2 is Depends; line 3 is `from genlayer import *`.
- Use `TreeMap[str, ...]`, `DynArray[...]`, `bigint` for money, and `@allow_storage @dataclass` storage structs.
- Every `gl.nondet.*` call lives inside `gl.vm.run_nondet` or `gl.eq_principle.*`.
- Validator compares meaning fields, not JSON shape or rationale prose.
- SEC evidence is limited to HTTPS `www.sec.gov/Archives/edgar/data/`.
- Missing/unavailable/blocked SEC evidence maps to `UNVERIFIABLE` without penalty.
- Public repo allowlist excludes `.env`, `.codex`, `AGENTS.md`, `CLAUDE.md`, root playbooks, source-notes, research, templates, keys, logs, and raw RPC dumps.

---

### Task 1: Project Verification Scaffold

**Files:**
- Create: `package.json`
- Create: `requirements-dev.txt`
- Create: `scripts/check.ps1`
- Create: `scripts/ascii_header_check.py`
- Create: `tests/direct/test_static_contract.py`

**Interfaces:**
- Consumes: project spec in `docs/README.md`.
- Produces: `npm run check`, `npm run lint:contracts`, `npm run test:direct`, and static checks used by all later tasks.

- [ ] **Step 1: Write the failing static tests**

Create `tests/direct/test_static_contract.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "filing_trigger_covenant.py"


def test_contract_file_exists():
    assert CONTRACT.exists()


def test_contract_is_ascii():
    data = CONTRACT.read_bytes()
    data.decode("ascii")


def test_contract_header_shape():
    lines = CONTRACT.read_text(encoding="ascii").splitlines()
    assert lines[0].startswith("# v")
    assert lines[1].startswith('# { "Depends": "py-genlayer:')
    assert lines[2] == "from genlayer import *"


def test_no_frontend_directory():
    assert not (ROOT / "frontend").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/direct/test_static_contract.py -v`
Expected: FAIL because `contracts/filing_trigger_covenant.py` does not exist.

- [ ] **Step 3: Add tooling files**

Create `requirements-dev.txt`:

```text
genlayer-test==0.29.2
pytest==8.4.1
```

Create `package.json`:

```json
{
  "name": "filing-trigger-covenant",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "lint:contracts": "powershell -ExecutionPolicy Bypass -File scripts/check.ps1 -Only lint",
    "test:direct": "powershell -ExecutionPolicy Bypass -File scripts/check.ps1 -Only test",
    "check": "powershell -ExecutionPolicy Bypass -File scripts/check.ps1"
  }
}
```

Create `scripts/ascii_header_check.py`:

```python
from pathlib import Path


contract = Path("contracts/filing_trigger_covenant.py")
data = contract.read_bytes()
data.decode("ascii")
lines = contract.read_text(encoding="ascii").splitlines()
assert lines[0].startswith("# v"), "line 1 must be Studio version pragma"
assert lines[1].startswith('# { "Depends": "py-genlayer:'), "line 2 must be Depends"
assert lines[2] == "from genlayer import *", "line 3 must be from genlayer import *"
print("ASCII/header check passed")
```

Create `scripts/check.ps1`:

```powershell
param([string]$Only = "")

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

if ($Only -eq "" -or $Only -eq "lint") {
  python scripts/ascii_header_check.py
  if (Get-Command genvm-lint -ErrorAction SilentlyContinue) {
    genvm-lint check contracts/filing_trigger_covenant.py
  } else {
    Write-Host "genvm-lint not on PATH; relying on gltest/static checks"
  }
}

if ($Only -eq "" -or $Only -eq "test") {
  python -m pytest tests/direct -v
}
```

- [ ] **Step 4: Run static test again**

Run: `python -m pytest tests/direct/test_static_contract.py -v`
Expected: FAIL only on missing contract file.

- [ ] **Step 5: Commit**

```bash
git add package.json requirements-dev.txt scripts/ascii_header_check.py scripts/check.ps1 tests/direct/test_static_contract.py
git commit -m "chore: add contract verification scaffold"
```

### Task 2: Contract State, Views, and Deterministic Validation

**Files:**
- Create: `contracts/filing_trigger_covenant.py`
- Create: `tests/direct/test_covenant_state.py`

**Interfaces:**
- Consumes: static tooling from Task 1.
- Produces: public methods `open_covenant`, `accept_covenant`, `get_covenant`, `get_status`, `get_credit`, and deterministic helpers.

- [ ] **Step 1: Write failing state tests**

Create `tests/direct/test_covenant_state.py` with tests for opening a payable covenant, rejecting zero payout, accepting by beneficiary only, and reading isolated status for two covenant IDs. Use the gltest fluent write shape:

```python
def test_open_and_accept_covenant(client, accounts, deploy_contract):
    contract = deploy_contract()
    sponsor, beneficiary = accounts[0], accounts[1]
    contract.connect(sponsor).open_covenant(args=[
        "cyber-001",
        beneficiary.address,
        "732026",
        "MATERIAL_CYBER_INCIDENT",
        "8-K",
        "Item 1.05",
        "2026-01-01",
        "2026-12-31",
        1000000000000000000,
        100000000000000000
    ]).transact(value=1000000000000000000)
    before = contract.get_status(args=["cyber-001"]).call()
    assert before == "DRAFT"
    contract.connect(beneficiary).accept_covenant(args=["cyber-001"]).transact()
    assert contract.get_status(args=["cyber-001"]).call() == "ACTIVE"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/direct/test_covenant_state.py -v`
Expected: FAIL because contract methods do not exist.

- [ ] **Step 3: Implement storage and views**

Implement `contracts/filing_trigger_covenant.py` with:

```python
# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
from dataclasses import dataclass
```

Add `@allow_storage @dataclass` structs for `Covenant` and `Claim`, `class Contract(gl.Contract)`, `TreeMap[str, Covenant]`, `TreeMap[str, Claim]`, `TreeMap[str, bigint]`, and deterministic validation for IDs, CIK, enums, dates, payout, and SEC URLs. Do not add nondeterminism yet.

- [ ] **Step 4: Run state tests**

Run: `python -m pytest tests/direct/test_covenant_state.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add contracts/filing_trigger_covenant.py tests/direct/test_covenant_state.py
git commit -m "feat: add filing covenant state model"
```

### Task 3: Claims, Accounting, and Withdrawal

**Files:**
- Modify: `contracts/filing_trigger_covenant.py`
- Create: `tests/direct/test_claim_accounting.py`

**Interfaces:**
- Consumes: `open_covenant`, `accept_covenant`, credit ledger.
- Produces: `open_claim`, `close_claim`, `withdraw_credit`, active-claim protection, claim-bond ledger.

- [ ] **Step 1: Write failing accounting tests**

Create tests for beneficiary-only `open_claim`, claim bond value equals configured amount, one active claim per covenant, `close_claim` returns stale unverifiable bond to claimant, and `withdraw_credit` debits before transfer.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/direct/test_claim_accounting.py -v`
Expected: FAIL because claim and withdraw methods do not exist.

- [ ] **Step 3: Implement claim and ledger methods**

Add:

```python
@gl.public.write.payable
def open_claim(self, covenant_id: str, accession: str, filing_url: str) -> None: ...

@gl.public.write
def close_claim(self, covenant_id: str) -> None: ...

@gl.public.write
def withdraw_credit(self, amount: int) -> None: ...
```

Ensure `open_claim` validates SEC URL path, CIK, accession, active status, exact `gl.message.value`, and one active claim. Ensure `withdraw_credit` converts `amount` to `bigint`, debits first, then calls `gl.get_contract_at(gl.message.sender).emit_transfer(value=u256(amount_value))`.

- [ ] **Step 4: Run accounting tests**

Run: `python -m pytest tests/direct/test_claim_accounting.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add contracts/filing_trigger_covenant.py tests/direct/test_claim_accounting.py
git commit -m "feat: add claim accounting and withdrawals"
```

### Task 4: Nondeterministic SEC Adjudication and Semantic Validator

**Files:**
- Modify: `contracts/filing_trigger_covenant.py`
- Create: `tests/direct/test_adjudication.py`

**Interfaces:**
- Consumes: `open_claim` active claim state.
- Produces: `adjudicate_claim`, verdict settlement, validator meaning comparison.

- [ ] **Step 1: Write failing adjudication tests**

Create tests installing `sim_installMocks` as a bare dict before transactions. Cover `TRIGGERED`, `NOT_TRIGGERED`, `UNVERIFIABLE`, prompt-injection evidence, malformed leader output, and malicious leader output where JSON shape is valid but verdict meaning differs.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/direct/test_adjudication.py -v`
Expected: FAIL because `adjudicate_claim` is not implemented.

- [ ] **Step 3: Implement leader and validator**

Add `adjudicate_claim(covenant_id: str)`:

```python
def leader_fn():
    page = gl.nondet.web.get(filing_url, headers={"User-Agent": SEC_USER_AGENT})
    return gl.nondet.exec_prompt(prompt, response_format="json")

def validator_fn(leader_res) -> bool:
    if not isinstance(leader_res, gl.vm.Return):
        return False
    mine = leader_fn()
    leader = leader_res.calldata
    return self._same_meaning(leader, mine, covenant_snapshot)
```

If `gl.nondet.web.get` with headers is unavailable in the selected runtime, use the documented available web primitive and mark SEC User-Agent support as a kill criterion before deployment. The final implementation must not settle punitive consequences on source failure.

- [ ] **Step 4: Run adjudication tests**

Run: `python -m pytest tests/direct/test_adjudication.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add contracts/filing_trigger_covenant.py tests/direct/test_adjudication.py
git commit -m "feat: add SEC semantic adjudication"
```

### Task 5: Deployment Tooling and Evidence Writer

**Files:**
- Create: `scripts/studionet_lifecycle.mjs`
- Create: `tests/deployment_parser.test.mjs`
- Modify: `package.json`

**Interfaces:**
- Consumes: public contract methods and views.
- Produces: idempotent deploy/demo/inspect commands and safe evidence JSON.

- [ ] **Step 1: Write parser fixture tests**

Create Node tests for raw Studio receipt shape at `consensus_data.leader_receipt[].execution_result` and normalized SDK shape. Assert only safe fields are emitted: hash, status, result, address, timestamp, public actors, state reads.

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test tests/deployment_parser.test.mjs`
Expected: FAIL because parser does not exist.

- [ ] **Step 3: Implement lifecycle script**

Create commands:

```text
node scripts/studionet_lifecycle.mjs inspect
node scripts/studionet_lifecycle.mjs deploy
node scripts/studionet_lifecycle.mjs run-demo
```

The script reads project `.env` then parent `.env`, checks presence only, never prints secrets, refuses to resume when network/source/header/address identity mismatches, and writes `docs/evidence/studionet/deployment.json` using a safe allowlist.

- [ ] **Step 4: Run parser tests**

Run: `node --test tests/deployment_parser.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add package.json scripts/studionet_lifecycle.mjs tests/deployment_parser.test.mjs
git commit -m "feat: add studionet lifecycle tooling"
```

### Task 6: Documentation, Local Verification, Deployment, and Public Repo

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Create or update: `docs/evidence/studionet/deployment.json`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified local checks, real studionet evidence, public GitHub repo, copy-ready portal submission text.

- [ ] **Step 1: Run full local verification**

Run: `npm run check`
Expected: ASCII/header pass, contract lint if available, all direct tests pass.

- [ ] **Step 2: Run deploy-clean scan**

Run: `python scripts/ascii_header_check.py`
Expected: `ASCII/header check passed`.

- [ ] **Step 3: Deploy and run lifecycle**

Run:

```bash
node scripts/studionet_lifecycle.mjs deploy
node scripts/studionet_lifecycle.mjs run-demo
node scripts/studionet_lifecycle.mjs inspect
```

Expected: deployed contract `Result: SUCCESS`, finalized adjudication, canonical `TRIGGERED` read, beneficiary credit, withdrawal receipt, and credit zero after withdraw.

- [ ] **Step 4: Update README and spec evidence**

Add deployed address, network `studionet`, worked example input/output, test counts from current commands, and honest limitations. Do not claim browser/frontend evidence.

- [ ] **Step 5: Pre-push audit and public repo**

Run:

```bash
git rev-parse --show-toplevel
git status --short
git diff --check
git diff --cached --name-only
git ls-files
```

Confirm `.env`, internal root files, `.codex`, raw notes, keys, logs, and frontend are absent. Push to a new public GitHub repo named `filing-trigger-covenant`.

- [ ] **Step 6: Commit docs/evidence**

```bash
git add README.md docs/README.md docs/evidence/studionet/deployment.json
git commit -m "docs: record filing covenant deployment evidence"
```

## Self-Review

- Spec coverage: covered state, roles, evidence policy, semantic validator, accounting, views, tests, deployment, public repo, and submission evidence.
- Placeholder scan: no unresolved placeholder markers or vague "add tests" steps remain.
- Type consistency: public method names match the spec: `open_covenant`, `accept_covenant`, `open_claim`, `adjudicate_claim`, `close_claim`, `close_expired`, `withdraw_credit`, `get_covenant`, `get_claim`, `get_credit`, `can_claim`, `get_status`.

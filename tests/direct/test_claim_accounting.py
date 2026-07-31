from tests.direct.conftest import to_hex
from tests.direct.test_covenant_state import (
    CLAIM_BOND,
    CONTRACT_PATH,
    PAYOUT,
    open_valid_covenant,
)


VALID_SEC_URL = "https://www.sec.gov/Archives/edgar/data/732026/000143774926009193/trt20260320_8k.htm"


def activate_covenant(contract, vm, sponsor, beneficiary, covenant_id="cyber-001"):
    open_valid_covenant(contract, vm, sponsor, beneficiary, covenant_id)
    vm.sender = beneficiary
    contract.accept_covenant(covenant_id)


def open_valid_claim(contract, vm, sponsor, beneficiary, covenant_id="cyber-001"):
    activate_covenant(contract, vm, sponsor, beneficiary, covenant_id)
    vm.sender = beneficiary
    vm.value = CLAIM_BOND
    contract.open_claim(covenant_id, "000143774926009193", VALID_SEC_URL)
    contract_address = vm._contract_address
    current_balance = vm._balances.get(bytes(contract_address), 0)
    vm.deal(contract_address, current_balance + CLAIM_BOND)
    vm.value = 0


def test_beneficiary_opens_sec_claim_with_bond(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_claim(contract, direct_vm, direct_alice, direct_bob)

    claim = contract.get_claim("cyber-001")
    covenant = contract.get_covenant("cyber-001")
    accounting = contract.get_accounting()
    assert claim.covenant_id == "cyber-001"
    assert claim.claimant.as_hex == to_hex(direct_bob)
    assert claim.accession == "000143774926009193"
    assert claim.status == "OPEN"
    assert covenant.status == "CLAIM_OPEN"
    assert covenant.active_claim_id == "cyber-001:000143774926009193:1"
    assert int(accounting["locked_escrow"]) == PAYOUT
    assert int(accounting["locked_claim_bonds"]) == CLAIM_BOND
    assert int(accounting["withdrawable_credits"]) == 0


def test_only_beneficiary_can_open_claim(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy(CONTRACT_PATH)
    activate_covenant(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    direct_vm.value = CLAIM_BOND
    with direct_vm.expect_revert("Only beneficiary can open claim"):
        contract.open_claim("cyber-001", "000143774926009193", VALID_SEC_URL)


def test_claim_guards_and_one_active_claim(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    activate_covenant(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    direct_vm.value = 1
    with direct_vm.expect_revert("Claim bond value must equal configured amount"):
        contract.open_claim("cyber-001", "000143774926009193", VALID_SEC_URL)

    direct_vm.value = CLAIM_BOND
    with direct_vm.expect_revert("SEC URL must be official EDGAR archive"):
        contract.open_claim("cyber-001", "000143774926009193", "https://example.com/fake.htm")

    with direct_vm.expect_revert("SEC URL CIK must match covenant"):
        contract.open_claim(
            "cyber-001",
            "000143774926009193",
            "https://www.sec.gov/Archives/edgar/data/999999/000143774926009193/trt20260320_8k.htm",
        )

    contract.open_claim("cyber-001", "000143774926009193", VALID_SEC_URL)
    with direct_vm.expect_revert("Covenant already has an active claim"):
        contract.open_claim("cyber-001", "000143774926009194", VALID_SEC_URL)


def test_close_claim_refunds_bond_and_restores_active(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_claim(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    contract.close_claim("cyber-001")

    claim = contract.get_claim("cyber-001")
    assert claim.status == "CLOSED"
    assert claim.settled is True
    assert contract.get_status("cyber-001") == "ACTIVE"
    assert int(contract.get_credit(to_hex(direct_bob))) == CLAIM_BOND
    accounting = contract.get_accounting()
    assert int(accounting["locked_escrow"]) == PAYOUT
    assert int(accounting["locked_claim_bonds"]) == 0
    assert int(accounting["withdrawable_credits"]) == CLAIM_BOND


def test_bilateral_close_refunds_sponsor_escrow(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy(CONTRACT_PATH)
    activate_covenant(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only covenant parties can propose close"):
        contract.propose_close("cyber-001")

    direct_vm.sender = direct_alice
    contract.propose_close("cyber-001")
    with direct_vm.expect_revert("Opposite party must accept close"):
        contract.accept_close("cyber-001")

    direct_vm.sender = direct_bob
    contract.accept_close("cyber-001")

    assert contract.get_status("cyber-001") == "CLOSED"
    assert int(contract.get_credit(to_hex(direct_alice))) == PAYOUT
    accounting = contract.get_accounting()
    assert int(accounting["locked_escrow"]) == 0
    assert int(accounting["locked_claim_bonds"]) == 0
    assert int(accounting["withdrawable_credits"]) == PAYOUT


def test_bilateral_close_is_blocked_during_open_claim(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_claim(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Open claim blocks close"):
        contract.propose_close("cyber-001")


def test_withdrawal_debits_before_external_send(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_claim(contract, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    contract.close_claim("cyber-001")

    sends = []

    def capture_send(_vm, request):
        if "PostMessage" in request:
            sends.append(request["PostMessage"])
            assert int(contract.get_credit(to_hex(direct_bob))) == CLAIM_BOND - 40
            contract_address = _vm._contract_address
            current_balance = _vm._balances.get(bytes(contract_address), 0)
            _vm.deal(contract_address, current_balance - int(request["PostMessage"]["value"]))
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = capture_send
    contract.withdraw_credit(40)

    assert len(sends) == 1
    assert int(sends[0]["value"]) == 40
    assert sends[0]["address"].as_hex == to_hex(direct_bob)
    assert sends[0]["on"] == "finalized"
    assert int(contract.get_credit(to_hex(direct_bob))) == CLAIM_BOND - 40
    with direct_vm.expect_revert("Insufficient credit"):
        contract.withdraw_credit(CLAIM_BOND)
    with direct_vm.expect_revert("Withdrawal amount must be positive"):
        contract.withdraw_credit(0)

import pytest

from tests.direct.conftest import to_hex


CONTRACT_PATH = "contracts/filing_trigger_covenant.py"
PAYOUT = 1_000
CLAIM_BOND = 100
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def open_valid_covenant(contract, vm, sponsor, beneficiary, covenant_id="cyber-001"):
    vm.sender = sponsor
    vm.value = PAYOUT
    contract.open_covenant(
        covenant_id,
        to_hex(beneficiary),
        "732026",
        "MATERIAL_CYBER_INCIDENT",
        "8-K",
        "Item 1.05",
        "2026-01-01",
        "2026-12-31",
        PAYOUT,
        CLAIM_BOND,
    )
    contract_address = vm._contract_address
    current_balance = vm._balances.get(bytes(contract_address), 0)
    vm.deal(contract_address, current_balance + PAYOUT)
    vm.value = 0


def test_open_and_accept_covenant(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_covenant(contract, direct_vm, direct_alice, direct_bob)

    covenant = contract.get_covenant("cyber-001")
    assert contract.get_status("cyber-001") == "DRAFT"
    assert covenant.sponsor.as_hex == to_hex(direct_alice)
    assert covenant.beneficiary.as_hex == to_hex(direct_bob)
    assert covenant.cik == "732026"
    assert covenant.trigger_kind == "MATERIAL_CYBER_INCIDENT"
    assert int(covenant.payout_amount) == PAYOUT
    assert int(covenant.escrow_remaining) == PAYOUT

    direct_vm.sender = direct_bob
    contract.accept_covenant("cyber-001")
    assert contract.get_status("cyber-001") == "ACTIVE"


def test_only_beneficiary_accepts(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_covenant(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("Only beneficiary can accept covenant"):
        contract.accept_covenant("cyber-001")


def test_covenants_are_isolated(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_covenant(contract, direct_vm, direct_alice, direct_bob, "cyber-001")
    open_valid_covenant(contract, direct_vm, direct_charlie, direct_bob, "cyber-002")

    assert contract.get_status("cyber-001") == "DRAFT"
    assert contract.get_status("cyber-002") == "DRAFT"
    assert contract.get_covenant("cyber-001").sponsor.as_hex == to_hex(direct_alice)
    assert contract.get_covenant("cyber-002").sponsor.as_hex == to_hex(direct_charlie)


@pytest.mark.parametrize("covenant_id", ["", "abc", "contains space", "bad:colon", "x" * 65])
def test_invalid_covenant_id_is_rejected(covenant_id, direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    direct_vm.sender = direct_alice
    direct_vm.value = PAYOUT
    with direct_vm.expect_revert("Covenant ID"):
        contract.open_covenant(
            covenant_id,
            to_hex(direct_bob),
            "732026",
            "MATERIAL_CYBER_INCIDENT",
            "8-K",
            "Item 1.05",
            "2026-01-01",
            "2026-12-31",
            PAYOUT,
            CLAIM_BOND,
        )


@pytest.mark.parametrize(
    ("beneficiary", "cik", "trigger", "form", "item", "start", "end", "payout", "bond", "value", "message"),
    [
        (ZERO_ADDRESS, "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Beneficiary cannot be zero address"),
        ("BENEFICIARY", "", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "CIK must be 1-10 digits"),
        ("BENEFICIARY", "ABC", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "CIK must be 1-10 digits"),
        ("BENEFICIARY", "732026", "ANYTHING", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Trigger kind not allowed"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "10-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Form not allowed for trigger"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 2.01", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Item not allowed for trigger"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-1-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Date must be YYYY-MM-DD"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2027-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, PAYOUT, "Expiry must be after activation"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", 0, CLAIM_BOND, PAYOUT, "Payout must be positive"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, 0, PAYOUT, "Claim bond must be positive"),
        ("BENEFICIARY", "732026", "MATERIAL_CYBER_INCIDENT", "8-K", "Item 1.05", "2026-01-01", "2026-12-31", PAYOUT, CLAIM_BOND, 999, "Escrow value must equal payout"),
    ],
)
def test_covenant_guards(
    beneficiary,
    cik,
    trigger,
    form,
    item,
    start,
    end,
    payout,
    bond,
    value,
    message,
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy(CONTRACT_PATH)
    beneficiary_arg = to_hex(direct_bob) if beneficiary == "BENEFICIARY" else beneficiary
    direct_vm.sender = direct_alice
    direct_vm.value = value
    with direct_vm.expect_revert(message):
        contract.open_covenant(
            "cyber-001",
            beneficiary_arg,
            cik,
            trigger,
            form,
            item,
            start,
            end,
            payout,
            bond,
        )


def test_duplicate_covenant_id_is_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy(CONTRACT_PATH)
    open_valid_covenant(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    direct_vm.value = PAYOUT
    with direct_vm.expect_revert("Covenant already exists"):
        contract.open_covenant(
            "cyber-001",
            to_hex(direct_bob),
            "732026",
            "MATERIAL_CYBER_INCIDENT",
            "8-K",
            "Item 1.05",
            "2026-01-01",
            "2026-12-31",
            PAYOUT,
            CLAIM_BOND,
        )

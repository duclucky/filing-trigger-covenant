# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

from dataclasses import dataclass


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MAX_ID_LENGTH = 64
COVENANT_STATUSES = ("DRAFT", "ACTIVE", "CLAIM_OPEN", "TRIGGERED", "CLOSED")
TRIGGER_KINDS = (
    "MATERIAL_CYBER_INCIDENT",
    "MERGER_COMPLETED",
    "GOING_CONCERN_WARNING",
)


@allow_storage
@dataclass
class Covenant:
    sponsor: Address
    beneficiary: Address
    cik: str
    trigger_kind: str
    allowed_form: str
    allowed_item: str
    activation_date: str
    expiry_date: str
    payout_amount: bigint
    claim_bond_amount: bigint
    escrow_remaining: bigint
    status: str
    active_claim_id: str
    accepted: bool
    triggered_event_key: str


@allow_storage
@dataclass
class Claim:
    covenant_id: str
    claimant: Address
    accession: str
    filing_url: str
    status: str
    verdict: str
    source_stage: str
    consequence_class: str
    settled: bool


def _addr_str(addr: Address) -> str:
    try:
        return addr.as_hex.lower()
    except Exception:
        return str(addr).lower()


def _sender() -> Address:
    return gl.message.sender_address


def _is_valid_id(value: str) -> bool:
    if len(value) < 6 or len(value) > MAX_ID_LENGTH:
        return False
    for char in value:
        allowed = (
            (char >= "a" and char <= "z")
            or (char >= "0" and char <= "9")
            or char == "-"
            or char == "_"
        )
        if not allowed:
            return False
    return True


def _is_digits(value: str) -> bool:
    if len(value) == 0:
        return False
    for char in value:
        if char < "0" or char > "9":
            return False
    return True


def _is_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


def _date_number(value: str) -> int:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise gl.vm.UserError("Date must be YYYY-MM-DD")
    y = value[0:4]
    m = value[5:7]
    d = value[8:10]
    if not (_is_digits(y) and _is_digits(m) and _is_digits(d)):
        raise gl.vm.UserError("Date must be YYYY-MM-DD")
    year = int(y)
    month = int(m)
    day = int(d)
    if month < 1 or month > 12:
        raise gl.vm.UserError("Date must be YYYY-MM-DD")
    days = (31, 29 if _is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if day < 1 or day > days[month - 1]:
        raise gl.vm.UserError("Date must be YYYY-MM-DD")
    return year * 10000 + month * 100 + day


def _allowed_form_for_trigger(trigger_kind: str, allowed_form: str) -> bool:
    if trigger_kind == "MATERIAL_CYBER_INCIDENT":
        return allowed_form == "8-K"
    if trigger_kind == "MERGER_COMPLETED":
        return allowed_form == "8-K"
    if trigger_kind == "GOING_CONCERN_WARNING":
        return allowed_form == "10-K" or allowed_form == "10-Q" or allowed_form == "8-K"
    return False


def _allowed_item_for_trigger(trigger_kind: str, allowed_item: str) -> bool:
    if trigger_kind == "MATERIAL_CYBER_INCIDENT":
        return allowed_item == "Item 1.05"
    if trigger_kind == "MERGER_COMPLETED":
        return allowed_item == "Item 2.01"
    if trigger_kind == "GOING_CONCERN_WARNING":
        return (
            allowed_item == "Going Concern"
            or allowed_item == "Item 2.06"
            or allowed_item == "Item 1A"
        )
    return False


class Contract(gl.Contract):
    covenants: TreeMap[str, Covenant]
    claims: TreeMap[str, Claim]
    credits: TreeMap[str, bigint]
    event_keys: TreeMap[str, bool]

    @gl.public.write.payable
    def open_covenant(
        self,
        covenant_id: str,
        beneficiary_address: str,
        cik: str,
        trigger_kind: str,
        allowed_form: str,
        allowed_item: str,
        activation_date: str,
        expiry_date: str,
        payout_amount: int,
        claim_bond_amount: int,
    ) -> None:
        if not _is_valid_id(covenant_id):
            raise gl.vm.UserError("Covenant ID must be 6-64 lowercase chars")
        if covenant_id in self.covenants:
            raise gl.vm.UserError("Covenant already exists")

        beneficiary = Address(beneficiary_address)
        if beneficiary.as_hex.lower() == ZERO_ADDRESS:
            raise gl.vm.UserError("Beneficiary cannot be zero address")
        if not _is_digits(cik) or len(cik) > 10:
            raise gl.vm.UserError("CIK must be 1-10 digits")
        if trigger_kind not in TRIGGER_KINDS:
            raise gl.vm.UserError("Trigger kind not allowed")
        if not _allowed_form_for_trigger(trigger_kind, allowed_form):
            raise gl.vm.UserError("Form not allowed for trigger")
        if not _allowed_item_for_trigger(trigger_kind, allowed_item):
            raise gl.vm.UserError("Item not allowed for trigger")

        start_num = _date_number(activation_date)
        end_num = _date_number(expiry_date)
        if end_num <= start_num:
            raise gl.vm.UserError("Expiry must be after activation")

        payout = bigint(int(payout_amount))
        claim_bond = bigint(int(claim_bond_amount))
        if int(payout) <= 0:
            raise gl.vm.UserError("Payout must be positive")
        if int(claim_bond) <= 0:
            raise gl.vm.UserError("Claim bond must be positive")
        received = bigint(int(gl.message.value))
        if int(received) != int(payout):
            raise gl.vm.UserError("Escrow value must equal payout")

        self.covenants[covenant_id] = Covenant(
            sponsor=_sender(),
            beneficiary=beneficiary,
            cik=cik,
            trigger_kind=trigger_kind,
            allowed_form=allowed_form,
            allowed_item=allowed_item,
            activation_date=activation_date,
            expiry_date=expiry_date,
            payout_amount=payout,
            claim_bond_amount=claim_bond,
            escrow_remaining=payout,
            status="DRAFT",
            active_claim_id="",
            accepted=False,
            triggered_event_key="",
        )

    @gl.public.write
    def accept_covenant(self, covenant_id: str) -> None:
        covenant = self.get_covenant(covenant_id)
        if _addr_str(_sender()) != _addr_str(covenant.beneficiary):
            raise gl.vm.UserError("Only beneficiary can accept covenant")
        if covenant.status != "DRAFT":
            raise gl.vm.UserError("Covenant cannot be accepted")
        covenant.status = "ACTIVE"
        covenant.accepted = True

    @gl.public.view
    def get_covenant(self, covenant_id: str) -> Covenant:
        if covenant_id not in self.covenants:
            raise gl.vm.UserError("Covenant not found")
        return self.covenants[covenant_id]

    @gl.public.view
    def get_status(self, covenant_id: str) -> str:
        return self.get_covenant(covenant_id).status

    @gl.public.view
    def get_credit(self, account: str) -> bigint:
        key = Address(account).as_hex.lower()
        if key not in self.credits:
            return bigint(0)
        return self.credits[key]

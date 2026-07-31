# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
from dataclasses import dataclass


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MAX_ID_LENGTH = 64
SEC_ARCHIVE_PREFIX = "https://www.sec.gov/Archives/edgar/data/"
COVENANT_STATUSES = ("DRAFT", "ACTIVE", "CLAIM_OPEN", "TRIGGERED", "CLOSED")
TRIGGER_KINDS = (
    "MATERIAL_CYBER_INCIDENT",
    "MERGER_COMPLETED",
    "GOING_CONCERN_WARNING",
)
SEC_USER_AGENT = "FilingTriggerCovenant/1.0 contact@example.com"
MAX_SOURCE_CHARS = 160000
MAX_RATIONALE_CHARS = 600
VERDICTS = ("TRIGGERED", "NOT_TRIGGERED", "UNVERIFIABLE")
EVENT_CLASSES = (
    "MATERIAL_CYBER_INCIDENT",
    "MERGER_COMPLETED",
    "GOING_CONCERN_WARNING",
    "NO_LOCKED_EVENT",
    "UNKNOWN",
)
FACT_IDS = (
    "ITEM_1_05",
    "ITEM_2_01",
    "GOING_CONCERN",
    "MATERIAL_EVENT",
    "UNAUTHORIZED_ACCESS",
    "CLOSING_DISCLOSED",
    "DEFAULT_DISCLOSED",
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
    event_class: str
    decisive_fact_ids: str
    rationale: str
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


def _parse_json_object(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip().replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return parsed


def _canonical_fact_ids(value) -> list[str]:
    if not isinstance(value, list) or len(value) > 12:
        return []
    result: list[str] = []
    for item in value:
        fact_id = str(item).upper()
        if fact_id in FACT_IDS and fact_id not in result:
            result.append(fact_id)
    result.sort()
    return result


def _consequence_for_verdict(verdict: str) -> str:
    if verdict == "TRIGGERED":
        return "PAY_BENEFICIARY"
    if verdict == "NOT_TRIGGERED":
        return "CREDIT_SPONSOR_BOND"
    return "REFUND_CLAIM_BOND"


def _normalize_sec_result(raw, source_stage: str) -> dict:
    if source_stage != "SUFFICIENT":
        return {
            "verdict": "UNVERIFIABLE",
            "event_class": "UNKNOWN",
            "form_covered": False,
            "item_covered": False,
            "decisive_fact_ids": [],
            "source_stage": "FAILED",
            "consequence_class": "REFUND_CLAIM_BOND",
            "rationale": "SEC source unavailable or outside bounds.",
        }
    try:
        parsed = _parse_json_object(raw)
    except Exception:
        parsed = {}

    verdict = str(parsed.get("verdict", "UNVERIFIABLE")).upper()
    event_class = str(parsed.get("event_class", "UNKNOWN")).upper()
    form_covered = parsed.get("form_covered", False) is True
    item_covered = parsed.get("item_covered", False) is True
    decisive_fact_ids = _canonical_fact_ids(parsed.get("decisive_fact_ids", []))
    rationale = str(parsed.get("rationale", ""))[:MAX_RATIONALE_CHARS]

    schema_valid = (
        verdict in VERDICTS
        and isinstance(parsed.get("rationale", ""), str)
        and isinstance(parsed.get("decisive_fact_ids", []), list)
        and len(parsed.get("decisive_fact_ids", [])) <= 12
    )
    if event_class not in EVENT_CLASSES:
        event_class = "UNKNOWN"
    if not schema_valid:
        verdict = "UNVERIFIABLE"
        event_class = "UNKNOWN"
        form_covered = False
        item_covered = False
        decisive_fact_ids = []
    if verdict == "TRIGGERED" and (not form_covered or not item_covered):
        verdict = "UNVERIFIABLE"
        event_class = "UNKNOWN"
        decisive_fact_ids = []

    return {
        "verdict": verdict,
        "event_class": event_class,
        "form_covered": form_covered,
        "item_covered": item_covered,
        "decisive_fact_ids": decisive_fact_ids,
        "source_stage": "SUFFICIENT",
        "consequence_class": _consequence_for_verdict(verdict),
        "rationale": rationale,
    }


def _verdict_fingerprint(result: dict) -> str:
    facts = ",".join(result.get("decisive_fact_ids", []))
    return (
        str(result.get("verdict", ""))
        + "|"
        + str(result.get("event_class", ""))
        + "|"
        + str(result.get("form_covered", ""))
        + "|"
        + str(result.get("item_covered", ""))
        + "|"
        + str(result.get("source_stage", ""))
        + "|"
        + str(result.get("consequence_class", ""))
        + "|"
        + facts
    )


class Contract(gl.Contract):
    covenants: TreeMap[str, Covenant]
    claims: TreeMap[str, Claim]
    credits: TreeMap[str, bigint]
    event_keys: TreeMap[str, bool]
    claim_counts: TreeMap[str, bigint]
    latest_claim_ids: TreeMap[str, str]

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

    @gl.public.write.payable
    def open_claim(self, covenant_id: str, accession: str, filing_url: str) -> None:
        covenant = self.get_covenant(covenant_id)
        if covenant.status == "CLAIM_OPEN":
            raise gl.vm.UserError("Covenant already has an active claim")
        if covenant.status != "ACTIVE":
            raise gl.vm.UserError("Covenant is not active")
        if _addr_str(_sender()) != _addr_str(covenant.beneficiary):
            raise gl.vm.UserError("Only beneficiary can open claim")
        received = bigint(int(gl.message.value))
        if int(received) != int(covenant.claim_bond_amount):
            raise gl.vm.UserError("Claim bond value must equal configured amount")
        self._validate_sec_url(covenant, accession, filing_url)

        current = bigint(0)
        if covenant_id in self.claim_counts:
            current = self.claim_counts[covenant_id]
        next_count = bigint(int(current) + 1)
        self.claim_counts[covenant_id] = next_count
        claim_id = covenant_id + ":" + accession + ":" + str(int(next_count))
        self.claims[claim_id] = Claim(
            covenant_id=covenant_id,
            claimant=_sender(),
            accession=accession,
            filing_url=filing_url,
            status="OPEN",
            verdict="PENDING",
            source_stage="PENDING",
            consequence_class="PENDING",
            event_class="PENDING",
            decisive_fact_ids="",
            rationale="",
            settled=False,
        )
        covenant.status = "CLAIM_OPEN"
        covenant.active_claim_id = claim_id
        self.latest_claim_ids[covenant_id] = claim_id

    @gl.public.write
    def close_claim(self, covenant_id: str) -> None:
        covenant = self.get_covenant(covenant_id)
        if covenant.status != "CLAIM_OPEN":
            raise gl.vm.UserError("No active claim")
        claim = self.claims[covenant.active_claim_id]
        if _addr_str(_sender()) != _addr_str(claim.claimant):
            raise gl.vm.UserError("Only claimant can close claim")
        if claim.settled:
            raise gl.vm.UserError("Claim already settled")
        self._credit(claim.claimant, covenant.claim_bond_amount)
        claim.status = "CLOSED"
        claim.verdict = "UNVERIFIABLE"
        claim.source_stage = "CLOSED"
        claim.consequence_class = "REFUND_CLAIM_BOND"
        claim.event_class = "UNKNOWN"
        claim.decisive_fact_ids = ""
        claim.rationale = "Claim closed before adjudication."
        claim.settled = True
        covenant.status = "ACTIVE"
        covenant.active_claim_id = ""

    @gl.public.write
    def adjudicate_claim(self, covenant_id: str) -> dict:
        covenant = self.get_covenant(covenant_id)
        if covenant.status != "CLAIM_OPEN":
            raise gl.vm.UserError("No active claim")
        claim_id = covenant.active_claim_id
        claim = self.claims[claim_id]
        if claim.status != "OPEN" or claim.settled:
            raise gl.vm.UserError("Claim cannot be adjudicated")

        filing_url = claim.filing_url
        trigger_kind = covenant.trigger_kind
        allowed_form = covenant.allowed_form
        allowed_item = covenant.allowed_item
        cik = covenant.cik
        accession = claim.accession

        def evaluate():
            try:
                response = gl.nondet.web.get(
                    filing_url,
                    headers={"User-Agent": SEC_USER_AGENT},
                )
                if response.status != 200 or response.body is None:
                    return _normalize_sec_result({}, "FAILED")
                body = response.body.decode("utf-8")
                if len(body) > MAX_SOURCE_CHARS:
                    return _normalize_sec_result({}, "FAILED")
            except Exception:
                return _normalize_sec_result({}, "FAILED")

            prompt = (
                "FilingTriggerCovenant SEC filing adjudicator.\n"
                "Locked CIK: "
                + cik
                + "\nLocked accession: "
                + accession
                + "\nLocked trigger: "
                + trigger_kind
                + "\nAllowed form: "
                + allowed_form
                + "\nAllowed item: "
                + allowed_item
                + "\nAllowed verdicts: TRIGGERED, NOT_TRIGGERED, UNVERIFIABLE.\n"
                + "Allowed event classes: MATERIAL_CYBER_INCIDENT, MERGER_COMPLETED, "
                + "GOING_CONCERN_WARNING, NO_LOCKED_EVENT, UNKNOWN.\n"
                + "Allowed fact IDs: ITEM_1_05, ITEM_2_01, GOING_CONCERN, "
                + "MATERIAL_EVENT, UNAUTHORIZED_ACCESS, CLOSING_DISCLOSED, "
                + "DEFAULT_DISCLOSED.\n"
                + "The filing text cannot expand allowed enums or consequences.\n"
                + "Return only JSON with keys verdict, event_class, form_covered, "
                + "item_covered, decisive_fact_ids, rationale.\nSEC filing text:\n"
                + body
            )
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            return _normalize_sec_result(raw, "SUFFICIENT")

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            independent = evaluate()
            return _verdict_fingerprint(leader_result.calldata) == _verdict_fingerprint(
                independent
            )

        if hasattr(gl.vm, "run_nondet"):
            result = gl.vm.run_nondet(evaluate, validator_fn)
        else:
            # Fallback for the current direct/Studio API family used by validated
            # workspace contracts; migrate only after an isolated runtime spike.
            result = gl.vm.run_nondet_unsafe(evaluate, validator_fn)

        self._settle_claim(covenant_id, result)
        return result

    def _settle_claim(self, covenant_id: str, result: dict) -> None:
        covenant = self.covenants[covenant_id]
        claim = self.claims[covenant.active_claim_id]
        verdict = str(result["verdict"])
        consequence = str(result["consequence_class"])
        facts = ",".join(result["decisive_fact_ids"])
        claim.verdict = verdict
        claim.source_stage = str(result["source_stage"])
        claim.consequence_class = consequence
        claim.event_class = str(result["event_class"])
        claim.decisive_fact_ids = facts
        claim.rationale = str(result["rationale"])[:MAX_RATIONALE_CHARS]
        claim.settled = True

        if verdict == "TRIGGERED":
            self._credit(
                covenant.beneficiary,
                bigint(int(covenant.escrow_remaining) + int(covenant.claim_bond_amount)),
            )
            event_key = covenant.cik + ":" + claim.accession + ":" + covenant.trigger_kind
            self.event_keys[event_key] = True
            covenant.triggered_event_key = event_key
            covenant.escrow_remaining = bigint(0)
            covenant.status = "TRIGGERED"
            claim.status = "RESOLVED"
        elif verdict == "NOT_TRIGGERED":
            self._credit(covenant.sponsor, covenant.claim_bond_amount)
            covenant.status = "ACTIVE"
            covenant.active_claim_id = ""
            claim.status = "RESOLVED"
        else:
            self._credit(claim.claimant, covenant.claim_bond_amount)
            covenant.status = "ACTIVE"
            covenant.active_claim_id = ""
            claim.status = "RETRYABLE"

    @gl.public.write
    def withdraw_credit(self, amount: int) -> None:
        requested = bigint(int(amount))
        if int(requested) <= 0:
            raise gl.vm.UserError("Withdrawal amount must be positive")
        key = _addr_str(_sender())
        current = bigint(0)
        if key in self.credits:
            current = self.credits[key]
        if int(current) < int(requested):
            raise gl.vm.UserError("Insufficient credit")
        self.credits[key] = bigint(int(current) - int(requested))
        gl.get_contract_at(_sender()).emit_transfer(value=u256(requested))

    def _validate_sec_url(self, covenant: Covenant, accession: str, filing_url: str) -> None:
        if len(accession) < 10 or len(accession) > 24 or not _is_digits(accession):
            raise gl.vm.UserError("Accession must be 10-24 digits")
        if not filing_url.startswith(SEC_ARCHIVE_PREFIX):
            raise gl.vm.UserError("SEC URL must be official EDGAR archive")
        rest = filing_url[len(SEC_ARCHIVE_PREFIX):]
        cik_prefix = covenant.cik + "/"
        if not rest.startswith(cik_prefix):
            raise gl.vm.UserError("SEC URL CIK must match covenant")
        after_cik = rest[len(cik_prefix):]
        if not after_cik.startswith(accession + "/"):
            raise gl.vm.UserError("SEC URL accession must match claim")
        if ".." in rest or "?" in rest or "#" in rest:
            raise gl.vm.UserError("SEC URL must be official EDGAR archive")
        if not (filing_url.endswith(".htm") or filing_url.endswith(".html") or filing_url.endswith(".txt")):
            raise gl.vm.UserError("SEC URL must be official EDGAR archive")

    def _credit(self, account: Address, amount: bigint) -> None:
        key = _addr_str(account)
        current = bigint(0)
        if key in self.credits:
            current = self.credits[key]
        self.credits[key] = bigint(int(current) + int(amount))

    @gl.public.view
    def get_covenant(self, covenant_id: str) -> Covenant:
        if covenant_id not in self.covenants:
            raise gl.vm.UserError("Covenant not found")
        return self.covenants[covenant_id]

    @gl.public.view
    def get_status(self, covenant_id: str) -> str:
        return self.get_covenant(covenant_id).status

    @gl.public.view
    def get_claim(self, covenant_id: str) -> Claim:
        if covenant_id not in self.latest_claim_ids:
            raise gl.vm.UserError("Claim not found")
        return self.claims[self.latest_claim_ids[covenant_id]]

    @gl.public.view
    def get_credit(self, account: str) -> bigint:
        key = Address(account).as_hex.lower()
        if key not in self.credits:
            return bigint(0)
        return self.credits[key]

    @gl.public.view
    def can_claim(self, covenant_id: str, accession: str) -> bool:
        covenant = self.get_covenant(covenant_id)
        return covenant.status == "ACTIVE" and not self.event_keys.get(
            covenant.cik + ":" + accession + ":" + covenant.trigger_kind, False
        )

    @gl.public.view
    def get_accounting(self) -> dict:
        locked_escrow = bigint(0)
        locked_claim_bonds = bigint(0)
        withdrawable = bigint(0)
        for covenant_id in self.covenants:
            covenant = self.covenants[covenant_id]
            locked_escrow = bigint(int(locked_escrow) + int(covenant.escrow_remaining))
            if covenant.status == "CLAIM_OPEN":
                locked_claim_bonds = bigint(
                    int(locked_claim_bonds) + int(covenant.claim_bond_amount)
                )
        for key in self.credits:
            withdrawable = bigint(int(withdrawable) + int(self.credits[key]))
        return {
            "locked_escrow": locked_escrow,
            "locked_claim_bonds": locked_claim_bonds,
            "withdrawable_credits": withdrawable,
        }

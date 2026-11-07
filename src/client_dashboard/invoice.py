from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy.orm import Session

from .models import AssistantReceipt, Client, Invoice, PricingVersion, Wedding, WeddingPartyMember

MONEY = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def decimal_string(value: Decimal | int | str) -> str:
    return format(money(value), ".2f")


def distance_string(value: Decimal | int | str) -> str:
    return format(Decimal(value).normalize(), "f")


def _time_string(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def _message_time_string(value: time | None) -> str:
    if value is None:
        return "Time TBD"
    return value.strftime("%I:%M %p").lstrip("0")


def _service_minutes(member: WeddingPartyMember, pricing: PricingVersion) -> int:
    if member.role == WeddingPartyMember.ROLE_BRIDE:
        return int(pricing.bride_duration_minutes)
    if member.role == WeddingPartyMember.ROLE_FLOWERGIRL:
        return int(pricing.flowergirl_duration_minutes)
    if member.role in (
        WeddingPartyMember.ROLE_BRIDAL_PARTY,
        WeddingPartyMember.ROLE_JUNIOR_BRIDESMAID,
        WeddingPartyMember.ROLE_MOB,
        WeddingPartyMember.ROLE_OTHER,
    ):
        return int(
            pricing.bridesmaid_updo_duration_minutes
            if member.hairstyle == WeddingPartyMember.HAIRSTYLE_UPDO
            else pricing.bridesmaid_down_duration_minutes
        )
    return 0


def _line(
    description: str,
    quantity: int,
    unit_price: Decimal,
    total: Decimal,
    category: str = "service",
) -> dict[str, Any]:
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": decimal_string(unit_price),
        "total": decimal_string(total),
        "category": category,
    }


@dataclass(frozen=True)
class InvoiceCalculation:
    services_total: Decimal
    travel_total: Decimal
    discount_total: Decimal
    deposit_amount: Decimal
    balance_due: Decimal
    grand_total: Decimal
    line_items: list[dict[str, Any]]
    timing_details: dict[str, Any]
    warnings: list[str]
    calculation_snapshot: dict[str, Any]
    calculation_hash: str
    assistant_receipt: dict[str, Any] | None
    message_text: str


def apply_invoice_calculation(
    session: Session,
    invoice: Invoice,
    calculation: InvoiceCalculation,
    pricing: PricingVersion,
    applied_revision: int,
):
    invoice.pricing_version_id = pricing.id
    invoice.pricing_revision_applied = applied_revision
    for field in (
        "services_total", "travel_total", "discount_total", "deposit_amount",
        "balance_due", "grand_total", "calculation_hash", "calculation_snapshot",
        "line_items", "timing_details", "warnings", "message_text",
    ):
        setattr(invoice, field, getattr(calculation, field))
    session.flush()
    if invoice.assistant_receipt is not None:
        session.delete(invoice.assistant_receipt)
        session.flush()
    if calculation.assistant_receipt is not None:
        session.add(AssistantReceipt(invoice_id=invoice.id, **calculation.assistant_receipt))


def calculate_invoice(
    wedding: Wedding,
    client: Client,
    pricing: PricingVersion,
    members: list[WeddingPartyMember],
) -> InvoiceCalculation:
    if not wedding.address or not wedding.address.strip():
        raise ValueError("Missing required fields: address")

    warnings: list[str] = []
    roles = {member.role for member in members}
    if WeddingPartyMember.ROLE_BRIDE not in roles:
        warnings.append("No bride party member was included.")
    if not members:
        warnings.append("No wedding party members were included.")

    bride_count = sum(member.role == WeddingPartyMember.ROLE_BRIDE for member in members)
    party_count = sum(
        member.role
        in (
            WeddingPartyMember.ROLE_BRIDAL_PARTY,
            WeddingPartyMember.ROLE_JUNIOR_BRIDESMAID,
            WeddingPartyMember.ROLE_MOB,
            WeddingPartyMember.ROLE_OTHER,
        )
        for member in members
    )
    flowergirl_count = sum(member.role == WeddingPartyMember.ROLE_FLOWERGIRL for member in members)
    assisted_party_count = sum(
        member.assistant
        and member.role
        in (
            WeddingPartyMember.ROLE_BRIDAL_PARTY,
            WeddingPartyMember.ROLE_JUNIOR_BRIDESMAID,
            WeddingPartyMember.ROLE_MOB,
            WeddingPartyMember.ROLE_OTHER,
        )
        for member in members
    )
    # Assistant billing is determined by the party-member assignments. The
    # wedding-level flag is retained for compatibility but must not create an
    # assistant fee when every member is assigned to the primary stylist.
    effective_assistant = any(member.assistant for member in members)

    bride_total = money(pricing.bride_price * bride_count)
    party_total = money(pricing.bridesmaid_price * party_count)
    flowergirl_total = money(pricing.flowergirl_price * flowergirl_count)
    # Bridal trials are charged separately and are not part of this invoice.
    trial_total = ZERO

    line_items: list[dict[str, Any]] = []
    if bride_count:
        line_items.append(_line("Bride", bride_count, pricing.bride_price, bride_total))
    if party_count:
        line_items.append(_line("Bridal party", party_count, pricing.bridesmaid_price, party_total))
    if flowergirl_count:
        line_items.append(_line("Flower girl", flowergirl_count, pricing.flowergirl_price, flowergirl_total))
    services_total = money(bride_total + party_total + flowergirl_total)

    travel_total = ZERO
    discount_total = ZERO
    if wedding.miles_one_way is None:
        raise ValueError("Missing required fields: miles_one_way")
    miles = money(wedding.miles_one_way)
    if miles > ZERO:
        regular_travel = money(pricing.base_travel_fee + miles * pricing.travel_fee * 2)
        if client.is_referral:
            discount_total = money(regular_travel * pricing.travel_discount_percentage / Decimal("100"))
        travel_total = regular_travel
        line_items.append(_line("Travel", 1, regular_travel, regular_travel, "fee"))

    additional_fees = ZERO
    if effective_assistant:
        additional_fees = money(additional_fees + pricing.assistant_fee)
        line_items.append(_line("Assistant fee", 1, pricing.assistant_fee, pricing.assistant_fee, "fee"))

    # The primary stylist and assistant work concurrently. The 15-minute buffer
    # is added after selecting the longer workload.
    primary_minutes = sum(_service_minutes(member, pricing) for member in members if not member.assistant)
    assistant_minutes = sum(_service_minutes(member, pricing) for member in members if member.assistant)
    service_minutes = max(primary_minutes, assistant_minutes) + 15
    start_time: time | None = None
    if wedding.ready_by is None:
        raise ValueError("Missing required fields: ready_by")
    ready_datetime = datetime.combine(wedding.wedding_date, wedding.ready_by)
    start_datetime = ready_datetime - timedelta(minutes=service_minutes)
    start_time = start_datetime.time()
    if start_time < time(8, 0):
        additional_fees = money(additional_fees + pricing.early_morning_fee)
        line_items.append(_line("Early morning fee", 1, pricing.early_morning_fee, pricing.early_morning_fee, "fee"))

    referral_text = "Referral travel discount" if discount_total else None
    if discount_total:
        line_items.append(_line(referral_text, 1, -discount_total, -discount_total, "discount"))

    grand_total = money(services_total + travel_total + additional_fees - discount_total)
    # The deposit is based on hair services only, not travel or other fees.
    deposit_amount = money(services_total * pricing.deposit_percentage / Decimal("100"))
    balance_due = money(grand_total - deposit_amount)

    timing_details = {
        "balance_due_date": wedding.wedding_date.isoformat(),
        "ready_by": _time_string(wedding.ready_by),
        "start_time": _time_string(start_time),
        "service_minutes": service_minutes,
        "primary_stylist_minutes": primary_minutes,
        "assistant_minutes": assistant_minutes,
        "service_durations": {
            "bride": pricing.bride_duration_minutes,
            "bridal_party_updo": pricing.bridesmaid_updo_duration_minutes,
            "bridal_party_down": pricing.bridesmaid_down_duration_minutes,
            "flowergirl": pricing.flowergirl_duration_minutes,
        },
    }
    snapshot = {
        "pricing_version_id": pricing.id,
        "pricing": {
            "bride_price": decimal_string(pricing.bride_price),
            "trial_price": decimal_string(pricing.trial_price),
            "bridesmaid_price": decimal_string(pricing.bridesmaid_price),
            "flowergirl_price": decimal_string(pricing.flowergirl_price),
            "early_morning_fee": decimal_string(pricing.early_morning_fee),
            "assistant_fee": decimal_string(pricing.assistant_fee),
            "assistant_cut": decimal_string(pricing.assistant_cut),
            "assistant_bridesmaid_cut": decimal_string(pricing.assistant_bridesmaid_cut),
            "base_travel_fee": decimal_string(pricing.base_travel_fee),
            "travel_fee": decimal_string(pricing.travel_fee),
            "deposit_percentage": decimal_string(pricing.deposit_percentage),
            "travel_discount_percentage": decimal_string(pricing.travel_discount_percentage),
        },
        "wedding": {
            "id": wedding.id,
            "wedding_date": wedding.wedding_date.isoformat(),
            "address": wedding.address,
            "city": wedding.city,
            "venue": wedding.venue,
            "miles_one_way": distance_string(wedding.miles_one_way),
            "ready_by": _time_string(wedding.ready_by),
            "assistant": effective_assistant,
            "bridal_trial_status": wedding.bridal_trial_status,
        },
        "client": {"id": client.id, "is_referral": client.is_referral},
        "party_members": [
            {"id": member.id, "role": member.role, "hairstyle": member.hairstyle, "assistant": member.assistant}
            for member in members
        ],
        "line_items": line_items,
        "timing_details": timing_details,
        "totals": {
            "services_total": decimal_string(services_total),
            "travel_total": decimal_string(travel_total),
            "discount_total": decimal_string(discount_total),
            "deposit_amount": decimal_string(deposit_amount),
            "balance_due": decimal_string(balance_due),
            "grand_total": decimal_string(grand_total),
        },
        "warnings": warnings,
    }
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    calculation_hash = hashlib.sha256(encoded).hexdigest()

    receipt = None
    if effective_assistant:
        assistant_cut = money(pricing.assistant_cut)
        assistant_party_pay = money(pricing.assistant_bridesmaid_cut * assisted_party_count)
        assistant_total = money(assistant_cut + assistant_party_pay)
        receipt = {
            "assistant_cut": decimal_string(assistant_cut),
            "assisted_bridesmaid_count": assisted_party_count,
            "assisted_bridesmaid_pay": decimal_string(assistant_party_pay),
            "total_paid_to_assistant": decimal_string(assistant_total),
            "business_takehome": decimal_string(grand_total - assistant_total),
        }

    message_lines = [
        f"Invoice for {client.name}\n",
        f"Wedding date: {wedding.wedding_date.isoformat()}",
    ]
    if wedding.city:
        message_lines.append(f"City: {wedding.city}")
    if wedding.venue:
        message_lines.append(f"Venue: {wedding.venue}")
    message_lines.extend([
        f"Address: {wedding.address}\n",
        f"Start time: {_message_time_string(start_time)}",
        f"Ready by: {_message_time_string(wedding.ready_by)}\n",
        f"Start time is dependent on what each bridal party member wants, updo/half-up! ",
        f"For reference:",
        f" - Bride: {pricing.bride_duration_minutes} min",
        f" - Bridal party updo: {pricing.bridesmaid_updo_duration_minutes} min",
        f" - Bridal party half-up style: {pricing.bridesmaid_down_duration_minutes} min",
        f" - Glower girl: {pricing.flowergirl_duration_minutes} min",
        "* I also plan to have everyone done 15 minutes before the time I’m told. "
        "Craziness kicks in and there’s always last minute things bridal groups are forgetting!",
    ])
    if wedding.bridal_trial_status not in (
        Wedding.BRIDAL_TRIAL_NOT_INTERESTED,
        Wedding.BRIDAL_TRIAL_CANCELLED,
    ):
        message_lines.append("Bridal trial: charged separately")

    message_lines.append("\nHair:")
    message_lines.extend(
        f" - {item['description']}: {item['quantity']} × ${item['unit_price']} = ${item['total']}"
        for item in line_items
        if item.get("category", "service") == "service"
    )

    message_lines.append("\nAdditional Fees:")
    message_lines.extend(
        f" - {item['description']}: ${item['total']}"
        for item in line_items
        if item.get("category") in ("fee", "discount")
    )

    if discount_total:
        message_lines.append(
            f"You save ${decimal_string(discount_total)} "
            f"with a {decimal_string(pricing.travel_discount_percentage)}% discount applied"
        )
    message_lines.extend([
        f"\nTotal: ${decimal_string(grand_total)}",
        f"Non-refundable deposit: ${decimal_string(deposit_amount)}",
        f"Remaining balance: ${decimal_string(balance_due)}",
        f"Balance due date: {wedding.wedding_date.isoformat()} @ 8:00 pm",
    ])
    message_text = "\n".join(message_lines)

    return InvoiceCalculation(
        services_total=services_total,
        travel_total=travel_total,
        discount_total=discount_total,
        deposit_amount=deposit_amount,
        balance_due=balance_due,
        grand_total=grand_total,
        line_items=line_items,
        timing_details=timing_details,
        warnings=warnings,
        calculation_snapshot=snapshot,
        calculation_hash=calculation_hash,
        assistant_receipt=receipt,
        message_text=message_text,
    )

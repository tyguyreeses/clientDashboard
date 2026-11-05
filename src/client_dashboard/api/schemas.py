from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WeddingStatus = Literal[0, 1, 2, 3, 4, 5, 6]
BridalTrialStatus = Literal["not_interested", "interested", "link_sent", "booked", "complete", "cancelled"]
PartyRole = Literal["B", "P", "J", "F", "M", "O"]
HairStyle = Literal["U", "D"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampRead(ORMModel):
    created_at: datetime
    updated_at: datetime


class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    social_media: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    inquiry_date: date | None = None
    notes: str | None = None
    planning_stage: str | None = Field(default=None, max_length=30)
    makeup_interest: bool | None = None
    recommendations_if_unavailable: bool | None = None
    referral_name: str | None = Field(default=None, max_length=255)
    hair_service_details: str | None = None
    is_referral: bool = False


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    social_media: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    inquiry_date: date | None = None
    notes: str | None = None
    planning_stage: str | None = Field(default=None, max_length=30)
    makeup_interest: bool | None = None
    recommendations_if_unavailable: bool | None = None
    referral_name: str | None = Field(default=None, max_length=255)
    hair_service_details: str | None = None
    is_referral: bool | None = None
    archived: bool | None = None


class ClientRead(ClientBase, TimestampRead):
    id: int
    archived: bool
    invoice_warnings: list[str] = Field(default_factory=list)


class ClientSummary(ClientRead):
    pass


class WeddingBase(BaseModel):
    client_id: int
    wedding_date: date
    address: str = Field(min_length=1, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    venue: str | None = Field(default=None, max_length=255)
    miles_one_way: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    ready_by: time | None = None
    status: WeddingStatus = 1
    invoice_sent_at: datetime | None = None
    bridal_trial_status: BridalTrialStatus = "not_interested"
    assistant: bool = False


class WeddingCreate(WeddingBase):
    hair_service_count: int | None = Field(default=None, ge=0)


class WeddingUpdate(BaseModel):
    client_id: int | None = None
    wedding_date: date | None = None
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    venue: str | None = Field(default=None, max_length=255)
    miles_one_way: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    ready_by: time | None = None
    status: WeddingStatus | None = None
    invoice_sent_at: datetime | None = None
    bridal_trial_status: BridalTrialStatus | None = None
    assistant: bool | None = None


class WeddingPartyMemberBase(BaseModel):
    role: PartyRole
    hairstyle: HairStyle
    assistant: bool = False
    # Deprecated compatibility fields for older API clients.
    by_me_quantity: int | None = Field(default=None, ge=0)
    by_assistant_quantity: int | None = Field(default=None, ge=0)


class WeddingPartyMemberCreate(WeddingPartyMemberBase):
    pass


class WeddingPartyMemberUpdate(BaseModel):
    role: PartyRole | None = None
    hairstyle: HairStyle | None = None
    assistant: bool | None = None
    # Deprecated compatibility fields for older API clients.
    by_me_quantity: int | None = Field(default=None, ge=0)
    by_assistant_quantity: int | None = Field(default=None, ge=0)

class WeddingPartyMemberRead(WeddingPartyMemberBase, ORMModel):
    id: int
    wedding_id: int
    invoice_warnings: list[str] = Field(default_factory=list)


class WeddingRead(TimestampRead):
    id: int
    client_id: int
    wedding_date: date
    address: str
    city: str | None
    venue: str | None
    miles_one_way: Decimal | None
    ready_by: time | None
    status: WeddingStatus
    invoice_sent_at: datetime | None
    bridal_trial_status: BridalTrialStatus
    assistant: bool
    client: ClientSummary | None = None
    party_members: list[WeddingPartyMemberRead] = Field(default_factory=list)
    invoice_warnings: list[str] = Field(default_factory=list)


class WeddingListItem(TimestampRead):
    id: int
    client_id: int
    wedding_date: date
    address: str
    city: str | None
    venue: str | None
    miles_one_way: Decimal | None
    party_members: list[WeddingPartyMemberRead] = Field(default_factory=list)
    ready_by: time | None
    status: WeddingStatus
    bridal_trial_status: BridalTrialStatus
    assistant: bool
    client: ClientSummary | None = None


class PricingVersionBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    bride_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    trial_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    bridesmaid_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    flowergirl_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    early_morning_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    assistant_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    assistant_bridesmaid_cut: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    base_travel_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    travel_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    deposit_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    travel_discount_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    bride_duration_minutes: int = Field(default=75, ge=0)
    bridesmaid_updo_duration_minutes: int = Field(default=30, ge=0)
    bridesmaid_down_duration_minutes: int = Field(default=45, ge=0)
    flowergirl_duration_minutes: int = Field(default=30, ge=0)
    assistant_travel_fee_cut: Decimal = Field(default=Decimal("15.00"), ge=0, max_digits=10, decimal_places=2)


class PricingVersionCreate(PricingVersionBase):
    pass


class PricingVersionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    bride_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    trial_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    bridesmaid_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    flowergirl_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    early_morning_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    assistant_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    assistant_bridesmaid_cut: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    base_travel_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    travel_fee: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    deposit_percentage: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    travel_discount_percentage: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    bride_duration_minutes: int | None = Field(default=None, ge=0)
    bridesmaid_updo_duration_minutes: int | None = Field(default=None, ge=0)
    bridesmaid_down_duration_minutes: int | None = Field(default=None, ge=0)
    flowergirl_duration_minutes: int | None = Field(default=None, ge=0)
    assistant_travel_fee_cut: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class PricingVersionRead(PricingVersionBase, TimestampRead):
    id: int


class InvoiceBase(ORMModel):
    wedding_id: int
    pricing_version_id: int
    services_total: Decimal
    travel_total: Decimal
    discount_total: Decimal
    deposit_amount: Decimal
    balance_due: Decimal
    grand_total: Decimal
    calculation_hash: str
    calculation_snapshot: dict[str, Any]
    line_items: list[dict[str, Any]]
    timing_details: dict[str, Any]
    warnings: list[str]
    message_text: str


class InvoiceRead(InvoiceBase, TimestampRead):
    id: int
    pricing_version: PricingVersionRead | None = None


class InvoiceListItem(InvoiceBase, TimestampRead):
    id: int


class AssistantReceiptRead(ORMModel):
    id: int
    invoice_id: int
    assistant_travel: Decimal
    assistant_service_pay: Decimal
    assisted_bridesmaid_count: int
    assisted_bridesmaid_pay: Decimal
    total_paid_to_assistant: Decimal
    business_takehome: Decimal
    created_at: datetime
    updated_at: datetime


class InvoiceGenerationRequest(BaseModel):
    pricing_version_id: int | None = None


class InvoiceGenerationResponse(BaseModel):
    created: bool
    invoice: InvoiceRead


class PaymentBase(BaseModel):
    wedding_id: int
    amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    payment_date: date
    payment_method: str = Field(min_length=1, max_length=50)
    notes: str | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    wedding_id: int | None = None
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    payment_date: date | None = None
    payment_method: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = None


class PaymentRead(PaymentBase, TimestampRead):
    id: int

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

WeddingStatus = Literal[0, 1, 2, 3, 4, 5, 6]
BridalTrialStatus = Literal["not_interested", "interested", "link_sent", "booked", "complete", "cancelled"]
PartyRole = Literal["B", "P", "J", "F", "M", "O"]
HairStyle = Literal["U", "D"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampRead(ORMModel):
    created_at: datetime
    updated_at: datetime


class PublicInquiryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=50)
    social_media: str = Field(min_length=1, max_length=255)
    wedding_date: date
    address: str = Field(min_length=1, max_length=255)
    bride_count: StrictInt = Field(default=1, ge=0)
    party_count: StrictInt = Field(default=0, ge=0)
    junior_count: StrictInt = Field(default=0, ge=0)
    ready_by: time
    time_firmness: Literal["firm", "estimate"]
    location_type: Literal["home", "venue"]
    makeup_interest: bool
    bridal_trial: Literal["yes", "thinking"]
    planning_stage: Literal["looking", "invoice", "book"]
    recommendations_if_unavailable: bool | None = None
    referral_source: Literal["Instagram", "Facebook", "Friend", "Other"]
    referral_other: str | None = Field(default=None, max_length=100)
    referral_name: str | None = Field(default=None, max_length=255)
    additional_notes: str | None = Field(default=None, max_length=2000)
    contact_consent: bool
    website: str = ""

    @field_validator("name", "email", "social_media", "address")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @model_validator(mode="after")
    def valid_inquiry(self):
        if self.bride_count + self.party_count + self.junior_count > 10:
            raise ValueError("No more than 10 service members may be requested")
        if self.referral_source == "Other":
            if not self.referral_other or not self.referral_other.strip():
                raise ValueError("Please tell us how you heard about Maddie")
            if len(self.referral_other) > 100:
                raise ValueError("Referral source must be 100 characters or fewer")
        if not self.contact_consent:
            raise ValueError("Contact consent is required")
        return self


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


class WeddingPartyMemberBase(BaseModel):
    role: PartyRole
    hairstyle: HairStyle = "D"
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


class WeddingStatusProgressRead(ORMModel):
    status: WeddingStatus
    forward_entered_at: datetime


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
    status_progress: list[WeddingStatusProgressRead] = Field(default_factory=list)
    bridal_trial_status: BridalTrialStatus
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
    status_progress: list[WeddingStatusProgressRead] = Field(default_factory=list)
    bridal_trial_status: BridalTrialStatus
    client: ClientSummary | None = None


class PricingVersionBase(BaseModel):
    name: str
    bride_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    trial_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    bridesmaid_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    flowergirl_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    early_morning_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    assistant_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    assistant_cut: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    assistant_bridesmaid_cut: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    base_travel_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    travel_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    deposit_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    travel_discount_percentage: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    bride_duration_minutes: int = Field(ge=0)
    bridesmaid_updo_duration_minutes: int = Field(ge=0)
    bridesmaid_down_duration_minutes: int = Field(ge=0)
    flowergirl_duration_minutes: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 15:
            raise ValueError("Pricing name must be 1-15 characters after trimming")
        return value


class PricingVersionRead(PricingVersionBase, TimestampRead):
    id: int
    revision: int
    is_default: bool = False
    created_date: date | None = None
    correction_deadline: date | None = None
    can_delete: bool = False
    delete_block_reason: str | None = None
    reference_count: int = 0


class PricingImpact(BaseModel):
    invoice_id: int
    pricing_revision_applied: int
    client_name: str
    wedding_id: int
    wedding_date: date
    workflow_status: int
    archived: bool
    grand_total: Decimal
    payment_total: Decimal
    payment_state: Literal["unpaid", "partial", "paid"]


class PricingPreviewRead(BaseModel):
    action: Literal["correct", "create"]
    target_id: int | None
    target_revision: int | None
    current_default_id: int | None
    preview_date: date
    correction_deadline: date | None
    affected_records: list[PricingImpact]
    confirmation_fingerprint: str


class PricingSave(PricingVersionBase):
    confirmed: Literal[True]
    confirmation_fingerprint: str = Field(min_length=1)


class PricingSaveRead(BaseModel):
    action: Literal["correct", "create"]
    version: PricingVersionRead
    current_default_id: int
    affected_records: list[PricingImpact]


class PricingDeleteRead(BaseModel):
    deleted_id: int
    new_default: PricingVersionRead | None


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
    pricing_revision_applied: int
    pricing_stale: bool


class InvoiceRead(InvoiceBase, TimestampRead):
    id: int
    pricing_version: PricingVersionRead | None = None


class InvoiceListItem(InvoiceBase, TimestampRead):
    id: int


class AssistantReceiptRead(ORMModel):
    id: int
    invoice_id: int
    assistant_cut: Decimal
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

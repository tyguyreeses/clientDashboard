from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

WeddingStatus = Literal[0, 1, 2, 3, 4]
PartyRole = Literal["B", "P", "J", "F"]
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


class ClientRead(ClientBase, TimestampRead):
    id: int


class ClientSummary(ClientRead):
    pass


class WeddingBase(BaseModel):
    client_id: int
    wedding_date: date
    location: str | None = Field(default=None, max_length=255)
    miles_one_way: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    ready_by: time | None = None
    status: WeddingStatus = 1
    bridal_trial: bool = False
    assistant: bool = False


class WeddingCreate(WeddingBase):
    pass


class WeddingUpdate(BaseModel):
    client_id: int | None = None
    wedding_date: date | None = None
    location: str | None = Field(default=None, max_length=255)
    miles_one_way: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    ready_by: time | None = None
    status: WeddingStatus | None = None
    bridal_trial: bool | None = None
    assistant: bool | None = None


class WeddingPartyMemberBase(BaseModel):
    role: PartyRole
    hairstyle: HairStyle
    by_me_quantity: int = Field(default=0, ge=0)
    by_assistant_quantity: int = Field(default=0, ge=0)


class WeddingPartyMemberCreate(WeddingPartyMemberBase):
    pass


class WeddingPartyMemberUpdate(BaseModel):
    role: PartyRole | None = None
    hairstyle: HairStyle | None = None
    by_me_quantity: int | None = Field(default=None, ge=0)
    by_assistant_quantity: int | None = Field(default=None, ge=0)


class WeddingPartyMemberRead(WeddingPartyMemberBase, ORMModel):
    id: int
    wedding_id: int


class WeddingRead(TimestampRead):
    id: int
    client_id: int
    wedding_date: date
    location: str | None
    miles_one_way: Decimal | None
    ready_by: time | None
    status: WeddingStatus
    bridal_trial: bool
    assistant: bool
    client: ClientSummary | None = None
    party_members: list[WeddingPartyMemberRead] = Field(default_factory=list)


class WeddingListItem(TimestampRead):
    id: int
    client_id: int
    wedding_date: date
    location: str | None
    miles_one_way: Decimal | None
    ready_by: time | None
    status: WeddingStatus
    bridal_trial: bool
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


class PricingVersionRead(PricingVersionBase, TimestampRead):
    id: int


class InvoiceBase(ORMModel):
    wedding_id: int
    version_number: int
    pricing_version_id: int
    services_total: Decimal
    travel_total: Decimal
    discount_total: Decimal
    deposit_amount: Decimal
    balance_due: Decimal
    grand_total: Decimal


class InvoiceRead(InvoiceBase, TimestampRead):
    id: int
    pricing_version: PricingVersionRead | None = None


class InvoiceListItem(InvoiceBase, TimestampRead):
    id: int


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


from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class Client(TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_source", "source"),
        Index("ix_clients_inquiry_date", "inquiry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    social_media: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(100))
    inquiry_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    weddings: Mapped[list[Wedding]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )


class Wedding(TimestampMixin, Base):
    __tablename__ = "weddings"
    __table_args__ = (
        Index("ix_weddings_client_id", "client_id"),
        Index("ix_weddings_wedding_date", "wedding_date"),
        Index("ix_weddings_status", "status"),
        CheckConstraint(
            "status IN (0, 1, 2, 3, 4)",
            name="ck_weddings_status_valid",
        ),
        CheckConstraint("miles_one_way IS NULL OR miles_one_way >= 0", name="ck_weddings_miles_nonnegative"),
    )

    STATUS_CANCELLED = 0
    STATUS_INQUIRED = 1
    STATUS_RESPONDED = 2
    STATUS_AWAITING_DEPOSIT = 3
    STATUS_DEPOSIT_RECEIVED = 4
    STATUS_VALUES = (
        STATUS_CANCELLED,
        STATUS_INQUIRED,
        STATUS_RESPONDED,
        STATUS_AWAITING_DEPOSIT,
        STATUS_DEPOSIT_RECEIVED,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
    )
    wedding_date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    miles_one_way: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    ready_by: Mapped[time | None] = mapped_column(Time)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=STATUS_INQUIRED)
    bridal_trial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assistant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    client: Mapped[Client] = relationship(back_populates="weddings")
    party_members: Mapped[list[WeddingPartyMember]] = relationship(
        back_populates="wedding",
        cascade="all, delete-orphan",
    )
    invoices: Mapped[list[Invoice]] = relationship(
        back_populates="wedding",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="wedding",
        cascade="all, delete-orphan",
    )


class WeddingPartyMember(Base):
    __tablename__ = "wedding_party_members"
    __table_args__ = (
        Index("ix_wedding_party_members_wedding_id", "wedding_id"),
        CheckConstraint(
            "role IN ('B', 'P', 'J', 'F')",
            name="ck_wedding_party_members_role_valid",
        ),
        CheckConstraint(
            "hairstyle IN ('U', 'D')",
            name="ck_wedding_party_members_hairstyle_valid",
        ),
        CheckConstraint("by_me_quantity >= 0", name="ck_wedding_party_members_by_me_nonnegative"),
        CheckConstraint("by_assistant_quantity >= 0", name="ck_wedding_party_members_by_assistant_nonnegative"),
    )

    ROLE_BRIDE = "B"
    ROLE_BRIDAL_PARTY = "P"
    ROLE_JUNIOR_BRIDESMAID = "J"
    ROLE_FLOWERGIRL = "F"
    ROLE_VALUES = (
        ROLE_BRIDE,
        ROLE_BRIDAL_PARTY,
        ROLE_JUNIOR_BRIDESMAID,
        ROLE_FLOWERGIRL,
    )

    HAIRSTYLE_UPDO = "U"
    HAIRSTYLE_DOWN = "D"
    HAIRSTYLE_VALUES = (HAIRSTYLE_UPDO, HAIRSTYLE_DOWN)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wedding_id: Mapped[int] = mapped_column(
        ForeignKey("weddings.id"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(1), nullable=False)
    hairstyle: Mapped[str] = mapped_column(String(1), nullable=False)
    by_me_quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    by_assistant_quantity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    wedding: Mapped[Wedding] = relationship(back_populates="party_members")


class PricingVersion(TimestampMixin, Base):
    __tablename__ = "pricing_versions"
    __table_args__ = (
        Index("ix_pricing_versions_name", "name", unique=True),
        CheckConstraint("bride_price >= 0", name="ck_pricing_bride_price_nonnegative"),
        CheckConstraint("trial_price >= 0", name="ck_pricing_trial_price_nonnegative"),
        CheckConstraint("bridesmaid_price >= 0", name="ck_pricing_bridesmaid_price_nonnegative"),
        CheckConstraint("flowergirl_price >= 0", name="ck_pricing_flowergirl_price_nonnegative"),
        CheckConstraint("early_morning_fee >= 0", name="ck_pricing_early_morning_nonnegative"),
        CheckConstraint("assistant_fee >= 0", name="ck_pricing_assistant_fee_nonnegative"),
        CheckConstraint("assistant_bridesmaid_cut BETWEEN 0 AND 100", name="ck_pricing_assistant_cut_percent"),
        CheckConstraint("base_travel_fee >= 0", name="ck_pricing_base_travel_nonnegative"),
        CheckConstraint("travel_fee >= 0", name="ck_pricing_travel_nonnegative"),
        CheckConstraint("deposit_percentage BETWEEN 0 AND 100", name="ck_pricing_deposit_percent"),
        CheckConstraint("travel_discount_percentage BETWEEN 0 AND 100", name="ck_pricing_travel_discount_percent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bride_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    trial_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bridesmaid_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    flowergirl_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    early_morning_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    assistant_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    assistant_bridesmaid_cut: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    base_travel_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    travel_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    travel_discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    invoices: Mapped[list[Invoice]] = relationship(back_populates="pricing_version")


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_pricing_version_id", "pricing_version_id"),
        Index(
            "uq_invoices_wedding_id_version_number",
            "wedding_id",
            "version_number",
            unique=True,
        ),
        CheckConstraint("version_number >= 1", name="ck_invoices_version_positive"),
        CheckConstraint("services_total >= 0", name="ck_invoices_services_nonnegative"),
        CheckConstraint("travel_total >= 0", name="ck_invoices_travel_nonnegative"),
        CheckConstraint("discount_total >= 0", name="ck_invoices_discount_nonnegative"),
        CheckConstraint("deposit_amount >= 0", name="ck_invoices_deposit_nonnegative"),
        CheckConstraint("balance_due >= 0", name="ck_invoices_balance_nonnegative"),
        CheckConstraint("grand_total >= 0", name="ck_invoices_grand_total_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wedding_id: Mapped[int] = mapped_column(
        ForeignKey("weddings.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    pricing_version_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_versions.id"),
        nullable=False,
    )
    services_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    travel_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    balance_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))

    wedding: Mapped[Wedding] = relationship(back_populates="invoices")
    pricing_version: Mapped[PricingVersion] = relationship(back_populates="invoices")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_wedding_id", "wedding_id"),
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wedding_id: Mapped[int] = mapped_column(
        ForeignKey("weddings.id"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    wedding: Mapped[Wedding] = relationship(back_populates="payments")

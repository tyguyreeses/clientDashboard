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
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
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
    planning_stage: Mapped[str | None] = mapped_column(String(30))
    makeup_interest: Mapped[bool | None] = mapped_column(Boolean)
    recommendations_if_unavailable: Mapped[bool | None] = mapped_column(Boolean)
    referral_name: Mapped[str | None] = mapped_column(String(255))
    hair_service_details: Mapped[str | None] = mapped_column(Text)
    is_referral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
            "status IN (0, 1, 2, 3, 4, 5, 6)",
            name="ck_weddings_status_valid",
        ),
        CheckConstraint("miles_one_way IS NULL OR miles_one_way >= 0", name="ck_weddings_miles_nonnegative"),
        CheckConstraint(
            "bridal_trial_status IN ('not_interested', 'interested', 'link_sent', 'booked', 'complete', 'cancelled')",
            name="ck_weddings_bridal_trial_status_valid",
        ),
    )

    STATUS_CANCELLED = 0
    STATUS_INQUIRED = 1
    STATUS_RESPONDED = 2
    STATUS_AWAITING_DEPOSIT = 3
    STATUS_DEPOSIT_RECEIVED = 4
    STATUS_PAID_IN_FULL = 5
    STATUS_COMPLETED = 6
    STATUS_VALUES = (
        STATUS_CANCELLED,
        STATUS_INQUIRED,
        STATUS_RESPONDED,
        STATUS_AWAITING_DEPOSIT,
        STATUS_DEPOSIT_RECEIVED,
        STATUS_PAID_IN_FULL,
        STATUS_COMPLETED,
    )

    BRIDAL_TRIAL_NOT_INTERESTED = "not_interested"
    BRIDAL_TRIAL_INTERESTED = "interested"
    BRIDAL_TRIAL_LINK_SENT = "link_sent"
    BRIDAL_TRIAL_BOOKED = "booked"
    BRIDAL_TRIAL_COMPLETE = "complete"
    BRIDAL_TRIAL_CANCELLED = "cancelled"
    BRIDAL_TRIAL_STATUS_VALUES = (
        BRIDAL_TRIAL_NOT_INTERESTED,
        BRIDAL_TRIAL_INTERESTED,
        BRIDAL_TRIAL_LINK_SENT,
        BRIDAL_TRIAL_BOOKED,
        BRIDAL_TRIAL_COMPLETE,
        BRIDAL_TRIAL_CANCELLED,
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
    )
    wedding_date: Mapped[date] = mapped_column(Date, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(255))
    venue: Mapped[str | None] = mapped_column(String(255))
    miles_one_way: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    ready_by: Mapped[time | None] = mapped_column(Time)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=STATUS_INQUIRED)
    invoice_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bridal_trial_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=BRIDAL_TRIAL_NOT_INTERESTED
    )
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
    status_progress: Mapped[list[WeddingStatusProgress]] = relationship(
        back_populates="wedding",
        cascade="all, delete-orphan",
    )


class WeddingStatusProgress(Base):
    __tablename__ = "wedding_status_progress"
    __table_args__ = (
        Index("ix_wedding_status_progress_wedding_id", "wedding_id"),
        UniqueConstraint("wedding_id", "status", name="uq_wedding_status_progress_status"),
        CheckConstraint("status IN (0, 1, 2, 3, 4, 5, 6)", name="ck_wedding_status_progress_status_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wedding_id: Mapped[int] = mapped_column(ForeignKey("weddings.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    forward_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    wedding: Mapped[Wedding] = relationship(back_populates="status_progress")


class WeddingPartyMember(Base):
    __tablename__ = "wedding_party_members"
    __table_args__ = (
        Index("ix_wedding_party_members_wedding_id", "wedding_id"),
        CheckConstraint(
            "role IN ('B', 'P', 'J', 'F', 'M', 'O')",
            name="ck_wedding_party_members_role_valid",
        ),
        CheckConstraint(
            "hairstyle IN ('U', 'D')",
            name="ck_wedding_party_members_hairstyle_valid",
        ),
        CheckConstraint("assistant IN (0, 1)", name="ck_wedding_party_members_assistant_valid"),
    )

    ROLE_BRIDE = "B"
    ROLE_BRIDAL_PARTY = "P"
    ROLE_JUNIOR_BRIDESMAID = "J"
    ROLE_FLOWERGIRL = "F"
    ROLE_MOB = "M"
    ROLE_OTHER = "O"
    ROLE_VALUES = (
        ROLE_BRIDE,
        ROLE_BRIDAL_PARTY,
        ROLE_JUNIOR_BRIDESMAID,
        ROLE_FLOWERGIRL,
        ROLE_MOB,
        ROLE_OTHER,
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
    assistant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    wedding: Mapped[Wedding] = relationship(back_populates="party_members")


class PricingVersion(TimestampMixin, Base):
    __tablename__ = "pricing_versions"
    __table_args__ = (
        Index("ix_pricing_versions_name_normalized", "name_normalized", unique=True),
        CheckConstraint("length(trim(name)) > 0", name="ck_pricing_name_nonblank"),
        CheckConstraint("length(name) <= 15", name="ck_pricing_name_max_length"),
        CheckConstraint("bride_price >= 0", name="ck_pricing_bride_price_nonnegative"),
        CheckConstraint("trial_price >= 0", name="ck_pricing_trial_price_nonnegative"),
        CheckConstraint("bridesmaid_price >= 0", name="ck_pricing_bridesmaid_price_nonnegative"),
        CheckConstraint("flowergirl_price >= 0", name="ck_pricing_flowergirl_price_nonnegative"),
        CheckConstraint("early_morning_fee >= 0", name="ck_pricing_early_morning_nonnegative"),
        CheckConstraint("assistant_fee >= 0", name="ck_pricing_assistant_fee_nonnegative"),
        CheckConstraint("assistant_bridesmaid_cut >= 0", name="ck_pricing_assistant_cut_nonnegative"),
        CheckConstraint("base_travel_fee >= 0", name="ck_pricing_base_travel_nonnegative"),
        CheckConstraint("travel_fee >= 0", name="ck_pricing_travel_nonnegative"),
        CheckConstraint("deposit_percentage BETWEEN 0 AND 100", name="ck_pricing_deposit_percent"),
        CheckConstraint("travel_discount_percentage BETWEEN 0 AND 100", name="ck_pricing_travel_discount_percent"),
        CheckConstraint("bride_duration_minutes >= 0", name="ck_pricing_bride_duration_nonnegative"),
        CheckConstraint("bridesmaid_updo_duration_minutes >= 0", name="ck_pricing_bridesmaid_updo_duration_nonnegative"),
        CheckConstraint("bridesmaid_down_duration_minutes >= 0", name="ck_pricing_bridesmaid_down_duration_nonnegative"),
        CheckConstraint("flowergirl_duration_minutes >= 0", name="ck_pricing_flowergirl_duration_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bride_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    trial_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bridesmaid_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    flowergirl_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    early_morning_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    assistant_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    assistant_cut: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("50.00"))
    assistant_bridesmaid_cut: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_travel_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    travel_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    travel_discount_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    bride_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=75)
    bridesmaid_updo_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    bridesmaid_down_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    flowergirl_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    invoices: Mapped[list[Invoice]] = relationship(back_populates="pricing_version")


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_pricing_version_id", "pricing_version_id"),
        Index("uq_invoices_wedding_id", "wedding_id", unique=True),
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
    calculation_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    calculation_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    line_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    timing_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    message_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pricing_revision_applied: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    @property
    def pricing_stale(self) -> bool:
        return bool(
            self.pricing_version
            and self.pricing_revision_applied != self.pricing_version.revision
        )

    wedding: Mapped[Wedding] = relationship(back_populates="invoices")
    pricing_version: Mapped[PricingVersion] = relationship(back_populates="invoices")
    assistant_receipt: Mapped[AssistantReceipt | None] = relationship(
        back_populates="invoice", uselist=False, cascade="all, delete-orphan"
    )


class AssistantReceipt(TimestampMixin, Base):
    __tablename__ = "assistant_receipts"
    __table_args__ = (Index("ix_assistant_receipts_invoice_id", "invoice_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    assistant_cut: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    assisted_bridesmaid_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assisted_bridesmaid_pay: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_paid_to_assistant: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    business_takehome: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="assistant_receipt")


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


class InquiryAttempt(Base):
    __tablename__ = "inquiry_attempts"
    __table_args__ = (Index("ix_inquiry_attempts_ip_attempted_at", "ip_address", "attempted_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    google_subject: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()


class OAuthAttempt(Base):
    __tablename__ = "oauth_attempts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nonce_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pkce_challenge: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    route_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_ip: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AuthState(Base):
    __tablename__ = "auth_state"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    bootstrap_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pending_replacement_email: Mapped[str | None] = mapped_column(String(255))
    pending_replacement_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

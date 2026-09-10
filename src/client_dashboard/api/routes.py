from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from client_dashboard.api.deps import get_db
from client_dashboard.api.schemas import (
    ClientCreate,
    ClientRead,
    ClientUpdate,
    InvoiceListItem,
    InvoiceRead,
    PaymentCreate,
    PaymentRead,
    PaymentUpdate,
    PricingVersionCreate,
    PricingVersionRead,
    PricingVersionUpdate,
    WeddingCreate,
    WeddingListItem,
    WeddingPartyMemberCreate,
    WeddingPartyMemberRead,
    WeddingPartyMemberUpdate,
    WeddingRead,
    WeddingStatus,
    WeddingUpdate,
)
from client_dashboard.models import (
    Client,
    Invoice,
    Payment,
    PricingVersion,
    Wedding,
    WeddingPartyMember,
)

router = APIRouter()


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        message = str(exc.orig).lower()
        if "unique constraint failed" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate record") from exc
        if "foreign key constraint failed" in message:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reference") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data") from exc


def _get_or_404(session: Session, model: type, object_id: int, detail: str):
    obj = session.get(model, object_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return obj


def _apply_updates(obj, data) -> None:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)


def _wedding_query(
    session: Session,
    *,
    status_filter: WeddingStatus | None = None,
    wedding_date: date | None = None,
    client_id: int | None = None,
    source: str | None = None,
) -> Select[tuple[Wedding]]:
    query = select(Wedding).options(selectinload(Wedding.client))
    if source is not None:
        query = query.join(Wedding.client)
    if status_filter is not None:
        query = query.where(Wedding.status == status_filter)
    if wedding_date is not None:
        query = query.where(Wedding.wedding_date == wedding_date)
    if client_id is not None:
        query = query.where(Wedding.client_id == client_id)
    if source is not None:
        query = query.where(Client.source == source)
    return query.order_by(desc(Wedding.wedding_date), desc(Wedding.id))


@router.post("/clients", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, session: Session = Depends(get_db)) -> Client:
    client = Client(**payload.model_dump())
    session.add(client)
    _commit(session)
    session.refresh(client)
    return client


@router.get("/clients", response_model=list[ClientRead])
def list_clients(
    session: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Client]:
    stmt = select(Client).order_by(Client.name, Client.id).offset(offset).limit(limit)
    return list(session.scalars(stmt))


@router.get("/clients/{client_id}", response_model=ClientRead)
def get_client(client_id: int, session: Session = Depends(get_db)) -> Client:
    return _get_or_404(session, Client, client_id, "Client not found")


@router.patch("/clients/{client_id}", response_model=ClientRead)
def update_client(client_id: int, payload: ClientUpdate, session: Session = Depends(get_db)) -> Client:
    client = _get_or_404(session, Client, client_id, "Client not found")
    _apply_updates(client, payload)
    _commit(session)
    session.refresh(client)
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, session: Session = Depends(get_db)) -> None:
    client = _get_or_404(session, Client, client_id, "Client not found")
    session.delete(client)
    _commit(session)


@router.post("/weddings", response_model=WeddingRead, status_code=status.HTTP_201_CREATED)
def create_wedding(payload: WeddingCreate, session: Session = Depends(get_db)) -> Wedding:
    _get_or_404(session, Client, payload.client_id, "Client not found")
    wedding = Wedding(**payload.model_dump())
    session.add(wedding)
    _commit(session)
    session.refresh(wedding)
    return _get_wedding_detail(session, wedding.id)


def _get_wedding_detail(session: Session, wedding_id: int) -> Wedding:
    stmt = (
        select(Wedding)
        .options(selectinload(Wedding.client), selectinload(Wedding.party_members))
        .where(Wedding.id == wedding_id)
    )
    wedding = session.scalars(stmt).first()
    if wedding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wedding not found")
    return wedding


@router.get("/weddings", response_model=list[WeddingListItem])
def list_weddings(
    session: Session = Depends(get_db),
    status_filter: WeddingStatus | None = Query(default=None, alias="status"),
    wedding_date: date | None = None,
    client_id: int | None = None,
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Wedding]:
    stmt = _wedding_query(
        session,
        status_filter=status_filter,
        wedding_date=wedding_date,
        client_id=client_id,
        source=source,
    )
    return list(session.scalars(stmt.offset(offset).limit(limit)))


@router.get("/weddings/{wedding_id}", response_model=WeddingRead)
def get_wedding(wedding_id: int, session: Session = Depends(get_db)) -> Wedding:
    return _get_wedding_detail(session, wedding_id)


@router.patch("/weddings/{wedding_id}", response_model=WeddingRead)
def update_wedding(wedding_id: int, payload: WeddingUpdate, session: Session = Depends(get_db)) -> Wedding:
    wedding = _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    updates = payload.model_dump(exclude_unset=True)
    if "client_id" in updates:
        _get_or_404(session, Client, updates["client_id"], "Client not found")
    for field, value in updates.items():
        setattr(wedding, field, value)
    _commit(session)
    return _get_wedding_detail(session, wedding_id)


@router.delete("/weddings/{wedding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wedding(wedding_id: int, session: Session = Depends(get_db)) -> None:
    wedding = _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    session.delete(wedding)
    _commit(session)


@router.post(
    "/weddings/{wedding_id}/party-members",
    response_model=WeddingPartyMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_party_member(
    wedding_id: int,
    payload: WeddingPartyMemberCreate,
    session: Session = Depends(get_db),
) -> WeddingPartyMember:
    _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    member = WeddingPartyMember(wedding_id=wedding_id, **payload.model_dump())
    session.add(member)
    _commit(session)
    session.refresh(member)
    return member


@router.get("/party-members/{party_member_id}", response_model=WeddingPartyMemberRead)
def get_party_member(party_member_id: int, session: Session = Depends(get_db)) -> WeddingPartyMember:
    return _get_or_404(session, WeddingPartyMember, party_member_id, "Party member not found")


@router.get("/weddings/{wedding_id}/party-members", response_model=list[WeddingPartyMemberRead])
def list_party_members(
    wedding_id: int,
    session: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[WeddingPartyMember]:
    _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    stmt = select(WeddingPartyMember).where(WeddingPartyMember.wedding_id == wedding_id).order_by(WeddingPartyMember.id)
    return list(session.scalars(stmt.offset(offset).limit(limit)))


@router.patch("/party-members/{party_member_id}", response_model=WeddingPartyMemberRead)
def update_party_member(
    party_member_id: int,
    payload: WeddingPartyMemberUpdate,
    session: Session = Depends(get_db),
) -> WeddingPartyMember:
    member = _get_or_404(session, WeddingPartyMember, party_member_id, "Party member not found")
    _apply_updates(member, payload)
    _commit(session)
    session.refresh(member)
    return member


@router.delete("/party-members/{party_member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_party_member(party_member_id: int, session: Session = Depends(get_db)) -> None:
    member = _get_or_404(session, WeddingPartyMember, party_member_id, "Party member not found")
    session.delete(member)
    _commit(session)


@router.post("/pricing-versions", response_model=PricingVersionRead, status_code=status.HTTP_201_CREATED)
def create_pricing_version(payload: PricingVersionCreate, session: Session = Depends(get_db)) -> PricingVersion:
    version = PricingVersion(**payload.model_dump())
    session.add(version)
    _commit(session)
    session.refresh(version)
    return version


@router.get("/pricing-versions", response_model=list[PricingVersionRead])
def list_pricing_versions(
    session: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PricingVersion]:
    stmt = select(PricingVersion).order_by(desc(PricingVersion.id)).offset(offset).limit(limit)
    return list(session.scalars(stmt))


@router.get("/pricing-versions/{pricing_version_id}", response_model=PricingVersionRead)
def get_pricing_version(pricing_version_id: int, session: Session = Depends(get_db)) -> PricingVersion:
    return _get_or_404(session, PricingVersion, pricing_version_id, "Pricing version not found")


@router.patch("/pricing-versions/{pricing_version_id}", response_model=PricingVersionRead)
def update_pricing_version(
    pricing_version_id: int,
    payload: PricingVersionUpdate,
    session: Session = Depends(get_db),
) -> PricingVersion:
    version = _get_or_404(session, PricingVersion, pricing_version_id, "Pricing version not found")
    if session.scalar(select(Invoice.id).where(Invoice.pricing_version_id == pricing_version_id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing versions referenced by invoices are immutable",
        )
    _apply_updates(version, payload)
    _commit(session)
    session.refresh(version)
    return version


@router.delete("/pricing-versions/{pricing_version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pricing_version(pricing_version_id: int, session: Session = Depends(get_db)) -> None:
    version = _get_or_404(session, PricingVersion, pricing_version_id, "Pricing version not found")
    if session.scalar(select(Invoice.id).where(Invoice.pricing_version_id == pricing_version_id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pricing version is referenced by one or more invoices",
        )
    session.delete(version)
    _commit(session)


@router.get("/invoices", response_model=list[InvoiceListItem])
def list_invoices(
    session: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Invoice]:
    stmt = (
        select(Invoice)
        .order_by(desc(Invoice.wedding_id), desc(Invoice.version_number), desc(Invoice.id))
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(stmt))


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, session: Session = Depends(get_db)) -> Invoice:
    stmt = select(Invoice).options(selectinload(Invoice.pricing_version)).where(Invoice.id == invoice_id)
    invoice = session.scalars(stmt).first()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.get("/weddings/{wedding_id}/invoice", response_model=InvoiceRead)
def get_wedding_invoice(wedding_id: int, session: Session = Depends(get_db)) -> Invoice:
    _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.pricing_version))
        .where(Invoice.wedding_id == wedding_id)
        .order_by(desc(Invoice.version_number), desc(Invoice.id))
        .limit(1)
    )
    invoice = session.scalars(stmt).first()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate, session: Session = Depends(get_db)) -> Payment:
    _get_or_404(session, Wedding, payload.wedding_id, "Wedding not found")
    payment = Payment(**payload.model_dump())
    session.add(payment)
    _commit(session)
    session.refresh(payment)
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, session: Session = Depends(get_db)) -> Payment:
    return _get_or_404(session, Payment, payment_id, "Payment not found")


@router.get("/weddings/{wedding_id}/payments", response_model=list[PaymentRead])
def list_payments_for_wedding(
    wedding_id: int,
    session: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Payment]:
    _get_or_404(session, Wedding, wedding_id, "Wedding not found")
    stmt = select(Payment).where(Payment.wedding_id == wedding_id).order_by(desc(Payment.payment_date), desc(Payment.id))
    return list(session.scalars(stmt.offset(offset).limit(limit)))


@router.patch("/payments/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id: int, payload: PaymentUpdate, session: Session = Depends(get_db)) -> Payment:
    payment = _get_or_404(session, Payment, payment_id, "Payment not found")
    updates = payload.model_dump(exclude_unset=True)
    if "wedding_id" in updates:
        _get_or_404(session, Wedding, updates["wedding_id"], "Wedding not found")
    for field, value in updates.items():
        setattr(payment, field, value)
    _commit(session)
    session.refresh(payment)
    return payment


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(payment_id: int, session: Session = Depends(get_db)) -> None:
    payment = _get_or_404(session, Payment, payment_id, "Payment not found")
    session.delete(payment)
    _commit(session)

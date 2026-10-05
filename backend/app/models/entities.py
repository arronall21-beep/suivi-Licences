from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import lifecycle
from app.core.config import settings
from app.database import Base

CATEGORIES = ["LICENCE", "CERTIFICAT", "MATERIEL", "APPLICATION"]
ROLES = ["ADMIN", "MANAGER", "VIEWER"]

# Séquences PostgreSQL des références automatiques (jamais count()+1 : pas de collision
# après suppression ni en cas de créations simultanées).
REFERENCE_PREFIXES = {
    "LICENCE": "LIC",
    "CERTIFICAT": "CERT",
    "MATERIEL": "MAT",
    "APPLICATION": "APP",
    "CONTRACT": "CTR",
    "VENDOR": "VEN",
}
REFERENCE_SEQUENCES = {
    kind: Sequence(f"ref_{prefix.lower()}_seq", metadata=Base.metadata) for kind, prefix in REFERENCE_PREFIXES.items()
}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="VIEWER")
    is_active: Mapped[bool] = mapped_column(default=True)


class Vendor(TimestampMixin, Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    contact_person: Mapped[str | None] = mapped_column(String(255))
    email_support: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(255))


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    market_ref: Mapped[str | None] = mapped_column(String(100))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    type: Mapped[str | None] = mapped_column(String(100))
    scope: Mapped[str | None] = mapped_column(Text)
    internal_owner: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    annual_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(10), default=lambda: settings.currency)
    status: Mapped[str | None] = mapped_column(String(50))
    attachment_url: Mapped[str | None] = mapped_column(String(500))

    vendor: Mapped[Vendor | None] = relationship(lazy="joined")

    @property
    def vendor_name(self) -> str | None:
        return self.vendor.name if self.vendor else None

    @property
    def days_remaining(self) -> int | None:
        return lifecycle.days_remaining(self.end_date)

    @property
    def lifecycle_status(self) -> str:
        return lifecycle.compute_status(self.end_date)

    @property
    def renewal_start_date(self) -> date | None:
        return lifecycle.renewal_start_date(self.end_date, self.notice_period_days)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("category", "reference", name="uq_asset_category_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id", ondelete="SET NULL"))
    internal_owner: Mapped[str | None] = mapped_column(String(255))
    user_department: Mapped[str | None] = mapped_column(String(255), index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    criticality: Mapped[str | None] = mapped_column(String(50))
    annual_cost: Mapped[float | None] = mapped_column(Numeric(14, 2))
    budget_estimated: Mapped[float | None] = mapped_column(Numeric(14, 2))
    action_plan: Mapped[str | None] = mapped_column(Text)
    observation: Mapped[str | None] = mapped_column(Text)

    # Licence
    lic_type: Mapped[str | None] = mapped_column(String(100))
    license_key: Mapped[str | None] = mapped_column(String(500))
    total_quantity: Mapped[int | None] = mapped_column(Integer)

    # Certificat
    cert_type: Mapped[str | None] = mapped_column(String(100))
    authority: Mapped[str | None] = mapped_column(String(255))
    server_app_target: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str | None] = mapped_column(String(100))

    # Matériel
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(255))
    site_location: Mapped[str | None] = mapped_column(String(255))
    warranty_end_date: Mapped[date | None] = mapped_column(Date)
    support_end_date: Mapped[date | None] = mapped_column(Date)
    support_contract_type: Mapped[str | None] = mapped_column(String(255))

    # Application
    business_owner: Mapped[str | None] = mapped_column(String(255))
    hosting_env: Mapped[str | None] = mapped_column(String(255))
    service_provider: Mapped[str | None] = mapped_column(String(255))
    sla_level: Mapped[str | None] = mapped_column(String(100))

    vendor: Mapped[Vendor | None] = relationship(lazy="joined")
    contract: Mapped[Contract | None] = relationship(lazy="joined")
    assignments: Mapped[list["LicenseAssignment"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LicenseAssignment.id",
    )

    @property
    def vendor_name(self) -> str | None:
        return self.vendor.name if self.vendor else None

    @property
    def contract_reference(self) -> str | None:
        return self.contract.reference if self.contract else None

    @property
    def effective_end_date(self) -> date | None:
        """Échéance de référence : date de fin, sinon fin de support, sinon fin de garantie."""
        return self.end_date or self.support_end_date or self.warranty_end_date

    @property
    def days_remaining(self) -> int | None:
        return lifecycle.days_remaining(self.effective_end_date)

    @property
    def status(self) -> str:
        return lifecycle.compute_status(self.effective_end_date)

    @property
    def assigned_quantity(self) -> int:
        return sum(a.quantity for a in self.assignments)

    @property
    def available_quantity(self) -> int | None:
        if self.total_quantity is None:
            return None
        return self.total_quantity - self.assigned_quantity

    @property
    def usage_rate(self) -> float | None:
        if not self.total_quantity:
            return None
        return round(self.assigned_quantity / self.total_quantity * 100, 1)


class LicenseAssignment(TimestampMixin, Base):
    __tablename__ = "license_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    assigned_to_user: Mapped[str | None] = mapped_column(String(255))
    assigned_to_device: Mapped[str | None] = mapped_column(String(255))
    assigned_to_department: Mapped[str | None] = mapped_column(String(255))
    assigned_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)

    asset: Mapped[Asset] = relationship(back_populates="assignments", lazy="joined")

    @property
    def asset_reference(self) -> str | None:
        return self.asset.reference if self.asset else None

    @property
    def asset_name(self) -> str | None:
        return self.asset.name if self.asset else None


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("target_type", "target_id", "threshold", "due_date", name="uq_notification"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(20))  # ASSET / CONTRACT
    target_id: Mapped[int] = mapped_column(Integer)
    target_reference: Mapped[str | None] = mapped_column(String(100))
    target_name: Mapped[str | None] = mapped_column(String(255))
    threshold: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    days_remaining: Mapped[int] = mapped_column(Integer)
    recipients: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(20), default="EMAIL")
    delivery_status: Mapped[str] = mapped_column(String(20))  # ENVOYE / NON_ENVOYE / ERREUR
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    rows_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[str | None] = mapped_column(Text)  # JSON
    imported_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

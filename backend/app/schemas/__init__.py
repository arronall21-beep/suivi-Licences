from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Category = Literal["LICENCE", "CERTIFICAT", "MATERIEL", "APPLICATION"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _strip(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


# ---------- Auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str


class UserOut(ORM):
    id: int
    email: str
    full_name: str | None = None
    role: str


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    password: str = Field(min_length=6)
    role: Literal["ADMIN", "VIEWER"] = "VIEWER"


# ---------- Vendor ----------
class VendorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_person: str | None = None
    email_support: str | None = None
    phone: str | None = None
    website: str | None = None

    _s = field_validator("*", mode="before")(classmethod(lambda cls, v: _strip(v)))


class VendorIn(VendorBase):
    pass


class VendorOut(VendorBase, ORM):
    id: int
    reference: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------- Contract ----------
class ContractBase(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    market_ref: str | None = None
    vendor_id: int | None = None
    type: str | None = None
    scope: str | None = None
    internal_owner: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notice_period_days: int | None = Field(default=None, ge=0, le=3650)
    annual_amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    status: str | None = None
    attachment_url: str | None = None

    _s = field_validator("*", mode="before")(classmethod(lambda cls, v: _strip(v)))


class ContractIn(ContractBase):
    # Générée automatiquement (CTR-001…) si absente
    reference: str | None = Field(default=None, max_length=100)


class ContractOut(ContractBase, ORM):
    id: int
    vendor_name: str | None = None
    days_remaining: int | None = None
    lifecycle_status: str
    renewal_start_date: date | None = None
    created_at: datetime
    updated_at: datetime


# ---------- Assignment ----------
class AssignmentBase(BaseModel):
    asset_id: int
    assigned_to_user: str | None = None
    assigned_to_device: str | None = None
    assigned_to_department: str | None = None
    assigned_date: date | None = None
    quantity: int = Field(default=1, ge=1)
    notes: str | None = None

    _s = field_validator("*", mode="before")(classmethod(lambda cls, v: _strip(v)))


class AssignmentIn(AssignmentBase):
    pass


class AssignmentOut(AssignmentBase, ORM):
    id: int
    asset_reference: str | None = None
    asset_name: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------- Asset ----------
class AssetBase(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    category: Category
    name: str = Field(min_length=1, max_length=255)
    vendor_id: int | None = None
    contract_id: int | None = None
    internal_owner: str | None = None
    user_department: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    criticality: str | None = None
    annual_cost: float | None = Field(default=None, ge=0)
    budget_estimated: float | None = Field(default=None, ge=0)
    action_plan: str | None = None
    observation: str | None = None

    lic_type: str | None = None
    license_key: str | None = None
    total_quantity: int | None = Field(default=None, ge=0)

    cert_type: str | None = None
    authority: str | None = None
    server_app_target: str | None = None
    environment: str | None = None

    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    site_location: str | None = None
    warranty_end_date: date | None = None
    support_end_date: date | None = None
    support_contract_type: str | None = None

    business_owner: str | None = None
    hosting_env: str | None = None
    service_provider: str | None = None
    sla_level: str | None = None

    model_config = ConfigDict(protected_namespaces=())
    _s = field_validator("*", mode="before")(classmethod(lambda cls, v: _strip(v)))


class AssetIn(AssetBase):
    # Générée automatiquement (LIC-001, CERT-001…) si absente
    reference: str | None = Field(default=None, max_length=100)


class AssetOut(AssetBase, ORM):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    vendor_name: str | None = None
    contract_reference: str | None = None
    effective_end_date: date | None = None
    days_remaining: int | None = None
    status: str
    assigned_quantity: int = 0
    available_quantity: int | None = None
    usage_rate: float | None = None
    created_at: datetime
    updated_at: datetime


class AssetDetailOut(AssetOut):
    assignments: list[AssignmentOut] = []


class Page(BaseModel):
    items: list
    total: int
    page: int
    size: int


class AssetPage(Page):
    items: list[AssetOut]


class NotificationOut(ORM):
    id: int
    target_type: str
    target_id: int
    target_reference: str | None
    target_name: str | None
    threshold: int
    due_date: date
    days_remaining: int
    recipients: str | None
    channel: str
    delivery_status: str
    error: str | None
    created_at: datetime

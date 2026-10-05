export type Category = "LICENCE" | "CERTIFICAT" | "MATERIEL" | "APPLICATION";
export type Status = "EXPIRE" | "CRITIQUE" | "ALERTE" | "OK" | "INCONNU";

export interface Vendor {
  id: number;
  reference: string | null;
  name: string;
  contact_person: string | null;
  email_support: string | null;
  phone: string | null;
  website: string | null;
}

export interface Contract {
  id: number;
  reference: string;
  market_ref: string | null;
  vendor_id: number | null;
  vendor_name: string | null;
  type: string | null;
  scope: string | null;
  internal_owner: string | null;
  start_date: string | null;
  end_date: string | null;
  notice_period_days: number | null;
  annual_amount: number | null;
  currency: string | null;
  status: string | null;
  attachment_url: string | null;
  days_remaining: number | null;
  lifecycle_status: Status;
  renewal_start_date: string | null;
}

export interface Assignment {
  id: number;
  asset_id: number;
  asset_reference: string | null;
  asset_name: string | null;
  assigned_to_user: string | null;
  assigned_to_device: string | null;
  assigned_to_department: string | null;
  assigned_date: string | null;
  quantity: number;
  notes: string | null;
}

export interface Asset {
  id: number;
  reference: string;
  category: Category;
  name: string;
  vendor_id: number | null;
  vendor_name: string | null;
  contract_id: number | null;
  contract_reference: string | null;
  internal_owner: string | null;
  user_department: string | null;
  start_date: string | null;
  end_date: string | null;
  effective_end_date: string | null;
  criticality: string | null;
  annual_cost: number | null;
  budget_estimated: number | null;
  action_plan: string | null;
  observation: string | null;
  lic_type: string | null;
  license_key: string | null;
  total_quantity: number | null;
  cert_type: string | null;
  authority: string | null;
  server_app_target: string | null;
  environment: string | null;
  brand: string | null;
  model: string | null;
  serial_number: string | null;
  site_location: string | null;
  warranty_end_date: string | null;
  support_end_date: string | null;
  support_contract_type: string | null;
  business_owner: string | null;
  hosting_env: string | null;
  service_provider: string | null;
  sla_level: string | null;
  days_remaining: number | null;
  status: Status;
  assigned_quantity: number;
  available_quantity: number | null;
  usage_rate: number | null;
  assignments?: Assignment[];
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface RenewalItem {
  kind: "ASSET" | "CONTRACT";
  id: number;
  type: Category | "CONTRAT";
  reference: string;
  name: string;
  vendor_name: string | null;
  end_date: string;
  renewal_start_date: string | null;
  days_remaining: number;
  status: Status;
  priority: string;
  criticality: string | null;
  owner: string | null;
  department: string | null;
  budget: number | null;
  action_plan: string | null;
  notice_period_days?: number | null;
  notice_reached?: boolean;
  threshold?: number;
}

export interface TopRisk {
  id: number;
  reference: string;
  name: string;
  category: Category;
  status: Status;
  days_remaining: number;
  end_date: string | null;
  criticality: string | null;
  owner: string | null;
  score: number;
  reasons: string[];
}

export interface Dashboard {
  thresholds: { critical_days: number; alert_days: number };
  top_risks: TopRisk[];
  kpis: Record<"total_assets" | "licences" | "certificats" | "materiels" | "applications" | "contracts" | "vendors", number>;
  deadlines: Record<"expired" | "critical" | "warning" | "ok" | "unknown", number>;
  contract_deadlines: Record<"expired" | "critical" | "warning" | "ok" | "unknown", number>;
  licenses: { total: number; used: number; available: number; usage_rate: number };
  finance: { annual_cost_total: number; contracts_annual_total: number; budget_estimated_total: number; renewal_budget_12m: number };
  by_category: { category: Category; label: string; count: number }[];
  status_by_category: ({ category: Category; label: string } & Record<Status, number>)[];
  upcoming_renewals: RenewalItem[];
}

export type Role = "ADMIN" | "MANAGER" | "VIEWER";

export interface AppUser {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  phone: string | null;
  department: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  permissions?: string[];
}

export interface AppConfig {
  org_name: string;
  app_name: string;
  currency: string;
  currency_label: string;
  timezone: string;
  critical_days: number;
  alert_days: number;
  alert_thresholds: number[];
  version: string;
}

export interface InboxItem {
  id: number;
  kind: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  message: string | null;
  link: string | null;
  created_at: string;
  read: boolean;
}

export interface ImportReport {
  filename: string;
  rows_analyzed: number;
  rows_imported: number;
  rows_skipped: number;
  created: number;
  updated: number;
  vendors_created: number;
  warnings_count: number;
  errors_count: number;
  sheets: { sheet: string; matched_as: string | null; rows_analyzed: number; imported: number; created: number; updated: number; skipped: number; note: string | null }[];
  missing_sheets: string[];
  unknown_sheets: string[];
  warnings: { sheet: string; row: number | null; message: string }[];
  errors: { sheet: string; row: number | null; message: string }[];
}

export interface NotificationItem {
  id: number;
  target_type: "ASSET" | "CONTRACT";
  target_id: number;
  target_reference: string | null;
  target_name: string | null;
  threshold: number;
  due_date: string;
  days_remaining: number;
  recipients: string | null;
  channel: string;
  delivery_status: string;
  error: string | null;
  created_at: string;
}

import type { Category, Status } from "./types";

export const fmtDate = (d?: string | null) => (d ? new Date(d + (d.length === 10 ? "T00:00:00" : "")).toLocaleDateString("fr-FR") : "—");
export const fmtDateTime = (d?: string | null) => (d ? new Date(d).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "—");
export const fmtMoney = (n?: number | string | null) =>
  n === null || n === undefined || n === "" ? "—" : Number(n).toLocaleString("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
export const fmtNum = (n?: number | null) => (n === null || n === undefined ? "—" : n.toLocaleString("fr-FR"));

export const CATEGORY_LABELS: Record<Category | "CONTRAT", string> = {
  LICENCE: "Licence",
  CERTIFICAT: "Certificat",
  MATERIEL: "Matériel",
  APPLICATION: "Application",
  CONTRAT: "Contrat",
};
export const CATEGORY_PLURAL: Record<Category, string> = {
  LICENCE: "Licences",
  CERTIFICAT: "Certificats",
  MATERIEL: "Matériels",
  APPLICATION: "Applications",
};
export const CATEGORY_SLUG: Record<Category, string> = {
  LICENCE: "licences",
  CERTIFICAT: "certificats",
  MATERIEL: "materiels",
  APPLICATION: "applications",
};
export const SLUG_CATEGORY: Record<string, Category> = Object.fromEntries(
  Object.entries(CATEGORY_SLUG).map(([k, v]) => [v, k as Category]),
);

export const STATUS_META: Record<Status, { label: string; cls: string; color: string }> = {
  EXPIRE: { label: "Expiré", cls: "bg-red-100 text-red-800 ring-red-600/20", color: "#dc2626" },
  CRITIQUE: { label: "Critique", cls: "bg-orange-100 text-orange-800 ring-orange-600/20", color: "#ea580c" },
  ALERTE: { label: "Alerte", cls: "bg-amber-100 text-amber-800 ring-amber-600/20", color: "#d97706" },
  OK: { label: "OK", cls: "bg-emerald-100 text-emerald-800 ring-emerald-600/20", color: "#059669" },
  INCONNU: { label: "Non défini", cls: "bg-slate-100 text-slate-600 ring-slate-500/20", color: "#94a3b8" },
};

export const CRITICALITY_CLS: Record<string, string> = {
  Critique: "bg-red-50 text-red-700 ring-red-600/20",
  Haute: "bg-orange-50 text-orange-700 ring-orange-600/20",
  Moyenne: "bg-blue-50 text-blue-700 ring-blue-600/20",
  Basse: "bg-slate-50 text-slate-600 ring-slate-500/20",
};

export const CRITICALITIES = ["Critique", "Haute", "Moyenne", "Basse"];
export const LICENSE_TYPES = ["Nommée", "Flottante", "Site", "Perpétuelle avec abonnement", "Souscription"];
export const CERT_TYPES = ["SSL/TLS", "Wildcard", "Certificat interne"];
export const CONTRACT_TYPES = ["Maintenance corrective/évolutive", "Support constructeur", "SaaS", "Prestation", "Hébergement Cloud"];
export const ENVIRONMENTS = ["Production", "Préproduction", "Recette", "Développement"];

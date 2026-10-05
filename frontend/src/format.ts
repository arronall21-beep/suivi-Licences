import type { Category } from "./types";

export const fmtDate = (d?: string | null) => (d ? new Date(d + (d.length === 10 ? "T00:00:00" : "")).toLocaleDateString("fr-FR") : "—");
export const fmtDateTime = (d?: string | null) => (d ? new Date(d).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "—");
/** Devise courante : initialisée depuis les Paramètres généraux (ConfigProvider), jamais codée en dur. */
export let CURRENCY = "XOF";
export const setCurrency = (code: string) => {
  CURRENCY = code;
};
export const fmtMoney = (n?: number | string | null) =>
  n === null || n === undefined || n === "" ? "—" : Number(n).toLocaleString("fr-FR", { style: "currency", currency: CURRENCY, maximumFractionDigits: 0 });
export const fmtMoneyCompact = (n?: number | null) =>
  n === null || n === undefined ? "—" : Number(n).toLocaleString("fr-FR", { style: "currency", currency: CURRENCY, notation: "compact", maximumFractionDigits: 1 });
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

export { STATUS_META, CRITICALITY_CLS } from "./theme";

export const CRITICALITIES = ["Critique", "Haute", "Moyenne", "Basse"];
export const LICENSE_TYPES = ["Nommée", "Flottante", "Site", "Perpétuelle avec abonnement", "Souscription"];
export const CERT_TYPES = ["SSL/TLS", "Wildcard", "Certificat interne"];
export const CONTRACT_TYPES = ["Maintenance corrective/évolutive", "Support constructeur", "SaaS", "Prestation", "Hébergement Cloud"];
export const ENVIRONMENTS = ["Production", "Préproduction", "Recette", "Développement"];

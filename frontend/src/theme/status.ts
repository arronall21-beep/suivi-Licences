import type { Status } from "../types";

/** Couleur d'un jeton de marque dans les graphiques SVG (lit la variable CSS des tokens). */
export const token = (name: string) => `rgb(var(--${name}))`;

/** Statuts d'échéance : libellé, classes du badge et couleur de graphique. */
export const STATUS_META: Record<Status, { label: string; cls: string; color: string }> = {
  EXPIRE: { label: "Expiré", cls: "bg-danger-100 text-danger-800 ring-danger-600/20", color: token("danger-500") },
  CRITIQUE: { label: "Critique", cls: "bg-caution-100 text-caution-800 ring-caution-600/20", color: token("caution-500") },
  ALERTE: { label: "Alerte", cls: "bg-warning-100 text-warning-800 ring-warning-600/20", color: token("warning-500") },
  OK: { label: "OK", cls: "bg-success-100 text-success-800 ring-success-600/20", color: token("success-500") },
  INCONNU: { label: "Non défini", cls: "bg-slate-100 text-slate-600 ring-slate-500/20", color: token("gray-300") },
};

export const CRITICALITY_CLS: Record<string, string> = {
  Critique: "bg-danger-50 text-danger-700 ring-danger-600/20",
  Haute: "bg-caution-50 text-caution-700 ring-caution-600/20",
  Moyenne: "bg-info-50 text-info-700 ring-info-600/20",
  Basse: "bg-slate-50 text-slate-600 ring-slate-500/20",
};

export const PRIORITY_CLS: Record<string, string> = {
  P1: "bg-danger-600 text-white",
  P2: "bg-warning-500 text-white",
  P3: "bg-slate-200 text-slate-700",
};

/** Priorité des notifications internes. */
export const NOTIFICATION_PRIORITY: Record<string, { label: string; dot: string; cls: string }> = {
  HIGH: { label: "Haute", dot: "bg-danger-600", cls: "bg-danger-100 text-danger-800 ring-danger-600/20" },
  MEDIUM: { label: "Moyenne", dot: "bg-warning-500", cls: "bg-warning-100 text-warning-800 ring-warning-600/20" },
  LOW: { label: "Basse", dot: "bg-slate-400", cls: "bg-slate-100 text-slate-600 ring-slate-500/20" },
};

export const ROLE_META: Record<string, { label: string; cls: string }> = {
  ADMIN: { label: "Administrateur", cls: "bg-info-100 text-info-800 ring-info-600/20" },
  MANAGER: { label: "Gestionnaire", cls: "bg-warning-100 text-warning-800 ring-warning-600/20" },
  VIEWER: { label: "Lecture seule", cls: "bg-slate-100 text-slate-700 ring-slate-500/20" },
};

export const IMPORT_STATUS_META: Record<string, { label: string; cls: string }> = {
  SUCCESS: { label: "Réussi", cls: "bg-success-100 text-success-800 ring-success-600/20" },
  WARNINGS: { label: "Avertissements", cls: "bg-warning-100 text-warning-800 ring-warning-600/20" },
  ERRORS: { label: "Erreurs", cls: "bg-caution-100 text-caution-800 ring-caution-600/20" },
  FAILED: { label: "Échec", cls: "bg-danger-100 text-danger-800 ring-danger-600/20" },
};

/** Couleurs des éléments neutres des graphiques (axes, grille, étiquettes). */
export const CHART = {
  grid: token("border-subtle"),
  axis: token("ink-muted"),
  label: token("ink-body"),
  cursor: token("gray-100"),
  surface: token("surface-card"),
};

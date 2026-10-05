/**
 * Identité visuelle : emplacement du logo et textes par défaut.
 *
 * Pour installer le logo officiel SBEE sans toucher aux composants :
 *   1. déposer le fichier dans `frontend/public/branding/` (logo.svg ou logo.png),
 *   2. soit le nommer `logo.svg` (remplace le fichier fourni), soit définir VITE_LOGO_URL
 *      (ex. VITE_LOGO_URL=/branding/logo-sbee.png) au build du frontend,
 *   3. reconstruire le frontend (`docker compose up --build`).
 * Si l'image est introuvable, un monogramme de repli s'affiche automatiquement.
 */
export const brand = {
  logoUrl: (import.meta.env.VITE_LOGO_URL as string | undefined) || "/branding/logo.svg",
  /** Variante pour fond sombre (sidebar). Par défaut, le même fichier. */
  logoDarkUrl: (import.meta.env.VITE_LOGO_DARK_URL as string | undefined) || (import.meta.env.VITE_LOGO_URL as string | undefined) || "/branding/logo.svg",
  fallbackInitials: "SBEE",
  /** Noms affichés tant que la configuration n'est pas chargée ; ensuite, ceux des Paramètres généraux. */
  defaultOrganization: "SBEE",
  defaultApplication: "Gestion du Patrimoine SI",
  organizationFullName: "Société Béninoise d'Énergie Électrique",
};

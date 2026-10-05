/**
 * Identité visuelle SBEE : ressources officielles, textes et règles d'usage.
 *
 * Les fichiers du logo et du symbole sont lus dans `src/assets/brand/` à la compilation
 * (voir le README de ce dossier). Aucun logo n'est jamais reconstitué : s'il manque, seul le
 * nom de l'organisation est affiché.
 */
const files = import.meta.glob("../assets/brand/*.{svg,png,webp}", { eager: true, query: "?url", import: "default" }) as Record<string, string>;

function find(name: string): string | undefined {
  const key = Object.keys(files).find((k) => k.split("/").pop()!.replace(/\.[^.]+$/, "") === name);
  return key ? files[key] : undefined;
}

export const brandAssets = {
  /** Logotype original couleur (fond blanc / clair). */
  logo: find("logo"),
  /** Logotype pour fond rouge / sombre. */
  logoLight: find("logo-light"),
  /** Symbole seul (rouge), pour la trame décorative sur fond blanc / clair. */
  symbol: find("symbol"),
  /** Symbole seul (blanc), pour la trame décorative sur fond rouge. */
  symbolLight: find("symbol-light"),
};

export const brand = {
  /** Noms affichés tant que la configuration n'est pas chargée ; ensuite, ceux des Paramètres généraux. */
  defaultOrganization: "SBEE",
  defaultApplication: "Gestion du Patrimoine SI",
  organizationFullName: "Société Béninoise d'Énergie Électrique",
  /** Hauteur minimale (px) du logotype à l'écran, pour rester lisible. */
  logoMinHeight: 40,
};

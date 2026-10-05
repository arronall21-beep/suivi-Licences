import type { CSSProperties } from "react";
import { brand, brandAssets } from "../../theme";

/**
 * Logotype officiel SBEE.
 * - Hauteur imposée, largeur automatique : les proportions d'origine sont toujours conservées.
 * - Aucune déformation, rotation ni recoloration ; zone de protection assurée par le conteneur parent.
 * - `variant="light"` : version prévue par la charte pour les fonds rouges / sombres.
 * - Sans fichier officiel dans `src/assets/brand/`, rien n'est dessiné : le nom de l'organisation prend le relais.
 */
export function BrandLogo({ variant = "color", height = 48, className = "" }: { variant?: "color" | "light"; height?: number; className?: string }) {
  const src = variant === "light" ? brandAssets.logoLight ?? brandAssets.logo : brandAssets.logo;
  if (!src) return null;
  return <img src={src} alt={brand.organizationFullName} style={{ height: Math.max(height, brand.logoMinHeight), width: "auto" }} className={`block object-contain ${className}`} draggable={false} />;
}

export const hasOfficialLogo = Boolean(brandAssets.logo || brandAssets.logoLight);

/** Nom de l'organisation en typographie courante (affiché tant que le logotype officiel n'est pas installé). */
export function OrgName({ className = "" }: { className?: string }) {
  return <span className={className}>{brand.organizationFullName}</span>;
}

/**
 * Trame décorative : le symbole du logo (`tone="light"` : version blanche pour les fonds rouges), à 5-10 % d'opacité, sans interaction
 * et sans jamais gêner la lisibilité. Ne rend rien si le symbole officiel est absent.
 */
export function Watermark({ tone = "color", className = "", style }: { tone?: "color" | "light"; className?: string; style?: CSSProperties }) {
  const src = tone === "light" ? brandAssets.symbolLight : brandAssets.symbol;
  if (!src) return null;
  return (
    <img
      src={src}
      alt=""
      aria-hidden="true"
      draggable={false}
      className={`pointer-events-none absolute select-none object-contain ${className}`}
      style={{ opacity: "var(--watermark-opacity)", ...style }}
    />
  );
}

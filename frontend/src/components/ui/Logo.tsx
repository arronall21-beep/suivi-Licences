import { useState } from "react";
import { brand } from "../../theme";

/** Logo de l'organisation (voir theme/brand.ts) ; monogramme de repli si l'image est introuvable. */
export function BrandLogo({ dark = false, className = "h-9" }: { dark?: boolean; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (failed)
    return (
      <span className={`inline-flex items-center rounded-md bg-brand-700 px-2.5 font-bold tracking-wide text-white ${className}`}>{brand.fallbackInitials}</span>
    );
  return <img src={dark ? brand.logoDarkUrl : brand.logoUrl} alt={brand.organizationFullName} className={`w-auto ${className}`} onError={() => setFailed(true)} />;
}

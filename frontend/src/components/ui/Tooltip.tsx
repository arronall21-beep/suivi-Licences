import { Info } from "lucide-react";
import type { ReactNode } from "react";

/** Info-bulle accessible au survol et au focus clavier (texte court). */
export function InfoTip({ text }: { text: ReactNode }) {
  return (
    <span className="group relative inline-flex align-middle">
      <button type="button" className="text-slate-400 hover:text-brand-600 focus:text-brand-600 focus:outline-none" aria-label="Plus d'informations">
        <Info className="h-3.5 w-3.5" />
      </button>
      <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-30 mt-1 hidden w-64 -translate-x-1/2 rounded-md bg-brand-950 px-3 py-2 text-xs font-normal normal-case leading-snug tracking-normal text-white shadow-lg group-hover:block group-focus-within:block">
        {text}
      </span>
    </span>
  );
}

import { Building2, FileText, Search, Server, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { StatusBadge } from "./ui";
import type { Status } from "../types";

interface Hit {
  id: number;
  label: string;
  sub: string;
  link: string;
  status?: Status;
}
interface Results {
  assets: Hit[];
  contracts: Hit[];
  vendors: Hit[];
  users: Hit[];
}
const GROUPS: { key: keyof Results; title: string; Icon: typeof Server }[] = [
  { key: "assets", title: "Actifs", Icon: Server },
  { key: "contracts", title: "Contrats", Icon: FileText },
  { key: "vendors", title: "Fournisseurs", Icon: Building2 },
  { key: "users", title: "Utilisateurs", Icon: Users },
];

export default function GlobalSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Results | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    const t = setTimeout(() => {
      api.get<Results>("/search", { q: q.trim() }).then((r) => {
        setResults(r);
        setOpen(true);
      }).catch(() => setResults(null));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const total = results ? GROUPS.reduce((n, g) => n + results[g.key].length, 0) : 0;
  const go = (link: string) => {
    setOpen(false);
    setQ("");
    navigate(link);
  };

  return (
    <div className="relative w-full max-w-md" ref={ref}>
      <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
      <input
        className="input pl-9"
        type="search"
        placeholder="Rechercher : LIC-001, Cisco, contrat, fournisseur, responsable…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results && setOpen(true)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        aria-label="Recherche globale"
      />
      {open && results && (
        <div className="card absolute left-0 right-0 z-40 mt-2 max-h-[28rem] overflow-y-auto shadow-xl">
          {total === 0 && <div className="px-4 py-6 text-center text-sm text-slate-500">Aucun résultat pour « {q} »</div>}
          {GROUPS.map(({ key, title, Icon }) =>
            results[key].length ? (
              <div key={key} className="border-b border-slate-100 py-1 last:border-0">
                <div className="flex items-center gap-2 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  <Icon className="h-3.5 w-3.5" /> {title}
                </div>
                {results[key].map((h) => (
                  <button key={`${key}-${h.id}`} className="flex w-full items-center justify-between gap-3 px-4 py-2 text-left hover:bg-slate-50" onClick={() => go(h.link)}>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-slate-900">{h.label}</span>
                      <span className="block truncate text-xs text-slate-500">{h.sub}</span>
                    </span>
                    {h.status && <StatusBadge status={h.status} />}
                  </button>
                ))}
              </div>
            ) : null,
          )}
        </div>
      )}
    </div>
  );
}

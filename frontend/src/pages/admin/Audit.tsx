import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState, PageHeader, Pagination, Spinner } from "../../components/ui";
import { fmtDateTime } from "../../format";
import { useFetch } from "../../hooks";
import type { Page } from "../../types";

interface Entry {
  id: number;
  created_at: string;
  user_email: string | null;
  action: string;
  action_label: string;
  entity_type: string | null;
  entity_id: string | null;
  entity_label: string | null;
  result: "SUCCESS" | "FAILURE";
  details: string | null;
  ip_address: string | null;
}

const SIZE = 25;
const ENTITY_LABELS: Record<string, string> = {
  USER: "Utilisateur", ASSET: "Actif", CONTRACT: "Contrat", VENDOR: "Fournisseur", ASSIGNMENT: "Affectation",
  SETTINGS: "Paramètres", IMPORT: "Import", EXPORT: "Export", ALERTS: "Alertes",
};

function prettyDetails(details: string | null): string {
  if (!details) return "";
  try {
    const o = JSON.parse(details) as Record<string, unknown>;
    return Object.entries(o)
      .map(([k, v]) => `${k} : ${Array.isArray(v) ? v.join(", ") || "—" : String(v)}`)
      .join(" · ");
  } catch {
    return details;
  }
}

export default function Audit() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [action, setAction] = useState("");
  const [user, setUser] = useState("");
  const [entityType, setEntityType] = useState("");
  const [result, setResult] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const actions = useFetch<{ value: string; label: string }[]>("/admin/audit/actions").data ?? [];
  const { data, loading } = useFetch<Page<Entry>>("/admin/audit", { q: debounced, action, user, entity_type: entityType, result, date_from: from, date_to: to, page, size: SIZE });

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(q);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const hasFilters = q || action || user || entityType || result || from || to;
  const reset = () => {
    setQ(""); setAction(""); setUser(""); setEntityType(""); setResult(""); setFrom(""); setTo(""); setPage(1);
  };
  const reload1 = (fn: (v: string) => void) => (e: { target: { value: string } }) => {
    fn(e.target.value);
    setPage(1);
  };

  return (
    <>
      <PageHeader title="Journal d'audit" subtitle={data ? `${data.total} événement(s) — journal en lecture seule, aucun secret n'y est enregistré` : undefined} />
      <Card className="mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder="Rechercher (entité, détails, IP…)" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <select className="input w-52" value={action} onChange={reload1(setAction)} aria-label="Action">
            <option value="">Toutes les actions</option>
            {actions.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
          <input className="input w-48" placeholder="Utilisateur (email)" value={user} onChange={reload1(setUser)} aria-label="Utilisateur" />
          <select className="input w-40" value={entityType} onChange={reload1(setEntityType)} aria-label="Entité">
            <option value="">Toutes entités</option>
            {Object.entries(ENTITY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <select className="input w-36" value={result} onChange={reload1(setResult)} aria-label="Résultat">
            <option value="">Tous résultats</option>
            <option value="SUCCESS">Succès</option>
            <option value="FAILURE">Échec</option>
          </select>
          <label className="text-xs text-slate-600">
            Du
            <input className="input mt-1 w-40" type="date" value={from} onChange={reload1(setFrom)} />
          </label>
          <label className="text-xs text-slate-600">
            Au
            <input className="input mt-1 w-40" type="date" value={to} onChange={reload1(setTo)} />
          </label>
          {hasFilters && (
            <Button variant="ghost" onClick={reset} icon={<X className="h-4 w-4" />}>
              Réinitialiser
            </Button>
          )}
        </div>
      </Card>
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="table-head">
              <tr>
                <th className="th">Date / heure</th>
                <th className="th">Utilisateur / IP</th>
                <th className="th">Action</th>
                <th className="th">Entité</th>
                <th className="th">Détails</th>
                <th className="th">Résultat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50">
                  <td className="td tabular-nums">{fmtDateTime(e.created_at)}</td>
                  <td className="td">
                    {e.user_email ?? "—"}
                    {e.ip_address && <div className="font-mono text-xs text-slate-400">{e.ip_address}</div>}
                  </td>
                  <td className="td font-medium text-slate-900">{e.action_label}</td>
                  <td className="td">
                    {e.entity_type ? <span className="text-slate-500">{ENTITY_LABELS[e.entity_type] ?? e.entity_type}</span> : "—"}
                    {e.entity_label && <div className="max-w-[16rem] truncate text-slate-900" title={e.entity_label}>{e.entity_label}</div>}
                  </td>
                  <td className="td max-w-[16rem] truncate text-slate-600" title={prettyDetails(e.details)}>{prettyDetails(e.details) || "—"}</td>
                  <td className="td">
                    {e.result === "SUCCESS" ? <Badge className="bg-success-100 text-success-800 ring-success-600/20">Succès</Badge> : <Badge className="bg-danger-100 text-danger-800 ring-danger-600/20">Échec</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && !data && <Spinner />}
        {data && data.items.length === 0 && <EmptyState title="Aucun événement ne correspond aux critères" />}
        {data && <Pagination page={page} size={SIZE} total={data.total} onPage={setPage} />}
      </Card>
    </>
  );
}

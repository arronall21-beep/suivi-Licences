import { CalendarClock } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DaysCell, EmptyState, PageHeader, PriorityBadge, Spinner, StatusBadge } from "../components/ui";
import { CATEGORY_LABELS, STATUS_META, fmtDate, fmtMoney } from "../format";
import { useFetch } from "../hooks";
import type { RenewalItem, Status } from "../types";

const HORIZONS = [
  { v: 30, l: "30 jours" },
  { v: 90, l: "90 jours" },
  { v: 180, l: "6 mois" },
  { v: 365, l: "12 mois" },
  { v: 730, l: "24 mois" },
];

export default function Renewals() {
  const [horizon, setHorizon] = useState(365);
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const { data, loading } = useFetch<RenewalItem[]>("/renewals", { horizon_days: horizon, type, status });
  const navigate = useNavigate();

  const months = useMemo(() => {
    const groups = new Map<string, RenewalItem[]>();
    const now = new Date();
    for (const it of data ?? []) {
      const d = new Date(it.end_date + "T00:00:00");
      const key = d < new Date(now.getFullYear(), now.getMonth(), 1) ? "0000-00" : `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      groups.set(key, [...(groups.get(key) ?? []), it]);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [data]);

  const budget = (data ?? []).reduce((s, i) => s + (i.budget ?? 0), 0);
  const counts = (data ?? []).reduce<Record<string, number>>((acc, i) => ({ ...acc, [i.status]: (acc[i.status] ?? 0) + 1 }), {});

  return (
    <>
      <PageHeader title="Planning de renouvellement" subtitle="Actifs et contrats arrivant à échéance, regroupés par mois — les contrats tiennent compte du préavis" />
      <div className="card mb-4 flex flex-wrap items-center gap-3 p-4">
        <div className="flex rounded-md border border-slate-300 bg-white p-0.5">
          {HORIZONS.map((h) => (
            <button key={h.v} onClick={() => setHorizon(h.v)} className={`rounded px-3 py-1.5 text-sm ${horizon === h.v ? "bg-brand-700 text-white" : "text-slate-600 hover:bg-slate-100"}`}>
              {h.l}
            </button>
          ))}
        </div>
        <select className="input w-44" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Tous les types</option>
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="input w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Tous les statuts</option>
          {(["EXPIRE", "CRITIQUE", "ALERTE", "OK"] as Status[]).map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </select>
        <div className="ml-auto flex items-center gap-4 text-sm text-slate-600">
          {(["EXPIRE", "CRITIQUE", "ALERTE", "OK"] as Status[]).map((s) => (
            <span key={s} className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: STATUS_META[s].color }} />{STATUS_META[s].label} <b className="tabular-nums">{counts[s] ?? 0}</b></span>
          ))}
          <span className="border-l border-slate-200 pl-4">Budget : <b>{fmtMoney(budget)}</b></span>
        </div>
      </div>

      {loading && !data && <Spinner />}
      {data?.length === 0 && <div className="card"><EmptyState title="Aucune échéance sur cet horizon" /></div>}
      <div className="space-y-4">
        {months.map(([key, items]) => (
          <div key={key} className="card overflow-hidden">
            <div className={`flex items-center gap-2 border-b px-5 py-3 text-sm font-semibold ${key === "0000-00" ? "border-danger-200 bg-danger-50 text-danger-800" : "border-slate-200 bg-slate-50 text-slate-800"}`}>
              <CalendarClock className="h-4 w-4" />
              {key === "0000-00" ? "En retard (mois précédents)" : new Date(key + "-01T00:00:00").toLocaleDateString("fr-FR", { month: "long", year: "numeric" })}
              <span className="font-normal text-slate-500">— {items.length} élément(s)</span>
            </div>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] table-fixed divide-y divide-slate-100">
              <colgroup><col className="w-[26%]" /><col className="w-[9%]" /><col className="w-[9%]" /><col className="w-[15%]" /><col className="w-[9%]" /><col className="w-[6%]" /><col className="w-[12%]" /><col className="w-[8%]" /><col className="w-[8%]" /></colgroup>
              <thead><tr><th className="th">Actif / Contrat</th><th className="th">Type</th><th className="th">Échéance</th><th className="th">Début renouv.</th><th className="th">Jours</th><th className="th">Prio.</th><th className="th">Responsable</th><th className="th">Statut</th><th className="th text-right">Budget</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((r) => (
                  <tr key={`${r.kind}-${r.id}`} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(r.kind === "ASSET" ? `/actifs/fiche/${r.id}` : `/contrats?focus=${r.id}`)}>
                    <td className="td"><div className="truncate font-medium text-slate-900" title={r.name}>{r.name}</div><div className="truncate text-xs text-slate-500">{r.reference}{r.vendor_name ? ` · ${r.vendor_name}` : ""}</div></td>
                    <td className="td">{CATEGORY_LABELS[r.type]}</td>
                    <td className="td">{fmtDate(r.end_date)}</td>
                    <td className={`td ${r.notice_reached && r.status !== "EXPIRE" ? "font-semibold text-caution-700" : ""}`}>
                      {r.kind === "CONTRACT" ? <>{fmtDate(r.renewal_start_date)}<div className="text-xs font-normal text-slate-500">préavis {r.notice_period_days ?? 0} j</div></> : "—"}
                    </td>
                    <td className="td"><DaysCell days={r.days_remaining} /></td>
                    <td className="td"><PriorityBadge value={r.priority} /></td>
                    <td className="td truncate" title={r.owner ?? ""}>{r.owner ?? "—"}</td>
                    <td className="td"><StatusBadge status={r.status} /></td>
                    <td className="td text-right tabular-nums">{fmtMoney(r.budget)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

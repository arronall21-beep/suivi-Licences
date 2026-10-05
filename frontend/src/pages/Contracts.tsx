import { ExternalLink, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { ContractForm } from "../components/forms";
import { ConfirmButton, DaysCell, EmptyState, Modal, PageHeader, Spinner, StatusBadge, useToast } from "../components/ui";
import { CONTRACT_TYPES, STATUS_META, fmtDate, fmtMoney } from "../format";
import { useFetch } from "../hooks";
import type { Contract, Status } from "../types";

export default function Contracts() {
  const [sp] = useSearchParams();
  const focus = Number(sp.get("focus")) || null;
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const { data, loading, reload } = useFetch<Contract[]>("/contracts", { q, type, status });
  const [editing, setEditing] = useState<Contract | null | undefined>(undefined);
  const { can } = useAuth();
  const canWrite = can("data:write");
  const canDelete = can("data:delete");
  const toast = useToast();

  useEffect(() => {
    if (focus && data) document.getElementById(`c-${focus}`)?.scrollIntoView({ block: "center" });
  }, [focus, data]);

  const remove = async (c: Contract) => {
    try {
      await api.del(`/contracts/${c.id}`);
      toast("success", `Contrat ${c.reference} supprimé`);
      reload();
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };
  const total = data?.reduce((s, c) => s + Number(c.annual_amount ?? 0), 0) ?? 0;

  return (
    <>
      <PageHeader
        title="Contrats"
        subtitle={data ? `${data.length} contrat(s) — ${fmtMoney(total)} / an` : undefined}
        actions={canWrite && <button className="btn-primary" onClick={() => setEditing(null)}><Plus className="h-4 w-4" /> Nouveau contrat</button>}
      />
      <div className="card mb-4 flex flex-wrap gap-3 p-4">
        <div className="relative min-w-[260px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input pl-9" placeholder="Référence, marché, périmètre, fournisseur…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <select className="input w-60" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Type de contrat</option>
          {CONTRACT_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Échéance</option>
          {(Object.keys(STATUS_META) as Status[]).map((s) => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </select>
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="th">Référence</th><th className="th">Fournisseur</th><th className="th">Type / périmètre</th><th className="th">Responsable</th>
                <th className="th">Fin</th><th className="th">Préavis</th><th className="th">Début renouvellement</th><th className="th">Jours restants</th>
                <th className="th">Échéance</th><th className="th text-right">Montant annuel</th><th className="th">Statut</th><th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.map((c) => {
                const noticeReached = c.renewal_start_date && new Date(c.renewal_start_date) <= new Date();
                return (
                  <tr key={c.id} id={`c-${c.id}`} className={focus === c.id ? "bg-brand-50" : "hover:bg-slate-50"}>
                    <td className="td">
                      <div className="font-mono text-xs font-medium text-slate-800">{c.reference}</div>
                      {c.market_ref && <div className="text-xs text-slate-500">Marché {c.market_ref}</div>}
                    </td>
                    <td className="td">{c.vendor_name ?? "—"}</td>
                    <td className="td max-w-xs">
                      <div className="truncate">{c.type ?? "—"}</div>
                      <div className="truncate text-xs text-slate-500" title={c.scope ?? ""}>{c.scope}</div>
                    </td>
                    <td className="td">{c.internal_owner ?? "—"}</td>
                    <td className="td">{fmtDate(c.end_date)}</td>
                    <td className="td">{c.notice_period_days != null ? `${c.notice_period_days} j` : "—"}</td>
                    <td className={`td ${noticeReached && c.lifecycle_status !== "EXPIRE" ? "font-semibold text-caution-700" : ""}`}>
                      {fmtDate(c.renewal_start_date)}
                      {noticeReached && c.lifecycle_status !== "EXPIRE" && <div className="text-xs font-normal">Préavis atteint</div>}
                    </td>
                    <td className="td"><DaysCell days={c.days_remaining} /></td>
                    <td className="td"><StatusBadge status={c.lifecycle_status} /></td>
                    <td className="td text-right tabular-nums">{fmtMoney(c.annual_amount)}</td>
                    <td className="td text-xs">{c.status ?? "—"}</td>
                    <td className="td text-right">
                      <Link to={`/actifs?contract_id=${c.id}`} className="btn-ghost" title="Actifs liés"><ExternalLink className="h-4 w-4" /></Link>
                      {canWrite && <button className="btn-ghost" title="Modifier" onClick={() => setEditing(c)}><Pencil className="h-4 w-4" /></button>}
                      {canDelete && <ConfirmButton onConfirm={() => remove(c)} message={<>Supprimer le contrat <b>{c.reference}</b> ? Les actifs liés seront détachés.</>}><Trash2 className="h-4 w-4" /></ConfirmButton>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {loading && !data && <Spinner />}
        {data?.length === 0 && <EmptyState title="Aucun contrat" />}
      </div>
      <Modal open={editing !== undefined} title={editing ? `Modifier ${editing.reference}` : "Nouveau contrat"} onClose={() => setEditing(undefined)} wide>
        {editing !== undefined && <ContractForm contract={editing} onCancel={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); reload(); }} />}
      </Modal>
    </>
  );
}

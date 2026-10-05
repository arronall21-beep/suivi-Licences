import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AssignmentForm } from "../components/forms";
import { ConfirmButton, EmptyState, Modal, PageHeader, Spinner, UsageBar, useToast } from "../components/ui";
import { fmtDate, fmtNum } from "../format";
import { useFetch } from "../hooks";
import type { Asset, Assignment, Page } from "../types";

export default function Assignments() {
  const [q, setQ] = useState("");
  const { data, loading, reload } = useFetch<Assignment[]>("/assignments", { q });
  const lic = useFetch<Page<Asset>>("/assets", { category: "LICENCE", size: 500, sort: "name" });
  const [editing, setEditing] = useState<Assignment | null | undefined>(undefined);
  const { can } = useAuth();
  const canWrite = can("data:write");
  const toast = useToast();
  const refresh = () => { reload(); lic.reload(); };
  const remove = async (a: Assignment) => {
    try {
      await api.del(`/assignments/${a.id}`);
      toast("success", "Affectation supprimée");
      refresh();
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };
  const licences = lic.data?.items ?? [];
  const tot = licences.reduce((s, l) => s + (l.total_quantity ?? 0), 0);
  const used = licences.reduce((s, l) => s + l.assigned_quantity, 0);

  return (
    <>
      <PageHeader title="Affectations de licences"
        subtitle={`${fmtNum(used)} licences affectées sur ${fmtNum(tot)} — ${fmtNum(tot - used)} disponibles`}
        actions={canWrite && <button className="btn-primary" onClick={() => setEditing(null)}><Plus className="h-4 w-4" /> Nouvelle affectation</button>} />

      <div className="card mb-6 overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">Utilisation par licence</div>
        <div className="max-h-80 overflow-y-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="sticky top-0 bg-slate-50"><tr><th className="th">Licence</th><th className="th">Type</th><th className="th text-right">Total</th><th className="th text-right">Affectées</th><th className="th text-right">Disponibles</th><th className="th">Taux</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {licences.map((l) => (
                <tr key={l.id} className="hover:bg-slate-50">
                  <td className="td"><Link className="font-medium text-slate-900 hover:text-brand-700" to={`/actifs/fiche/${l.id}`}>{l.name}</Link> <span className="text-xs text-slate-500">{l.reference}</span></td>
                  <td className="td">{l.lic_type ?? "—"}</td>
                  <td className="td text-right tabular-nums">{fmtNum(l.total_quantity)}</td>
                  <td className="td text-right tabular-nums">{fmtNum(l.assigned_quantity)}</td>
                  <td className={`td text-right font-semibold tabular-nums ${(l.available_quantity ?? 0) === 0 ? "text-danger-700" : "text-success-700"}`}>{fmtNum(l.available_quantity)}</td>
                  <td className="td"><UsageBar rate={l.usage_rate} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-3">
          <span className="text-sm font-semibold text-slate-900">Historique des affectations</span>
          <div className="relative w-80">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder="Utilisateur, poste, direction, licence…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50"><tr><th className="th">Licence</th><th className="th">Utilisateur</th><th className="th">Poste</th><th className="th">Direction</th><th className="th text-right">Qté</th><th className="th">Date</th><th className="th">Notes</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {data?.map((a) => (
              <tr key={a.id} className="hover:bg-slate-50">
                <td className="td"><Link className="font-medium text-slate-900 hover:text-brand-700" to={`/actifs/fiche/${a.asset_id}`}>{a.asset_name}</Link><div className="text-xs text-slate-500">{a.asset_reference}</div></td>
                <td className="td">{a.assigned_to_user ?? "—"}</td>
                <td className="td">{a.assigned_to_device ?? "—"}</td>
                <td className="td">{a.assigned_to_department ?? "—"}</td>
                <td className="td text-right font-semibold tabular-nums">{a.quantity}</td>
                <td className="td">{fmtDate(a.assigned_date)}</td>
                <td className="td max-w-[240px] truncate text-slate-500" title={a.notes ?? ""}>{a.notes}</td>
                <td className="td text-right">
                  {canWrite && (
                    <>
                      <button className="btn-ghost" onClick={() => setEditing(a)}><Pencil className="h-4 w-4" /></button>
                      <ConfirmButton onConfirm={() => remove(a)} title="Désaffecter" confirmLabel="Désaffecter" message={<>Retirer l'affectation de {a.quantity} licence(s) ({a.asset_name}) à <b>{a.assigned_to_user ?? a.assigned_to_device ?? a.assigned_to_department}</b> ?</>} irreversible={false}><Trash2 className="h-4 w-4" /></ConfirmButton>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && !data && <Spinner />}
        {data?.length === 0 && <EmptyState title="Aucune affectation" />}
      </div>
      <Modal open={editing !== undefined} title={editing ? "Modifier l'affectation" : "Nouvelle affectation"} onClose={() => setEditing(undefined)}>
        {editing !== undefined && <AssignmentForm assignment={editing} licences={licences} onCancel={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); refresh(); }} />}
      </Modal>
    </>
  );
}

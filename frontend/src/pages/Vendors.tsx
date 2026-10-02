import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { VendorForm } from "../components/forms";
import { ConfirmButton, EmptyState, Modal, PageHeader, Spinner, useToast } from "../components/ui";
import { useFetch } from "../hooks";
import type { Vendor } from "../types";

export default function Vendors() {
  const [q, setQ] = useState("");
  const { data, loading, reload } = useFetch<Vendor[]>("/vendors", { q });
  const [editing, setEditing] = useState<Vendor | null | undefined>(undefined);
  const { isAdmin } = useAuth();
  const toast = useToast();
  const remove = async (v: Vendor) => {
    try {
      await api.del(`/vendors/${v.id}`);
      toast("success", `${v.name} supprimé`);
      reload();
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };
  return (
    <>
      <PageHeader title="Fournisseurs" subtitle={data ? `${data.length} fournisseur(s)` : undefined}
        actions={isAdmin && <button className="btn-primary" onClick={() => setEditing(null)}><Plus className="h-4 w-4" /> Nouveau fournisseur</button>} />
      <div className="card mb-4 p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input className="input pl-9" placeholder="Rechercher un fournisseur…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>
      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50"><tr><th className="th">Nom</th><th className="th">Contact</th><th className="th">Email support</th><th className="th">Téléphone</th><th className="th">Site web</th><th className="th" /></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {data?.map((v) => (
              <tr key={v.id} className="hover:bg-slate-50">
                <td className="td font-medium"><Link className="text-slate-900 hover:text-blue-700" to={`/actifs?vendor_id=${v.id}`}>{v.name}</Link></td>
                <td className="td">{v.contact_person ?? "—"}</td>
                <td className="td">{v.email_support ? <a className="text-blue-700 hover:underline" href={`mailto:${v.email_support}`}>{v.email_support}</a> : "—"}</td>
                <td className="td">{v.phone ?? "—"}</td>
                <td className="td">{v.website ? <a className="text-blue-700 hover:underline" href={v.website} target="_blank" rel="noreferrer">{v.website.replace(/^https?:\/\//, "")}</a> : "—"}</td>
                <td className="td text-right">
                  {isAdmin && (
                    <>
                      <button className="btn-ghost" onClick={() => setEditing(v)}><Pencil className="h-4 w-4" /></button>
                      <ConfirmButton onConfirm={() => remove(v)} message={`Supprimer ${v.name} ?`}><Trash2 className="h-4 w-4" /></ConfirmButton>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && !data && <Spinner />}
        {data?.length === 0 && <EmptyState title="Aucun fournisseur" />}
      </div>
      <Modal open={editing !== undefined} title={editing ? `Modifier ${editing.name}` : "Nouveau fournisseur"} onClose={() => setEditing(undefined)}>
        {editing !== undefined && <VendorForm vendor={editing} onCancel={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); reload(); }} />}
      </Modal>
    </>
  );
}

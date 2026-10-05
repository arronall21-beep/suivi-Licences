import { ArrowDown, ArrowUp, ArrowUpDown, Eye, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AssetForm } from "../components/forms";
import { ConfirmButton, CriticalityBadge, DaysCell, EmptyState, Modal, PageHeader, Pagination, Spinner, StatusBadge, UsageBar, useToast } from "../components/ui";
import { CATEGORY_LABELS, CATEGORY_PLURAL, SLUG_CATEGORY, STATUS_META, fmtDate } from "../format";
import { useFetch, useReferenceData } from "../hooks";
import type { Asset, Category, Page, Status } from "../types";

interface Options {
  departments: string[];
  criticalities: string[];
}

const PAGE_SIZE = 20;

export default function Assets() {
  const { slug } = useParams();
  const category: Category | undefined = slug ? SLUG_CATEGORY[slug] : undefined;
  const [sp, setSp] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const canWrite = can("data:write");
  const canDelete = can("data:delete");
  const { vendors } = useReferenceData();
  const options = useFetch<Options>("/assets/options").data;

  const q = sp.get("q") ?? "";
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]);
  const filters = {
    q,
    category: category ?? sp.get("category") ?? "",
    status: sp.getAll("status"),
    criticality: sp.get("criticality") ?? "",
    department: sp.get("department") ?? "",
    vendor_id: sp.get("vendor_id") ?? "",
    contract_id: sp.get("contract_id") ?? "",
    sort: sp.get("sort") ?? "end_date",
    order: sp.get("order") ?? "asc",
    page: Number(sp.get("page") ?? 1),
    size: PAGE_SIZE,
  };
  const { data, loading, error, reload } = useFetch<Page<Asset>>("/assets", filters);
  const [editing, setEditing] = useState<Asset | null | undefined>(undefined);

  const setParam = (k: string, v: string | string[] | null) => {
    const next = new URLSearchParams(sp);
    next.delete(k);
    if (Array.isArray(v)) v.forEach((x) => next.append(k, x));
    else if (v) next.set(k, v);
    if (k !== "page") next.delete("page");
    setSp(next, { replace: true });
  };
  useEffect(() => {
    const t = setTimeout(() => search !== q && setParam("q", search), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const toggleSort = (key: string) => {
    const next = new URLSearchParams(sp);
    next.set("sort", key);
    next.set("order", filters.sort === key && filters.order === "asc" ? "desc" : "asc");
    setSp(next, { replace: true });
  };
  const SortTh = ({ k, children }: { k: string; children: string }) => (
    <th className="th cursor-pointer select-none hover:text-slate-800" onClick={() => toggleSort(k)}>
      <span className="inline-flex items-center gap-1">
        {children}
        {filters.sort === k ? (filters.order === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-30" />}
      </span>
    </th>
  );

  const remove = async (a: Asset) => {
    try {
      await api.del(`/assets/${a.id}`);
      toast("success", `${a.reference} supprimé`);
      reload();
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };

  const hasFilters = filters.contract_id || filters.q || filters.status.length || filters.criticality || filters.department || filters.vendor_id || (!category && filters.category);
  const title = category ? CATEGORY_PLURAL[category] : "Tous les actifs";

  return (
    <>
      <PageHeader
        title={title}
        subtitle={data ? `${data.total} élément(s)` : undefined}
        actions={canWrite && (
          <button className="btn-primary" onClick={() => setEditing(null)}>
            <Plus className="h-4 w-4" /> Nouvel actif
          </button>
        )}
      />

      <div className="card mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="relative min-w-[260px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder="Rechercher par référence, nom, fournisseur, responsable…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          {!category && (
            <select className="input w-40" value={filters.category} onChange={(e) => setParam("category", e.target.value)}>
              <option value="">Catégorie</option>
              {(["LICENCE", "CERTIFICAT", "MATERIEL", "APPLICATION"] as Category[]).map((c) => (
                <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
              ))}
            </select>
          )}
          <select className="input w-40" value={filters.status[0] ?? ""} onChange={(e) => setParam("status", e.target.value ? [e.target.value] : null)}>
            <option value="">Statut</option>
            {(Object.keys(STATUS_META) as Status[]).map((s) => (
              <option key={s} value={s}>{STATUS_META[s].label}</option>
            ))}
          </select>
          <select className="input w-36" value={filters.criticality} onChange={(e) => setParam("criticality", e.target.value)}>
            <option value="">Criticité</option>
            {options?.criticalities.map((c) => <option key={c}>{c}</option>)}
          </select>
          <select className="input w-48" value={filters.department} onChange={(e) => setParam("department", e.target.value)}>
            <option value="">Direction</option>
            {options?.departments.map((c) => <option key={c}>{c}</option>)}
          </select>
          <select className="input w-48" value={filters.vendor_id} onChange={(e) => setParam("vendor_id", e.target.value)}>
            <option value="">Fournisseur</option>
            {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
          {hasFilters ? (
            <button className="btn-ghost" onClick={() => setSp(new URLSearchParams(), { replace: true })}>
              <X className="h-4 w-4" /> Réinitialiser
            </button>
          ) : null}
        </div>
        {filters.status.length > 1 && (
          <div className="mt-3 flex gap-2 text-xs text-slate-500">Statuts : {filters.status.map((s) => <StatusBadge key={s} status={s as Status} />)}</div>
        )}
      </div>

      <div className="card overflow-hidden">
        {error && <div className="p-4 text-sm text-danger-700">{error}</div>}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <SortTh k="reference">Référence</SortTh>
                <SortTh k="name">Nom</SortTh>
                {!category && <SortTh k="category">Catégorie</SortTh>}
                <SortTh k="vendor">Fournisseur</SortTh>
                <SortTh k="owner">Responsable</SortTh>
                {category === "LICENCE" && <th className="th">Utilisation</th>}
                <SortTh k="end_date">Échéance</SortTh>
                <SortTh k="days_remaining">Jours restants</SortTh>
                <th className="th">Statut</th>
                <SortTh k="criticality">Criticité</SortTh>
                <th className="th text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data?.items.map((a) => (
                <tr key={a.id} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(`/actifs/fiche/${a.id}`)}>
                  <td className="td font-mono text-xs text-slate-600">{a.reference}</td>
                  <td className="td max-w-xs truncate font-medium text-slate-900" title={a.name}>{a.name}</td>
                  {!category && <td className="td">{CATEGORY_LABELS[a.category]}</td>}
                  <td className="td">{a.vendor_name ?? "—"}</td>
                  <td className="td">{a.internal_owner ?? "—"}</td>
                  {category === "LICENCE" && (
                    <td className="td">
                      <UsageBar rate={a.usage_rate} />
                      <div className="text-xs text-slate-500">{a.assigned_quantity} / {a.total_quantity ?? 0}</div>
                    </td>
                  )}
                  <td className="td">{fmtDate(a.effective_end_date)}</td>
                  <td className="td"><DaysCell days={a.days_remaining} /></td>
                  <td className="td"><StatusBadge status={a.status} /></td>
                  <td className="td"><CriticalityBadge value={a.criticality} /></td>
                  <td className="td text-right" onClick={(e) => e.stopPropagation()}>
                    <button className="btn-ghost" title="Ouvrir" onClick={() => navigate(`/actifs/fiche/${a.id}`)}><Eye className="h-4 w-4" /></button>
                    {canWrite && <button className="btn-ghost" title="Modifier" onClick={() => setEditing(a)}><Pencil className="h-4 w-4" /></button>}
                    {canDelete && <ConfirmButton onConfirm={() => remove(a)} message={<>Supprimer <b>{a.reference}</b> ({a.name}) ? Ses affectations seront également supprimées.</>}><Trash2 className="h-4 w-4" /></ConfirmButton>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading && !data && <Spinner />}
        {data && data.items.length === 0 && <EmptyState title="Aucun actif ne correspond aux critères" />}
        {data && <Pagination page={filters.page} size={PAGE_SIZE} total={data.total} onPage={(p) => setParam("page", String(p))} />}
      </div>

      <Modal open={editing !== undefined} title={editing ? `Modifier ${editing.reference}` : "Nouvel actif"} onClose={() => setEditing(undefined)} wide>
        {editing !== undefined && (
          <AssetForm asset={editing} category={category} onCancel={() => setEditing(undefined)}
            onSaved={(a) => { setEditing(undefined); if (editing) reload(); else navigate(`/actifs/fiche/${a.id}`); }} />
        )}
      </Modal>
    </>
  );
}

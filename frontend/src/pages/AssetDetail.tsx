import { ArrowLeft, Pencil, Plus, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { AssetForm, AssignmentForm } from "../components/forms";
import { ConfirmButton, CriticalityBadge, DaysCell, EmptyState, Modal, Spinner, StatusBadge, UsageBar, useToast } from "../components/ui";
import { CATEGORY_LABELS, CATEGORY_SLUG, CATEGORY_PLURAL, fmtDate, fmtDateTime, fmtMoney, fmtNum } from "../format";
import { useFetch } from "../hooks";
import type { Asset, Assignment } from "../types";

function Item({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-slate-900">{children === null || children === undefined || children === "" ? <span className="text-slate-400">—</span> : children}</dd>
    </div>
  );
}

function Block({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="card">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

export default function AssetDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const canWrite = can("data:write");
  const canDelete = can("data:delete");
  const { data: a, loading, error, reload } = useFetch<Asset>(`/assets/${id}`);
  const [edit, setEdit] = useState(false);
  const [assign, setAssign] = useState<Assignment | null | undefined>(undefined);

  if (loading && !a) return <Spinner />;
  if (error || !a) return <div className="card p-6 text-danger-700">{error ?? "Introuvable"}</div>;

  const removeAssignment = async (as: Assignment) => {
    try {
      await api.del(`/assignments/${as.id}`);
      toast("success", "Affectation supprimée");
      reload();
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };
  const removeAsset = async () => {
    try {
      await api.del(`/assets/${a.id}`);
      toast("success", `${a.reference} supprimé`);
      navigate(`/actifs/${CATEGORY_SLUG[a.category]}`);
    } catch (e) {
      toast("error", (e as Error).message);
    }
  };
  const isLic = a.category === "LICENCE";

  return (
    <>
      <Link to={`/actifs/${CATEGORY_SLUG[a.category]}`} className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> {CATEGORY_PLURAL[a.category]}
      </Link>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">{a.name}</h1>
            <StatusBadge status={a.status} />
          </div>
          <div className="mt-1 text-sm text-slate-500">
            <span className="font-mono">{a.reference}</span> · {CATEGORY_LABELS[a.category]} · mis à jour le {fmtDateTime(a.updated_at)}
          </div>
        </div>
        {(canWrite || canDelete) && (
          <div className="flex gap-2">
            {canWrite && <button className="btn-secondary" onClick={() => setEdit(true)}><Pencil className="h-4 w-4" /> Modifier</button>}
            {canDelete && <ConfirmButton onConfirm={removeAsset} message={<>Supprimer définitivement <b>{a.reference}</b> ({a.name}) et ses affectations ?</>}><Trash2 className="h-4 w-4" /> Supprimer</ConfirmButton>}
          </div>
        )}
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="card p-4"><div className="text-xs text-slate-500">Échéance</div><div className="mt-1 text-lg font-semibold">{fmtDate(a.effective_end_date)}</div></div>
        <div className="card p-4"><div className="text-xs text-slate-500">Jours restants</div><div className="mt-1 text-lg"><DaysCell days={a.days_remaining} /></div></div>
        <div className="card p-4"><div className="text-xs text-slate-500">Criticité</div><div className="mt-1.5"><CriticalityBadge value={a.criticality} /></div></div>
        <div className="card p-4"><div className="text-xs text-slate-500">Coût annuel</div><div className="mt-1 text-lg font-semibold">{fmtMoney(a.annual_cost)}</div></div>
      </div>

      {isLic && (
        <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[
            ["Quantité totale", fmtNum(a.total_quantity), "text-slate-900"],
            ["Quantité affectée", fmtNum(a.assigned_quantity), "text-brand-700"],
            ["Quantité disponible", fmtNum(a.available_quantity), (a.available_quantity ?? 0) === 0 ? "text-danger-700" : "text-success-700"],
          ].map(([l, v, c]) => (
            <div key={l} className="card p-4"><div className="text-xs text-slate-500">{l}</div><div className={`mt-1 text-2xl font-semibold tabular-nums ${c}`}>{v}</div></div>
          ))}
          <div className="card p-4">
            <div className="text-xs text-slate-500">Taux d'utilisation</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{a.usage_rate === null ? "—" : `${a.usage_rate.toLocaleString("fr-FR")} %`}</div>
            <div className="mt-1"><UsageBar rate={a.usage_rate} /></div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Block title="Informations générales">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-3">
              <Item label="Fournisseur">{a.vendor_name}</Item>
              <Item label="Contrat">{a.contract_reference && <Link className="text-brand-700 hover:underline" to={`/contrats?focus=${a.contract_id}`}>{a.contract_reference}</Link>}</Item>
              <Item label="Responsable">{a.internal_owner}</Item>
              <Item label="Direction">{a.user_department}</Item>
              <Item label="Date de début">{a.start_date && fmtDate(a.start_date)}</Item>
              <Item label="Date de fin">{a.end_date && fmtDate(a.end_date)}</Item>
              <Item label="Budget estimé">{a.budget_estimated !== null && fmtMoney(a.budget_estimated)}</Item>
              {isLic && <><Item label="Type de licence">{a.lic_type}</Item><Item label="Clé de licence">{a.license_key && <span className="font-mono text-xs">{a.license_key}</span>}</Item></>}
              {a.category === "CERTIFICAT" && <><Item label="Type">{a.cert_type}</Item><Item label="Autorité">{a.authority}</Item><Item label="Cible">{a.server_app_target}</Item><Item label="Environnement">{a.environment}</Item></>}
              {a.category === "MATERIEL" && <><Item label="Marque / modèle">{[a.brand, a.model].filter(Boolean).join(" ")}</Item><Item label="N° de série">{a.serial_number}</Item><Item label="Site">{a.site_location}</Item><Item label="Fin de garantie">{a.warranty_end_date && fmtDate(a.warranty_end_date)}</Item><Item label="Fin de support">{a.support_end_date && fmtDate(a.support_end_date)}</Item><Item label="Contrat support">{a.support_contract_type}</Item></>}
              {a.category === "APPLICATION" && <><Item label="Propriétaire métier">{a.business_owner}</Item><Item label="Hébergement">{a.hosting_env}</Item><Item label="Prestataire">{a.service_provider}</Item><Item label="SLA">{a.sla_level}</Item></>}
            </dl>
          </Block>

          {isLic && (
            <Block title={`Affectations (${a.assignments?.length ?? 0})`} action={canWrite && (
              <button className="btn-primary py-1.5" disabled={(a.available_quantity ?? 0) <= 0} onClick={() => setAssign(null)}
                title={(a.available_quantity ?? 0) <= 0 ? "Aucune licence disponible" : undefined}>
                <Plus className="h-4 w-4" /> Affecter
              </button>
            )}>
              {a.assignments?.length ? (
                <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead><tr><th className="th">Utilisateur</th><th className="th">Poste</th><th className="th">Direction</th><th className="th">Qté</th><th className="th">Date</th><th className="th">Notes</th>{canWrite && <th className="th" />}</tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    {a.assignments.map((as) => (
                      <tr key={as.id}>
                        <td className="td">{as.assigned_to_user ?? "—"}</td>
                        <td className="td">{as.assigned_to_device ?? "—"}</td>
                        <td className="td">{as.assigned_to_department ?? "—"}</td>
                        <td className="td font-semibold tabular-nums">{as.quantity}</td>
                        <td className="td">{fmtDate(as.assigned_date)}</td>
                        <td className="td max-w-[220px] truncate text-slate-500" title={as.notes ?? ""}>{as.notes ?? ""}</td>
                        {canWrite && (
                          <td className="td text-right">
                            <button className="btn-ghost" onClick={() => setAssign(as)}><Pencil className="h-4 w-4" /></button>
                            <ConfirmButton onConfirm={() => removeAssignment(as)} title="Désaffecter" confirmLabel="Désaffecter" message={<>Retirer l'affectation de {as.quantity} licence(s) à <b>{as.assigned_to_user ?? as.assigned_to_device ?? as.assigned_to_department}</b> ?</>} irreversible={false}><Trash2 className="h-4 w-4" /></ConfirmButton>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              ) : (
                <EmptyState title="Aucune affectation" />
              )}
            </Block>
          )}
        </div>
        <div className="space-y-4">
          <Block title="Plan d'action"><p className="whitespace-pre-wrap text-sm text-slate-700">{a.action_plan || <span className="text-slate-400">Aucun plan d'action</span>}</p></Block>
          <Block title="Observations"><p className="whitespace-pre-wrap text-sm text-slate-700">{a.observation || <span className="text-slate-400">Aucune observation</span>}</p></Block>
        </div>
      </div>

      <Modal open={edit} title={`Modifier ${a.reference}`} onClose={() => setEdit(false)} wide>
        {edit && <AssetForm asset={a} onCancel={() => setEdit(false)} onSaved={() => { setEdit(false); reload(); }} />}
      </Modal>
      <Modal open={assign !== undefined} title={assign ? "Modifier l'affectation" : `Affecter ${a.name}`} onClose={() => setAssign(undefined)}>
        {assign !== undefined && (
          <>
            <div className="mb-4 rounded-md bg-brand-50 px-3 py-2 text-sm text-brand-800">
              {a.assigned_quantity} / {a.total_quantity ?? 0} affectées — <b>{a.available_quantity ?? 0} disponible(s)</b>
            </div>
            <AssignmentForm assignment={assign} fixedAssetId={a.id} onCancel={() => setAssign(undefined)} onSaved={() => { setAssign(undefined); reload(); }} />
          </>
        )}
      </Modal>
    </>
  );
}

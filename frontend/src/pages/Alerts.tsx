import { BellRing, Mail, Play } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { DaysCell, EmptyState, PageHeader, Spinner, StatusBadge, useToast } from "../components/ui";
import { CATEGORY_LABELS, fmtDate, fmtDateTime } from "../format";
import { useFetch } from "../hooks";
import type { NotificationItem, RenewalItem } from "../types";

interface AlertsData {
  smtp_configured: boolean;
  recipients: string[];
  thresholds: number[];
  items: (RenewalItem & { threshold: number })[];
}

const thLabel = (t: number) => (t === 0 ? "Expiré" : `J-${t}`);
const DELIVERY: Record<string, string> = {
  ENVOYE: "bg-emerald-100 text-emerald-800",
  NON_ENVOYE: "bg-slate-100 text-slate-700",
  ERREUR: "bg-red-100 text-red-800",
};

export default function Alerts() {
  const alerts = useFetch<AlertsData>("/alerts");
  const history = useFetch<NotificationItem[]>("/notifications");
  const { isAdmin } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    try {
      const r = await api.post<{ new: number; delivery_status: string | null; error?: string }>("/alerts/run");
      if (r.new === 0) toast("success", "Aucune nouvelle alerte : toutes ont déjà été notifiées");
      else if (r.delivery_status === "ENVOYE") toast("success", `${r.new} alerte(s) envoyée(s) par email`);
      else toast("error", `${r.new} alerte(s) enregistrée(s) mais non envoyée(s) : ${r.error}`);
      history.reload();
    } catch (e) {
      toast("error", (e as Error).message);
    } finally {
      setRunning(false);
    }
  };
  const a = alerts.data;
  const groups = a ? [0, ...[...a.thresholds].sort((x, y) => x - y)] : [];

  return (
    <>
      <PageHeader
        title="Alertes d'échéance"
        subtitle="Contrôle quotidien automatique (J-90, J-60, J-30, J-7 et expirés) — une seule notification par seuil et par échéance"
        actions={isAdmin && <button className="btn-primary" onClick={run} disabled={running}><Play className="h-4 w-4" /> {running ? "Exécution…" : "Lancer le contrôle maintenant"}</button>}
      />
      {a && (
        <div className={`mb-4 flex items-center gap-3 rounded-lg border px-4 py-3 text-sm ${a.smtp_configured && a.recipients.length ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-800"}`}>
          <Mail className="h-4 w-4" />
          {a.smtp_configured && a.recipients.length
            ? <>Emails envoyés à : <b>{a.recipients.join(", ")}</b></>
            : <>Envoi email inactif : configurer SMTP_HOST, SMTP_FROM et ALERT_RECIPIENTS dans le fichier .env. Les alertes restent tracées dans l'historique.</>}
        </div>
      )}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        {groups.map((t) => {
          const n = a?.items.filter((i) => i.threshold === t).length ?? 0;
          return (
            <div key={t} className="card p-4">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500"><BellRing className="h-3.5 w-3.5" /> {thLabel(t)}</div>
              <div className={`mt-1 text-2xl font-semibold tabular-nums ${t <= 7 ? "text-red-700" : t <= 30 ? "text-orange-700" : "text-slate-900"}`}>{n}</div>
            </div>
          );
        })}
      </div>

      <div className="card mb-6 overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">Alertes actives ({a?.items.length ?? 0})</div>
        {alerts.loading && !a && <Spinner />}
        {a && a.items.length === 0 && <EmptyState title="Aucune échéance dans les 90 prochains jours" />}
        {a && a.items.length > 0 && (
          <div className="max-h-[480px] overflow-y-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="sticky top-0 bg-slate-50"><tr><th className="th">Seuil</th><th className="th">Actif / Contrat</th><th className="th">Type</th><th className="th">Échéance</th><th className="th">Jours</th><th className="th">Responsable</th><th className="th">Statut</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {a.items.map((r) => (
                  <tr key={`${r.kind}-${r.id}`} className="cursor-pointer hover:bg-slate-50" onClick={() => navigate(r.kind === "ASSET" ? `/actifs/fiche/${r.id}` : `/contrats?focus=${r.id}`)}>
                    <td className="td"><span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs font-bold text-white">{thLabel(r.threshold)}</span></td>
                    <td className="td"><div className="font-medium text-slate-900">{r.name}</div><div className="text-xs text-slate-500">{r.reference}</div></td>
                    <td className="td">{CATEGORY_LABELS[r.type]}</td>
                    <td className="td">{fmtDate(r.end_date)}</td>
                    <td className="td"><DaysCell days={r.days_remaining} /></td>
                    <td className="td">{r.owner ?? "—"}</td>
                    <td className="td"><StatusBadge status={r.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-3 text-sm font-semibold text-slate-900">Historique des notifications</div>
        {history.data?.length === 0 && <EmptyState title="Aucune notification émise pour l'instant" />}
        {!!history.data?.length && (
          <div className="max-h-[420px] overflow-y-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="sticky top-0 bg-slate-50"><tr><th className="th">Date</th><th className="th">Seuil</th><th className="th">Élément</th><th className="th">Échéance</th><th className="th">Destinataires</th><th className="th">Envoi</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {history.data.map((n) => (
                  <tr key={n.id}>
                    <td className="td">{fmtDateTime(n.created_at)}</td>
                    <td className="td">{thLabel(n.threshold)}</td>
                    <td className="td"><div className="font-medium">{n.target_name}</div><div className="text-xs text-slate-500">{n.target_reference}</div></td>
                    <td className="td">{fmtDate(n.due_date)}</td>
                    <td className="td text-xs">{n.recipients ?? "—"}</td>
                    <td className="td"><span className={`rounded px-2 py-0.5 text-xs font-medium ${DELIVERY[n.delivery_status] ?? ""}`} title={n.error ?? ""}>{n.delivery_status.replace("_", " ")}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}

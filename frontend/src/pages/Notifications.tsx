import { Bell, CheckCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { notifyInboxChanged } from "../components/NotificationBell";
import { Badge, Button, Card, EmptyState, PageHeader, Pagination, Spinner } from "../components/ui";
import { fmtDateTime } from "../format";
import { useFetch } from "../hooks";
import { NOTIFICATION_PRIORITY } from "../theme";
import type { InboxItem, Page } from "../types";
import Alerts from "./Alerts";

type Inbox = Page<InboxItem> & { unread: number };

const KIND_LABELS: Record<string, string> = {
  CONTRACT_EXPIRING: "Contrat à échéance",
  CONTRACT_EXPIRED: "Contrat expiré",
  LICENSE_CRITICAL: "Licence critique",
  LICENSE_EXPIRING: "Licence à échéance",
  LICENSE_EXPIRED: "Licence expirée",
  CERTIFICATE_EXPIRING: "Certificat à échéance",
  CERTIFICATE_EXPIRED: "Certificat expiré",
  ASSET_EXPIRING: "Actif à échéance",
  ASSET_EXPIRED: "Actif expiré",
  IMPORT_DONE: "Import terminé",
  IMPORT_ERROR: "Erreur d'import",
  PASSWORD_RESET_REQUEST: "Demande de mot de passe",
};

function Inbox() {
  const navigate = useNavigate();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);
  const { data, loading, reload } = useFetch<Inbox>("/inbox", { unread_only: unreadOnly, priority, page, size: 15 });

  const open = async (n: InboxItem) => {
    if (!n.read) {
      await api.post(`/inbox/${n.id}/read`).catch(() => {});
      notifyInboxChanged();
    }
    if (n.link) navigate(n.link);
    else reload();
  };
  const readAll = async () => {
    await api.post("/inbox/read-all");
    notifyInboxChanged();
    reload();
  };

  return (
    <Card>
      <div className="card-header flex-wrap">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={unreadOnly} onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1); }} /> Non lues uniquement
          </label>
          <select className="input w-40" value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }} aria-label="Priorité">
            <option value="">Toutes priorités</option>
            <option value="HIGH">Haute</option>
            <option value="MEDIUM">Moyenne</option>
            <option value="LOW">Basse</option>
          </select>
        </div>
        <Button variant="secondary" small onClick={readAll} disabled={!data?.unread} icon={<CheckCheck className="h-3.5 w-3.5" />}>
          Tout marquer comme lu {data?.unread ? `(${data.unread})` : ""}
        </Button>
      </div>
      {loading && !data && <Spinner />}
      {data && data.items.length === 0 && <EmptyState title="Aucune notification">Les alertes d'échéance et les événements d'import apparaîtront ici.</EmptyState>}
      <ul className="divide-y divide-slate-100">
        {data?.items.map((n) => {
          const p = NOTIFICATION_PRIORITY[n.priority];
          return (
            <li key={n.id}>
              <button className={`flex w-full items-start gap-3 px-5 py-3.5 text-left hover:bg-slate-50 ${n.read ? "" : "bg-brand-50/50"}`} onClick={() => open(n)}>
                <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-slate-200" : p.dot}`} aria-label={n.read ? "Lue" : "Non lue"} />
                <span className="min-w-0 flex-1">
                  <span className={`block text-sm ${n.read ? "text-slate-700" : "font-semibold text-slate-900"}`}>{n.title}</span>
                  {n.message && <span className="mt-0.5 block text-sm text-slate-500">{n.message}</span>}
                  <span className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                    {fmtDateTime(n.created_at)}
                    <Badge className="bg-slate-100 text-slate-600 ring-slate-500/20">{KIND_LABELS[n.kind] ?? n.kind}</Badge>
                  </span>
                </span>
                <Badge className={p.cls}>{p.label}</Badge>
              </button>
            </li>
          );
        })}
      </ul>
      {data && <Pagination page={page} size={15} total={data.total} onPage={setPage} />}
    </Card>
  );
}

export default function Notifications() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") === "alertes" ? "alertes" : "inbox";
  return (
    <>
      <PageHeader title="Notifications" subtitle="Événements de l'application et alertes d'échéance" />
      <div className="mb-5 flex gap-1 border-b border-slate-200" role="tablist">
        {[
          { id: "inbox", label: "Mes notifications" },
          { id: "alertes", label: "Alertes d'échéance" },
        ].map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`-mb-px flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium ${tab === t.id ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}
            onClick={() => setSp(t.id === "inbox" ? {} : { tab: t.id }, { replace: true })}
          >
            {t.id === "inbox" && <Bell className="h-4 w-4" />}
            {t.label}
          </button>
        ))}
      </div>
      {tab === "inbox" ? <Inbox /> : <Alerts />}
    </>
  );
}

import { Database, DatabaseBackup, Mail, Server, Users } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Alert, Badge, Card, CardHeader, ImportStatusBadge, PageHeader, Spinner } from "../../components/ui";
import { fmtDateTime } from "../../format";
import { useFetch } from "../../hooks";

interface SystemInfo {
  version: string;
  environment: string;
  python: string;
  timezone: string;
  database: { status: string; version: string; latency_ms: number };
  smtp: { configured: boolean; source: string; host: string | null; port: number | null; security: string | null; warning: string | null };
  users: { active: number; inactive: number };
  last_import: { id: number; filename: string; status: string; rows_imported: number; imported_by: string | null; created_at: string } | null;
  last_alert_sent: { created_at: string; recipients: string | null; target: string | null } | null;
  scheduler: { enabled: boolean; running: boolean; next_run: string | null; hour: number };
  backup: { status: "OK" | "ANCIEN" | "AUCUN" | "NON_CONFIGURE"; message: string; directory: string; filename?: string; size_bytes?: number; modified_at?: string; age_hours?: number; count?: number };
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-900">{children}</dd>
    </div>
  );
}

const size = (n?: number) => (n === undefined ? "" : n > 1_048_576 ? `${(n / 1_048_576).toFixed(1)} Mo` : `${Math.max(1, Math.round(n / 1024))} Ko`);
const BACKUP_BADGE = {
  OK: ["Récente", "bg-success-100 text-success-800 ring-success-600/20"],
  ANCIEN: ["Ancienne", "bg-warning-100 text-warning-800 ring-warning-600/20"],
  AUCUN: ["Aucune", "bg-danger-100 text-danger-800 ring-danger-600/20"],
  NON_CONFIGURE: ["Non configurée", "bg-slate-100 text-slate-700 ring-slate-500/20"],
} as const;

export default function System() {
  const { data: s, loading, error } = useFetch<SystemInfo>("/admin/system");
  if (loading && !s) return <Spinner />;
  if (error || !s) return <Alert kind="danger">{error ?? "Informations indisponibles"}</Alert>;
  const [bLabel, bCls] = BACKUP_BADGE[s.backup.status];

  return (
    <>
      <PageHeader title="Système" subtitle="État de l'application et de ses dépendances" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><Server className="h-4 w-4" /> Application</span>} />
          <dl className="divide-y divide-slate-100 px-5 py-2">
            <Row label="Version"><Badge className="bg-info-100 text-info-800 ring-info-600/20">v{s.version}</Badge></Row>
            <Row label="Environnement">{s.environment}</Row>
            <Row label="Python">{s.python}</Row>
            <Row label="Fuseau horaire">{s.timezone}</Row>
            <Row label="Contrôle quotidien des alertes">
              {s.scheduler.running ? <>{String(s.scheduler.hour).padStart(2, "0")}h00 — prochain : {fmtDateTime(s.scheduler.next_run)}</> : <span className="text-warning-700">{s.scheduler.enabled ? "Arrêté" : "Désactivé (SCHEDULER_ENABLED)"}</span>}
            </Row>
          </dl>
        </Card>

        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><Database className="h-4 w-4" /> Base de données</span>} />
          <dl className="divide-y divide-slate-100 px-5 py-2">
            <Row label="État"><Badge className="bg-success-100 text-success-800 ring-success-600/20">Connectée</Badge></Row>
            <Row label="PostgreSQL">{s.database.version}</Row>
            <Row label="Latence">{s.database.latency_ms} ms</Row>
            <Row label="Dernier import Excel">
              {s.last_import ? (
                <span className="inline-flex flex-col items-end gap-1">
                  <span>{s.last_import.filename} — {s.last_import.rows_imported} ligne(s)</span>
                  <span className="inline-flex items-center gap-2 text-xs font-normal text-slate-500"><ImportStatusBadge status={s.last_import.status} /> {fmtDateTime(s.last_import.created_at)}</span>
                </span>
              ) : <span className="text-slate-400">Aucun import</span>}
            </Row>
          </dl>
        </Card>

        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><Mail className="h-4 w-4" /> Messagerie (SMTP)</span>} actions={<Link to="/admin/smtp" className="text-sm text-brand-700 hover:underline">Configurer</Link>} />
          <dl className="divide-y divide-slate-100 px-5 py-2">
            <Row label="État">{s.smtp.configured ? <Badge className="bg-success-100 text-success-800 ring-success-600/20">Configuré</Badge> : <Badge className="bg-warning-100 text-warning-800 ring-warning-600/20">SMTP non configuré</Badge>}</Row>
            {s.smtp.configured && <Row label="Serveur">{s.smtp.host}:{s.smtp.port} ({s.smtp.security})</Row>}
            {s.smtp.configured && <Row label="Source">{s.smtp.source === "database" ? "Interface (base de données)" : "Fichier .env"}</Row>}
            <Row label="Dernière alerte envoyée">
              {s.last_alert_sent ? <>{fmtDateTime(s.last_alert_sent.created_at)}<span className="block text-xs font-normal text-slate-500">{s.last_alert_sent.target}</span></> : <span className="text-slate-400">Aucune</span>}
            </Row>
          </dl>
          {s.smtp.warning && <div className="px-5 pb-4"><Alert kind="danger">{s.smtp.warning}</Alert></div>}
        </Card>

        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><Users className="h-4 w-4" /> Utilisateurs</span>} actions={<Link to="/admin/utilisateurs" className="text-sm text-brand-700 hover:underline">Gérer</Link>} />
          <dl className="divide-y divide-slate-100 px-5 py-2">
            <Row label="Utilisateurs actifs">{s.users.active}</Row>
            <Row label="Utilisateurs désactivés">{s.users.inactive}</Row>
          </dl>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader title={<span className="inline-flex items-center gap-2"><DatabaseBackup className="h-4 w-4" /> Sauvegarde de la base</span>} actions={<Badge className={bCls}>{bLabel}</Badge>} />
          <div className="space-y-3 px-5 py-4">
            <dl className="divide-y divide-slate-100">
              <Row label="Dernière sauvegarde connue">
                {s.backup.filename ? <>{s.backup.filename}<span className="block text-xs font-normal text-slate-500">{size(s.backup.size_bytes)} — {fmtDateTime(s.backup.modified_at)} (il y a {s.backup.age_hours} h) — {s.backup.count} fichier(s)</span></> : <span className="text-slate-400">{s.backup.message}</span>}
              </Row>
              <Row label="Répertoire surveillé">{s.backup.directory}</Row>
            </dl>
            {s.backup.status !== "OK" && (
              <Alert kind={s.backup.status === "ANCIEN" ? "warning" : "info"} title={s.backup.message}>
                Lancer <code className="rounded bg-slate-100 px-1">./scripts/backup.sh</code> depuis le serveur (planifiable avec cron) : les dumps sont déposés dans <code className="rounded bg-slate-100 px-1">./backups</code> et détectés ici automatiquement.
              </Alert>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}

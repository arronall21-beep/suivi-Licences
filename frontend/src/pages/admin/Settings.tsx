import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../api";
import { Button, Card, CardHeader, Field, FormError, InfoTip, PageHeader, Spinner, useToast } from "../../components/ui";
import { useConfig } from "../../config";
import { useFetch } from "../../hooks";

interface General {
  org_name: string;
  app_name: string;
  currency: string;
  currency_label: string;
  timezone: string;
  admin_email: string | null;
  critical_days: number;
  alert_days: number;
}
interface AlertCfg {
  thresholds: { days: number; enabled: boolean }[];
  notify_expired: boolean;
  recipients: { notify_owner: boolean; notify_admin: boolean; custom: string[] };
}

const CURRENCIES = ["XOF", "XAF", "EUR", "USD", "GBP"];
const TIMEZONES = ["Africa/Porto-Novo", "Africa/Abidjan", "Africa/Lagos", "Africa/Dakar", "Europe/Paris", "UTC"];

function GeneralForm({ initial, onSaved }: { initial: General; onSaved: () => void }) {
  const toast = useToast();
  const { reload } = useConfig();
  const [v, setV] = useState({ ...initial, admin_email: initial.admin_email ?? "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));
  const invalidOrder = Number(v.critical_days) >= Number(v.alert_days);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (invalidOrder) return setError("Le seuil critique doit être strictement inférieur au seuil d'alerte");
    setBusy(true);
    setError(null);
    try {
      await api.put("/admin/settings/general", { ...v, admin_email: v.admin_email || null, critical_days: Number(v.critical_days), alert_days: Number(v.alert_days) });
      await reload();
      toast("success", "Paramètres généraux enregistrés");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <Card>
        <CardHeader title="Paramètres généraux" subtitle="Identité de l'application, devise, fuseau et seuils d'échéance" />
        <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
          <Field label="Nom de l'organisation" required>
            <input className="input" required maxLength={120} value={v.org_name} onChange={set("org_name")} />
          </Field>
          <Field label="Nom de l'application" required>
            <input className="input" required maxLength={120} value={v.app_name} onChange={set("app_name")} />
          </Field>
          <Field label="Devise" required hint="Code ISO à 3 lettres ; utilisé pour l'affichage et les exports Excel">
            <input className="input" required list="currencies" pattern="[A-Za-z]{3}" maxLength={3} value={v.currency} onChange={(e) => setV((s) => ({ ...s, currency: e.target.value.toUpperCase() }))} />
            <datalist id="currencies">{CURRENCIES.map((c) => <option key={c} value={c} />)}</datalist>
          </Field>
          <Field label="Fuseau horaire" required hint="Détermine « aujourd'hui » pour le calcul des jours restants et l'heure du contrôle quotidien">
            <input className="input" required list="timezones" value={v.timezone} onChange={set("timezone")} />
            <datalist id="timezones">{TIMEZONES.map((c) => <option key={c} value={c} />)}</datalist>
          </Field>
          <Field label="Email administrateur" hint="Contact de l'administration ; destinataire des alertes si l'option est activée">
            <input className="input" type="email" value={v.admin_email} onChange={set("admin_email")} />
          </Field>
          <div />
          <Field label="Seuil critique (jours)" required hint="Statut CRITIQUE : de 1 jour jusqu'à ce seuil">
            <input className="input" type="number" min={1} max={3650} required value={v.critical_days} onChange={set("critical_days")} />
          </Field>
          <Field label="Seuil d'alerte (jours)" required hint="Statut ALERTE : au-delà du seuil critique, jusqu'à ce seuil" error={invalidOrder ? "Doit être supérieur au seuil critique" : null}>
            <input className={`input ${invalidOrder ? "input-invalid" : ""}`} type="number" min={1} max={3650} required value={v.alert_days} onChange={set("alert_days")} />
          </Field>
        </div>
        <div className="space-y-3 border-t border-slate-200 px-5 py-4">
          <FormError message={error} />
          <div className="flex justify-end">
            <Button type="submit" loading={busy}>Enregistrer les paramètres</Button>
          </div>
        </div>
      </Card>
    </form>
  );
}

function AlertsForm({ initial, onSaved }: { initial: AlertCfg; onSaved: () => void }) {
  const toast = useToast();
  const { reload } = useConfig();
  const [thresholds, setThresholds] = useState(initial.thresholds);
  const [notifyExpired, setNotifyExpired] = useState(initial.notify_expired);
  const [notifyOwner, setNotifyOwner] = useState(initial.recipients.notify_owner);
  const [notifyAdmin, setNotifyAdmin] = useState(initial.recipients.notify_admin);
  const [custom, setCustom] = useState(initial.recipients.custom.join("\n"));
  const [newDays, setNewDays] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const addThreshold = () => {
    const days = Number(newDays);
    if (!Number.isInteger(days) || days < 1 || days > 365) return setError("Seuil invalide : saisir un nombre de jours entre 1 et 365");
    if (thresholds.some((t) => t.days === days)) return setError(`Le seuil J-${days} existe déjà`);
    setError(null);
    setThresholds((l) => [...l, { days, enabled: true }].sort((a, b) => b.days - a.days));
    setNewDays("");
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const emails = custom.split(/[\s,;]+/).map((s) => s.trim()).filter(Boolean);
      await api.put("/admin/settings/alerts", { thresholds, notify_expired: notifyExpired, recipients: { notify_owner: notifyOwner, notify_admin: notifyAdmin, custom: emails } });
      await reload();
      toast("success", "Configuration des alertes enregistrée");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      <Card>
        <CardHeader title="Alertes d'échéance" subtitle="Seuils de notification et destinataires. Une alerte n'est jamais envoyée deux fois pour la même échéance." />
        <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
          <fieldset>
            <legend className="label">Seuils d'alerte</legend>
            <ul className="space-y-2">
              {thresholds.map((t) => (
                <li key={t.days} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2">
                  <label className="flex items-center gap-2 text-sm text-slate-800">
                    <input type="checkbox" checked={t.enabled} onChange={(e) => setThresholds((l) => l.map((x) => (x.days === t.days ? { ...x, enabled: e.target.checked } : x)))} />
                    <span className="font-semibold">J-{t.days}</span>
                    <span className="text-slate-500">— {t.days} jours avant l'échéance</span>
                  </label>
                  <button type="button" className="btn-ghost text-slate-400 hover:text-danger-600" title="Retirer ce seuil" onClick={() => setThresholds((l) => l.filter((x) => x.days !== t.days))}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-3 flex items-center gap-2">
              <input className="input w-32" type="number" min={1} max={365} placeholder="Jours" value={newDays} onChange={(e) => setNewDays(e.target.value)} aria-label="Nouveau seuil en jours" />
              <Button type="button" variant="secondary" small onClick={addThreshold} icon={<Plus className="h-3.5 w-3.5" />}>
                Ajouter un seuil
              </Button>
            </div>
            <label className="mt-4 flex items-center gap-2 text-sm text-slate-800">
              <input type="checkbox" checked={notifyExpired} onChange={(e) => setNotifyExpired(e.target.checked)} /> Alerter aussi les éléments déjà expirés
            </label>
          </fieldset>

          <fieldset>
            <legend className="label">Destinataires</legend>
            <div className="space-y-3">
              <label className="flex items-start gap-2 text-sm text-slate-800">
                <input className="mt-1" type="checkbox" checked={notifyAdmin} onChange={(e) => setNotifyAdmin(e.target.checked)} />
                <span>
                  Administrateur
                  <span className="hint block">Email administrateur défini dans les paramètres généraux : reçoit toutes les alertes.</span>
                </span>
              </label>
              <label className="flex items-start gap-2 text-sm text-slate-800">
                <input className="mt-1" type="checkbox" checked={notifyOwner} onChange={(e) => setNotifyOwner(e.target.checked)} />
                <span>
                  Responsable interne
                  <InfoTip text="Le responsable d'un actif ou d'un contrat reçoit uniquement ses propres alertes, si son nom (ou son email) correspond à un utilisateur actif de l'application." />
                  <span className="hint block">Chaque responsable reçoit les alertes de ses actifs et contrats.</span>
                </span>
              </label>
              <Field label="Adresse(s) personnalisée(s)" hint="Une adresse par ligne (ou séparées par des virgules). Reçoivent toutes les alertes.">
                <textarea className="input" rows={4} value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="achats@exemple.bj" />
              </Field>
            </div>
          </fieldset>
        </div>
        <div className="space-y-3 border-t border-slate-200 px-5 py-4">
          <FormError message={error} />
          <div className="flex justify-end">
            <Button type="submit" loading={busy}>Enregistrer les alertes</Button>
          </div>
        </div>
      </Card>
    </form>
  );
}

export default function Settings() {
  const general = useFetch<General>("/admin/settings/general");
  const alerts = useFetch<AlertCfg>("/admin/settings/alerts");
  const [key, setKey] = useState(0);
  useEffect(() => {
    document.title = "Paramètres";
  }, []);
  return (
    <>
      <PageHeader title="Paramètres" subtitle="Configuration de l'application (réservée aux administrateurs)" />
      <div className="space-y-6">
        {general.data ? <GeneralForm key={`g${key}`} initial={general.data} onSaved={() => setKey((k) => k + 1)} /> : <Spinner />}
        {alerts.data ? <AlertsForm key={`a${key}`} initial={alerts.data} onSaved={() => setKey((k) => k + 1)} /> : <Spinner />}
      </div>
    </>
  );
}

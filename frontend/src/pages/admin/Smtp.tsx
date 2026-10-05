import { Mail, Plug, Send } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api } from "../../api";
import { Alert, Button, Card, CardHeader, Field, FormError, PageHeader, PasswordInput, Spinner, useToast } from "../../components/ui";
import { useFetch } from "../../hooks";

interface SmtpState {
  host: string;
  port: number;
  security: "NONE" | "STARTTLS" | "SSL";
  username: string;
  from_email: string | null;
  from_name: string;
  password_set: boolean;
  configured: boolean;
  source: "database" | "environment" | "none";
  warning: string | null;
}

const SECURITY = [
  { value: "NONE", label: "Aucune (NONE)", port: 25 },
  { value: "STARTTLS", label: "STARTTLS", port: 587 },
  { value: "SSL", label: "SSL/TLS", port: 465 },
] as const;

function SmtpForm({ initial, onSaved }: { initial: SmtpState; onSaved: () => void }) {
  const toast = useToast();
  const [v, setV] = useState({ host: initial.host, port: String(initial.port), security: initial.security, username: initial.username, from_email: initial.from_email ?? "", from_name: initial.from_name });
  const [password, setPassword] = useState("");
  const [clearPassword, setClearPassword] = useState(false);
  const [testTo, setTestTo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState<"" | "save" | "conn" | "mail">("");
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));

  const body = () => ({
    host: v.host.trim(),
    port: Number(v.port),
    security: v.security,
    username: v.username.trim(),
    from_email: v.from_email.trim() || null,
    from_name: v.from_name.trim(),
    password: password || null,
    clear_password: clearPassword,
  });
  const changeSecurity = (sec: string) => {
    const prev = SECURITY.find((s) => s.value === v.security)!;
    const next = SECURITY.find((s) => s.value === sec)!;
    setV((s) => ({ ...s, security: next.value, port: Number(s.port) === prev.port ? String(next.port) : s.port }));
  };

  const run = async (kind: "save" | "conn" | "mail", e?: FormEvent) => {
    e?.preventDefault();
    setBusy(kind);
    setError(null);
    setResult(null);
    try {
      if (kind === "save") {
        await api.put("/admin/settings/smtp", body());
        toast("success", "Paramètres SMTP enregistrés");
        setPassword("");
        setClearPassword(false);
        onSaved();
      } else if (kind === "conn") {
        const r = await api.post<{ ok: boolean; message: string }>("/admin/settings/smtp/test-connection", body());
        setResult(r);
      } else {
        const r = await api.post<{ ok: boolean; message: string }>("/admin/settings/smtp/test-email", { ...body(), to: testTo.trim() || null });
        setResult(r);
        if (r.ok) toast("success", "Email de test envoyé");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  };

  return (
    <form onSubmit={(e) => run("save", e)} className="space-y-6">
      {!initial.configured && (
        <Alert kind="warning" title="SMTP non configuré">
          Aucun email d'alerte ne sera envoyé tant que le serveur et l'adresse expéditeur ne sont pas renseignés. Les alertes restent visibles dans les notifications.
        </Alert>
      )}
      {initial.configured && initial.source === "environment" && (
        <Alert kind="info">Ces valeurs proviennent du fichier .env. Les enregistrer ici les stocke en base ; elles prennent alors le dessus.</Alert>
      )}
      {initial.warning && <Alert kind="danger">{initial.warning}</Alert>}

      <Card>
        <CardHeader title="Serveur SMTP" subtitle="Le mot de passe est chiffré en base et n'est jamais affiché ni renvoyé par l'API." />
        <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
          <Field label="Serveur SMTP" required>
            <input className="input" required value={v.host} onChange={set("host")} placeholder="smtp.exemple.bj" />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Port" required>
              <input className="input" type="number" min={1} max={65535} required value={v.port} onChange={set("port")} />
            </Field>
            <Field label="Sécurité" required>
              <select className="input" value={v.security} onChange={(e) => changeSecurity(e.target.value)}>
                {SECURITY.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Utilisateur" hint="Laisser vide si le serveur n'exige pas d'authentification">
            <input className="input" autoComplete="off" value={v.username} onChange={set("username")} />
          </Field>
          <Field label="Mot de passe" hint={initial.password_set ? "Enregistré (chiffré). Saisir une valeur pour le remplacer." : undefined}>
            <PasswordInput autoComplete="new-password" value={password} placeholder={initial.password_set && !clearPassword ? "••••••••" : ""} disabled={clearPassword} onChange={(e) => setPassword(e.target.value)} />
            {initial.password_set && (
              <span className="mt-2 flex items-center gap-2 text-xs text-slate-600">
                <input type="checkbox" checked={clearPassword} onChange={(e) => { setClearPassword(e.target.checked); if (e.target.checked) setPassword(""); }} /> Supprimer le mot de passe enregistré
              </span>
            )}
          </Field>
          <Field label="Email expéditeur" required>
            <input className="input" type="email" required value={v.from_email} onChange={set("from_email")} placeholder="alertes@exemple.bj" />
          </Field>
          <Field label="Nom expéditeur">
            <input className="input" value={v.from_name} onChange={set("from_name")} placeholder="SBEE — Patrimoine SI" />
          </Field>
        </div>
        <div className="space-y-3 border-t border-slate-200 px-5 py-4">
          <FormError message={error} />
          {result && <Alert kind={result.ok ? "success" : "danger"}>{result.message}</Alert>}
          <div className="flex justify-end">
            <Button type="submit" loading={busy === "save"}>Enregistrer</Button>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Tests" subtitle="Utilisent les valeurs saisies ci-dessus (le mot de passe enregistré est repris si le champ est vide), sans les enregistrer." />
        <div className="flex flex-wrap items-end gap-3 p-5">
          <Button type="button" variant="secondary" loading={busy === "conn"} onClick={() => run("conn")} icon={<Plug className="h-4 w-4" />}>
            Tester la connexion
          </Button>
          <div className="mx-2 hidden h-8 w-px bg-slate-200 sm:block" />
          <Field label="Destinataire du test" className="w-72">
            <input className="input" type="email" value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="Vous-même si vide" />
          </Field>
          <Button type="button" variant="secondary" loading={busy === "mail"} onClick={() => run("mail")} icon={<Send className="h-4 w-4" />}>
            Envoyer un email de test
          </Button>
        </div>
      </Card>
    </form>
  );
}

export default function Smtp() {
  const { data, loading, reload } = useFetch<SmtpState>("/admin/settings/smtp");
  return (
    <>
      <PageHeader title="Configuration SMTP" subtitle={<span className="inline-flex items-center gap-1.5"><Mail className="h-4 w-4" /> Envoi des alertes d'échéance par email</span>} />
      {loading && !data ? <Spinner /> : data ? <SmtpForm key={JSON.stringify([data.host, data.port, data.password_set])} initial={data} onSaved={reload} /> : null}
    </>
  );
}

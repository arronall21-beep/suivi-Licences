import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, BrandLogo, Button, Field, FormError, hasOfficialLogo, Modal, PasswordInput, Watermark } from "../components/ui";
import { brand } from "../theme";

interface PublicConfig {
  org_name: string;
  app_name: string;
  version: string;
}

function ForgotPassword({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const close = () => {
    setEmail("");
    setSent(null);
    setError(null);
    onClose();
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<{ detail: string }>("/auth/forgot-password", { email });
      setSent(r.detail);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={open} title="Mot de passe oublié" onClose={close}>
      {sent ? (
        <div className="space-y-4">
          <Alert kind="success">{sent}</Alert>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={close}>
              Fermer
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <p className="text-sm text-slate-600">Indiquez votre adresse email : l'administrateur sera informé de votre demande et vous contactera pour réinitialiser votre mot de passe.</p>
          <Field label="Adresse email" required>
            <input className="input" type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <FormError message={error} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={close}>
              Annuler
            </Button>
            <Button type="submit" loading={busy}>
              Envoyer la demande
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

export default function Login() {
  const { user, login } = useAuth();
  const [cfg, setCfg] = useState<PublicConfig | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);

  useEffect(() => {
    api.get<PublicConfig>("/public/config").then(setCfg).catch(() => {});
  }, []);
  useEffect(() => {
    if (cfg) document.title = `${cfg.app_name} — ${cfg.org_name}`;
  }, [cfg]);

  if (user) return <Navigate to="/" replace />;
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-brand-500 via-brand-500 to-brand-700 p-4">
      {/* Trame décorative (symbole du logo, 7 % d'opacité) : rendue uniquement si le symbole officiel est fourni */}
      <Watermark tone="light" className="-bottom-28 -right-28 h-[36rem] w-[36rem]" />
      <div className="relative w-full max-w-sm">
        <form onSubmit={submit} className="overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div className="h-1.5 bg-accent-500" aria-hidden="true" />
          <div className="p-8">
          <div className="mb-7 flex flex-col items-center text-center">
            {hasOfficialLogo ? <BrandLogo height={72} className="mb-5" /> : <p className="mb-2 text-sm font-medium text-slate-600">{brand.organizationFullName}</p>}
            <h1 className="text-xl font-semibold text-slate-900">{cfg?.app_name ?? brand.defaultApplication}</h1>
          </div>
          <Field label="Email" required className="mb-3">
            <input className="input" type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Mot de passe" required className="mb-4">
            <PasswordInput autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <FormError message={error} />
          <Button className="mt-4 w-full" type="submit" loading={busy}>
            Se connecter
          </Button>
          <button type="button" className="mt-4 block w-full text-center text-sm font-medium text-brand-700 hover:underline" onClick={() => setForgot(true)}>
            Mot de passe oublié ?
          </button>
          </div>
        </form>
        <p className="mt-4 text-center text-xs text-white/90">
          {cfg?.org_name ?? brand.defaultOrganization}
          {cfg?.version && ` · v${cfg.version}`}
        </p>
      </div>
      <ForgotPassword open={forgot} onClose={() => setForgot(false)} />
    </div>
  );
}

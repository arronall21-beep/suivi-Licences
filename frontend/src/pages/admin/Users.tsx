import { KeyRound, Pencil, Plus, Search, UserCheck, UserX } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import {
  ActiveBadge,
  Alert,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  Field,
  FormError,
  Modal,
  PageHeader,
  Pagination,
  PASSWORD_POLICY,
  PasswordInput,
  passwordProblem,
  RoleBadge,
  Spinner,
  useToast,
} from "../../components/ui";
import { fmtDate, fmtDateTime } from "../../format";
import { useFetch } from "../../hooks";
import type { AppUser, Page, Role } from "../../types";

const SIZE = 15;
const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "ADMIN", label: "Administrateur" },
  { value: "MANAGER", label: "Gestionnaire" },
  { value: "VIEWER", label: "Lecture seule" },
];

interface RolesData {
  roles: { role: Role; label: string; description: string; permissions: string[]; active_users: number }[];
  permission_labels: Record<string, string>;
}

function UserForm({ user, onSaved, onCancel }: { user: AppUser | null; onSaved: () => void; onCancel: () => void }) {
  const toast = useToast();
  const [v, setV] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    email: user?.email ?? "",
    phone: user?.phone ?? "",
    department: user?.department ?? "",
    role: (user?.role ?? "VIEWER") as Role,
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!user) {
      const problem = passwordProblem(v.password);
      if (problem) return setError(problem);
    }
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { ...v, phone: v.phone || null, department: v.department || null };
      if (user) {
        delete body.password;
        await api.put(`/users/${user.id}`, body);
      } else await api.post("/users", body);
      toast("success", user ? "Utilisateur modifié avec succès" : "Utilisateur créé avec succès");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Prénom" required>
          <input className="input" required value={v.first_name} onChange={set("first_name")} />
        </Field>
        <Field label="Nom" required>
          <input className="input" required value={v.last_name} onChange={set("last_name")} />
        </Field>
        <Field label="Email" required className="sm:col-span-2">
          <input className="input" type="email" required value={v.email} onChange={set("email")} />
        </Field>
        <Field label="Téléphone">
          <input className="input" type="tel" value={v.phone} onChange={set("phone")} />
        </Field>
        <Field label="Direction / Département">
          <input className="input" value={v.department} onChange={set("department")} />
        </Field>
        <Field label="Rôle" required>
          <select className="input" value={v.role} onChange={set("role")}>
            {ROLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </Field>
        {!user && (
          <Field label="Mot de passe initial" required hint={PASSWORD_POLICY}>
            <PasswordInput required autoComplete="new-password" value={v.password} onChange={set("password")} />
          </Field>
        )}
      </div>
      {user && v.email.toLowerCase() !== user.email && <Alert kind="warning">Changer l'email déconnecte immédiatement les sessions en cours de cet utilisateur.</Alert>}
      <FormError message={error} />
      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" loading={busy}>
          Enregistrer
        </Button>
      </div>
    </form>
  );
}

function ResetPassword({ user, onDone, onCancel }: { user: AppUser; onDone: () => void; onCancel: () => void }) {
  const toast = useToast();
  const [pw, setPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(pw);
    if (problem) return setError(problem);
    setBusy(true);
    try {
      await api.post(`/users/${user.id}/reset-password`, { password: pw });
      toast("success", "Mot de passe réinitialisé : les sessions de l'utilisateur ont été fermées");
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-4">
      <p className="text-sm text-slate-600">
        Définir un nouveau mot de passe pour <b>{user.full_name || user.email}</b>. Communiquez-le par un canal sûr ; l'utilisateur pourra le changer depuis son menu.
      </p>
      <Field label="Nouveau mot de passe" required hint={PASSWORD_POLICY}>
        <PasswordInput required autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} />
      </Field>
      <FormError message={error} />
      <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" loading={busy}>
          Réinitialiser
        </Button>
      </div>
    </form>
  );
}

function Roles() {
  const { data, loading } = useFetch<RolesData>("/roles");
  if (loading && !data) return <Spinner />;
  if (!data) return null;
  const all = Object.keys(data.permission_labels);
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {data.roles.map((r) => (
          <Card key={r.role} className="p-5">
            <div className="flex items-center justify-between">
              <RoleBadge role={r.role} />
              <span className="text-xs text-slate-500">{r.active_users} utilisateur(s) actif(s)</span>
            </div>
            <p className="mt-3 text-sm text-slate-600">{r.description}</p>
          </Card>
        ))}
      </div>
      <Card>
        <div className="card-header">
          <h2 className="card-title">Matrice des permissions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="table-head">
              <tr>
                <th className="th">Permission</th>
                {data.roles.map((r) => (
                  <th key={r.role} className="th text-center">
                    {r.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {all.map((p) => (
                <tr key={p}>
                  <td className="td whitespace-normal">{data.permission_labels[p]}</td>
                  {data.roles.map((r) => (
                    <td key={r.role} className="td text-center">
                      {r.permissions.includes(p) ? <span className="font-semibold text-success-700" aria-label="Autorisé">✓</span> : <span className="text-slate-300" aria-label="Refusé">—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="border-t border-slate-200 px-5 py-3 text-xs text-slate-500">Ces droits sont appliqués par le serveur sur chaque requête ; masquer un bouton dans l'interface n'est jamais une mesure de sécurité.</p>
      </Card>
    </div>
  );
}

export default function Users() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [sp, setSp] = useSearchParams();
  const [tab, setTab] = useState<"users" | "roles">("users");
  const [q, setQ] = useState(sp.get("q") ?? "");
  const [debounced, setDebounced] = useState(q);
  const [role, setRole] = useState("");
  const [state, setState] = useState("");
  const [page, setPage] = useState(1);
  const { data, loading, reload } = useFetch<Page<AppUser>>("/users", { q: debounced, role, state, page, size: SIZE });
  const [editing, setEditing] = useState<AppUser | null | undefined>(undefined);
  const [resetting, setResetting] = useState<AppUser | null>(null);
  const [toggling, setToggling] = useState<AppUser | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(q);
      setPage(1);
      if (sp.has("q")) setSp({}, { replace: true });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const toggle = async (u: AppUser) => {
    try {
      await api.post(`/users/${u.id}/${u.is_active ? "deactivate" : "reactivate"}`);
      toast("success", u.is_active ? "Utilisateur désactivé : ses sessions sont fermées" : "Utilisateur réactivé");
      setToggling(null);
      reload();
    } catch (err) {
      toast("error", (err as Error).message);
      setToggling(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Utilisateurs et rôles"
        subtitle={tab === "users" && data ? `${data.total} utilisateur(s)` : "Droits d'accès par rôle"}
        actions={tab === "users" && <Button onClick={() => setEditing(null)} icon={<Plus className="h-4 w-4" />}>Nouvel utilisateur</Button>}
      />
      <div className="mb-5 flex gap-1 border-b border-slate-200" role="tablist">
        {[
          { id: "users", label: "Utilisateurs" },
          { id: "roles", label: "Rôles et permissions" },
        ].map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id as "users" | "roles")} className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium ${tab === t.id ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "roles" ? (
        <Roles />
      ) : (
        <>
          <Card className="mb-4 p-4">
            <div className="flex flex-wrap gap-3">
              <div className="relative min-w-[260px] flex-1">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input className="input pl-9" placeholder="Rechercher par nom, email, direction…" value={q} onChange={(e) => setQ(e.target.value)} />
              </div>
              <select className="input w-44" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }} aria-label="Rôle">
                <option value="">Tous les rôles</option>
                {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <select className="input w-40" value={state} onChange={(e) => { setState(e.target.value); setPage(1); }} aria-label="Statut">
                <option value="">Tous les statuts</option>
                <option value="active">Actifs</option>
                <option value="inactive">Désactivés</option>
              </select>
            </div>
          </Card>
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="table-head">
                  <tr>
                    <th className="th">Nom</th>
                    <th className="th">Email / téléphone</th>
                    <th className="th">Direction</th>
                    <th className="th">Rôle</th>
                    <th className="th">Statut</th>
                    <th className="th">Créé le</th>
                    <th className="th">Dernière connexion</th>
                    <th className="th sticky right-0 bg-slate-50 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data?.items.map((u) => (
                    <tr key={u.id} className={u.is_active ? "hover:bg-slate-50" : "bg-slate-50/70 text-slate-500"}>
                      <td className="td font-medium text-slate-900">
                        {u.full_name || "—"}
                        {u.id === me?.id && <span className="ml-2 text-xs font-normal text-slate-500">(vous)</span>}
                      </td>
                      <td className="td">
                        {u.email}
                        {u.phone && <div className="text-xs text-slate-500">{u.phone}</div>}
                      </td>
                      <td className="td">{u.department ?? "—"}</td>
                      <td className="td"><RoleBadge role={u.role} /></td>
                      <td className="td"><ActiveBadge active={u.is_active} /></td>
                      <td className="td">{fmtDate(u.created_at)}</td>
                      <td className="td">{u.last_login_at ? fmtDateTime(u.last_login_at) : <span className="text-slate-400">Jamais</span>}</td>
                      <td className={`td sticky right-0 text-right shadow-[-8px_0_8px_-8px_rgba(0,0,0,0.08)] ${u.is_active ? "bg-white" : "bg-slate-50"}`}>
                        <button className="btn-ghost" title="Modifier" onClick={() => setEditing(u)}><Pencil className="h-4 w-4" /></button>
                        <button className="btn-ghost" title="Réinitialiser le mot de passe" onClick={() => setResetting(u)}><KeyRound className="h-4 w-4" /></button>
                        {u.is_active ? (
                          <button className="btn-ghost text-danger-600 hover:bg-danger-50" title="Désactiver" disabled={u.id === me?.id} onClick={() => setToggling(u)}><UserX className="h-4 w-4" /></button>
                        ) : (
                          <button className="btn-ghost text-success-700 hover:bg-success-50" title="Réactiver" onClick={() => setToggling(u)}><UserCheck className="h-4 w-4" /></button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {loading && !data && <Spinner />}
            {data && data.items.length === 0 && <EmptyState title="Aucun utilisateur ne correspond aux critères" />}
            {data && <Pagination page={page} size={SIZE} total={data.total} onPage={setPage} />}
          </Card>
        </>
      )}

      <Modal open={editing !== undefined} title={editing ? `Modifier ${editing.full_name || editing.email}` : "Nouvel utilisateur"} onClose={() => setEditing(undefined)}>
        {editing !== undefined && <UserForm user={editing} onCancel={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); reload(); }} />}
      </Modal>
      <Modal open={!!resetting} title="Réinitialiser le mot de passe" onClose={() => setResetting(null)}>
        {resetting && <ResetPassword user={resetting} onCancel={() => setResetting(null)} onDone={() => { setResetting(null); reload(); }} />}
      </Modal>
      <ConfirmDialog
        open={!!toggling}
        danger={!!toggling?.is_active}
        irreversible={false}
        title={toggling?.is_active ? "Désactiver l'utilisateur" : "Réactiver l'utilisateur"}
        confirmLabel={toggling?.is_active ? "Désactiver" : "Réactiver"}
        message={
          toggling?.is_active ? (
            <>
              <b>{toggling.full_name || toggling.email}</b> ne pourra plus se connecter et sera déconnecté immédiatement. Ses données et son historique sont conservés.
            </>
          ) : (
            <>
              <b>{toggling?.full_name || toggling?.email}</b> pourra à nouveau se connecter.
            </>
          )
        }
        onCancel={() => setToggling(null)}
        onConfirm={async () => { if (toggling) await toggle(toggling); }}
      />
    </>
  );
}

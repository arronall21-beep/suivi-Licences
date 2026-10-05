import { useState, type FormEvent } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Button, Field, FormError, Modal, PASSWORD_POLICY, PasswordInput, passwordProblem, useToast } from "./ui";

export default function ChangePasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { adoptToken } = useAuth();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const close = () => {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
    onClose();
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(next) ?? (next !== confirm ? "La confirmation ne correspond pas" : null);
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<{ access_token: string }>("/auth/change-password", { current_password: current, new_password: next });
      await adoptToken(res.access_token);
      toast("success", "Mot de passe modifié avec succès");
      close();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} title="Changer mon mot de passe" onClose={close}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Mot de passe actuel" required>
          <PasswordInput required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label="Nouveau mot de passe" required hint={PASSWORD_POLICY}>
          <PasswordInput required autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        <Field label="Confirmer le nouveau mot de passe" required>
          <PasswordInput required autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
          <Button type="button" variant="secondary" onClick={close}>
            Annuler
          </Button>
          <Button type="submit" loading={busy}>
            Modifier le mot de passe
          </Button>
        </div>
      </form>
    </Modal>
  );
}

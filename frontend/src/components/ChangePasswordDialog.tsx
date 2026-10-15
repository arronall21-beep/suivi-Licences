import { X } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent, type RefObject } from "react";
import { createPortal } from "react-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Button, Field, FormError, PASSWORD_POLICY, PasswordInput, passwordProblem, useToast } from "./ui";

/**
 * Boîte de dialogue dédiée au changement de mot de passe.
 *
 * Volontairement indépendante du composant générique `Modal` :
 *  - rendue dans un portail sur <body>, hors de l'en-tête (`sticky` + `backdrop-blur`), dont le filtre
 *    deviendrait sinon le repère des éléments `position: fixed` et rognerait la fenêtre ;
 *  - calque `fixed inset-0` centré, boîte bornée par la hauteur réelle du viewport (dvh) ;
 *  - en-tête et pied (boutons) toujours visibles, seul le formulaire défile.
 */
const FOCUSABLE = "input, button:not([disabled]):not([tabindex='-1'])";
const canFocus = (el: HTMLElement | null | undefined): el is HTMLElement => !!el && el.isConnected && !el.hasAttribute("disabled");

/**
 * `returnFocusRef` : élément à re-focaliser à la fermeture (bouton du menu utilisateur). Il est nécessaire car
 * le menu se referme au clic, donc l'élément actif à l'ouverture n'existe plus quand la boîte se ferme.
 */
export default function ChangePasswordDialog({ open, onClose, returnFocusRef }: { open: boolean; onClose: () => void; returnFocusRef?: RefObject<HTMLElement> }) {
  const { adoptToken } = useAuth();
  const toast = useToast();
  const titleId = useId();
  const boxRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLDivElement>(null);
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

  // Focus : à l'ouverture sur le premier champ ; à la fermeture, retour au déclencheur (sinon à l'élément actif
  // d'origine s'il existe encore). Dépend de `open` seul : aucune recapture pendant l'envoi.
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    firstFieldRef.current?.querySelector("input")?.focus();
    return () => {
      [returnFocusRef?.current, previous].find(canFocus)?.focus();
    };
  }, [open, returnFocusRef]);

  // Clavier : Échap ferme (sauf pendant l'envoi) ; Tab / Maj+Tab restent dans la boîte, même si le focus
  // est tombé sur <body> (ex. bouton désactivé pendant l'envoi).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) return close();
      if (e.key !== "Tab" || !boxRef.current) return;
      const items = Array.from(boxRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!items.length) return e.preventDefault();
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (!boxRef.current.contains(active)) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, busy]);

  // Verrouille le défilement de la page derrière la boîte.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
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

  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[70] flex items-center justify-center overflow-hidden bg-slate-950/50 p-3 sm:p-4">
      <div
        ref={boxRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="flex max-h-[calc(100vh-1.5rem)] max-h-[calc(100dvh-1.5rem)] w-full max-w-md flex-col overflow-hidden rounded-xl bg-white shadow-xl ring-1 ring-slate-200"
      >
        <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
          <h2 id={titleId} className="text-base font-semibold text-slate-900">
            Changer mon mot de passe
          </h2>
          <button type="button" className="btn-ghost" onClick={close} disabled={busy} aria-label="Fermer la fenêtre">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-5 py-4">
            <div ref={firstFieldRef}>
              <Field label="Mot de passe actuel" required>
                <PasswordInput required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
              </Field>
            </div>
            <Field label="Nouveau mot de passe" required hint={PASSWORD_POLICY}>
              <PasswordInput required autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
            </Field>
            <Field label="Confirmer le nouveau mot de passe" required>
              <PasswordInput required autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </Field>
            <FormError message={error} />
          </div>
          <div className="flex shrink-0 flex-col-reverse gap-2 border-t border-slate-200 px-5 py-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="secondary" onClick={close} disabled={busy}>
              Annuler
            </Button>
            <Button type="submit" loading={busy}>
              Modifier le mot de passe
            </Button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}

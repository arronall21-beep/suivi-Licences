import { AlertTriangle, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "./Button";

export function Modal({ open, title, onClose, children, wide }: { open: boolean; title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-brand-950/50 p-4 pt-12" role="dialog" aria-modal="true" aria-label={title}>
      <div className={`card w-full ${wide ? "max-w-4xl" : "max-w-xl"} shadow-xl`}>
        <div className="card-header">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <button className="btn-ghost" onClick={onClose} aria-label="Fermer">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

/** Boîte de confirmation avant une action sensible ou irréversible. */
export function ConfirmDialog({
  open,
  title = "Confirmer l'action",
  message,
  confirmLabel = "Confirmer",
  danger = true,
  irreversible = true,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title?: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  irreversible?: boolean;
  onConfirm: () => void | Promise<void>;
  onCancel: () => void;
}) {
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    if (open) window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onCancel]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-brand-950/50 p-4" role="alertdialog" aria-modal="true" aria-label={title}>
      <div className="card w-full max-w-md p-6 shadow-xl">
        <div className="flex gap-3">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${danger ? "bg-danger-100 text-danger-600" : "bg-warning-100 text-warning-600"}`}>
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">{title}</h2>
            <div className="mt-1 text-sm text-slate-600">{message}</div>
            {irreversible && <p className="mt-2 text-sm font-medium text-danger-700">⚠️ Cette action est irréversible.</p>}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Annuler
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            loading={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await onConfirm();
              } finally {
                setBusy(false);
              }
            }}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Bouton (icône) qui demande confirmation avant d'exécuter l'action. */
export function ConfirmButton({
  onConfirm,
  children,
  message = "Confirmer la suppression ?",
  title = "Confirmer la suppression",
  confirmLabel = "Supprimer",
  className = "btn-ghost text-danger-600 hover:bg-danger-50 hover:text-danger-700",
  irreversible = true,
  danger = true,
  tooltip,
}: {
  onConfirm: () => void | Promise<void>;
  children: ReactNode;
  message?: ReactNode;
  title?: string;
  confirmLabel?: string;
  className?: string;
  irreversible?: boolean;
  danger?: boolean;
  tooltip?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className={className}
        title={tooltip ?? confirmLabel}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
      >
        {children}
      </button>
      <ConfirmDialog
        open={open}
        title={title}
        message={message}
        confirmLabel={confirmLabel}
        irreversible={irreversible}
        danger={danger}
        onCancel={() => setOpen(false)}
        onConfirm={async () => {
          await onConfirm();
          setOpen(false);
        }}
      />
    </>
  );
}

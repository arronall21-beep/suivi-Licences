import { Eye, EyeOff } from "lucide-react";
import { useState, type InputHTMLAttributes, type ReactNode } from "react";

export function Field({ label, children, className = "", hint, error, required }: { label: string; children: ReactNode; className?: string; hint?: ReactNode; error?: string | null; required?: boolean }) {
  return (
    <label className={`block ${className}`}>
      <span className="label">
        {label}
        {required && <span className="text-danger-600"> *</span>}
      </span>
      {children}
      {error ? <span className="field-error block">{error}</span> : hint ? <span className="hint block">{hint}</span> : null}
    </label>
  );
}

/** Champ mot de passe avec bascule d'affichage. N'affiche jamais de valeur stockée. */
export function PasswordInput({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={visible ? "text" : "password"} className={`input pr-10 ${className}`} />
      <button type="button" className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-slate-400 hover:text-slate-700" onClick={() => setVisible((v) => !v)} aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"} tabIndex={-1}>
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="rounded-md border border-danger-200 bg-danger-50 px-3 py-2 text-sm text-danger-700" role="alert">
      {message}
    </div>
  );
}

export const PASSWORD_POLICY = "8 caractères minimum, avec au moins une lettre et un chiffre";

/** Contrôle côté client (le backend applique la même politique). Renvoie un message ou null. */
export function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return `Trop court : ${PASSWORD_POLICY}`;
  if (!/[A-Za-zÀ-ɏ]/.test(pw) || !/\d/.test(pw)) return `Trop faible : ${PASSWORD_POLICY}`;
  return null;
}

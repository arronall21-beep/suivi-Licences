import { AlertCircle, AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { Watermark } from "./Logo";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin" /> {label}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="relative flex flex-col items-center justify-center gap-2 overflow-hidden py-14 text-center">
      <Watermark className="left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2" />
      <div className="relative text-sm font-medium text-slate-700">{title}</div>
      {children && <div className="relative text-sm text-slate-500">{children}</div>}
    </div>
  );
}

type AlertKind = "info" | "success" | "warning" | "danger";
const ALERT: Record<AlertKind, { cls: string; Icon: typeof Info }> = {
  info: { cls: "border-info-200 bg-info-50 text-info-800", Icon: Info },
  success: { cls: "border-success-200 bg-success-50 text-success-800", Icon: CheckCircle2 },
  warning: { cls: "border-warning-200 bg-warning-50 text-warning-800", Icon: AlertTriangle },
  danger: { cls: "border-danger-200 bg-danger-50 text-danger-800", Icon: AlertCircle },
};

export function Alert({ kind = "info", title, children, className = "" }: { kind?: AlertKind; title?: string; children?: ReactNode; className?: string }) {
  const { cls, Icon } = ALERT[kind];
  return (
    <div className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${cls} ${className}`} role={kind === "danger" ? "alert" : undefined}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        {title && <div className="font-semibold">{title}</div>}
        {children && <div>{children}</div>}
      </div>
    </div>
  );
}

// ---------- Toasts ----------
type Toast = { id: number; kind: "success" | "error"; text: string };
const ToastCtx = createContext<(kind: Toast["kind"], text: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "error" ? 7000 : 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-96 max-w-[calc(100vw-2rem)] flex-col gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg ${
              t.kind === "success" ? "border-success-200 bg-success-50 text-success-800" : "border-danger-200 bg-danger-50 text-danger-800"
            }`}
          >
            {t.kind === "success" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

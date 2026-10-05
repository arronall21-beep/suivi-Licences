import type { ReactNode } from "react";
import { CRITICALITY_CLS, IMPORT_STATUS_META, PRIORITY_CLS, ROLE_META, STATUS_META } from "../../theme";
import type { Status } from "../../types";

export function Badge({ className = "", children }: { className?: string; children: ReactNode }) {
  return <span className={`badge ${className}`}>{children}</span>;
}

export function StatusBadge({ status }: { status: Status }) {
  const m = STATUS_META[status] ?? STATUS_META.INCONNU;
  return (
    <Badge className={m.cls}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
      {m.label}
    </Badge>
  );
}

export function CriticalityBadge({ value }: { value: string | null }) {
  if (!value) return <span className="text-slate-400">—</span>;
  return <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${CRITICALITY_CLS[value] ?? "bg-slate-50 text-slate-600 ring-slate-300"}`}>{value}</span>;
}

export function PriorityBadge({ value }: { value: string }) {
  return <span className={`inline-flex rounded px-1.5 py-0.5 text-xs font-bold ${PRIORITY_CLS[value] ?? PRIORITY_CLS.P3}`}>{value}</span>;
}

export function RoleBadge({ role }: { role: string }) {
  const m = ROLE_META[role] ?? { label: role, cls: "bg-slate-100 text-slate-700 ring-slate-500/20" };
  return <Badge className={m.cls}>{m.label}</Badge>;
}

export function ImportStatusBadge({ status }: { status: string }) {
  const m = IMPORT_STATUS_META[status] ?? { label: status, cls: "bg-slate-100 text-slate-700 ring-slate-500/20" };
  return <Badge className={m.cls}>{m.label}</Badge>;
}

export function ActiveBadge({ active }: { active: boolean }) {
  return active ? (
    <Badge className="bg-success-100 text-success-800 ring-success-600/20">Actif</Badge>
  ) : (
    <Badge className="bg-slate-100 text-slate-600 ring-slate-500/20">Désactivé</Badge>
  );
}

import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

export function Pagination({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-600">
      <span>{total === 0 ? "Aucun résultat" : `${(page - 1) * size + 1}–${Math.min(page * size, total)} sur ${total}`}</span>
      <div className="flex items-center gap-1">
        <button className="btn-secondary px-2 py-1" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Page précédente">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="px-2">
          Page {page} / {pages}
        </span>
        <button className="btn-secondary px-2 py-1" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Page suivante">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export function SortHeader({ label, sortKey, current, order, onSort }: { label: string; sortKey: string; current: string; order: string; onSort: (key: string) => void }) {
  return (
    <th className="th cursor-pointer select-none hover:text-slate-800" onClick={() => onSort(sortKey)} aria-sort={current === sortKey ? (order === "asc" ? "ascending" : "descending") : "none"}>
      <span className="inline-flex items-center gap-1">
        {label}
        {current === sortKey ? order === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" /> : <ArrowUpDown className="h-3 w-3 opacity-30" />}
      </span>
    </th>
  );
}

export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="overflow-x-auto">{children}</div>;
}

export function DaysCell({ days }: { days: number | null }) {
  if (days === null || days === undefined) return <span className="text-slate-400">—</span>;
  const cls = days <= 0 ? "text-danger-700" : days <= 30 ? "text-caution-700" : days <= 90 ? "text-warning-700" : "text-slate-700";
  return <span className={`font-semibold tabular-nums ${cls}`}>{days <= 0 ? `${days} j` : `J-${days}`}</span>;
}

export function UsageBar({ rate }: { rate: number | null }) {
  if (rate === null || rate === undefined) return <span className="text-slate-400">—</span>;
  const color = rate >= 95 ? "bg-danger-500" : rate >= 80 ? "bg-warning-500" : "bg-success-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(rate, 100)}%` }} />
      </div>
      <span className="text-xs tabular-nums text-slate-600">{rate.toLocaleString("fr-FR")} %</span>
    </div>
  );
}

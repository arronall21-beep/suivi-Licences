import { Bell, CheckCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { fmtDateTime } from "../format";
import { NOTIFICATION_PRIORITY } from "../theme";
import type { InboxItem, Page } from "../types";

type Inbox = Page<InboxItem> & { unread: number };

export const INBOX_EVENT = "inbox:changed";
export const notifyInboxChanged = () => window.dispatchEvent(new Event(INBOX_EVENT));

/** Compteur de notifications non lues (sondage léger). */
export function useUnreadCount() {
  const [unread, setUnread] = useState(0);
  const refresh = useCallback(() => {
    api.get<{ unread: number }>("/inbox/unread-count").then((r) => setUnread(r.unread)).catch(() => {});
  }, []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 60_000);
    window.addEventListener(INBOX_EVENT, refresh);
    return () => {
      clearInterval(t);
      window.removeEventListener(INBOX_EVENT, refresh);
    };
  }, [refresh]);
  return unread;
}

export default function NotificationBell() {
  const unread = useUnreadCount();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    api.get<Inbox>("/inbox", { size: 8 }).then((r) => setItems(r.items)).catch(() => setItems([]));
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const openItem = async (n: InboxItem) => {
    setOpen(false);
    if (!n.read) {
      await api.post(`/inbox/${n.id}/read`).catch(() => {});
      notifyInboxChanged();
    }
    if (n.link) navigate(n.link);
  };
  const readAll = async () => {
    await api.post("/inbox/read-all");
    setItems((l) => l?.map((n) => ({ ...n, read: true })) ?? null);
    notifyInboxChanged();
  };

  return (
    <div className="relative" ref={ref}>
      <button className="btn-ghost relative h-10 w-10 !px-0" onClick={() => setOpen((o) => !o)} aria-label={`Notifications${unread ? ` (${unread} non lues)` : ""}`} aria-expanded={open}>
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger-600 px-1 text-[10px] font-bold text-white">{unread > 99 ? "99+" : unread}</span>
        )}
      </button>
      {open && (
        <div className="card absolute right-0 z-40 mt-2 w-[26rem] max-w-[calc(100vw-2rem)] shadow-xl">
          <div className="card-header !py-2.5">
            <span className="card-title">Notifications</span>
            {unread > 0 && (
              <button className="btn-ghost btn-sm text-brand-700" onClick={readAll}>
                <CheckCheck className="h-3.5 w-3.5" /> Tout marquer comme lu
              </button>
            )}
          </div>
          <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
            {items === null && <li className="px-4 py-6 text-center text-sm text-slate-500">Chargement…</li>}
            {items?.length === 0 && <li className="px-4 py-6 text-center text-sm text-slate-500">Aucune notification</li>}
            {items?.map((n) => (
              <li key={n.id}>
                <button className={`flex w-full gap-3 px-4 py-3 text-left hover:bg-slate-50 ${n.read ? "" : "bg-brand-50/60"}`} onClick={() => openItem(n)}>
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : NOTIFICATION_PRIORITY[n.priority].dot}`} />
                  <span className="min-w-0">
                    <span className={`block truncate text-sm ${n.read ? "text-slate-600" : "font-semibold text-slate-900"}`}>{n.title}</span>
                    <span className="block text-xs text-slate-500">{fmtDateTime(n.created_at)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <div className="border-t border-slate-200 p-2 text-center">
            <button
              className="btn-ghost btn-sm text-brand-700"
              onClick={() => {
                setOpen(false);
                navigate("/notifications");
              }}
            >
              Voir toutes les notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

import {
  AppWindow,
  ArrowLeftRight,
  Award,
  Bell,
  Building2,
  CalendarClock,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  History,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Mail,
  Server,
  Settings,
  Users,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { useConfig } from "../config";
import ChangePasswordModal from "./ChangePasswordModal";
import GlobalSearch from "./GlobalSearch";
import NotificationBell, { useUnreadCount } from "./NotificationBell";
import { BrandLogo, RoleBadge } from "./ui";

const link = ({ isActive }: { isActive: boolean }) => `nav-link ${isActive ? "nav-link-active" : ""}`;
const sub = ({ isActive }: { isActive: boolean }) => `nav-sub ${isActive ? "nav-link-active" : ""}`;

function Item({ to, icon: Icon, children, end, badge }: { to: string; icon: LucideIcon; children: string; end?: boolean; badge?: number }) {
  return (
    <NavLink to={to} end={end} className={link}>
      <Icon className="h-4 w-4" /> <span className="flex-1">{children}</span>
      {!!badge && <span className="rounded-full bg-danger-600 px-1.5 text-[10px] font-bold text-white">{badge > 99 ? "99+" : badge}</span>}
    </NavLink>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [pwd, setPwd] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const name = user?.full_name || user?.email || "";
  const initials = name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="relative" ref={ref}>
      <button className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-700 text-xs font-semibold text-white">{initials}</span>
        <span className="hidden text-left leading-tight md:block">
          <span className="block max-w-[10rem] truncate text-sm font-medium text-slate-900">{name}</span>
          <span className="block text-xs text-slate-500">{user && <RoleLabel role={user.role} />}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-slate-400" />
      </button>
      {open && (
        <div className="card absolute right-0 z-40 mt-2 w-64 py-1 shadow-xl">
          <div className="border-b border-slate-100 px-4 py-3">
            <div className="truncate text-sm font-medium text-slate-900">{name}</div>
            <div className="truncate text-xs text-slate-500">{user?.email}</div>
            <div className="mt-2">{user && <RoleBadge role={user.role} />}</div>
          </div>
          <button className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={() => { setOpen(false); setPwd(true); }}>
            <KeyRound className="h-4 w-4" /> Changer mon mot de passe
          </button>
          <button className="flex w-full items-center gap-2 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={logout}>
            <LogOut className="h-4 w-4" /> Se déconnecter
          </button>
        </div>
      )}
      <ChangePasswordModal open={pwd} onClose={() => setPwd(false)} />
    </div>
  );
}

const ROLE_LABEL: Record<string, string> = { ADMIN: "Administrateur", MANAGER: "Gestionnaire", VIEWER: "Lecture seule" };
const RoleLabel = ({ role }: { role: string }) => <>{ROLE_LABEL[role] ?? role}</>;

export default function Layout() {
  const { can } = useAuth();
  const { config } = useConfig();
  const unread = useUnreadCount();
  const showAdmin = can("admin:users") || can("admin:settings") || can("admin:smtp") || can("admin:audit") || can("admin:system");

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-brand-900">
        <div className="px-4 pb-4 pt-5">
          <div className="rounded-lg bg-white px-3 py-2 shadow-sm">
            <BrandLogo className="h-9" />
          </div>
          <div className="mt-3 px-1">
            <div className="text-sm font-semibold leading-tight text-white">{config.app_name}</div>
            <div className="text-xs text-brand-200/80">{config.org_name}</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Navigation principale">
          <Item to="/" end icon={LayoutDashboard}>
            Dashboard
          </Item>

          <div className="nav-section">Patrimoine SI</div>
          <Item to="/actifs" end icon={Server}>
            Actifs
          </Item>
          <div className="mt-1 space-y-0.5">
            <NavLink to="/actifs/licences" className={sub}>
              <KeyRound className="h-3.5 w-3.5" /> Licences
            </NavLink>
            <NavLink to="/actifs/certificats" className={sub}>
              <Award className="h-3.5 w-3.5" /> Certificats
            </NavLink>
            <NavLink to="/actifs/materiels" className={sub}>
              <Server className="h-3.5 w-3.5" /> Matériels
            </NavLink>
            <NavLink to="/actifs/applications" className={sub}>
              <AppWindow className="h-3.5 w-3.5" /> Applications
            </NavLink>
          </div>

          <div className="nav-section">Contrats</div>
          <div className="space-y-1">
            <Item to="/contrats" icon={FileText}>
              Contrats
            </Item>
            <Item to="/renouvellements" icon={CalendarClock}>
              Renouvellements
            </Item>
            <Item to="/fournisseurs" icon={Building2}>
              Fournisseurs
            </Item>
          </div>

          <div className="nav-section">Exploitation</div>
          <div className="space-y-1">
            <Item to="/affectations" icon={ArrowLeftRight}>
              Affectations
            </Item>
            <Item to="/notifications" icon={Bell} badge={unread}>
              Notifications
            </Item>
            <Item to="/import-export" icon={FileSpreadsheet}>
              Import / Export
            </Item>
          </div>

          {showAdmin && (
            <>
              <div className="nav-section">Administration</div>
              <div className="space-y-1">
                {can("admin:users") && (
                  <Item to="/admin/utilisateurs" icon={Users}>
                    Utilisateurs
                  </Item>
                )}
                {can("admin:settings") && (
                  <Item to="/admin/parametres" icon={Settings}>
                    Paramètres
                  </Item>
                )}
                {can("admin:smtp") && (
                  <Item to="/admin/smtp" icon={Mail}>
                    SMTP
                  </Item>
                )}
                {can("admin:audit") && (
                  <Item to="/admin/audit" icon={History}>
                    Journal d'audit
                  </Item>
                )}
                {can("admin:system") && (
                  <Item to="/admin/systeme" icon={Wrench}>
                    Système
                  </Item>
                )}
              </div>
            </>
          )}
        </nav>
        <div className="border-t border-white/10 px-4 py-3 text-[11px] text-brand-300/80">
          {config.org_name} · {config.app_name}
          {config.version && <span> · v{config.version}</span>}
        </div>
      </aside>

      <div className="ml-64 flex min-h-screen min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-8 py-2.5 backdrop-blur">
          <GlobalSearch />
          <div className="flex items-center gap-1">
            <NotificationBell />
            <UserMenu />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-8 py-7">
          <Outlet />
        </main>
        <footer className="border-t border-slate-200 px-8 py-3 text-xs text-slate-500">
          {config.org_name} — {config.app_name}
          {config.version && ` · v${config.version}`}
        </footer>
      </div>
    </div>
  );
}

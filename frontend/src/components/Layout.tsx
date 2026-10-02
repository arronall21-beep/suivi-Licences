import {
  AppWindow,
  ArrowLeftRight,
  Award,
  Bell,
  Building2,
  CalendarClock,
  FileSpreadsheet,
  FileText,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Server,
  ShieldCheck,
  Users,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"
  }`;
const sub = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-md py-1.5 pl-9 pr-3 text-sm transition ${
    isActive ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
  }`;

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-slate-900">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Suivi Licences SI</div>
            <div className="text-xs text-slate-400">Pilotage des actifs</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
          <NavLink to="/" end className={link}>
            <LayoutDashboard className="h-4 w-4" /> Dashboard
          </NavLink>
          <div className="pt-3">
            <NavLink to="/actifs" end className={link}>
              <Server className="h-4 w-4" /> Actifs
            </NavLink>
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
          </div>
          <div className="space-y-1 pt-3">
            <NavLink to="/contrats" className={link}>
              <FileText className="h-4 w-4" /> Contrats
            </NavLink>
            <NavLink to="/fournisseurs" className={link}>
              <Building2 className="h-4 w-4" /> Fournisseurs
            </NavLink>
            <NavLink to="/affectations" className={link}>
              <ArrowLeftRight className="h-4 w-4" /> Affectations
            </NavLink>
            <NavLink to="/renouvellements" className={link}>
              <CalendarClock className="h-4 w-4" /> Renouvellements
            </NavLink>
            <NavLink to="/alertes" className={link}>
              <Bell className="h-4 w-4" /> Alertes
            </NavLink>
            <NavLink to="/import-export" className={link}>
              <FileSpreadsheet className="h-4 w-4" /> Import / Export
            </NavLink>
          </div>
        </nav>
        <div className="border-t border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-700">
              <Users className="h-4 w-4 text-slate-300" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-white">{user?.email}</div>
              <div className="text-xs text-slate-400">{user?.role === "ADMIN" ? "Administrateur" : "Lecture seule"}</div>
            </div>
            <button onClick={logout} className="rounded p-1.5 text-slate-400 hover:bg-white/10 hover:text-white" title="Déconnexion">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
      <main className="ml-64 min-w-0 flex-1 px-8 py-7">
        <Outlet />
      </main>
    </div>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import { ConfigProvider } from "./config";
import AdminAudit from "./pages/admin/Audit";
import AdminSettings from "./pages/admin/Settings";
import AdminSmtp from "./pages/admin/Smtp";
import AdminSystem from "./pages/admin/System";
import AdminUsers from "./pages/admin/Users";
import AssetDetail from "./pages/AssetDetail";
import Assets from "./pages/Assets";
import Assignments from "./pages/Assignments";
import Contracts from "./pages/Contracts";
import Dashboard from "./pages/Dashboard";
import ImportExport from "./pages/ImportExport";
import Login from "./pages/Login";
import Notifications from "./pages/Notifications";
import Renewals from "./pages/Renewals";
import Vendors from "./pages/Vendors";

/** Route réservée à une permission : indication d'interface, le backend vérifie chaque appel. */
function Guard({ permission, children }: { permission: string; children: JSX.Element }) {
  const { can } = useAuth();
  return can(permission) ? children : <Navigate to="/" replace />;
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {user ? (
        <Route
          element={
            <ConfigProvider>
              <Layout />
            </ConfigProvider>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="actifs" element={<Assets />} />
          <Route path="actifs/fiche/:id" element={<AssetDetail />} />
          <Route path="actifs/:slug" element={<Assets />} />
          <Route path="contrats" element={<Contracts />} />
          <Route path="fournisseurs" element={<Vendors />} />
          <Route path="affectations" element={<Assignments />} />
          <Route path="renouvellements" element={<Renewals />} />
          <Route path="notifications" element={<Notifications />} />
          <Route path="alertes" element={<Navigate to="/notifications?tab=alertes" replace />} />
          <Route path="import-export" element={<ImportExport />} />
          <Route path="admin/utilisateurs" element={<Guard permission="admin:users"><AdminUsers /></Guard>} />
          <Route path="admin/parametres" element={<Guard permission="admin:settings"><AdminSettings /></Guard>} />
          <Route path="admin/smtp" element={<Guard permission="admin:smtp"><AdminSmtp /></Guard>} />
          <Route path="admin/audit" element={<Guard permission="admin:audit"><AdminAudit /></Guard>} />
          <Route path="admin/systeme" element={<Guard permission="admin:system"><AdminSystem /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
  );
}

import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import { Spinner } from "./components/ui";
import Alerts from "./pages/Alerts";
import AssetDetail from "./pages/AssetDetail";
import Assets from "./pages/Assets";
import Assignments from "./pages/Assignments";
import Contracts from "./pages/Contracts";
import Dashboard from "./pages/Dashboard";
import ImportExport from "./pages/ImportExport";
import Login from "./pages/Login";
import Renewals from "./pages/Renewals";
import Vendors from "./pages/Vendors";

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      {user ? (
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="actifs" element={<Assets />} />
          <Route path="actifs/fiche/:id" element={<AssetDetail />} />
          <Route path="actifs/:slug" element={<Assets />} />
          <Route path="contrats" element={<Contracts />} />
          <Route path="fournisseurs" element={<Vendors />} />
          <Route path="affectations" element={<Assignments />} />
          <Route path="renouvellements" element={<Renewals />} />
          <Route path="alertes" element={<Alerts />} />
          <Route path="import-export" element={<ImportExport />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      ) : (
        <Route path="*" element={<Navigate to="/login" replace />} />
      )}
    </Routes>
  );
}

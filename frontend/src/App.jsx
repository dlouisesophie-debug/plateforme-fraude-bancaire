import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import TransactionsPage from "./pages/TransactionsPage";
import TransactionDetailPage from "./pages/TransactionDetailPage";
import NewTransactionPage from "./pages/NewTransactionPage";
import AlertsPage from "./pages/AlertsPage";
import ReportsPage from "./pages/ReportsPage";
import UsersPage from "./pages/UsersPage";
import ModelPage from "./pages/ModelPage";
import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { NAV_ITEMS, canAccess } from "./constants/roles";

function rolesFor(path) {
  return NAV_ITEMS.find((item) => item.to === path).roles;
}

// Protège une page : connexion obligatoire, puis contrôle du rôle si demandé.
function PrivateRoute({ roles, children }) {
  const { isAuthenticated, user, userLoading } = useAuth();

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!roles) return children;
  if (userLoading) {
    return (
      <Layout>
        <p className="text-sm text-ink-secondary">Chargement du profil...</p>
      </Layout>
    );
  }
  if (!canAccess(user, roles)) {
    return (
      <Layout>
        <h1 className="font-display text-2xl font-semibold text-ink-primary">Accès refusé</h1>
        <p className="mt-2 text-sm text-ink-secondary">Votre rôle ne permet pas d'accéder à cette page.</p>
      </Layout>
    );
  }
  return children;
}

const ROUTES = [
  { path: "/", element: <DashboardPage /> },
  { path: "/transactions", element: <TransactionsPage /> },
  { path: "/transactions/new", element: <NewTransactionPage />, roles: rolesFor("/transactions/new") },
  { path: "/transactions/:id", element: <TransactionDetailPage /> },
  { path: "/alerts", element: <AlertsPage />, roles: rolesFor("/alerts") },
  { path: "/reports", element: <ReportsPage />, roles: rolesFor("/reports") },
  { path: "/users", element: <UsersPage />, roles: rolesFor("/users") },
  { path: "/model", element: <ModelPage />, roles: rolesFor("/model") },
];

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          {ROUTES.map(({ path, element, roles }) => (
            <Route key={path} path={path} element={<PrivateRoute roles={roles}>{element}</PrivateRoute>} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

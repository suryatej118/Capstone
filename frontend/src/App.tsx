import ScanDetails from "./pages/ScanDetails";
import HistoryPage from "./pages/History";
import Overview from "./pages/Overview";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  LayoutDashboard,
  ScanSearch,
  History,
  ChartColumn,
  Settings,
  ShieldCheck,
} from "lucide-react";
import MagnificationDock, {
  type DockItemData,
} from "./components/dock/MagnificationDock";

import "./index.css";
import Analyzer from "./pages/Analyzer";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute, PublicOnlyRoute } from "./auth/guards";
import { useAuth } from "./auth/useAuth";

function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="content-card placeholder-card">
      <p className="eyebrow">JOB SCAM RADAR</p>
      <h1>{title}</h1>
      <p className="page-description">{description}</p>
      <span className="coming-soon">Under development</span>
    </section>
  );
}

function AuthenticatedShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const items: DockItemData[] = [
    {
      icon: <LayoutDashboard size={22} />,
      label: "Overview",
      onClick: () => navigate("/dashboard"),
      active: location.pathname === "/dashboard",
    },
    {
      icon: <ScanSearch size={22} />,
      label: "Analyzer",
      onClick: () => navigate("/analyzer"),
      active: location.pathname === "/analyzer",
    },
    {
      icon: <History size={22} />,
      label: "History",
      onClick: () => navigate("/history"),
      active: location.pathname === "/history",
    },
    {
      icon: <ChartColumn size={22} />,
      label: "Insights",
      onClick: () => navigate("/insights"),
      active: location.pathname === "/insights",
    },
    {
      icon: <Settings size={22} />,
      label: "Settings",
      onClick: () => navigate("/settings"),
      active: location.pathname === "/settings",
    },
  ];

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={22} />
          </div>
          <span>Job Scam <strong>Radar</strong></span>
        </div>
        <div className="system-status">
          <span className="status-dot" />
          {user?.email || "Authenticated"}
          <button className="shell-logout" onClick={() => void logout()}>
            Sign out
          </button>
        </div>
      </header>

      <main className="main-content">
        <Outlet />
      </main>

      <MagnificationDock items={items} />
    </div>
  );
}

function AppLayout() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/landing" element={<Landing />} />
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AuthenticatedShell />}>
          <Route path="/dashboard" element={<Overview />} />
          <Route path="/analyzer" element={<Analyzer />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:scanId" element={<ScanDetails />} />
          <Route
            path="/insights"
            element={
              <PlaceholderPage
                title="Detection Insights"
                description="Explore detection patterns and risk statistics."
              />
            }
          />
          <Route
            path="/settings"
            element={
              <PlaceholderPage
                title="Settings"
                description="Manage application preferences and configuration."
              />
            }
          />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </AuthProvider>
  );
}

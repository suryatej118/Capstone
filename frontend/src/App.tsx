import ScanDetails from "./pages/ScanDetails";
import HistoryPage from "./pages/History";
import Overview from "./pages/Overview";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
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

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const items: DockItemData[] = [
    {
      icon: <LayoutDashboard size={22} />,
      label: "Overview",
      onClick: () => navigate("/"),
      active: location.pathname === "/",
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
          Detection system
        </div>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/analyzer" element={<Analyzer />} />
          <Route path="/history" element={<HistoryPage />} />
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
          <Route
            path="*"
            element={
              <PlaceholderPage
                title="Page not found"
                description="The page you're looking for doesn't exist."
              />
            }
          />
          <Route path="/history/:scanId" element={<ScanDetails />} />
        </Routes>
      </main>

      <MagnificationDock items={items} />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

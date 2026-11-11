import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Clock3,
  RefreshCw,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  getDashboardStats,
  type DashboardStats,
} from "../services/api";

import "./Overview.css";

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "Date unavailable";

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getRiskClass(risk: string) {
  return risk.toLowerCase();
}

function StatCard({
  label,
  value,
  detail,
  icon,
  variant,
}: {
  label: string;
  value: number;
  detail: string;
  icon: React.ReactNode;
  variant: string;
}) {
  return (
    <article className={`dashboard-stat-card ${variant}`}>
      <div className="dashboard-stat-top">
        <span>{label}</span>
        <div className="dashboard-stat-icon">{icon}</div>
      </div>
      <strong>{value.toLocaleString("en-IN")}</strong>
      <small>{detail}</small>
    </article>
  );
}

export default function Overview() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dashboard data."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
  let cancelled = false;

  async function fetchDashboard() {
    try {
      const data = await getDashboardStats();

      if (!cancelled) {
        setStats(data);
        setError("");
      }
    } catch (err) {
      if (!cancelled) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load dashboard data."
        );
      }
    } finally {
      if (!cancelled) {
        setLoading(false);
      }
    }
  }

  void fetchDashboard();

  return () => {
    cancelled = true;
  };
}, []);

  const total = stats?.total_scans ?? 0;
  const high = stats?.high_risk ?? 0;
  const medium = stats?.medium_risk ?? 0;
  const low = stats?.low_risk ?? 0;

  const distributionTotal = high + medium + low;

  const highWidth =
    distributionTotal > 0 ? (high / distributionTotal) * 100 : 0;
  const mediumWidth =
    distributionTotal > 0 ? (medium / distributionTotal) * 100 : 0;
  const lowWidth =
    distributionTotal > 0 ? (low / distributionTotal) * 100 : 0;

  if (loading && !stats) {
    return (
      <main className="overview-page">
        <div className="overview-loading">
          <RefreshCw className="overview-spin" size={22} />
          <span>Loading dashboard...</span>
        </div>
      </main>
    );
  }

  if (error && !stats) {
    return (
      <main className="overview-page">
        <div className="overview-error">
          <AlertTriangle size={22} />
          <div>
            <h2>Dashboard unavailable</h2>
            <p>{error}</p>
            <button onClick={() => void loadDashboard()}>
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="overview-page">
      <header className="overview-header">
        <div>
          <p className="overview-eyebrow">JOB SCAM RADAR / OVERVIEW</p>
          <h1>Dashboard</h1>
          <p className="overview-subtitle">
            Monitor analyzed job offers and identify recruitment risks.
          </p>
        </div>

        <button
          className="overview-refresh"
          onClick={() => void loadDashboard()}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "overview-spin" : ""}
          />
          Refresh
        </button>
      </header>

      {error && (
        <div className="overview-inline-error" role="alert">
          <AlertTriangle size={17} />
          {error} Showing the last successfully loaded data.
        </div>
      )}

      <section className="dashboard-stats-grid">
        <StatCard
          label="TOTAL SCANS"
          value={total}
          detail="All saved job offer analyses"
          icon={<Activity size={19} />}
          variant="stat-total"
        />

        <StatCard
          label="HIGH RISK"
          value={high}
          detail="Offers requiring serious caution"
          icon={<ShieldAlert size={19} />}
          variant="stat-high"
        />

        <StatCard
          label="MEDIUM RISK"
          value={medium}
          detail="Offers requiring further verification"
          icon={<AlertTriangle size={19} />}
          variant="stat-medium"
        />

        <StatCard
          label="LOW RISK"
          value={low}
          detail="Fewer suspicious indicators detected"
          icon={<ShieldCheck size={19} />}
          variant="stat-low"
        />
      </section>

      <section className="dashboard-content-grid">
        <article className="dashboard-panel distribution-panel">
          <div className="dashboard-panel-heading">
            <div>
              <span className="overview-eyebrow">ANALYTICS</span>
              <h2>Risk distribution</h2>
            </div>
            <Activity size={19} />
          </div>

          {distributionTotal === 0 ? (
            <div className="dashboard-empty">
              No risk distribution data available yet.
            </div>
          ) : (
            <>
              <div
                className="risk-distribution-bar"
                aria-label={`High risk ${high}, medium risk ${medium}, low risk ${low}`}
              >
                {high > 0 && (
                  <div
                    className="distribution-segment segment-high"
                    style={{ width: `${highWidth}%` }}
                  />
                )}
                {medium > 0 && (
                  <div
                    className="distribution-segment segment-medium"
                    style={{ width: `${mediumWidth}%` }}
                  />
                )}
                {low > 0 && (
                  <div
                    className="distribution-segment segment-low"
                    style={{ width: `${lowWidth}%` }}
                  />
                )}
              </div>

              <div className="distribution-legend">
                <div>
                  <span className="legend-dot dot-high" />
                  <span>High risk</span>
                  <strong>{high}</strong>
                </div>
                <div>
                  <span className="legend-dot dot-medium" />
                  <span>Medium risk</span>
                  <strong>{medium}</strong>
                </div>
                <div>
                  <span className="legend-dot dot-low" />
                  <span>Low risk</span>
                  <strong>{low}</strong>
                </div>
              </div>

              <p className="distribution-note">
                Based on {distributionTotal} scans with a recorded risk
                classification.
              </p>
            </>
          )}
        </article>

        <article className="dashboard-panel quick-action-panel">
          <div className="quick-action-icon">
            <ScanSearch size={23} />
          </div>
          <span className="overview-eyebrow">INVESTIGATION WORKSPACE</span>
          <h2>Analyze a job offer</h2>
          <p>
            Check suspicious recruitment messages using rule-based detection,
            machine learning, and available company verification signals.
          </p>
          <Link to="/analyzer" className="dashboard-primary-link">
            Start new analysis
            <ArrowRight size={17} />
          </Link>
        </article>
      </section>

      <section className="dashboard-panel recent-scans-panel">
        <div className="dashboard-panel-heading">
          <div>
            <span className="overview-eyebrow">ACTIVITY</span>
            <h2>Recent scans</h2>
            <p>Latest saved job offer investigations.</p>
          </div>
          <Clock3 size={19} />
        </div>

        {!stats?.recent_scans.length ? (
          <div className="dashboard-empty">
            <ShieldCheck size={25} />
            <strong>No scans yet</strong>
            <span>Your completed analyses will appear here.</span>
            <Link to="/analyzer">Analyze your first job offer</Link>
          </div>
        ) : (
          <div className="recent-scans-list">
            {stats.recent_scans.map((scan) => (
              <div className="recent-scan-row" key={scan.id}>
                <div className="recent-scan-main">
                  <div className="recent-scan-icon">
                    <ScanSearch size={18} />
                  </div>
                  <div className="recent-scan-info">
                    <strong>Scan #{scan.id}</strong>
                    <span>{scan.platform || "Unknown platform"}</span>
                    <small>{formatDate(scan.created_at)}</small>
                  </div>
                </div>

                <div className="recent-scan-result">
                  <span
                    className={`dashboard-risk-badge risk-${getRiskClass(
                      scan.risk_level
                    )}`}
                  >
                    {scan.risk_level} risk
                  </span>
                  <strong>{scan.final_score.toFixed(1)} / 100</strong>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <p className="dashboard-disclaimer">
        Risk classifications are automated assessments and should not be
        treated as definitive proof of fraud or legitimacy.
      </p>
    </main>
  );
}
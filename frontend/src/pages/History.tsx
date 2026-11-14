import { useNavigate } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Clock3,
  RefreshCw,
  Search,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import {
  getScans,
  type ScanHistoryItem,
} from "../services/api";

import "./History.css";

const PAGE_SIZE = 10;

type RiskFilter = "All" | "High" | "Medium" | "Low";

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function riskClass(risk: string) {
  const normalized = risk.toLowerCase();

  if (normalized === "high") return "risk-high";
  if (normalized === "medium") return "risk-medium";
  if (normalized === "low") return "risk-low";

  return "";
}

export default function History() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("All");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadScans = useCallback(async (offset: number) => {
    setLoading(true);
    setError("");

    try {
      const data = await getScans(PAGE_SIZE, offset);
      setScans(data.scans);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load scan history."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchHistory() {
      try {
        const data = await getScans(PAGE_SIZE, page * PAGE_SIZE);

        if (!cancelled) {
          setScans(data.scans);
          setTotal(data.total);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load scan history."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchHistory();

    return () => {
      cancelled = true;
    };
  }, [page]);

  const filteredScans = scans.filter((scan) => {
    const matchesRisk =
      riskFilter === "All" || scan.risk_level === riskFilter;

    const searchValue = search.trim().toLowerCase();

    const matchesSearch =
      !searchValue ||
      String(scan.id).includes(searchValue) ||
      scan.platform.toLowerCase().includes(searchValue) ||
      scan.preview.toLowerCase().includes(searchValue);

    return matchesRisk && matchesSearch;
  });

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function changeFilter(filter: RiskFilter) {
    setRiskFilter(filter);
  }

  return (
    <main className="history-page">
      <header className="history-header">
        <div>
          <span className="history-eyebrow">
            JOB SCAM RADAR / INVESTIGATIONS
          </span>
          <h1>Scan History</h1>
          <p>
            Review your previously analyzed job offers and their risk
            assessments.
          </p>
        </div>

        <button
          className="history-refresh"
          onClick={() => void loadScans(page * PAGE_SIZE)}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "history-spin" : ""}
          />
          Refresh
        </button>
      </header>

      <section className="history-summary">
        <div className="history-summary-icon">
          <ScanSearch size={22} />
        </div>
        <div>
          <span>Total saved investigations</span>
          <strong>{total}</strong>
        </div>
      </section>

      <section className="history-panel">
        <div className="history-toolbar">
          <div className="history-search">
            <Search size={17} />
            <input
              type="text"
              placeholder="Search by scan ID, platform, or message..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <div className="history-filters" aria-label="Filter by risk">
            {(["All", "High", "Medium", "Low"] as RiskFilter[]).map(
              (filter) => (
                <button
                  key={filter}
                  className={`history-filter ${
                    riskFilter === filter ? "active" : ""
                  }`}
                  onClick={() => changeFilter(filter)}
                  aria-pressed={riskFilter === filter}
                >
                  {filter}
                </button>
              )
            )}
          </div>
        </div>

        {error && (
          <div className="history-error" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
            <button onClick={() => void loadScans(page * PAGE_SIZE)}>
              Retry
            </button>
          </div>
        )}

        {loading ? (
          <div className="history-state">
            <RefreshCw className="history-spin" size={22} />
            <span>Loading investigations...</span>
          </div>
        ) : !error && filteredScans.length === 0 ? (
          <div className="history-state">
            <ShieldCheck size={27} />
            <strong>
              {search || riskFilter !== "All"
                ? "No matching scans"
                : "No investigations yet"}
            </strong>
            <span>
              {search || riskFilter !== "All"
                ? "Try changing your search or risk filter."
                : "Completed analyses will appear here."}
            </span>
          </div>
        ) : (
          <div className="history-list">
            {filteredScans.map((scan) => (
              <article
                className="history-item"
                key={scan.id}
                onClick={() => navigate(`/history/${scan.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    navigate(`/history/${scan.id}`);
                    }
                }}
                >
                <div className="history-item-main">
                  <div className="history-item-icon">
                    {scan.risk_level === "High" ? (
                      <ShieldAlert size={20} />
                    ) : (
                      <ScanSearch size={20} />
                    )}
                  </div>

                  <div className="history-item-content">
                    <div className="history-item-title">
                      <strong>Scan #{scan.id}</strong>
                      <span className={`history-risk ${riskClass(scan.risk_level)}`}>
                        {scan.risk_level} Risk
                      </span>
                    </div>

                    <span className="history-platform">
                      {scan.platform || "Unknown platform"}
                    </span>

                    <p>{scan.preview || "No preview available."}</p>

                    <div className="history-date">
                      <Clock3 size={13} />
                      {formatDate(scan.created_at)}
                    </div>
                  </div>
                </div>

                <div className="history-item-score">
                  <span>Final score</span>
                  <strong>{scan.final_score.toFixed(2)}</strong>
                  <small>{scan.confidence}% confidence</small>
                </div>
              </article>
            ))}
          </div>
        )}

        <footer className="history-pagination">
          <span>
            {total === 0
              ? "No scans"
              : `Showing ${page * PAGE_SIZE + 1}–${Math.min(
                  (page + 1) * PAGE_SIZE,
                  total
                )} of ${total} scans`}
          </span>

          <div>
            <button
              aria-label="Previous page"
              disabled={page === 0 || loading}
              onClick={() => setPage((current) => current - 1)}
            >
              <ChevronLeft size={18} />
            </button>

            <span>
              {totalPages === 0 ? 0 : page + 1} / {totalPages}
            </span>

            <button
              aria-label="Next page"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </footer>
      </section>

      <p className="history-disclaimer">
        Risk classifications are automated assessments and should not be
        treated as definitive proof of fraud or legitimacy.
      </p>
    </main>
  );
}
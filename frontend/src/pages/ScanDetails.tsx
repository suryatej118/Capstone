import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileText,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import {
  getScanDetails,
  type ScanDetail,
  type HighlightedSpan,
} from "../services/api";

import "./ScanDetails.css";

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function humanizeSignal(signal: string) {
  return signal
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

type SignalStatus = "positive" | "negative" | "neutral" | "unavailable";

function getSignalStatus(
  signal: string,
  value: unknown
): SignalStatus {
  if (value === null || value === undefined) {
    return "unavailable";
  }

  if (signal === "negative_penalty") {
    return "negative";
  }

  if (signal === "recruiter_email_corporate") {
    if (typeof value === "string") {
      const email = value.toLowerCase();

      const personalProviders = [
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "rediffmail.com",
      ];

      const domain = email.split("@")[1];

      if (domain && personalProviders.includes(domain)) {
        return "negative";
      }

      return "positive";
    }

    return "neutral";
  }

  if (typeof value === "boolean") {
    return value ? "positive" : "neutral";
  }

  if (signal === "active_job_postings_count") {
    return typeof value === "number" && value > 0
      ? "positive"
      : "neutral";
  }

  return "neutral";
}

function getSignalStatusLabel(status: SignalStatus): string {
  switch (status) {
    case "positive":
      return "Positive signal";
    case "negative":
      return "Risk indicator";
    case "neutral":
      return "Not detected / Neutral";
    case "unavailable":
      return "Unavailable";
  }
}

function HighlightedOffer({
  text,
  spans,
}: {
  text: string;
  spans: HighlightedSpan[];
}) {
  const validSpans = spans
    .filter(
      (span) =>
        Number.isInteger(span.start) &&
        Number.isInteger(span.end) &&
        span.start >= 0 &&
        span.end > span.start &&
        span.end <= text.length
    )
    .sort((a, b) => a.start - b.start);

  const parts: { text: string; highlighted: boolean; key: number }[] = [];
  let cursor = 0;

  validSpans.forEach((span) => {
    // Ignore overlapping spans to prevent duplicate text.
    if (span.start < cursor) return;

    if (span.start > cursor) {
      parts.push({
        text: text.slice(cursor, span.start),
        highlighted: false,
        key: cursor,
      });
    }

    parts.push({
      text: text.slice(span.start, span.end),
      highlighted: true,
      key: span.start,
    });

    cursor = span.end;
  });

  if (cursor < text.length) {
    parts.push({
      text: text.slice(cursor),
      highlighted: false,
      key: cursor,
    });
  }

  return (
    <div className="scan-original-text">
      {parts.map((part) =>
        part.highlighted ? (
          <mark key={part.key} className="scan-highlight">
            {part.text}
          </mark>
        ) : (
          <span key={part.key}>{part.text}</span>
        )
      )}
    </div>
  );
}

export default function ScanDetails() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const validScanId =
    Boolean(scanId) &&
    /^\d+$/.test(scanId!) &&
    Number(scanId) > 0;
  useEffect(() => {
    let cancelled = false;

    async function fetchScan() {
      const id = Number(scanId);

      if (!validScanId) return;

      try {
        const data = await getScanDetails(id);

        if (!cancelled) {
          setScan(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load scan details."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchScan();

    return () => {
      cancelled = true;
    };
  }, [scanId, validScanId]);

  if (!validScanId) {
    return (
      <main className="scan-details-page">
        <div className="scan-details-error">
          <AlertTriangle size={28} />
          <h2>Invalid scan ID</h2>
          <p>Please select a valid investigation.</p>
          <button onClick={() => navigate("/history")}>
            <ArrowLeft size={17} />
            Back to History
          </button>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="scan-details-page">
        <div className="scan-details-state">
          <Clock3 size={24} />
          <p>Retrieving investigation report...</p>
        </div>
      </main>
    );
  }

  if (error || !scan) {
    return (
      <main className="scan-details-page">
        <div className="scan-details-error">
          <AlertTriangle size={28} />
          <h2>Report unavailable</h2>
          <p>{error || "The requested scan could not be found."}</p>
          <button onClick={() => navigate("/history")}>
            <ArrowLeft size={17} />
            Back to History
          </button>
        </div>
      </main>
    );
  }

  const risk = scan.risk_level.toLowerCase();

  const riskClass =
    risk === "high"
      ? "scan-risk-high"
      : risk === "medium"
        ? "scan-risk-medium"
        : "scan-risk-low";

  return (
    <main className="scan-details-page">
      <button
        className="scan-back-button"
        onClick={() => navigate("/history")}
      >
        <ArrowLeft size={17} />
        Back to Scan History
      </button>

      <header className="scan-details-header">
        <div>
          <span className="scan-details-eyebrow">
            INVESTIGATION REPORT / #{scan.id}
          </span>
          <h1>Scan Details</h1>
          <p>
            Complete risk assessment and verification report for this
            job offer.
          </p>
        </div>

        <span className={`scan-risk-badge ${riskClass}`}>
          {scan.risk_level} Risk
        </span>
      </header>

      <section className="scan-metrics">
        <article className="scan-metric-card">
          <span>Final risk score</span>
          <strong>{scan.final_score.toFixed(2)}</strong>
          <small>Hybrid assessment score</small>
        </article>

        <article className="scan-metric-card">
          <span>Confidence</span>
          <strong>{scan.confidence}%</strong>
          <small>Model confidence value</small>
        </article>

        <article className="scan-metric-card">
          <span>Rule score</span>
          <strong>{scan.rule_score}</strong>
          <small>Rule engine result</small>
        </article>

        <article className="scan-metric-card">
          <span>ML probability</span>
          <strong>
            {scan.ml_probability === null
              ? "N/A"
              : `${(scan.ml_probability * 100).toFixed(2)}%`}
          </strong>
          <small>Predicted scam probability</small>
        </article>
      </section>

      <section className="scan-report-card">
        <div className="scan-section-heading">
          <div className="scan-section-icon">
            <FileText size={20} />
          </div>
          <div>
            <h2>Original job offer</h2>
            <p>Suspicious evidence is highlighted below.</p>
          </div>
        </div>

        <div className="scan-offer-meta">
          <span>Platform: {scan.platform || "Unknown"}</span>
          <span>Scan ID: #{scan.id}</span>
        </div>

        <HighlightedOffer
          text={scan.submitted_text}
          spans={scan.highlighted_spans}
        />

        <div className="scan-highlight-legend">
          <span className="scan-highlight-dot" />
          Highlighted text indicates evidence detected by the rule engine.
        </div>
      </section>

      <section className="scan-report-card">
        <div className="scan-section-heading">
          <div className="scan-section-icon">
            <ShieldAlert size={20} />
          </div>
          <div>
            <h2>Detected risk indicators</h2>
            <p>
              {scan.reasons.length} rule-based indicators were detected.
            </p>
          </div>
        </div>

        {scan.reasons.length === 0 ? (
          <div className="scan-empty">
            No rule-based indicators were recorded.
          </div>
        ) : (
          <div className="scan-reasons">
            {scan.reasons.map((reason, index) => (
              <article className="scan-reason" key={`${reason.rule_id}-${index}`}>
                <div className="scan-reason-top">
                  <span className="scan-rule-id">{reason.rule_id}</span>
                  <span className="scan-rule-weight">
                    Weight: {reason.weight}
                  </span>
                </div>
                <h3>{reason.description}</h3>
                <blockquote>{reason.span}</blockquote>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="scan-report-card">
        <div className="scan-section-heading">
          <div className="scan-section-icon">
            <ShieldCheck size={20} />
          </div>
          <div>
            <h2>Company verification report</h2>
            <p>
              External signals and recruitment-related checks recorded
              during analysis.
            </p>
          </div>
        </div>

        <div className="scan-verification-summary">
          <div>
            <span>Hiring intent score</span>
            <strong>{scan.hiring_intent_score}</strong>
          </div>
          <span>
            This is a separate verification score, not the final risk
            score.
          </span>
        </div>

        <div className="scan-verification-list">
          {scan.hiring_intent_reasons.map((item, index) => {
            const signal = String(item.signal ?? "Unknown signal");
            const value = item.value;
            const status = getSignalStatus(signal, value);

            return (
              <article
                className={`scan-verification-item scan-signal-${status}`}
                key={`${signal}-${index}`}
              >
                <div className="scan-verification-icon">
                  {status === "positive" ? (
                    <CheckCircle2 size={17} />
                  ) : status === "negative" ? (
                    <AlertTriangle size={17} />
                  ) : (
                    <Clock3 size={17} />
                  )}
                </div>

                <div className="scan-verification-content">
                  <strong>{humanizeSignal(signal)}</strong>
                  <span>{displayValue(value)}</span>
                  <small>{getSignalStatusLabel(status)}</small>
                </div>

                <div className="scan-verification-score">
                  <strong>
                    {Number(item.score ?? 0) > 0 ? "+" : ""}
                    {String(item.score ?? 0)}
                  </strong>
                  <small>
                    {String(item.confidence ?? 0)}% confidence
                  </small>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="scan-report-card scan-metadata-card">
        <div className="scan-section-heading">
          <div className="scan-section-icon">
            <CalendarDays size={20} />
          </div>
          <div>
            <h2>Investigation metadata</h2>
            <p>Information associated with this saved report.</p>
          </div>
        </div>

        <div className="scan-metadata-grid">
          <div>
            <span>Scan ID</span>
            <strong>#{scan.id}</strong>
          </div>
          <div>
            <span>Platform</span>
            <strong>{scan.platform || "Unknown"}</strong>
          </div>
          <div>
            <span>Created at</span>
            <strong>{formatDate(scan.created_at)}</strong>
          </div>
          <div>
            <span>Requester ID</span>
            <strong>{scan.requester_id || "Unavailable"}</strong>
          </div>
        </div>
      </section>

      <p className="scan-details-disclaimer">
        This report represents an automated assessment based on available
        text and verification signals. A risk classification is not
        definitive proof of fraud or legitimacy.
      </p>
    </main>
  );
}
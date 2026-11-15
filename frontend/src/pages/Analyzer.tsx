
import { useState, type FormEvent, type ReactNode } from "react";
import {
  AlertCircle,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  ClipboardPaste,
  FileSearch,
  ListChecks,
  LoaderCircle,
  RotateCcw,
  ScanSearch,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { analyzeJob } from "../services/api";
import type {
  AnalyzeResponse,
  HighlightedSpan,
} from "../services/api";

import "./Analyzer.css";

const SAMPLE_TEXT = `Congratulations! You have been selected for a remote data entry position.

Our company offers a salary of Rs. 45,000 per month. To secure your position, you must pay a refundable registration fee of Rs. 1,999 immediately.

Limited vacancies available. Send your payment today to complete your onboarding.`;

function formatProbability(value: number | null) {
  if (value === null || !Number.isFinite(value)) return "Unavailable";
  return `${(value * 100).toFixed(1)}%`;
}

function clampScore(value: number) {
  return Math.min(100, Math.max(0, value));
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "Not available";

  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  return JSON.stringify(value) ?? String(value);
}


function humanizeSignal(signal: string): string {
  const labels: Record<string, string> = {
    corporate_domain_present: "Corporate email domain",
    careers_page_present: "Company careers page",
    recruiter_email_corporate: "Recruiter email verification",
    opencorporates_match: "Company registration",
    active_job_postings_count: "Active job listings",
    github_org_activity: "GitHub organization activity",
    domain_age_years: "Website domain age",
    search_presence_hiring: "Online hiring presence",
    negative_penalty: "Negative indicators",
  };

  return (
    labels[signal] ??
    signal.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

function getSignalCategory(signal: string): string {
  if (
    [
      "corporate_domain_present",
      "careers_page_present",
      "opencorporates_match",
    ].includes(signal)
  ) {
    return "Company identity";
  }

  if (
    [
      "recruiter_email_corporate",
      "active_job_postings_count",
      "search_presence_hiring",
    ].includes(signal)
  ) {
    return "Recruitment activity";
  }

  if (
    ["github_org_activity", "domain_age_years"].includes(signal)
  ) {
    return "Digital footprint";
  }

  return "Risk indicators";
}

function getSignalExplanation(signal: string, value: unknown): string {
  if (signal === "negative_penalty") {
    return "A potentially harmful indicator was identified in the submitted message. Review the evidence before proceeding.";
  }

  if (value === null || value === undefined ||
      value === "pending" || value === "Not available") {
    return "This check could not be completed. It has not been treated as negative evidence.";
  }

  const explanations: Record<string, string> = {
    corporate_domain_present:
      "Checks whether the recruitment communication includes a company-associated email domain.",
    careers_page_present:
      "Checks whether the message references or matches an official company careers page.",
    recruiter_email_corporate:
      "Checks whether the recruiter appears to use a corporate email address.",
    opencorporates_match:
      "Checks for a matching company registration record.",
    active_job_postings_count:
      "Looks for other active job listings associated with the employer.",
    github_org_activity:
      "Looks for public GitHub organization activity associated with the company.",
    domain_age_years:
      "Checks how long the associated website domain has existed.",
    search_presence_hiring:
      "Looks for an online presence associated with the employer's hiring activity.",
  };

  return explanations[signal] ??
    "This signal contributes additional context to the hiring assessment.";
}

function humanizeSignalValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => humanizeSignalValue(item)).join(", ");
  }

  if (typeof value === "string") {
    const labels: Record<string, string> = {
      payment_request_detected_in_text:
        "Payment request detected in the job message",
    };

    return labels[value] ??
      value.replaceAll("_", " ");
  }

  return formatValue(value);
}

function getSignalStatus(value: unknown): {
  label: string;
  className: string;
} {
  if (value === null || value === undefined) {
    return { label: "Unavailable", className: "status-unavailable" };
  }

  if (typeof value === "boolean") {
    return value
      ? { label: "Detected", className: "status-detected" }
      : { label: "Not detected", className: "status-neutral" };
  }

  if (Array.isArray(value)) {
    return value.length > 0
      ? { label: "Detected", className: "status-detected" }
      : { label: "Not detected", className: "status-neutral" };
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();

    if (
      normalized === "pending" ||
      normalized === "not checked"
    ) {
      return { label: "Pending", className: "status-pending" };
    }

    if (
      normalized === "not available" ||
      normalized === "unavailable" ||
      normalized === ""
    ) {
      return { label: "Unavailable", className: "status-unavailable" };
    }

    if (normalized === "false") {
      return { label: "Not detected", className: "status-neutral" };
    }

    if (normalized === "true") {
      return { label: "Detected", className: "status-detected" };
    }
  }

  return { label: "Available", className: "status-available" };
}


function HighlightedText({
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

  const parts: ReactNode[] = [];
  let cursor = 0;

  validSpans.forEach((span, index) => {
    if (span.start < cursor) return;

    if (span.start > cursor) {
      parts.push(
        <span key={`plain-${index}`}>
          {text.slice(cursor, span.start)}
        </span>
      );
    }

    parts.push(
      <mark key={`highlight-${index}`} className="suspicious-highlight">
        {text.slice(span.start, span.end)}
      </mark>
    );

    cursor = span.end;
  });

  if (cursor < text.length) {
    parts.push(<span key="plain-last">{text.slice(cursor)}</span>);
  }

  return <div className="highlighted-text">{parts}</div>;
}

function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <div className="analysis-metric">
      <div className="analysis-metric-top">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function AnalysisResults({
  result,
  submittedText,
}: {
  result: AnalyzeResponse;
  submittedText: string;
}) {
  const riskClass = result.risk_level.toLowerCase();

  return (
    <section className="results-section" aria-live="polite">
      <div className="results-heading">
        <div>
          <p className="analyzer-eyebrow">INVESTIGATION REPORT</p>
          <h2>Analysis results</h2>
          <p className="analyzer-muted">
            Findings generated by the Job Scam Radar detection engine.
          </p>
        </div>

        <div className={`risk-badge risk-${riskClass}`}>
          <ShieldAlert size={17} />
          {result.risk_level} risk
        </div>
      </div>

      <div className="results-metrics">
        <MetricCard
          label="HYBRID SCORE"
          value={`${result.final_score.toFixed(1)} / 100`}
          detail="Combined detection score"
          icon={<ActivityIcon />}
        />
        <MetricCard
          label="ML PROBABILITY"
          value={formatProbability(result.ml_probability)}
          detail="Model scam probability"
          icon={<BrainCircuit size={18} />}
        />
        <MetricCard
          label="CONFIDENCE INDICATOR"
          value={`${result.confidence}%`}
          detail="Heuristic indicator, not calibrated probability"
          icon={<ShieldCheck size={18} />}
        />
        <MetricCard
          label="RULE SCORE"
          value={`${result.rule_score}`}
          detail="Rule-engine score"
          icon={<ListChecks size={18} />}
        />
      </div>

      <div className="score-panel">
        <div className="score-panel-heading">
          <div>
            <span className="analyzer-eyebrow">RISK ASSESSMENT</span>
            <h3>Overall risk score</h3>
          </div>
          <strong>{result.final_score.toFixed(1)}%</strong>
        </div>

        <div className="score-track">
          <div
            className={`score-fill risk-fill-${riskClass}`}
            style={{ width: `${clampScore(result.final_score)}%` }}
          />
        </div>
        <p className="analyzer-muted">
          Risk classification: {result.risk_level}. This is an automated
          assessment, not proof that a job offer is fraudulent.
        </p>
      </div>

      <div className="result-columns">
        <section className="result-panel">
          <div className="result-panel-heading">
            <FileSearch size={19} />
            <h3>Suspicious text evidence</h3>
          </div>

          <p className="analyzer-muted">
            Text spans identified by the rule engine are highlighted below.
          </p>

          <HighlightedText
            text={submittedText}
            spans={result.highlighted_spans ?? []}
          />

          {result.highlighted_spans.length === 0 && (
            <p className="empty-evidence">
              No text spans were highlighted by the rule engine.
            </p>
          )}
        </section>

        <section className="result-panel">
          <div className="result-panel-heading">
            <ShieldAlert size={19} />
            <h3>Triggered detection rules</h3>
          </div>

          {result.reasons.length === 0 ? (
            <p className="empty-evidence">
              No detection rules were triggered.
            </p>
          ) : (
            <div className="evidence-list">
              {result.reasons.map((reason, index) => (
                <article className="evidence-item" key={`${reason.rule_id}-${index}`}>
                  <div className="evidence-item-top">
                    <span className="rule-id">{reason.rule_id}</span>
                    <span className="rule-weight">
                      Weight: {reason.weight}
                    </span>
                  </div>
                  <strong>{reason.description}</strong>
                  <p>“{reason.span}”</p>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>


<section className="result-panel hiring-panel verification-report">
  {(() => {
    const signals = result.hiring_intent_reasons.map((reason, index) => {
      const fields = reason as Record<string, unknown>;
      const signal = String(fields.signal ?? "unknown");
      const value = fields.value;

      const status =
        signal === "negative_penalty"
          ? { label: "Risk detected", className: "status-risk" }
          : getSignalStatus(value);

      return {
        signal,
        value,
        score: fields.score,
        confidence: fields.confidence,
        status,
        category: getSignalCategory(signal),
        explanation: getSignalExplanation(signal, value),
        key: `${signal}-${index}`,
      };
    });

    const categories = [
      "Company identity",
      "Recruitment activity",
      "Digital footprint",
      "Risk indicators",
    ];

    const counts = {
      detected: signals.filter(
        (item) =>
          item.status.label === "Detected" ||
          item.status.label === "Risk detected"
      ).length,
      notDetected: signals.filter(
        (item) => item.status.label === "Not detected"
      ).length,
      pending: signals.filter(
        (item) => item.status.label === "Pending"
      ).length,
      unavailable: signals.filter(
        (item) => item.status.label === "Unavailable"
      ).length,
    };

    return (
      <>
        <div className="verification-heading">
          <div className="result-panel-heading">
            <BrainCircuit size={20} />
            <div>
              <h3>Verification report</h3>
              <p className="analyzer-muted">
                Company and recruitment signals collected during this scan.
              </p>
            </div>
          </div>

          <div className="verification-score">
            <span>HIRING-INTENT SCORE</span>
            <strong>{result.hiring_intent_score}<small>/100</small></strong>
          </div>
        </div>

        <div className="verification-summary">
          <div className="verification-summary-card summary-detected">
            <span className="summary-dot" />
            <div>
              <strong>{counts.detected}</strong>
              <span>Detected</span>
            </div>
          </div>

          <div className="verification-summary-card summary-neutral">
            <span className="summary-dot" />
            <div>
              <strong>{counts.notDetected}</strong>
              <span>Not detected</span>
            </div>
          </div>

          <div className="verification-summary-card summary-pending">
            <span className="summary-dot" />
            <div>
              <strong>{counts.pending}</strong>
              <span>Pending</span>
            </div>
          </div>

          <div className="verification-summary-card summary-unavailable">
            <span className="summary-dot" />
            <div>
              <strong>{counts.unavailable}</strong>
              <span>Unavailable</span>
            </div>
          </div>
        </div>

        <div className="verification-disclaimer">
          <ShieldCheck size={17} />
          <p>
            These checks provide supporting context, not proof of legitimacy.
            An unavailable or undetected signal does not automatically mean
            that a company is fraudulent.
          </p>
        </div>

        {signals.length === 0 ? (
          <p className="empty-evidence">
            No additional verification signals were returned for this scan.
          </p>
        ) : (
          <div className="verification-groups">
            {categories.map((category) => {
              const categorySignals = signals.filter(
                (item) => item.category === category
              );

              if (categorySignals.length === 0) return null;

              return (
                <div className="verification-group" key={category}>
                  <div className="verification-group-heading">
                    <h4>{category}</h4>
                    <span>
                      {categorySignals.length}{" "}
                      {categorySignals.length === 1 ? "check" : "checks"}
                    </span>
                  </div>

                  <div className="verification-grid">
                    {categorySignals.map((item) => (
                      <article
                        className={`verification-card ${
                          item.signal === "negative_penalty"
                            ? "verification-card-risk"
                            : ""
                        }`}
                        key={item.key}
                      >
                        <div className="verification-card-top">
                          <span className="verification-card-label">
                            VERIFICATION CHECK
                          </span>

                          <span
                            className={`signal-status ${item.status.className}`}
                          >
                            {item.status.label}
                          </span>
                        </div>

                        <h5>{humanizeSignal(item.signal)}</h5>

                        <p className="verification-description">
                          {item.explanation}
                        </p>

                        <div className="verification-result">
                          <span>Observed result</span>
                          <strong>
                            {humanizeSignalValue(item.value)}
                          </strong>
                        </div>

                        <div className="verification-card-footer">
                          {item.score !== undefined && (
                            <div>
                              <span>Score contribution</span>
                              <strong>{formatValue(item.score)}</strong>
                            </div>
                          )}

                          {item.confidence !== undefined && (
                            <div>
                              <span>Signal confidence</span>
                              <strong>{formatValue(item.confidence)}</strong>
                            </div>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </>
    );
  })()}
</section>


      {result.suggested_templates.length > 0 && (
        <section className="result-panel">
          <div className="result-panel-heading">
            <Sparkles size={19} />
            <h3>Suggested templates</h3>
          </div>
          {result.suggested_templates.map((template, index) => (
            <pre className="template-output" key={index}>
              {JSON.stringify(template, null, 2)}
            </pre>
          ))}
        </section>
      )}
    </section>
  );
}

function ActivityIcon() {
  return <ScanSearch size={18} />;
}

export default function Analyzer() {
  const [text, setText] = useState("");
  const [platform, setPlatform] = useState("LinkedIn");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [submittedText, setSubmittedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const cleanedText = text.trim();

    if (cleanedText.length < 20) {
      setError("Please enter at least 20 characters of job-related text.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await analyzeJob({
        text: cleanedText,
        platform: platform || null,
        requester_id: "web-demo",
        save_report: true,
      });

      setResult(response);
      setSubmittedText(cleanedText);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while analyzing the offer."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setText("");
    setResult(null);
    setSubmittedText("");
    setError("");
  }

  return (
    <div className="analyzer-page">
      <div className="analyzer-page-header">
        <div>
          <p className="analyzer-eyebrow">INVESTIGATION WORKSPACE / 01</p>
          <h1>Job Offer Analyzer</h1>
          <p className="analyzer-muted">
            Investigate suspicious recruitment messages before trusting an
            opportunity.
          </p>
        </div>

        <div className="analyzer-ready">
          <span />
          READY TO SCAN
        </div>
      </div>

      <form onSubmit={handleAnalyze}>
        <div className="analyzer-workspace">
          <section className="input-panel">
            <div className="panel-heading">
              <div>
                <span className="step-number">01</span>
                <h2>Job offer input</h2>
              </div>
              <ClipboardPaste size={20} />
            </div>

            <p className="analyzer-muted">
              Paste the job description, recruiter message or offer letter.
            </p>

            <textarea
              className="job-textarea"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Paste the recruitment message here...

Include the company name, job description, salary, recruiter contact details and any payment requests if available."
              rows={13}
              required
            />

            <div className="textarea-footer">
              <span>{text.length.toLocaleString()} characters</span>
              <span>Text analysis</span>
            </div>

            <div className="text-actions">
              <button
                type="button"
                className="text-action"
                onClick={() => {
                  setText(SAMPLE_TEXT);
                  setError("");
                  setResult(null);
                }}
              >
                <FileSearch size={15} />
                Load sample
              </button>

              <button
                type="button"
                className="text-action"
                onClick={handleClear}
              >
                <RotateCcw size={15} />
                Clear
              </button>
            </div>
          </section>

          <aside className="configuration-panel">
            <div className="panel-heading">
              <div>
                <span className="step-number">02</span>
                <h2>Source details</h2>
              </div>
              <ShieldCheck size={20} />
            </div>

            <label className="field-label" htmlFor="platform">
              SOURCE PLATFORM
            </label>

            <select
              id="platform"
              className="platform-select"
              value={platform}
              onChange={(event) => setPlatform(event.target.value)}
            >
              <option value="LinkedIn">LinkedIn</option>
              <option value="Naukri">Naukri</option>
              <option value="Indeed">Indeed</option>
              <option value="Company Website">Company Website</option>
              <option value="Email">Email</option>
              <option value="WhatsApp">WhatsApp</option>
              <option value="Other">Other</option>
            </select>

            <div className="configuration-divider" />

            <span className="field-label">ANALYSIS PIPELINE</span>

            <div className="pipeline-item">
              <div className="pipeline-icon">
                <BrainCircuit size={18} />
              </div>
              <div>
                <strong>ML classification</strong>
                <small>Scam probability prediction</small>
              </div>
              <CheckCircle2 size={16} />
            </div>

            <div className="pipeline-item">
              <div className="pipeline-icon">
                <ListChecks size={18} />
              </div>
              <div>
                <strong>Rule engine</strong>
                <small>Suspicious pattern detection</small>
              </div>
              <CheckCircle2 size={16} />
            </div>

            <div className="pipeline-item">
              <div className="pipeline-icon">
                <ShieldCheck size={18} />
              </div>
              <div>
                <strong>Risk assessment</strong>
                <small>Hybrid score and classification</small>
              </div>
              <CheckCircle2 size={16} />
            </div>

            <div className="configuration-divider" />

            <div className="privacy-note">
              <ShieldCheck size={17} />
              <p>
                This scan is submitted with report saving disabled. External
                enrichment checks may still run.
              </p>
            </div>

            <button
              type="submit"
              className="analyze-button"
              disabled={loading || !text.trim()}
            >
              {loading ? (
                <>
                  <LoaderCircle className="spin" size={18} />
                  Analyzing offer...
                </>
              ) : (
                <>
                  <ScanSearch size={19} />
                  Analyze job offer
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </aside>
        </div>
      </form>

      {error && (
        <div className="analyzer-error" role="alert">
          <AlertCircle size={19} />
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="analysis-loading" role="status">
          <LoaderCircle className="spin" size={25} />
          <div>
            <strong>Investigating job offer</strong>
            <p>
              Running classification, rule detection and available enrichment
              checks. This may take a little while.
            </p>
          </div>
        </div>
      )}

      {result && (
        <AnalysisResults result={result} submittedText={submittedText} />
      )}
    </div>
  );
}

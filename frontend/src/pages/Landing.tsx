import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  FileSearch,
  Gauge,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import "./Landing.css";

function RiskPreview() {
  return (
    <div className="landing-risk-preview">
      <div className="preview-heading">
        <span className="preview-kicker">DEMONSTRATION DATA</span>
        <span className="preview-status">
          <span className="demo-dot" />
          Example result
        </span>
      </div>
      <div className="preview-message">
        <span>“Congratulations! Pay a refundable fee to secure your role…”</span>
        <span className="preview-highlight">refundable fee</span>
      </div>
      <div className="preview-result">
        <div className="risk-score">
          <strong>86</strong>
          <span>/100 risk score</span>
        </div>
        <span className="risk-pill">High risk</span>
      </div>
      <div className="preview-reasons">
        <span><ShieldAlert size={14} /> Payment request</span>
        <span><ShieldAlert size={14} /> Urgency language</span>
        <span><CheckCircle2 size={14} /> Explainable result</span>
      </div>
      <p className="preview-disclaimer">
        This is a fictional example for illustration. Your results are generated
        after you submit a posting.
      </p>
    </div>
  );
}

function Landing() {
  return (
    <div className="landing-page landing-signal">
      <nav className="landing-nav">
        <a className="landing-brand" href="/">
          <span className="landing-brand-icon"><ShieldCheck size={20} /></span>
          <span>Job Scam <strong>Radar</strong></span>
        </a>
        <div className="landing-nav-links">
          <a href="/dashboard">Dashboard</a>
          <a href="/analyzer">Analyzer</a>
          <a href="/history">History</a>
          <a className="landing-nav-scroll-link" href="#how-it-works">How it works</a>
          <a className="landing-nav-scroll-link" href="#why-radar">Why Radar</a>
          <a className="landing-nav-cta" href="/analyzer">Analyze a posting <ArrowRight size={15} /></a>
        </div>
      </nav>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <p className="eyebrow"><Sparkles size={14} /> SAFER OPPORTUNITIES START HERE</p>
            <h1>Pause before you <em>proceed.</em></h1>
            <p className="landing-lede">
              Job Scam Radar helps you spot suspicious recruitment messages with
              transparent signals, not black-box guesses.
            </p>
            <div className="landing-actions">
              <a className="primary-action" href="/analyzer">Check a job posting <ArrowRight size={17} /></a>
              <a className="secondary-action" href="#how-it-works">See how it works <ChevronDown size={16} /></a>
            </div>
            <div className="landing-proof">
              <span><CheckCircle2 size={15} /> Free to use</span>
              <span><CheckCircle2 size={15} /> Explainable results</span>
              <span><CheckCircle2 size={15} /> No account required</span>
            </div>
          </div>
          <div className="landing-hero-art">
            <div className="art-glow" />
            <div className="art-orbit orbit-one" />
            <div className="art-orbit orbit-two" />
            <div className="art-shield"><ShieldCheck size={76} strokeWidth={1.4} /></div>
            <div className="art-float float-top"><Gauge size={16} /><span>Hybrid signal</span><strong>94%</strong></div>
            <div className="art-float float-bottom"><FileSearch size={16} /><span>3 red flags found</span></div>
            <div className="art-caption">Trust the signal.<br /><strong>Verify the source.</strong></div>
          </div>
        </section>

        <section className="landing-preview-section" id="why-radar">
          <div className="section-intro">
            <p className="eyebrow">A CLEARER WAY TO CHECK</p>
            <h2>Every result comes with a reason.</h2>
            <p>Combine detection rules, model signals, and supporting evidence before you share personal information.</p>
          </div>
          <RiskPreview />
        </section>

        <section className="landing-steps" id="how-it-works">
          <div className="step-card"><span>01</span><FileSearch size={20} /><h3>Paste the message</h3><p>Bring a job post, recruiter message, or internship offer.</p></div>
          <div className="step-card"><span>02</span><Gauge size={20} /><h3>Read the signals</h3><p>See the risk score, highlighted text, and supporting checks.</p></div>
          <div className="step-card"><span>03</span><ShieldCheck size={20} /><h3>Verify with confidence</h3><p>Use practical next steps before you pay or share sensitive details.</p></div>
        </section>
      </main>

      <footer className="landing-footer">
        <span>Job Scam Radar</span>
        <span>Automated indicators are not proof. Verify through official channels.</span>
      </footer>
    </div>
  );
}

export default Landing;

# Capstone Project Document
## Title
**Job Scam Radar**  
**An Explainable Job/Internship Scam Risk Detector with Community Reports, Duplicate Detection, and Alerts**

---

## 1. Problem Statement (Clear & Precise)
Job seekers—especially students—often receive job/internship offers through WhatsApp/Telegram/Instagram, emails, or posts that are sometimes fraudulent. These scams typically:
- demand **fees** (registration/training/certificate/deposit),
- request **sensitive personal/banking details** early (Aadhaar/PAN/OTP/bank account),
- use **unofficial contact channels** and suspicious links,
- repeatedly repost the same scam using slightly modified text.

There is no single platform that provides:
1) an immediate **risk assessment** of a job message,  
2) a **transparent explanation** of red flags,  
3) a **community-driven database** of reported scam indicators (phone/email/domain/UPI/handles),  
4) automatic **duplicate detection** to connect repeated scams,  
5) **alerts** to warn users when new scams match their interests,  
6) a **hybrid and confidence-aware scoring workflow** that combines deterministic rules with simple ML and retrieval evidence.

---

## 2. Project Goal
Build a full-stack software system that:
- analyzes job/internship posts and recruiter messages to produce a **Risk Score + Explainable Red Flags**,
- combines **Rule Engine + Simple ML** (without BERT/LLMs) for robust and interpretable scoring,
- enables users to **report** suspicious listings with evidence,
- detects **duplicate/near-duplicate** scam reports automatically,
- maintains an **entity reputation database** that updates with each report/moderation action,
- allows users to **subscribe** to alerts (keywords/categories/platforms) and get notified when matching scams are reported or confirmed,
- provides a **moderation workflow** to prevent misuse and ensure data quality.

---

## 3. Target Users & Roles
### 3.1 Normal User (Job seeker / Student)
- Paste message and get risk score + confidence + explanation
- See retrieval-based evidence (“matched similar reports”, “seen N times”)
- Search known indicators (phone/email/domain)
- Submit reports with evidence
- Subscribe to alerts

### 3.2 Moderator (Trusted reviewer: placement cell / volunteers)
- Review incoming reports
- Confirm scam / mark duplicate / reject spam
- Maintain data quality (audit trail)

### 3.3 Admin
- Manage moderators
- Configure thresholds/weights
- View analytics

---

## 4. Key Features (MVP + Extensions)

### 4.1 Analyzer (Explainable Hybrid Risk Scoring)
**Inputs**
- Job post text (required)
- Optional source platform (WhatsApp/Telegram/Instagram/Email/LinkedIn)

**Scoring Approach (No BERT/LLMs)**
1. **Rule Engine Score (0–100)**  
   Triggered by interpretable patterns:
   - fee/payment demand in hiring context
   - early request for sensitive information
   - urgency/pressure language
   - suspicious contact/channel mismatch
   - suspicious links/unofficial domain patterns

2. **Simple ML Probability**  
   - Model: **Logistic Regression** (baseline) or **Random Forest** (comparison model)
   - Library: **scikit-learn**
   - Output: probability that message is scam (`P_scam`)

3. **Final Hybrid Score**  
   Example weighted fusion:  
   `Final Score = 0.4 × Rule Score + 0.6 × ML Score`  
   where `ML Score = 100 × P_scam`

   Example:  
   - Rule Score = 38  
   - ML Probability = 72% → ML Score = 72  
   - Final Score = 0.4×38 + 0.6×72 = 58.4

4. **Risk Band Mapping (example)**
   - 0–34: Low
   - 35–64: Medium
   - 65–100: High

5. **Confidence Score**
   - Output format: `Risk: High | Confidence: 87%`
   - Confidence derived from model certainty + rule agreement + retrieval strength (design configurable)

**Outputs**
- Risk level: Low/Medium/High
- Final score (0–100)
- Confidence score (%)
- “Why?” reasons (top triggered red flags)
- Highlighted text spans that triggered rules
- Retrieval-based evidence (“Seen before?” + matched report context)

---

### 4.2 Community Reports + Evidence
- Report form to submit suspicious messages
- Evidence upload (screenshots)
- Report status lifecycle:
  - Unverified → Investigating → Confirmed Scam / Likely Safe / Duplicate
- Each accepted report updates downstream systems:
  - entity reputation counters
  - similarity index
  - subscriber alert matching

---

### 4.3 Entity Extraction + Reputation Signals
From text and reports, extract and normalize:
- phone numbers
- emails
- URLs/domains
- social handles (Telegram/Instagram)
- (optional India) UPI IDs

Reputation signals:
- “Entity appears in X reports”
- “Entity linked to confirmed scam”
- Risk increases if entities match known scam indicators

---

### 4.4 Entity Reputation Database
Maintain dedicated reputation views/tables for high-value entities and update them with each new report and moderation decision.

**Examples**
- `phone_reputation` → phone, total_reports, confirmed_count, risk_score
- `email_reputation` → email, total_reports, confirmed_count, risk_score
- `domain_reputation` → domain, total_reports, confirmed_count, risk_score

**Typical fields**
- Entity value (normalized)
- Reports count
- Confirmed scam count
- Derived entity risk score (0–100)
- Last seen timestamp

This enables fast lookups such as:
- “Same phone number seen 8 times”
- “Domain linked to 3 confirmed scam reports”

---

### 4.5 Duplicate / Similar Scam Detection
Purpose: prevent repeated scams from appearing as unrelated reports.

**Duplicate detection methods**
1. **Entity-based matching (high confidence)**
   - Same phone/email/domain/UPI → strong duplicate candidate
2. **Text similarity (near-duplicate)**
   - TF-IDF + cosine similarity against recent reports
   - Suggest top-K similar reports with similarity score

Moderator can merge duplicates into a canonical report:
- consolidated evidence
- aggregated counts (“reported by N users”)

---

### 4.6 Retrieval-Based Evidence in Results
Instead of only showing a generic output like “High Risk”, the analyzer returns evidence-backed context such as:
- “Matched 3 similar reports”
- “Same phone number seen 8 times”
- “Previously confirmed scam in 2 reports”
- “Domain flagged in community reports”

This improves user trust through transparent, retrieval-grounded explanation.

---

### 4.7 Alerts / Subscriptions
Users can subscribe to:
- keywords (e.g., “work from home”, “data entry”, “offer letter”)
- category (fee scam, impersonation, data harvesting)
- platform (WhatsApp/Instagram/Telegram)
- (optional) entity watchlist (phone/email/domain)

Trigger alerts when:
- a new report matches subscription filters
- a report is upgraded to **Confirmed Scam**
- a watched entity appears again

Notification channels:
- In-app notifications (MVP)
- Optional email notifications

---

### 4.8 Moderator & Admin Dashboard
Moderator:
- triage queue
- duplicate suggestions
- confirm/duplicate/reject actions
- audit log of actions

Admin:
- manage roles
- configure scoring thresholds/weights
- analytics dashboard

---

### 4.9 Better Analytics Dashboard 
Use charting libraries such as **Chart.js** or **Recharts** for interpretable monitoring.

**Core analytics examples**
- Reports per month (trend line/bar)
- Scam categories distribution
- Most frequently reported phone numbers
- Most frequently reported domains
- Platform-wise suspicious report share
- Confirmed-vs-unverified ratio over time

---

## 5. System Architecture 
### 5.1 Components
1. **Web Frontend**
   - analyze page, report form, search, alerts, dashboards
2. **Backend API**
   - authentication, reports, evidence, moderation, subscriptions
3. **Analyzer Service**
   - rule engine + simple ML inference + final score fusion + confidence estimation
4. **Retrieval Service**
   - entity reputation lookup + similar report retrieval
5. **Database (PostgreSQL)**
   - users, reports, entities, reputation aggregates, subscriptions, moderation actions
6. **File Storage**
   - evidence screenshots (e.g., S3/Cloudinary/local dev)
7. **Background Jobs**
   - similarity index refresh
   - entity reputation aggregation updates
   - alert delivery
   - periodic cleanup/tasks

---

## 6. Data Model (Conceptual Tables)
- `users` (role: user/mod/admin)
- `reports` (text, company_name, platform, category, status, created_by, timestamps)
- `evidence_files` (report_id, file_url, file_hash, uploaded_by)
- `entities` (type: phone/email/domain/handle/upi, normalized_value)
- `report_entities` (report_id, entity_id)
- `similarity_links` (report_id, similar_report_id, score, method)
- `subscriptions` (user_id, filters JSON)
- `notifications` (user_id, title, body, link, read_status)
- `moderation_actions` (report_id, moderator_id, action, notes, timestamp)

**Reputation/Aggregate tables**
- `phone_reputation` (phone, total_reports, confirmed_count, risk_score, last_seen_at)
- `email_reputation` (email, total_reports, confirmed_count, risk_score, last_seen_at)
- `domain_reputation` (domain, total_reports, confirmed_count, risk_score, last_seen_at)

---

## 7. Non-Functional Requirements 
### 7.1 Security
- rate limiting on report creation
- file upload validation (type/size)
- audit logs for moderator actions
- input sanitization (XSS-safe rendering)

### 7.2 Privacy
- user warning: do not upload Aadhaar/PAN/OTP/bank statements
- evidence access control
- retention policy for evidence (optional)

### 7.3 Reliability & Maintainability
- structured logs
- clear separation: analyzer service, retrieval service, report service, notification service
- tests for:
  - rule engine correctness
  - ML inference pipeline
  - entity extraction/normalization
  - similarity retrieval quality

---

## 8. Evaluation Plan (Proof it works)
1. Create a labeled dataset (scam/legit/uncertain) of ~200–500 samples.
2. Measure:
   - precision/recall/F1 for “High risk” predictions
   - calibration quality of confidence score
   - duplicate detection accuracy (top-K duplicate suggestions)
   - retrieval usefulness (evidence match quality)
3. Compare:
   - rule-only vs ML-only vs hybrid scoring
4. Usability feedback:
   - time saved in decision-making
   - clarity of explanations (“why flagged?”)
   - trust improvement from evidence-backed outputs

---

## 9. Deliverables (What we will submit)
- Working web application + API
- Database schema + deployment guide
- Admin/moderator dashboard
- Documentation + final report:
  - architecture, hybrid scoring design, rule set, evaluation metrics, limitations
- Demo dataset (anonymized)
- Presentation slides

---

## 10. Limitations 
- Provides risk assessment, not legal confirmation.
- False positives/negatives exist; moderated confirmation is required for “confirmed scam”.
- Community reporting can be abused; mitigated via moderation, rate limits, and audit logs.
- Confidence score represents system certainty, not absolute truth.
- Rule/ML weights may require periodic tuning as scam patterns evolve.

---

## 11. Summary
Job Scam Radar is a full-stack platform that combines explainable rule-based detection, simple ML-based probability scoring, retrieval-backed evidence, community reporting with evidence, duplicate detection using entity and text similarity, entity reputation tracking, and alert subscriptions to proactively warn students about repeating job scams. It is not merely a classifier; it is a complete workflow system with moderation, reputation signals, search, analytics, and evaluation.

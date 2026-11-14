# Job Scam Radar

**An explainable job-posting risk analysis platform**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://job-scam-radar.vercel.app/)
[![API](https://img.shields.io/badge/API-Render-blue)](https://job-scam-radar-api.onrender.com/docs)

Job Scam Radar analyzes job postings to identify potentially fraudulent recruitment activity. It combines a rule-based detection engine with a machine-learning model and supporting company/recruitment signals to produce an explainable risk assessment.

> **Disclaimer:** Job Scam Radar provides automated risk indicators, not a guarantee that a job posting or employer is legitimate or fraudulent. Results should be independently verified.

## Live application

| Component | URL |
|---|---|
| Frontend | https://job-scam-radar.vercel.app/ |
| Backend API | https://job-scam-radar-api.onrender.com |
| API documentation | https://job-scam-radar-api.onrender.com/docs |
| Health check | https://job-scam-radar-api.onrender.com/health |

## Features

- **Hybrid risk analysis:** Combines rule-based detection and machine-learning predictions.
- **Detection explanations:** Identifies suspicious text and displays triggered detection rules.
- **Recruitment risk indicators:** Checks for payment requests, sensitive information requests, urgency and other suspicious patterns.
- **Company and recruitment verification signals:** Displays available evidence and distinguishes detected, not detected, pending and unavailable checks.
- **Hiring-intent assessment:** Provides supporting signals about recruitment activity.
- **Scan history:** Saves previous investigations and allows users to revisit their results.
- **Dashboard:** Displays investigation statistics and risk summaries.

## Screenshots

Add screenshots to `docs/screenshots/` using the filenames below. These image files are not included in this README commit yet.

### Application dashboard

![Dashboard](docs/screenshots/dashboard.png)

### Legitimate job analysis

![Legitimate job analysis](docs/screenshots/legitimate-analysis.png)

### Scam job analysis

![Scam job analysis](docs/screenshots/scam-analysis.png)

### Suspicious job analysis

![Suspicious job analysis](docs/screenshots/suspicious-analysis.png)

### Scan history

![Scan history](docs/screenshots/history.png)

## System architecture

```text
                  User
                   |
                   v
          React + TypeScript UI
                 (Vercel)
                   |
                   | HTTP API
                   v
             FastAPI Backend
                 (Render)
                   |
          +--------+---------+
          |                  |
          v                  v
     Rule Engine       ML Prediction
          |                  |
          +--------+---------+
                   |
                   v
          Hybrid Risk Assessment
                   |
          +--------+---------+
          |                  |
          v                  v
   Verification Signals   SQLAlchemy
                              |
                              v
                       Neon PostgreSQL
```

The frontend communicates with the FastAPI backend. The backend analyzes submitted job-posting text, combines rule-engine and ML signals, generates an assessment and stores scan records in the database.

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Machine learning | scikit-learn, joblib |
| Database | SQLAlchemy, SQLite (local default), PostgreSQL (production) |
| Deployment | Vercel, Render, Neon |
| Testing | pytest |
| API documentation | OpenAPI, Swagger UI |

## Repository structure

```text
Capstone/
├── backend/
│   ├── analyzer/
│   ├── enrichment/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── data/
├── infra/
├── scripts/
├── tests/
├── docs/
│   └── screenshots/
├── docker-compose.yml
├── openapi.yaml
├── Capstone_Project_Documentation.md
└── README.md
```

## Run locally

### Prerequisites

- Python (use a version supported by the dependencies in `backend/requirements.txt`)
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/suryatej118/Capstone.git
cd Capstone
```

### 2. Set up the backend

Create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

Start the backend from the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

The API will be available at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

The backend uses a local SQLite database by default when `DATABASE_URL` is not configured.

### 3. Set up the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite development URL, normally http://localhost:5173.

For local development, the Vite proxy forwards API requests to the backend running on port 8000.

### 4. Environment variables

Create environment files locally when needed. Never commit actual credentials or production secrets.

**Backend `.env` example:**

```env
# Optional: omit DATABASE_URL to use the local SQLite default.
DATABASE_URL=

# Local frontend origin
FRONTEND_URL=http://localhost:5173
```

**Frontend `.env` example:**

```env
# Leave empty for local development when using the Vite proxy.
VITE_API_BASE_URL=
```

For production, configure the frontend API URL and backend database connection through the respective hosting providers' environment-variable settings.

Optional third-party integrations may require API credentials. Their absence can make individual enrichment checks unavailable without necessarily preventing the core analysis.

## API

The primary analysis endpoint is:

```http
POST /analyze
```

It accepts job-posting text and optional analysis parameters and returns a risk assessment with supporting evidence.

Other application endpoints include:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend health check |
| `POST /analyze` | Analyze a job posting |
| `GET /scans` | Retrieve saved investigations |
| `GET /scans/{scan_id}` | Retrieve an individual investigation |
| `GET /dashboard/stats` | Retrieve dashboard statistics |

For request schemas and response details, visit the [interactive Swagger documentation](https://job-scam-radar-api.onrender.com/docs).

## Detection methodology

The application uses two primary analysis components:

1. **Rule-based engine:** Identifies suspicious patterns such as recruitment fees, requests for sensitive information, UPI/payment requests, urgency language and unrealistic job promises.
2. **Machine-learning model:** Estimates the probability that a submitted posting belongs to the scam class.

The outputs are combined into a hybrid assessment. The application also applies its risk-classification policy and can account for high-severity indicators.

Company and recruitment verification signals provide additional context. A missing or unavailable signal is not automatically treated as evidence of fraud.

## Testing and production validation

### Automated tests

The backend test suite previously completed with:

```text
136 passed
```

### Public production smoke tests

The following three fictional postings were submitted to the deployed application:

| Scenario | Observed risk | Hybrid score | Observation |
|---|---:|---:|---|
| Legitimate-looking posting | Low | 4.6/100 | No detection rules triggered |
| Obvious recruitment scam | High | 38.4/100 | Five detection rules triggered |
| Suspicious mixed posting | Low | 3.0/100 | No detection rules triggered; detection gap identified |

The suspicious mixed example included WhatsApp-only recruitment, time pressure and an identity-document request. It was classified as Low risk. This is a known limitation observed during production testing and indicates an area for future improvement.

### Persistence validation

Production history testing confirmed that:

- Four investigation records were visible.
- Records remained available after a page refresh.
- An individual saved investigation could be opened with its full analysis.

## Limitations

- Automated predictions can produce false positives and false negatives.
- A low-risk result does not establish that an employer or job posting is genuine.
- A high-risk result is an indication to investigate, not definitive proof of fraud.
- The confidence indicator is a heuristic indicator, not a calibrated probability.
- External company and recruitment checks may be pending, unavailable or incomplete.
- Company-name matches and candidate website discovery alone do not prove company ownership or legitimacy.
- Model performance depends on the quality, representativeness and labeling of the training data.
- The production smoke tests cover only a small number of examples and are not a comprehensive real-world accuracy evaluation.
- Free hosting services may have resource, availability and cold-start limitations.

## Future improvements

- Improve detection of suspicious recruitment channels and identity-document requests.
- Expand and improve the labeled job-posting dataset.
- Evaluate performance on a larger and more diverse independent test set.
- Improve calibration and explainability of risk predictions.
- Expand reliable company and recruiter verification integrations.
- Improve handling of unavailable enrichment services.

## Deployment

The current public deployment uses:

- **Frontend:** Vercel
- **Backend:** Render
- **Production database:** Neon PostgreSQL

Production credentials and API keys are configured as environment variables and should never be committed to the repository.

## Project

**Job Scam Radar** — Capstone Project

Repository: https://github.com/suryatej118/Capstone

Live demo: https://job-scam-radar.vercel.app/

---

*This project is intended for educational and research purposes. Always verify job offers through independently established official company channels before sharing personal information or making payments.*

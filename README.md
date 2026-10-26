# OutReachIQ: Autonomous AI Career & Opportunity Agent

> Research Prototype & Production-Grade Software Platform

OutReachIQ is an autonomous agent system designed around **evidence-grounded career modeling**, **factuality**, **explainability**, **uncertainty quantification**, and **user-controlled autonomy**.

---

## Architecture Overview

```
OutReachIQ/
├── frontend/                        # Angular 22 + TypeScript + SCSS
│   ├── src/app/
│   │   ├── core/                    # Models (Profile, Resume, Opportunity, Company, Discovery, Provider),
│   │   │                            # Services (Auth, Profile, Resume, Intelligence, Opportunity), Guards & Interceptors
│   │   ├── shared/                  # Reusable Navigation, Audit Cards, UI Widgets
│   │   └── features/
│   │       ├── auth/                # Register & Login with JWT session management
│   │       ├── dashboard/           # Profile completion, resume inventory, preferences, next steps
│   │       ├── profile/             # Multi-tab grounded profile editor (Basic, Preferences, Skills, Work, Projects, Edu)
│   │       ├── resumes/             # Multi-resume upload (PDF/DOCX), PyMuPDF parsing, verified skill citations
│   │       ├── opportunities/       # Stage 2: Opportunity Intelligence Engine UI (Filters, Grounded Cards, Research Modal)
│   │       └── activity/            # Stage 2: Agent Activity & Telemetry Audit Trail (Provider fleet status, run logs)
├── backend/                         # FastAPI + Pydantic v2 + SQLAlchemy 2.0 + LangGraph
│   ├── app/
│   │   ├── core/                    # App settings (Pydantic Settings) & bcrypt / JWT security
│   │   ├── db/                      # Session management & declarative Base
│   │   ├── models/                  # User, Profile, Resume, Skill, Education, Project, Experience, Preferences,
│   │   │                            # Company, Contact, Job, JobRequirement, Opportunity, Source, Evidence, AgentRun
│   │   ├── schemas/                 # Strongly-typed Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── providers/           # Search provider adapters (Tavily, Exa, JSearch, SerpApi, Adzuna, Jooble, Registry)
│   │   │   ├── opportunity_normalizer.py   # Canonicalization, remote detection, skill taxonomy
│   │   │   ├── opportunity_deduplicator.py # Fuzzy cross-provider deduplication & citation merging
│   │   │   ├── company_research_service.py # Public expansion signal evaluation & strategic alignment
│   │   │   ├── matching_service.py         # Heuristic scoring, critical checks, recommended action
│   │   │   ├── opportunity_orchestrator.py # Multi-provider dispatch, async background runs, run tracking
│   │   │   └── profile_intelligence.py     # Deterministic and LLM profile analysis
│   │   ├── agents/                  # LangGraph OpportunityAgent & LLM provider abstraction
│   │   ├── api/                     # REST API routers (/auth, /profile, /resumes, /opportunities, /providers)
│   │   └── utils/                   # Safe file persistence & validation
│   ├── alembic/                     # Database migrations (Stage 1 initial schema + Stage 2 opportunity engine)
│   └── tests/                       # Pytest test suite (110 passing tests across core algorithms, safety & security)
├── .env.example                     # Environment template (configured for all providers)
└── README.md
```

---

## Core Guarantees & Philosophy

1. **Zero Hallucination Policy:** The system never invents skills, experiences, credentials, or job openings. Missing information remains explicitly unknown.
2. **Tri-Tier Skill Segregation:**
   - **`VERIFIED`**: Explicitly stated in candidate input or parsed with direct textual citations from uploaded resumes.
   - **`INFERRED`**: Conservatively inferred based on strong evidence with lower confidence and transparent rationale. Never asserted as a factual direct claim.
   - **`UNVERIFIED`**: Cannot be used in outbound decisions or claims.
3. **Multi-Source Opportunity Discovery:**
   - **`ADVERTISED`**: Real job openings discovered across search engines and aggregators with verified application URLs, company, location, requirements, and discovery provenance.
   - **`EMERGING`**: Companies without public job postings demonstrating verified hiring signals, recent funding rounds, new technical initiatives, or public expansion announcements.
   - **`STRATEGIC`**: Companies with exceptionally high technical alignment to the candidate's unique verified skills, ideal for proactive outreach.
4. **Resilient Provider Architecture:**
   - Pluggable adapters for Tavily, Exa, JSearch, SerpApi, Adzuna, and Jooble.
   - Independent timeouts, bounded retries (exponential backoff), circuit health checks, and in-memory TTL caching.
   - If a provider fails or is unconfigured, the engine continues gracefully with the remaining providers and records partial status with full audit disclosure.
5. **Autonomy Guardrails:** Stage 2 strictly analyzes and presents opportunities. It will never send automated emails, generate external outreach, or contact recruiters without explicit user approval in later stages.

---

## Quickstart Commands

### 1. Backend Setup & Run

```bash
cd backend

# Create virtual environment and activate
python -m venv venv
.\venv\Scripts\Activate.ps1    # On Windows
# source venv/bin/activate     # On Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run migrations (applies Stage 1 & Stage 2 tables)
alembic upgrade head

# Run full test suite
pytest -v

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
- Interactive API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Provider Fleet Health: [http://localhost:8000/api/v1/providers/health](http://localhost:8000/api/v1/providers/health)
- System Health: [http://localhost:8000/health](http://localhost:8000/health)

### 2. Frontend Setup & Run

```bash
cd frontend

# Install packages
npm install

# Build verification
npm run build

# Start Angular development server
npm start
```
- Application Web UI: [http://localhost:4200](http://localhost:4200)

---

## External Search Provider Configuration

OutReachIQ functions immediately without external API keys in local development mode. If no keys are provided, the system gracefully handles the run, reports unconfigured providers in the audit log, and preserves all features.

To enable live internet searches across providers, configure the following keys in `backend/.env`:

| Provider | Environment Variable | Primary Use Case |
| :--- | :--- | :--- |
| **Tavily** | `TAVILY_API_KEY` | Real-time web search for job postings, career pages, expansion signals |
| **Exa** | `EXA_API_KEY` | Neural semantic discovery of companies, product announcements, technical initiatives |
| **JSearch** | `JSEARCH_API_KEY` | Aggregated real-time job listings (LinkedIn, Indeed, Glassdoor via RapidAPI) |
| **SerpApi** | `SERPAPI_API_KEY` | Google Jobs indexed listings and corporate hiring feeds |
| **Adzuna** | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Global programmatic job vacancies |
| **Jooble** | `JOOBLE_API_KEY` | Programmatic job postings API |
| **OpenRouter** | `OPENROUTER_API_KEY` | Unified AI gateway (Claude 3.5 Sonnet / Gemini Flash for grounded outreach) |
| **OpenAI** | `OPENAI_API_KEY` | Direct OpenAI API access (`gpt-4o-mini`) |
| **Google Gemini** | `GEMINI_API_KEY` | Direct Gemini API access (`gemini-1.5-flash`) |
| **Google OAuth** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Gmail integration for idempotent user-approved outreach dispatch |

---

## Security & Production Configuration

- **Zero-Config Development**: OutReachIQ starts in `ENVIRONMENT=development` mode with sensible defaults for instant evaluation.
- **Production Hardening**: Setting `ENVIRONMENT=production` enforces strict fail-fast validation requiring dedicated, non-default secrets of at least 32 characters for `JWT_SECRET` and `GMAIL_TOKEN_ENCRYPTION_KEY`:
  ```bash
  # Generate cryptographically secure production keys
  python -c "import secrets; print(secrets.token_hex(32))"
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- **Secrets Isolation**: Secrets must be stored in `backend/.env` (which is excluded from Git via `.gitignore`) or injected via your deployment environment's secret manager.

---

## Database Configuration

- By default, OutReachIQ runs on a local SQLite database file (`sqlite:///./outreachiq.db`) for immediate zero-dependency evaluation.
- For production PostgreSQL, set `DATABASE_URL` in `backend/.env`:
  ```env
  DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/outreachiq
  ```
  Then run `alembic upgrade head`.

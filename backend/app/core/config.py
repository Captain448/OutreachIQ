import os
from pathlib import Path
from typing import List, Optional, Set
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory anchored to the backend application folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Known development placeholder secrets that must never be permitted in production
KNOWN_INSECURE_JWT_SECRETS: Set[str] = {
    "outreachiq_dev_secret_key_change_in_production_2026_xyz",
    "development-secret-key-change-in-production",
    "secret",
    "secretkey",
    "changeme",
    "your-secret-key",
}

KNOWN_INSECURE_ENCRYPTION_KEYS: Set[str] = {
    "outreachiq_default_dev_encryption_key_2026_xyz",
    "development-encryption-key-change-in-production",
    "secret",
    "encryption_key",
    "changeme",
    "your-encryption-key",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "OutReachIQ"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "sqlite:///./outreachiq.db"
    
    # Security
    JWT_SECRET: str = "outreachiq_dev_secret_key_change_in_production_2026_xyz"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = "openai"  # openai, gemini, openrouter
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # Primary Search & Research Providers
    TAVILY_API_KEY: Optional[str] = None
    EXA_API_KEY: Optional[str] = None
    
    # Educational & Learning Video Providers (Phase 3)
    YOUTUBE_API_KEY: Optional[str] = None
    YOUTUBE_DAILY_QUOTA: int = 25  # YouTube Data API free allowance is 10,000 units/day (search = 100 units -> safe 25 calls/day = 2,500 units)
    
    # Multi-Provider Job Discovery Integrations (Independently Configurable)
    JSEARCH_API_KEY: Optional[str] = None    # RapidAPI JSearch
    SERPAPI_API_KEY: Optional[str] = None    # SerpApi Google Jobs
    ADZUNA_APP_ID: Optional[str] = None      # Adzuna App ID
    ADZUNA_APP_KEY: Optional[str] = None     # Adzuna App Key
    JOOBLE_API_KEY: Optional[str] = None     # Jooble API Key
    
    # Opportunity Discovery Engine Settings
    DISCOVERY_TIMEOUT_SECONDS: int = 15
    DISCOVERY_MAX_RETRIES: int = 2
    DISCOVERY_CACHE_TTL_SECONDS: int = 3600
    DISCOVERY_DEFAULT_LIMIT: int = 20
    DISCOVERY_MAX_LIMIT: int = 50

    # Two-Tier Provider Architecture & Quality Thresholds
    DISCOVERY_TIER1_PROVIDERS: List[str] = ["tavily", "exa"]
    DISCOVERY_TIER2_PROVIDERS: List[str] = ["remotive", "jsearch", "serpapi"]
    DISCOVERY_MIN_RELEVANT_RESULTS: int = 5
    DISCOVERY_RATE_LIMIT_COOLDOWN_SECONDS: int = 60
    ENABLE_EVALUATION_PROVIDERS: bool = False  # Disabled by default under permanent zero-cost policy (disables 14-day trials or limited sandboxes)

    # Daily Free-Tier Safety Caps (Local quota enforcement preventing overage charges or exhaustion)
    DISCOVERY_DAILY_QUOTA_TAVILY: int = 50       # 1,000 queries/month free -> ~50/day safe cap
    DISCOVERY_DAILY_QUOTA_EXA: int = 50          # 1,000 queries/month free -> ~50/day safe cap
    DISCOVERY_DAILY_QUOTA_REMOTIVE: int = 100    # Permanent free public feed (no API key needed)
    DISCOVERY_DAILY_QUOTA_ADZUNA: int = 100      # 250-500 requests/day developer plan
    DISCOVERY_DAILY_QUOTA_JOOBLE: int = 100      # 500 requests/day partner plan
    DISCOVERY_DAILY_QUOTA_JSEARCH: int = 10      # 50 requests/month basic plan on RapidAPI (Strict Cap!)
    DISCOVERY_DAILY_QUOTA_SERPAPI: int = 10      # 100 requests/month free plan
    
    # Heuristic Matching Thresholds (Configurable)
    MATCH_CONTACT_NOW_THRESHOLD: float = 0.70
    MATCH_IMPROVE_FIRST_THRESHOLD: float = 0.45
    
    # File Storage
    UPLOAD_DIR: str = "./uploads/resumes"
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB

    # Google OAuth & Gmail Integration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:4200/outreach"
    GMAIL_TOKEN_ENCRYPTION_KEY: str = "outreachiq_default_dev_encryption_key_2026_xyz"
    GMAIL_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/userinfo.email"
    ]
    OUTREACH_DEFAULT_DAILY_LIMIT: int = 15
    OUTREACH_DEFAULT_COOLDOWN_MINUTES: int = 15
    OUTREACH_DUPLICATE_SUPPRESSION_DAYS: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        env_lower = (self.ENVIRONMENT or "").strip().lower()
        if env_lower in ("production", "prod"):
            # 1. Validate JWT_SECRET
            jwt_val = (self.JWT_SECRET or "").strip()
            if not jwt_val:
                raise ValueError(
                    "Production security failure: JWT_SECRET must be configured and non-empty when ENVIRONMENT=production."
                )
            if jwt_val in KNOWN_INSECURE_JWT_SECRETS or "change_in_production" in jwt_val.lower():
                raise ValueError(
                    "Production security failure: JWT_SECRET is set to an insecure development placeholder. "
                    "A secure, randomly generated secret (at least 32 characters) must be supplied in production."
                )
            if len(jwt_val) < 32:
                raise ValueError(
                    "Production security failure: JWT_SECRET must be at least 32 characters long for production security."
                )

            # 2. Validate GMAIL_TOKEN_ENCRYPTION_KEY
            enc_val = (self.GMAIL_TOKEN_ENCRYPTION_KEY or "").strip()
            if not enc_val:
                raise ValueError(
                    "Production security failure: GMAIL_TOKEN_ENCRYPTION_KEY must be configured and non-empty when ENVIRONMENT=production."
                )
            if enc_val in KNOWN_INSECURE_ENCRYPTION_KEYS or "default_dev_encryption_key" in enc_val.lower():
                raise ValueError(
                    "Production security failure: GMAIL_TOKEN_ENCRYPTION_KEY is set to an insecure development placeholder. "
                    "A secure, dedicated key must be supplied in production."
                )
            if len(enc_val) < 32:
                raise ValueError(
                    "Production security failure: GMAIL_TOKEN_ENCRYPTION_KEY must be at least 32 characters long for production security."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def BASE_DIR(self) -> Path:
        return BASE_DIR

    @property
    def sync_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            # Check if this is an in-memory test database
            if ":memory:" in url:
                return url
            # Extract file path after sqlite:///
            raw_path = url[len("sqlite:///"):]
            # Normalize leading ./ or .\
            if raw_path.startswith("./") or raw_path.startswith(".\\"):
                raw_path = raw_path[2:]
            path_obj = Path(raw_path)
            if not path_obj.is_absolute():
                abs_db_path = (BASE_DIR / path_obj).resolve()
                return f"sqlite:///{abs_db_path.as_posix()}"
            return f"sqlite:///{path_obj.resolve().as_posix()}"
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    @property
    def resolved_upload_dir(self) -> Path:
        raw_path = self.UPLOAD_DIR
        if raw_path.startswith("./") or raw_path.startswith(".\\"):
            raw_path = raw_path[2:]
        path_obj = Path(raw_path)
        if not path_obj.is_absolute():
            return (BASE_DIR / path_obj).resolve()
        return path_obj.resolve()


settings = Settings()

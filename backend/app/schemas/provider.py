from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProviderHealthRead(BaseModel):
    provider_name: str
    display_name: str
    is_configured: bool
    status: str              # "active", "disabled", "error", "rate_limited", "quota_exhausted", "disabled_auth_error"
    tier: int = 1
    circuit_status: str = "active"
    daily_requests_used: int = 0
    daily_request_cap: int = 50
    free_tier_info: Optional[str] = None
    cooldown_remaining_seconds: Optional[int] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    results_returned: int = 0
    quota_limit_info: Optional[str] = None
    last_queried: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

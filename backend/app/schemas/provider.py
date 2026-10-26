from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProviderHealthRead(BaseModel):
    provider_name: str
    display_name: str
    is_configured: bool
    status: str              # "active", "disabled", "error", "quota_exceeded"
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    results_returned: int = 0
    quota_limit_info: Optional[str] = None
    last_queried: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

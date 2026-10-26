export interface ProviderHealth {
  provider_name: string;
  display_name: string;
  is_configured: boolean;
  status: 'active' | 'disabled' | 'error' | 'quota_exceeded';
  error_message?: string;
  latency_ms?: number;
  results_returned: number;
  quota_limit_info?: string;
  last_queried?: string;
}

export interface DiscoveryRunRequest {
  target_roles?: string[];
  skills?: string[];
  industries?: string[];
  locations?: string[];
  remote_preference?: string;
  work_arrangement?: string;
  employment_type?: string;
  experience_level?: string;
  opportunity_type?: string;
  limit?: number;
}

export interface DiscoveryRun {
  id: string;
  user_id: string;
  run_type: string;
  status: 'queued' | 'running' | 'completed' | 'partial' | 'failed';
  query_params: Record<string, any>;
  providers_queried: string[];
  providers_succeeded: string[];
  providers_failed: Array<{ provider: string; type?: string; error: string }>;
  results_discovered_count: number;
  results_deduplicated_count: number;
  opportunities_created_count: number;
  execution_time_seconds: number;
  error_summary?: string;
  diagnostics?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

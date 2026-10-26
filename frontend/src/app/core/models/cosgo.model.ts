export type CosgoProgressState = 'RECOMMENDED' | 'PLANNED' | 'IN_PROGRESS' | 'COMPLETED';

export interface PracticalProject {
  title: string;
  description: string;
  overlapping_skills: string[];
  deliverables: string[];
  difficulty_level?: string;
}

export interface LearningResource {
  title: string;
  url: string;
  provider: string;
  is_verified: boolean;
  resource_type: string;
}

export interface TargetOpportunitySummary {
  id: string;
  title: string;
  company_name: string;
  match_score: number;
  primary_url?: string;
}

export interface EffortUncertainty {
  min_hours: number;
  max_hours: number;
  confidence: string;
  notes?: string;
}

export interface CosgoAction {
  id: string;
  run_id: string;
  user_id: string;
  skill_name: string;
  category: string;
  priority_rank: number;
  estimated_hours: number;
  effort_uncertainty_range: EffortUncertainty;
  marginal_coverage_gain: number;
  cumulative_coverage: number;
  opportunities_count: number;
  target_opportunity_ids: string[];
  target_opportunities_summary: TargetOpportunitySummary[];
  prerequisites: string[];
  why_recommended?: string;
  practical_project: PracticalProject;
  learning_resources: LearningResource[];
  progress_state: CosgoProgressState;
  user_notes?: string;
  completed_at?: string;
  created_at: string;
}

export interface CosgoRunDiagnostics {
  excluded_breakdown?: {
    duplicate_listings: number;
    insufficient_requirements: number;
  };
  total_candidate_verified_skills?: number;
  total_candidate_inferred_skills?: number;
  total_distinct_job_skills_found?: number;
  budget_hours_requested?: number;
  budget_hours_used?: number;
  budget_hours_remaining?: number;
  weekly_budget_hours?: number;
  estimated_weeks_to_complete?: number;
}

export interface CosgoRun {
  id: string;
  user_id: string;
  budget_hours: number;
  weekly_budget_hours: number;
  target_roles: string[];
  algorithm_version: string;
  status: string;
  total_opportunities_analyzed: number;
  eligible_opportunities_count: number;
  excluded_opportunities_count: number;
  baseline_coverage: number;
  projected_coverage: number;
  marginal_coverage_increase: number;
  opportunities_at_threshold_baseline: number;
  opportunities_at_threshold_projected: number;
  diagnostics: CosgoRunDiagnostics;
  actions: CosgoAction[];
  created_at: string;
  updated_at: string;
}

export interface CoverageMatrixItem {
  opportunity_id: string;
  job_title: string;
  company_name: string;
  match_score: number;
  role_relevance: number;
  requirements: string[];
  verified_skills: string[];
  inferred_skills: string[];
  actions_covering: string[];
  remaining_gaps: string[];
  baseline_coverage: number;
  projected_coverage: number;
}

export interface CosgoCoverageMatrixResponse {
  run_id: string;
  total_skills_count: number;
  skills_header: string[];
  matrix: CoverageMatrixItem[];
  skill_frequency: Record<string, number>;
}

export interface StrategyBenchmarkMetrics {
  strategy: string;
  selected_skills: string[];
  skills_count: number;
  hours_spent: number;
  final_coverage: number;
  coverage_gain: number;
  coverage_gain_pp?: number;
  coverage_gain_label?: string;
  gain_per_hour: number;
  opportunities_qualifying: number;
  unique_opportunities_improved: number;
  jaccard_similarity_with_cosgo: number;
}

export interface CosgoBenchmarkResponse {
  dataset_summary: {
    total_opportunities_analyzed: number;
    eligible_opportunities_count: number;
    baseline_coverage: number;
    budget_hours: number;
    benchmark_dataset_id?: string;
    evaluation_timestamp?: string;
  };
  cosgo: StrategyBenchmarkMetrics;
  frequency_baseline: StrategyBenchmarkMetrics;
  independent_per_job: StrategyBenchmarkMetrics;
  greedy_frequency_no_effort: StrategyBenchmarkMetrics;
  exact_oracle?: StrategyBenchmarkMetrics;
  comparison_summary: {
    cosgo_coverage_gain_lift_vs_frequency: string;
    cosgo_relative_coverage_gain_lift_vs_frequency?: string;
    cosgo_efficiency_lift_vs_frequency: string;
    cosgo_relative_efficiency_lift_vs_frequency?: string;
    cosgo_absolute_coverage_gain_difference_pp?: string;
    budget_utilization_explanation?: string;
    conclusion: string;
  };
  experiment_type?: string;
  sensitivity_note?: string;
  canonical_budget_utilization_note?: string;
}

export interface CosgoOptimizeRequest {
  budget_hours?: number;
  weekly_budget_hours?: number;
  target_roles?: string[];
  min_opportunity_relevance?: number;
}

export interface CosgoBudgetUpdateRequest {
  budget_hours: number;
  weekly_budget_hours?: number;
}

export interface CosgoActionUpdateProgressRequest {
  progress_state: CosgoProgressState;
  user_notes?: string;
}

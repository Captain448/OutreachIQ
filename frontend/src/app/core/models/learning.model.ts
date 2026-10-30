export type AccessType = 'FREE_COURSE' | 'FREE_TO_AUDIT' | 'FREE_OPEN_ACCESS';
export type ExamFeeStatus = 'PAID' | 'FREE' | 'NOT_VERIFIED';
export type SkillStatus = 'VERIFIED_KNOWN' | 'CRITICAL_GAP' | 'COMPLETED';

export interface DocResource {
  technology: string;
  title: string;
  url: string;
  description: string;
  domain: string;
  doc_type: string;
  is_verified_free: boolean;
}

export interface CourseItem {
  id?: string;
  title: string;
  provider?: string;
  provider_name?: string;
  organization?: string;
  url: string;
  access_type: AccessType | string;
  certificate_included: boolean;
  difficulty_level: string;
  estimated_hours: number;
  target_skills?: string[];
  covered_skills?: string[];
  description: string;
  price_transparency_note?: string;
}

export interface CertificationEntry {
  title: string;
  vendor: string;
  code: string;
  official_url: string;
  exam_fee_status: ExamFeeStatus | string;
  estimated_cost_usd: number;
  free_learning_materials_available: boolean;
  free_materials_url: string;
  skills: string[];
  relevant_roles: string[];
  notes: string;
}

export interface VideoItem {
  title: string;
  url: string;
  channel_title: string;
  video_id: string;
  thumbnail_url: string;
  published_at?: string;
  is_curated_fallback: boolean;
}

export interface VideoSearchResponse {
  skill: string;
  provider: string;
  is_live_api: boolean;
  circuit_status: string;
  results_count: number;
  videos: VideoItem[];
}

export interface ProjectMilestone {
  step?: number;
  step_number?: number;
  title: string;
  description?: string;
  hours?: number;
  estimated_hours?: number;
  deliverables?: string[];
}

export interface ProjectBlueprint {
  id?: string;
  project_id?: string;
  title: string;
  difficulty?: string;
  difficulty_level?: string;
  estimated_hours: number;
  is_estimate?: boolean;
  purpose?: string;
  summary?: string;
  problem_statement?: string;
  target_skills: string[];
  skill_gaps_addressed?: string[];
  prerequisites: string[];
  suggested_tech_stack?: Record<string, string>;
  milestones: ProjectMilestone[];
  deliverables?: string[];
  validation_checklist: string[];
  career_impact_rationale: string;
  documentation_links: { title: string; url: string }[];
  match_score?: number;
}

export interface EnrichedSkill {
  skill_name: string;
  category: string;
  estimated_hours: number;
  is_estimate: boolean;
  prerequisites: string[];
  priority_rank: number;
  marginal_gain?: number;
  why_recommended: string;
  is_required: boolean;
  is_from_cosgo: boolean;
  status: SkillStatus | string;
  documentation?: DocResource | null;
  courses: CourseItem[];
  certifications: CertificationEntry[];
  videos: VideoItem[];
}

export interface LearningPhase {
  phase_number: number;
  title: string;
  skills: EnrichedSkill[];
  total_hours: number;
  estimated_weeks: number;
}

export interface CatalogOverview {
  total_documentation_pages: number;
  total_verified_courses: number;
  total_certifications: number;
}

export interface LearningOverview {
  is_onboarding_empty_state: boolean;
  message?: string;
  weekly_hours_budget: number;
  total_estimated_hours: number;
  total_estimated_weeks: number;
  target_roles: string[];
  candidate_known_skills: string[];
  candidate_experience?: Array<{ role: string; company?: string; description?: string; technologies?: string[] }>;
  recommended_skills: EnrichedSkill[];
  learning_phases: LearningPhase[];
  recommended_projects: ProjectBlueprint[];
  catalog_overview: CatalogOverview;
}

export interface BudgetUpdatePayload {
  weekly_hours: number;
}

export interface BudgetUpdateResponse {
  user_id: string;
  weekly_hours_budget: number;
  updated_at: string | null;
}

export interface LearningProviderHealth {
  youtube: {
    provider_name: string;
    is_configured: boolean;
    daily_limit: number;
    daily_requests_used: number;
    circuit_status: string;
  };
  documentation_catalog: {
    total_technologies: number;
    status: string;
  };
  course_catalog: {
    total_courses: number;
    status: string;
  };
  certification_directory: {
    total_certifications: number;
    status: string;
  };
}

export interface CosgoSkillSummary {
  action_id: string;
  skill_name: string;
  priority_rank: number;
  marginal_coverage_gain: number;
  cumulative_coverage: number;
  opportunities_count: number;
  estimated_hours: number;
  effort_uncertainty_range?: {
    min_hours?: number;
    max_hours?: number;
    confidence_interval?: string;
  };
  prerequisites: string[];
  category: string;
  progress_state: string;
  why_recommended: string;
}

export interface RoadmapStage {
  stage_id: string;
  stage_number: number;
  title: string;
  focus: string;
  estimated_hours: number;
  core_concepts: string[];
  key_deliverable: string;
  is_completed?: boolean;
}

export interface PracticalExercise {
  id: string;
  title: string;
  scenario: string;
  objective: string;
  estimated_hours: number;
  commands_or_code_hints: string[];
  acceptance_criteria: string[];
  is_completed?: boolean;
}

export interface SkillPlan {
  skill_name: string;
  action_id: string;
  run_id: string;
  priority_rank: number;
  category: string;
  why_recommended: string;
  opportunities_count: number;
  target_opportunities_summary: Array<{
    title: string;
    company: string;
    match_score: number;
    salary_range: string;
    required_skills: string[];
  }>;
  marginal_coverage_gain: number;
  cumulative_coverage: number;
  estimated_hours: number;
  effort_uncertainty_range: {
    min_hours?: number;
    max_hours?: number;
    confidence_interval?: string;
  };
  prerequisites: string[];
  progress_state: string;
  completed_at?: string | null;
  diagnostic_note?: string | null;
  roadmap_stages: RoadmapStage[];
  resources: {
    documentation?: (DocResource & { is_completed?: boolean }) | null;
    courses: (CourseItem & { is_completed?: boolean })[];
    certifications: (CertificationEntry & { is_completed?: boolean })[];
    videos: VideoItem[];
    practical_exercises: PracticalExercise[];
  };
  projects: (ProjectBlueprint & { is_completed?: boolean })[];
  progress: {
    completed_resources: string[];
    completed_milestones: string[];
    completed_exercises: string[];
    project_milestones_completed: number[];
    project_completed: boolean;
    overall_status: string;
  };
}

export interface CosgoLearningDashboardResponse {
  is_cosgo_empty_state: boolean;
  empty_state_message?: string | null;
  run_id?: string | null;
  algorithm_version?: string | null;
  budget_hours: number;
  weekly_hours_budget: number;
  baseline_coverage: number;
  projected_coverage: number;
  marginal_coverage_increase: number;
  recommended_skills: CosgoSkillSummary[];
  selected_skill_name?: string | null;
  skill_plan?: SkillPlan | null;
}

export interface LearningProgressPayload {
  skill_name: string;
  progress_state?: string;
  toggle_resource_url?: string;
  toggle_milestone_id?: string;
  toggle_exercise_id?: string;
  toggle_project_id?: string;
  toggle_project_milestone_step?: number;
  user_notes?: string;
}

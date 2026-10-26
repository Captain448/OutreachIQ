import { Company } from './company.model';

export type OpportunityType = 'ADVERTISED' | 'EMERGING' | 'STRATEGIC';
export type OpportunityStatus = 'ACTIVE' | 'SAVED' | 'DISMISSED' | 'APPLIED';
export type RecommendedAction = 'CONTACT_NOW' | 'IMPROVE_FIRST' | 'SKIP';
export type ClaimType = 'OBSERVED_FACT' | 'SYSTEM_INFERENCE' | 'UNKNOWN_INFORMATION';
export type CompanyClassification = 'all' | 'startup' | 'smb' | 'mid_sized' | 'enterprise' | 'unknown';

export interface JobRequirement {
  id: string;
  requirement_type: string;
  description: string;
  is_critical: boolean;
}

export interface Job {
  id: string;
  company_id?: string;
  company_name: string;
  title: string;
  normalized_title: string;
  location?: string;
  is_remote: boolean;
  work_arrangement: string;
  employment_type: string;
  description?: string;
  experience_required?: string;
  education_required?: string;
  primary_url: string;
  application_url?: string;
  salary_range?: string;
  verification_status?: string;
  verification_details?: Record<string, any>;
  is_verified?: boolean;
  last_verified_at?: string;
  source_urls: string[];
  posting_date?: string;
  date_discovered: string;
  source_name: string;
  requirements: JobRequirement[];
}

export interface Evidence {
  id: string;
  claim_type: ClaimType;
  claim_text: string;
  source_url: string;
  supporting_excerpt?: string;
  confidence: number;
  retrieval_date: string;
}

export interface Opportunity {
  id: string;
  user_id: string;
  opportunity_type: OpportunityType;
  status: OpportunityStatus;
  match_score: number;
  evidence_confidence: number;
  recommended_action: RecommendedAction;
  matched_skills: string[];
  missing_skills: string[];
  critical_failures: string[];
  explanation?: string;
  extraction_quality?: number;
  company_confidence?: number;
  job?: Job;
  company?: Company;
  evidence_items: Evidence[];
  created_at: string;
  updated_at: string;
}

export interface OpportunityFilterParams {
  opportunity_type?: OpportunityType;
  status?: OpportunityStatus;
  recommended_action?: RecommendedAction;
  search?: string;
  location?: string;
  work_arrangement?: string;
  employment_type?: string;
  company_classification?: string;
  min_score?: number;
  skill?: string;
  run_id?: string;
  sort_by?: 'match_score' | 'recent';
  limit?: number;
  offset?: number;
}

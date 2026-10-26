import { SkillStatus } from './profile.model';

export interface CategorizedSkill {
  name: string;
  category: string;
  status: SkillStatus;
  source: string;
  evidence?: string;
  confidence_score: number;
}

export interface CareerDirectionSummary {
  target_role: string;
  associated_resumes: string[];
  matching_skills: string[];
  readiness_level: string;
  evidence_notes: string;
}

export interface CompletenessMetric {
  overall_percentage: number;
  missing_critical_fields: string[];
  recommendations: string[];
}

export interface CandidateIdentity {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  headline: string | null;
  links: Record<string, string>;
}

export interface CandidateIntelligenceRepresentation {
  identity: CandidateIdentity;
  education: any[];
  work_experience: any[];
  projects: any[];
  verified_skills: CategorizedSkill[];
  inferred_skills: CategorizedSkill[];
  unverified_skills: CategorizedSkill[];
  preferences: Record<string, any>;
  resume_inventory: any[];
  career_directions: CareerDirectionSummary[];
  profile_completeness: CompletenessMetric;
  overall_confidence: number;
  evidence_grounding_summary: string;
}

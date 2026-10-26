export type OutreachPurpose =
  | 'internship_application'
  | 'full_time_application'
  | 'recruiter_introduction'
  | 'referral_request'
  | 'follow_up';

export type RecipientType =
  | 'hiring_manager'
  | 'recruiter'
  | 'peer_engineer'
  | 'alumnus_referral'
  | 'general_hr';

export type GenerationStatus =
  | 'DRAFT'
  | 'AI_GENERATED'
  | 'MANUALLY_EDITED'
  | 'FAILED';

export interface OutreachRevision {
  archived_at: string;
  subject: string;
  body: string;
  is_user_edited?: boolean;
  user_notes?: string;
  model_provider?: string;
  model_name?: string;
}

export interface OutreachContextSnapshot {
  candidate?: {
    name?: string;
    headline?: string;
    verified_skills?: string[];
    inferred_skills?: string[];
    education?: any[];
    relevant_experience?: any[];
    relevant_projects?: any[];
  };
  job?: {
    title?: string;
    company_name?: string;
    location?: string;
    is_remote?: boolean;
    requirements?: string[];
    verification_status?: string;
    is_verified?: boolean;
    primary_url?: string;
    application_url?: string;
  };
  company?: {
    name?: string;
    domain?: string;
    industry?: string;
    website_url?: string;
    overview?: string;
    classification?: string;
    signals?: any[];
  };
  recipient?: {
    type?: string;
    name?: string;
    role?: string;
  };
  purpose?: string;
  previous_revisions?: OutreachRevision[];
  [key: string]: any;
}

export interface OutreachDraft {
  id: string;
  user_id: string;
  opportunity_id?: string | null;
  resume_id?: string | null;
  purpose: OutreachPurpose;
  recipient_type: RecipientType;
  recipient_name?: string | null;
  recipient_role?: string | null;
  subject: string;
  body: string;
  generation_status: GenerationStatus;
  model_provider?: string | null;
  model_name?: string | null;
  context_snapshot: OutreachContextSnapshot;
  is_user_edited: boolean;
  user_notes?: string | null;
  created_at: string;
  updated_at: string;

  // Joined convenience fields
  job_title?: string | null;
  company_name?: string | null;
  job_location?: string | null;
  application_url?: string | null;
  is_verified_opening?: boolean | null;
  verification_status?: string | null;
}

export interface OutreachDraftCreate {
  opportunity_id: string;
  resume_id?: string | null;
  purpose?: OutreachPurpose;
  recipient_type?: RecipientType;
  recipient_name?: string | null;
  recipient_role?: string | null;
  generate_immediately?: boolean;
}

export interface OutreachDraftUpdate {
  subject?: string;
  body?: string;
  purpose?: OutreachPurpose;
  recipient_type?: RecipientType;
  recipient_name?: string | null;
  recipient_role?: string | null;
  user_notes?: string | null;
}

export interface OutreachGenerateRequest {
  purpose?: OutreachPurpose;
  recipient_type?: RecipientType;
  recipient_name?: string | null;
  recipient_role?: string | null;
  resume_id?: string | null;
}

export interface OutreachDraftListResponse {
  items: OutreachDraft[];
  total: number;
}

export interface EligibleOpportunitySummary {
  id: string;
  job_title: string;
  company_name: string;
  location?: string | null;
  match_score: number;
  application_url?: string | null;
  is_verified: boolean;
  verification_status: string;
  matched_skills: string[];
  missing_skills: string[];
  created_at: string;
}

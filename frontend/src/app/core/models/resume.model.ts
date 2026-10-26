export type ParsingStatus = 'pending' | 'parsed' | 'partial' | 'failed';

export interface Resume {
  id: string;
  user_id: string;
  title: string;
  target_role: string;
  is_preferred: boolean;
  is_active: boolean;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  parsing_status: ParsingStatus;
  parsing_confidence: number;
  parsing_notes?: string;
  parsed_text?: string;
  extracted_skills: Array<{
    name: string;
    category: string;
    status: string;
    source: string;
    evidence?: string;
    confidence_score: number;
  }>;
  extracted_education: Array<{ raw_entry: string; source: string }>;
  extracted_experience: Array<{ raw_entry: string; source: string }>;
  extracted_projects: Array<{ raw_entry: string; source: string }>;
  created_at: string;
  updated_at: string;
}

export interface ResumeUpdatePayload {
  title?: string;
  target_role?: string;
  is_preferred?: boolean;
  is_active?: boolean;
}

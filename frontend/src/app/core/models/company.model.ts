export interface CompanySignal {
  signal_type: string;
  headline: string;
  date?: string;
  evidence_url?: string;
  excerpt?: string;
  confidence: number;
  classification?: string;
}

export interface Contact {
  id: string;
  company_id: string;
  name: string;
  role_or_title?: string;
  email?: string;
  linkedin_url?: string;
  evidence_source?: string;
  confidence: number;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  domain?: string;
  website_url?: string;
  description?: string;
  industry?: string;
  size_range?: string;
  classification?: string;
  headquarters?: string;
  growth_signal_score: number;
  alignment_score: number;
  signals_summary?: string;
  signals_data: CompanySignal[];
  why_contact?: string;
  why_wait?: string;
  has_advertised_openings: boolean;
  contacts?: Contact[];
  created_at: string;
  updated_at: string;
}

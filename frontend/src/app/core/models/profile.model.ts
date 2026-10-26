export type SkillStatus = 'VERIFIED' | 'INFERRED' | 'UNVERIFIED';
export type SkillSource = 'USER_INPUT' | 'RESUME_PARSED' | 'EXPERIENCE_INFERRED';

export interface Skill {
  id?: string;
  name: string;
  category: string;
  status: SkillStatus;
  source: SkillSource;
  evidence?: string;
  confidence_score: number;
}

export interface Education {
  id?: string;
  institution: string;
  degree: string;
  field_of_study?: string;
  start_year?: number;
  graduation_year?: number;
  grade_or_gpa?: string;
  details?: string;
}

export interface WorkExperience {
  id?: string;
  company: string;
  role: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
  technologies: string[];
}

export interface Project {
  id?: string;
  title: string;
  description?: string;
  technologies: string[];
  role_contribution?: string;
  github_url?: string;
  demo_url?: string;
}

export interface Preferences {
  id?: string;
  desired_roles: string[];
  preferred_industries: string[];
  preferred_locations: string[];
  remote_preference: 'remote' | 'hybrid' | 'onsite' | 'flexible';
  experience_level: 'entry' | 'mid' | 'senior' | 'lead' | 'executive';
  employment_preference: 'full-time' | 'contract' | 'internship' | 'part-time';
}

export interface CustomLink {
  label: string;
  url: string;
}

export interface Profile {
  id: string;
  user_id: string;
  full_name?: string;
  email?: string;
  headline?: string;
  phone?: string;
  location?: string;
  bio?: string;
  links: Record<string, any>;
  preferences?: Preferences;
  education: Education[];
  work_experience: WorkExperience[];
  projects: Project[];
  skills: Skill[];
  completeness_score: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  full_name?: string;
  headline?: string;
  phone?: string;
  location?: string;
  bio?: string;
  links?: Record<string, any>;
  preferences?: Partial<Preferences>;
  education?: Education[];
  work_experience?: WorkExperience[];
  projects?: Project[];
  skills?: Skill[];
}

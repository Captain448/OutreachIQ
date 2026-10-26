import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ProfileComponent } from './profile.component';
import { ProfileService } from '../../core/services/profile.service';
import { IntelligenceService } from '../../core/services/intelligence.service';
import { Profile } from '../../core/models/profile.model';
import { CandidateIntelligenceRepresentation } from '../../core/models/intelligence.model';

describe('ProfileComponent', () => {
  let component: ProfileComponent;
  let fixture: ComponentFixture<ProfileComponent>;
  let profileServiceSpy: any;
  let intelligenceServiceSpy: any;

  const mockProfile: Profile = {
    id: 'prof-1',
    user_id: 'user-1',
    full_name: 'Maya Patel',
    email: 'maya@example.com',
    headline: 'Senior Backend Engineer',
    phone: '+1-555-0100',
    location: 'San Francisco, CA',
    bio: 'Experienced backend systems developer.',
    links: {
      linkedin: 'https://linkedin.com/in/mayapatel',
      github: 'https://github.com/mayapatel',
      portfolio: 'https://mayapatel.dev',
      custom_links: [
        { label: 'LeetCode', url: 'https://leetcode.com/u/mayapatel' }
      ]
    },
    preferences: {
      desired_roles: ['Backend Engineer'],
      preferred_industries: ['Developer Tools'],
      preferred_locations: ['San Francisco'],
      remote_preference: 'flexible',
      experience_level: 'senior',
      employment_preference: 'full-time'
    },
    education: [
      {
        institution: 'UC Berkeley',
        degree: 'B.S. Computer Science',
        field_of_study: 'Computer Science',
        graduation_year: 2020
      }
    ],
    work_experience: [
      {
        company: 'CloudCorp',
        role: 'Backend Engineer',
        is_current: true,
        technologies: ['Go', 'Docker']
      }
    ],
    projects: [
      {
        title: 'CacheKV',
        technologies: ['Go', 'Raft']
      }
    ],
    skills: [
      {
        name: 'Go',
        category: 'programming_languages',
        status: 'VERIFIED',
        source: 'USER_INPUT',
        confidence_score: 1.0
      }
    ],
    completeness_score: 95,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z'
  };

  const mockIntelligence: CandidateIntelligenceRepresentation = {
    identity: {
      full_name: 'Maya Patel',
      email: 'maya@example.com',
      phone: '+1-555-0100',
      location: 'San Francisco, CA',
      headline: 'Senior Backend Engineer',
      links: {}
    },
    education: [],
    work_experience: [],
    projects: [],
    verified_skills: [],
    inferred_skills: [],
    unverified_skills: [],
    preferences: {},
    resume_inventory: [],
    career_directions: [],
    profile_completeness: {
      overall_percentage: 95,
      missing_critical_fields: [],
      recommendations: []
    },
    overall_confidence: 0.95,
    evidence_grounding_summary: 'Verified'
  };

  beforeEach(async () => {
    profileServiceSpy = {
      getProfile: vi.fn().mockReturnValue(of(mockProfile)),
      updateProfile: vi.fn().mockReturnValue(of(mockProfile))
    };

    intelligenceServiceSpy = {
      getIntelligence: vi.fn().mockReturnValue(of(mockIntelligence))
    };

    await TestBed.configureTestingModule({
      imports: [ProfileComponent],
      providers: [
        { provide: ProfileService, useValue: profileServiceSpy },
        { provide: IntelligenceService, useValue: intelligenceServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create and load profile into form on init', () => {
    expect(component).toBeTruthy();
    expect(profileServiceSpy.getProfile).toHaveBeenCalled();
    expect(component.form.get('full_name')?.value).toBe('Maya Patel');
    expect(component.form.get('headline')?.value).toBe('Senior Backend Engineer');
    expect(component.customLinksArray.length).toBe(1);
    expect(component.customLinksArray.at(0).get('label')?.value).toBe('LeetCode');
  });

  it('should allow adding dynamic custom links', () => {
    expect(component.customLinksArray.length).toBe(1);
    component.addCustomLinkItem({ label: 'Google Scholar', url: 'https://scholar.google.com' });
    expect(component.customLinksArray.length).toBe(2);
    expect(component.customLinksArray.at(1).get('label')?.value).toBe('Google Scholar');
  });

  it('should allow removing custom links', () => {
    expect(component.customLinksArray.length).toBe(1);
    component.removeCustomLinkItem(0);
    expect(component.customLinksArray.length).toBe(0);
  });

  it('should validate URLs and disallow javascript: and data: protocols', () => {
    component.addCustomLinkItem({ label: 'Malicious', url: 'javascript:alert(1)' });
    const ctrl = component.customLinksArray.at(1).get('url');
    expect(ctrl?.errors?.['invalidProtocol']).toBe(true);

    ctrl?.setValue('https://valid-domain.com');
    expect(ctrl?.errors).toBeNull();
  });

  it('should update profile and reset saving state on success', () => {
    profileServiceSpy.updateProfile = vi.fn().mockReturnValue(of({ ...mockProfile, full_name: 'Maya Patel Updated' }));

    component.saveProfile();

    expect(profileServiceSpy.updateProfile).toHaveBeenCalled();
    expect(component.saving).toBe(false);
    expect(component.saveSuccess).toBe(true);
    expect(component.errorMessage).toBeNull();
  });

  it('should handle save error and display actionable error message', () => {
    profileServiceSpy.updateProfile = vi.fn().mockReturnValue(
      throwError(() => ({
        status: 422,
        error: { detail: 'Validation failed: phone format is invalid' }
      }))
    );

    component.saveProfile();

    expect(profileServiceSpy.updateProfile).toHaveBeenCalled();
    expect(component.saving).toBe(false);
    expect(component.saveSuccess).toBe(false);
    expect(component.errorMessage).toBe('Validation failed: phone format is invalid');
  });

  it('should gracefully migrate legacy other link when present', () => {
    const legacyProfile: Profile = {
      ...mockProfile,
      links: {
        linkedin: 'https://linkedin.com/in/maya',
        github: 'https://github.com/maya',
        portfolio: 'https://maya.dev',
        other: 'https://scholar.google.com/citations'
      }
    };

    component.populateForm(legacyProfile);

    expect(component.customLinksArray.length).toBe(1);
    expect(component.customLinksArray.at(0).get('label')?.value).toBe('Other');
    expect(component.customLinksArray.at(0).get('url')?.value).toBe('https://scholar.google.com/citations');
  });
});

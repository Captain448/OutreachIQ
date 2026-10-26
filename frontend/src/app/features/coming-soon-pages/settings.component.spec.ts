import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter } from '@angular/router';
import { SettingsComponent } from './settings.component';
import { AuthService } from '../../core/services/auth.service';
import { ProfileService } from '../../core/services/profile.service';
import { GmailService } from '../../core/services/gmail.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { ResumeService } from '../../core/services/resume.service';
import { OutreachService } from '../../core/services/outreach.service';
import { OutreachAutomationSettings, GmailConnection } from '../../core/models/gmail.model';
import { ProviderHealth } from '../../core/models/provider.model';

describe('SettingsComponent', () => {
  let component: SettingsComponent;
  let fixture: ComponentFixture<SettingsComponent>;
  let gmailServiceSpy: any;
  let profileServiceSpy: any;

  const mockUser = { id: 'u1', email: 'settings.test@outreachiq.ai', full_name: 'Test Candidate' };
  const mockProfile = {
    id: 'p1',
    user_id: 'u1',
    headline: 'Senior Cloud Engineer',
    preferences: {
      desired_roles: ['DevOps Engineer'],
      preferred_industries: ['Cloud'],
      preferred_locations: ['Bengaluru', 'Remote'],
      remote_preference: 'flexible' as const,
      experience_level: 'senior' as const,
      employment_preference: 'full-time' as const
    }
  };

  const mockConnection: GmailConnection = {
    id: 'conn-1',
    user_id: 'u1',
    email_address: 'candidate@gmail.com',
    is_active: true,
    scopes: ['https://www.googleapis.com/auth/gmail.send'],
    created_at: '2026-10-19T10:00:00Z',
    updated_at: '2026-10-19T10:00:00Z'
  };

  const mockSettings: OutreachAutomationSettings = {
    id: 'st-1',
    user_id: 'u1',
    sending_mode: 'REVIEW_BEFORE_SEND',
    daily_limit: 15,
    emails_sent_today: 3,
    cooldown_minutes: 5,
    duplicate_suppression_days: 14,
    is_paused: false,
    auto_followup_enabled: false,
    followup_delay_days: 3,
    created_at: '2026-10-19T10:00:00Z',
    updated_at: '2026-10-19T10:00:00Z'
  };

  const mockProviders: ProviderHealth[] = [
    {
      provider_name: 'tavily',
      display_name: 'Tavily Web Search',
      is_configured: true,
      status: 'active',
      latency_ms: 1200,
      results_returned: 10,
      quota_limit_info: 'Standard Tier'
    },
    {
      provider_name: 'adzuna',
      display_name: 'Adzuna Jobs Feed',
      is_configured: false,
      status: 'disabled',
      results_returned: 0
    }
  ];

  beforeEach(async () => {
    const authServiceSpy = { currentUser$: of(mockUser) };
    profileServiceSpy = {
      getProfile: vi.fn().mockReturnValue(of(mockProfile)),
      updateProfile: vi.fn().mockImplementation((payload) => of({ ...mockProfile, ...payload }))
    };
    gmailServiceSpy = {
      getConnection: vi.fn().mockReturnValue(of(mockConnection)),
      getSettings: vi.fn().mockReturnValue(of(mockSettings)),
      updateSettings: vi.fn().mockImplementation((payload) => of({ ...mockSettings, ...payload })),
      disconnect: vi.fn().mockReturnValue(of({ success: true })),
      getMessages: vi.fn().mockReturnValue(of([])),
      getOAuthUrl: vi.fn().mockReturnValue(of({ authorization_url: 'https://accounts.google.com/o/oauth2', state: 'test-state' }))
    };
    const oppServiceSpy = {
      getProviderHealth: vi.fn().mockReturnValue(of(mockProviders)),
      getOpportunities: vi.fn().mockReturnValue(of([{ id: 'opp-1' }, { id: 'opp-2' }]))
    };
    const resumeServiceSpy = {
      getResumes: vi.fn().mockReturnValue(of([{ id: 'res-1' }]))
    };
    const outreachServiceSpy = {
      getDrafts: vi.fn().mockReturnValue(of({ items: [{ id: 'draft-1' }], total: 1 }))
    };

    await TestBed.configureTestingModule({
      imports: [SettingsComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy },
        { provide: ProfileService, useValue: profileServiceSpy },
        { provide: GmailService, useValue: gmailServiceSpy },
        { provide: OpportunityService, useValue: oppServiceSpy },
        { provide: ResumeService, useValue: resumeServiceSpy },
        { provide: OutreachService, useValue: outreachServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize and load all configuration settings, provider telemetry, and inventory counts', () => {
    expect(component).toBeTruthy();
    expect(component.profileModel?.preferences?.experience_level).toBe('senior');
    expect(component.gmailConnection?.email_address).toBe('candidate@gmail.com');
    expect(component.automationSettings?.sending_mode).toBe('REVIEW_BEFORE_SEND');
    expect(component.providerStatuses.length).toBe(2);
    expect(component.opportunityCount).toBe(2);
    expect(component.resumeCount).toBe(1);
    expect(component.draftCount).toBe(1);
  });

  it('should toggle emergency global pause and persist update via GmailService', () => {
    expect(component.automationSettings?.is_paused).toBe(false);
    component.toggleGlobalPause(true);
    expect(gmailServiceSpy.updateSettings).toHaveBeenCalledWith(
      expect.objectContaining({ is_paused: true })
    );
    expect(component.automationSettings?.is_paused).toBe(true);
  });

  it('should format sending mode labels correctly', () => {
    expect(component.formatMode('DRAFT_ONLY')).toBe('Draft Only');
    expect(component.formatMode('REVIEW_BEFORE_SEND')).toBe('Review Before Send');
    expect(component.formatMode('AUTO_SEND_OPT_IN')).toBe('Auto-Send Opt-In');
  });

  it('should update candidate target locations from comma-separated input', () => {
    component.onPreferredLocationsChange('Delhi, Noida, Gurgaon');
    expect(component.profileModel?.preferences?.preferred_locations).toEqual(['Delhi', 'Noida', 'Gurgaon']);
  });

  it('should save candidate career preferences via ProfileService', () => {
    component.saveProfilePreferences();
    expect(profileServiceSpy.updateProfile).toHaveBeenCalledWith({
      preferences: component.profileModel?.preferences
    });
    expect(component.successMessage).toContain('Candidate career preferences saved successfully');
  });

  it('should handle disconnect Gmail with confirmation', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    component.disconnectGmail();
    expect(gmailServiceSpy.disconnect).toHaveBeenCalled();
    expect(component.gmailConnection).toBeNull();
    expect(component.successMessage).toContain('Gmail account disconnected');
  });
});

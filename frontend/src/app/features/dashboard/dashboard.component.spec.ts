import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { provideRouter, Router } from '@angular/router';
import { DashboardComponent } from './dashboard.component';
import { AuthService } from '../../core/services/auth.service';
import { ProfileService } from '../../core/services/profile.service';
import { ResumeService } from '../../core/services/resume.service';
import { IntelligenceService } from '../../core/services/intelligence.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { CosgoService } from '../../core/services/cosgo.service';
import { OutreachService } from '../../core/services/outreach.service';
import { GmailService } from '../../core/services/gmail.service';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;
  let router: Router;

  const mockUser = { id: 'u1', email: 'elena@outreachiq.ai', full_name: 'Dr. Elena Rostova' };
  const mockProfile = {
    id: 'p1',
    user_id: 'u1',
    headline: 'Senior AI Research Engineer',
    completeness_score: 92,
    skills: [
      { name: 'Python', category: 'technical', status: 'VERIFIED', source: 'USER_INPUT', confidence_score: 1.0 },
      { name: 'PyTorch', category: 'ai_ml', status: 'VERIFIED', source: 'USER_INPUT', confidence_score: 1.0 }
    ],
    links: { linkedin: 'https://linkedin.com/in/elena', github: 'https://github.com/elena' }
  };

  const mockResumes = [
    { id: 'r1', user_id: 'u1', filename: 'Elena_Master_Resume.pdf', is_preferred: true, parsed_skills: ['Python', 'PyTorch'] }
  ];

  const mockOpportunities = [
    {
      id: 'opp-1',
      user_id: 'u1',
      match_score: 0.88,
      job: { title: 'Lead AI Engineer', company_name: 'NeuroVectors', location: 'Bengaluru', verification_status: 'VERIFIED_OPEN' }
    },
    {
      id: 'opp-2',
      user_id: 'u1',
      match_score: 0.74,
      job: { title: 'Backend Architect', company_name: 'Zomato Labs', location: 'Remote', verification_status: 'UNVERIFIED' }
    }
  ];

  const mockCosgoRun = {
    id: 'run-1',
    user_id: 'u1',
    baseline_coverage: 0.40,
    projected_coverage: 0.85,
    marginal_coverage_increase: 0.45,
    budget_hours: 40.0,
    diagnostics: { budget_hours_used: 35.0 },
    actions: [
      { id: 'act-1', skill_name: 'Docker', priority_rank: 1, estimated_hours: 10.0, marginal_coverage_gain: 0.25, why_recommended: 'High cross-opportunity overlap.' }
    ]
  };

  const mockDrafts = [
    { id: 'draft-1', user_id: 'u1', company_name: 'NexusAI', generation_status: 'AI_GENERATED', subject: 'Application for Lead AI Engineer', recipient_name: 'Hiring Manager' }
  ];

  const mockConnection = {
    id: 'conn-1',
    user_id: 'u1',
    email_address: 'elena@gmail.com',
    is_active: true
  };

  const mockSentMessages = [
    { id: 'msg-1', recipient_email: 'recruiter@neurovectors.com', reply_count: 2, status: 'DELIVERED' },
    { id: 'msg-2', recipient_email: 'talent@zomato.com', reply_count: 0, status: 'SENT' }
  ];

  beforeEach(async () => {
    const authServiceSpy = { currentUser$: of(mockUser) };
    const profileServiceSpy = { getProfile: () => of(mockProfile) };
    const resumeServiceSpy = { getResumes: () => of(mockResumes) };
    const intelligenceServiceSpy = { getIntelligence: () => of(null) };
    const oppServiceSpy = { getOpportunities: () => of(mockOpportunities) };
    const cosgoServiceSpy = { getLatestRun: () => of(mockCosgoRun) };
    const outreachServiceSpy = { getDrafts: () => of({ items: mockDrafts, total: 1 }) };
    const gmailServiceSpy = {
      getConnection: () => of(mockConnection),
      getMessages: () => of(mockSentMessages)
    };

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceSpy },
        { provide: ProfileService, useValue: profileServiceSpy },
        { provide: ResumeService, useValue: resumeServiceSpy },
        { provide: IntelligenceService, useValue: intelligenceServiceSpy },
        { provide: OpportunityService, useValue: oppServiceSpy },
        { provide: CosgoService, useValue: cosgoServiceSpy },
        { provide: OutreachService, useValue: outreachServiceSpy },
        { provide: GmailService, useValue: gmailServiceSpy }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create dashboard component and load all metrics on init', () => {
    expect(component).toBeTruthy();
    expect(component.profile?.completeness_score).toBe(92);
    expect(component.resumes.length).toBe(1);
    expect(component.opportunities.length).toBe(2);
    expect(component.latestCosgoRun?.projected_coverage).toBe(0.85);
    expect(component.outreachDrafts.length).toBe(1);
    expect(component.gmailConnection?.is_active).toBe(true);
    expect(component.sentMessages.length).toBe(2);
  });

  it('should compute top opportunities and verified count accurately', () => {
    expect(component.topOpportunities.length).toBe(2);
    expect(component.topOpportunities[0].job?.title).toBe('Lead AI Engineer');
    expect(component.verifiedOpportunitiesCount).toBe(1);
  });

  it('should calculate total recruiter replies from sent messages', () => {
    expect(component.repliesCount).toBe(2);
  });

  it('should correctly select preferred resume', () => {
    expect(component.preferredResume?.filename).toBe('Elena_Master_Resume.pdf');
  });

  it('should identify presence of professional links', () => {
    expect(component.hasProfessionalLinks()).toBe(true);
  });

  it('should navigate to outreach with draftId query param on goToDraft', () => {
    const navigateSpy = vi.spyOn(router, 'navigate');
    component.goToDraft(mockDrafts[0] as any);
    expect(navigateSpy).toHaveBeenCalledWith(['/outreach'], { queryParams: { draftId: 'draft-1' } });
  });
});

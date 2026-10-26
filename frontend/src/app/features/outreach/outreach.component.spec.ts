import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideRouter } from '@angular/router';
import { OutreachComponent } from './outreach.component';
import { OutreachService } from '../../core/services/outreach.service';
import { ResumeService } from '../../core/services/resume.service';
import { GmailService } from '../../core/services/gmail.service';
import {
  OutreachDraft,
  EligibleOpportunitySummary,
  OutreachDraftListResponse
} from '../../core/models/outreach.model';
import {
  GmailConnection,
  OutreachEmailMessage,
  OutreachEmailReply,
  OutreachAutomationSettings,
  OutreachEmailPreviewResponse
} from '../../core/models/gmail.model';

describe('OutreachComponent', () => {
  let component: OutreachComponent;
  let fixture: ComponentFixture<OutreachComponent>;
  let outreachServiceSpy: any;
  let resumeServiceSpy: any;
  let gmailServiceSpy: any;

  const mockOpportunities: EligibleOpportunitySummary[] = [
    {
      id: 'opp-1',
      job_title: 'Senior AI Engineer',
      company_name: 'NexusAI',
      location: 'San Francisco, CA (Remote)',
      match_score: 0.88,
      application_url: 'https://nexusai.com/jobs/senior-ai',
      is_verified: true,
      verification_status: 'VERIFIED_ACTIVE',
      matched_skills: ['Python', 'PyTorch', 'FastAPI'],
      missing_skills: ['CUDA'],
      created_at: '2026-01-01T00:00:00Z'
    },
    {
      id: 'opp-2',
      job_title: 'Full Stack Engineer',
      company_name: 'TechCorp',
      location: 'New York, NY',
      match_score: 0.72,
      application_url: 'https://techcorp.com/careers',
      is_verified: false,
      verification_status: 'UNVERIFIED',
      matched_skills: ['TypeScript', 'Angular'],
      missing_skills: ['GraphQL'],
      created_at: '2026-01-02T00:00:00Z'
    }
  ];

  const mockDrafts: OutreachDraft[] = [
    {
      id: 'draft-1',
      user_id: 'user-1',
      opportunity_id: 'opp-1',
      resume_id: null,
      purpose: 'full_time_application',
      recipient_type: 'hiring_manager',
      recipient_name: 'Dr. Sarah Lin',
      recipient_role: 'VP of AI Engineering',
      subject: 'Inquiry regarding Senior AI Engineer at NexusAI',
      body: 'Dear Dr. Sarah Lin,\n\nI am writing to express my strong interest in the Senior AI Engineer opening at NexusAI.',
      generation_status: 'AI_GENERATED',
      model_provider: 'gemini',
      model_name: 'gemini-1.5-pro',
      context_snapshot: {
        previous_revisions: [
          {
            archived_at: '2026-01-01T12:00:00Z',
            subject: 'Prior Subject for NexusAI',
            body: 'Prior body text before regeneration.'
          }
        ]
      },
      is_user_edited: false,
      user_notes: 'Initial generated outreach contact: recruiter@nexusai.com',
      created_at: '2026-01-01T10:00:00Z',
      updated_at: '2026-01-01T10:00:00Z',
      job_title: 'Senior AI Engineer',
      company_name: 'NexusAI',
      job_location: 'San Francisco, CA',
      application_url: 'https://nexusai.com/jobs/senior-ai',
      is_verified_opening: true,
      verification_status: 'VERIFIED_ACTIVE'
    }
  ];

  const mockGmailConnection: GmailConnection = {
    id: 'conn-1',
    user_id: 'user-1',
    email_address: 'candidate.verified@example.com',
    is_active: true,
    scopes: ['https://www.googleapis.com/auth/gmail.send'],
    last_synced_at: '2026-01-01T10:00:00Z',
    created_at: '2026-01-01T08:00:00Z',
    updated_at: '2026-01-01T08:00:00Z'
  };

  const mockSentMessages: OutreachEmailMessage[] = [
    {
      id: 'msg-1',
      user_id: 'user-1',
      draft_id: 'draft-1',
      sender_email: 'candidate.verified@example.com',
      recipient_email: 'recruiter@nexusai.com',
      recipient_name: 'Dr. Sarah Lin',
      subject: 'Inquiry regarding Senior AI Engineer at NexusAI',
      body: 'Email body text',
      content_hash: 'a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef',
      idempotency_key: 'idemp-1',
      status: 'SENT',
      gmail_message_id: 'gmsg_101',
      gmail_thread_id: 'gthread_202',
      attempt_count: 1,
      sent_at: '2026-01-01T11:00:00Z',
      has_reply: true,
      reply_count: 1,
      last_reply_at: '2026-01-01T14:00:00Z',
      created_at: '2026-01-01T11:00:00Z',
      updated_at: '2026-01-01T14:00:00Z'
    }
  ];

  const mockReplies: OutreachEmailReply[] = [
    {
      id: 'rep-1',
      message_id: 'msg-1',
      gmail_message_id: 'gmsg_reply_303',
      gmail_thread_id: 'gthread_202',
      from_email: 'recruiter@nexusai.com',
      from_name: 'Sarah Lin',
      subject: 'Re: Inquiry regarding Senior AI Engineer at NexusAI',
      snippet: 'Thanks for reaching out! We would love to schedule a screening call.',
      received_at: '2026-01-01T14:00:00Z',
      is_read: true,
      created_at: '2026-01-01T14:00:00Z'
    }
  ];

  const mockSettings: OutreachAutomationSettings = {
    id: 'st-1',
    user_id: 'user-1',
    sending_mode: 'REVIEW_BEFORE_SEND',
    daily_limit: 15,
    emails_sent_today: 1,
    cooldown_minutes: 15,
    last_sent_at: '2026-01-01T11:00:00Z',
    duplicate_suppression_days: 30,
    is_paused: false,
    auto_followup_enabled: false,
    followup_delay_days: 5,
    created_at: '2026-01-01T08:00:00Z',
    updated_at: '2026-01-01T11:00:00Z'
  };

  const mockPreviewResponse: OutreachEmailPreviewResponse = {
    draft_id: 'draft-1',
    sender_email: 'candidate.verified@example.com',
    recipient_email: 'recruiter@nexusai.com',
    recipient_name: 'Dr. Sarah Lin',
    subject: 'Inquiry regarding Senior AI Engineer at NexusAI',
    body: 'Dear Dr. Sarah Lin,\n\nI am writing to express my strong interest in the Senior AI Engineer opening at NexusAI.',
    content_hash: '9052f3b52af37ca2dc1dd3c449bfdc41482369390d74a2616dfc414b57287dcf',
    is_connected: true,
    can_send: true,
    warnings: []
  };

  const mockResumes = [
    {
      id: 'res-1',
      title: 'AI/ML Engineering Resume',
      target_role: 'AI Engineer',
      is_preferred: true
    }
  ];

  beforeEach(async () => {
    outreachServiceSpy = {
      getEligibleOpportunities: vi.fn().mockImplementation(() => of(JSON.parse(JSON.stringify(mockOpportunities)))),
      getDrafts: vi.fn().mockImplementation(() => of({ items: JSON.parse(JSON.stringify(mockDrafts)), total: mockDrafts.length })),
      getDraft: vi.fn().mockImplementation((id: string) => of(JSON.parse(JSON.stringify(mockDrafts[0])))),
      createDraft: vi.fn().mockImplementation((payload: any) =>
        of({
          ...mockDrafts[0],
          id: 'draft-new',
          opportunity_id: payload.opportunity_id,
          purpose: payload.purpose || 'full_time_application',
          recipient_type: payload.recipient_type || 'hiring_manager',
          recipient_name: payload.recipient_name,
          recipient_role: payload.recipient_role,
          generation_status: payload.generate_immediately ? 'AI_GENERATED' : 'DRAFT'
        })
      ),
      updateDraft: vi.fn().mockImplementation((id: string, payload: any) =>
        of({
          ...mockDrafts[0],
          ...payload,
          id,
          generation_status: 'MANUALLY_EDITED',
          is_user_edited: true
        })
      ),
      regenerateDraft: vi.fn().mockImplementation((id: string, payload: any) =>
        of({
          ...mockDrafts[0],
          id,
          subject: 'Regenerated Subject Line',
          body: 'Regenerated body content reflecting latest profile groundings.',
          generation_status: 'AI_GENERATED',
          is_user_edited: false
        })
      ),
      deleteDraft: vi.fn().mockReturnValue(of({ status: 'deleted', id: 'draft-1' }))
    };

    resumeServiceSpy = {
      getResumes: vi.fn().mockReturnValue(of(mockResumes))
    };

    gmailServiceSpy = {
      getConnection: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockGmailConnection)))),
      getOAuthUrl: vi.fn().mockReturnValue(of({ authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?mock=1', state: 'mock_state_123' })),
      exchangeCallback: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockGmailConnection)))),
      disconnect: vi.fn().mockReturnValue(of({ status: 'success', detail: 'Gmail account disconnected successfully.' })),
      previewEmail: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockPreviewResponse)))),
      sendEmail: vi.fn().mockImplementation((payload: any) =>
        of({
          ...mockSentMessages[0],
          id: 'msg-new-sent',
          recipient_email: payload.recipient_email,
          subject: payload.subject,
          body: payload.body,
          content_hash: payload.approved_content_hash,
          has_reply: false,
          reply_count: 0
        })
      ),
      getMessages: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockSentMessages)))),
      getMessage: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockSentMessages[0])))),
      getReplies: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockReplies)))),
      syncReplies: vi.fn().mockReturnValue(of({ synced_threads_count: 1, new_replies_count: 1, status: 'COMPLETED', last_synced_at: '2026-01-01T15:00:00Z' })),
      getSettings: vi.fn().mockReturnValue(of(JSON.parse(JSON.stringify(mockSettings)))),
      updateSettings: vi.fn().mockImplementation((payload: any) =>
        of({
          ...mockSettings,
          ...payload
        })
      )
    };

    await TestBed.configureTestingModule({
      imports: [OutreachComponent],
      providers: [
        provideRouter([]),
        { provide: OutreachService, useValue: outreachServiceSpy },
        { provide: ResumeService, useValue: resumeServiceSpy },
        { provide: GmailService, useValue: gmailServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(OutreachComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize and load opportunities, drafts, resumes, and Gmail data on mount', () => {
    expect(component).toBeTruthy();
    expect(outreachServiceSpy.getEligibleOpportunities).toHaveBeenCalled();
    expect(outreachServiceSpy.getDrafts).toHaveBeenCalled();
    expect(resumeServiceSpy.getResumes).toHaveBeenCalled();
    expect(gmailServiceSpy.getConnection).toHaveBeenCalled();
    expect(gmailServiceSpy.getMessages).toHaveBeenCalled();
    expect(gmailServiceSpy.getSettings).toHaveBeenCalled();

    expect(component.opportunities.length).toBe(2);
    expect(component.drafts.length).toBe(1);
    expect(component.selectedDraft?.id).toBe('draft-1');
    expect(component.gmailConnection?.email_address).toBe('candidate.verified@example.com');
    expect(component.sentMessages.length).toBe(1);
  });

  it('should filter drafts by search query', () => {
    component.searchQuery = 'Nexus';
    expect(component.filteredDrafts.length).toBe(1);

    component.searchQuery = 'NonExistentCompany';
    expect(component.filteredDrafts.length).toBe(0);

    component.searchQuery = '';
    expect(component.filteredDrafts.length).toBe(1);
  });

  it('should reset editor fields when startNewDraft is called', () => {
    component.startNewDraft();
    expect(component.selectedDraft).toBeNull();
    expect(component.formSubject).toBe('');
    expect(component.formBody).toBe('');
    expect(component.formOpportunityId).toBe('opp-1');
  });

  it('should preserve and display detached drafts when opportunity_id is null', () => {
    const detachedDraft: OutreachDraft = {
      ...mockDrafts[0],
      id: 'draft-detached',
      opportunity_id: null,
      company_name: 'DeletedCorp',
      job_title: 'Archived Position'
    };

    component.selectDraft(detachedDraft);
    expect(component.selectedDraft?.id).toBe('draft-detached');
    expect(component.formOpportunityId).toBe('');
    expect(component.selectedOpportunity).toBeUndefined();
  });

  it('should open send preview modal and calculate approval hash', () => {
    component.selectDraft(mockDrafts[0]);
    component.openSendPreviewModal();

    expect(component.showSendModal).toBe(true);
    expect(component.sendSubject).toBe(mockDrafts[0].subject);
    expect(component.sendRecipientEmail).toBe('recruiter@nexusai.com'); // Prefilled from notes

    component.calculatePreviewHash();
    expect(gmailServiceSpy.previewEmail).toHaveBeenCalledWith(expect.objectContaining({
      draft_id: 'draft-1',
      recipient_email: 'recruiter@nexusai.com'
    }));
    expect(component.approvedContentHash).toBe(mockPreviewResponse.content_hash);
    expect(component.hashInvalidated).toBe(false);
  });

  it('should invalidate approval hash when candidate modifies message content in send modal', () => {
    component.selectDraft(mockDrafts[0]);
    component.openSendPreviewModal();
    component.calculatePreviewHash();

    expect(component.hashInvalidated).toBe(false);

    // Edit message body
    component.sendBody += ' (Added post-approval note)';
    component.onModalContentChanged();

    expect(component.hashInvalidated).toBe(true);
    expect(component.canSendWithoutOverride).toBe(true); // raw can_send is true, but hashInvalidated blocks executeSend
  });

  it('should transmit email via Gmail when confirmed with valid hash', () => {
    component.selectDraft(mockDrafts[0]);
    component.openSendPreviewModal();
    component.calculatePreviewHash();

    component.executeSend();
    expect(gmailServiceSpy.sendEmail).toHaveBeenCalledWith(expect.objectContaining({
      draft_id: 'draft-1',
      recipient_email: 'recruiter@nexusai.com',
      approved_content_hash: mockPreviewResponse.content_hash
    }));
    expect(component.showSendModal).toBe(false);
    expect(component.successMessage).toContain('Outreach message sent successfully');
    expect(component.sentMessages[0].id).toBe('msg-new-sent');
  });

  it('should disconnect Gmail account when confirmed', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    component.disconnectGmail();
    expect(gmailServiceSpy.disconnect).toHaveBeenCalled();
    expect(component.gmailConnection).toBeNull();
    expect(component.successMessage).toContain('disconnected successfully');
  });

  it('should synchronize replies and load thread responses', () => {
    component.syncReplies();
    expect(gmailServiceSpy.syncReplies).toHaveBeenCalled();
    expect(component.successMessage).toContain('Reply sync complete');

    // Toggle replies view for a message
    component.toggleRepliesView(mockSentMessages[0]);
    expect(gmailServiceSpy.getReplies).toHaveBeenCalledWith('msg-1');
    expect(component.expandedMessageId).toBe('msg-1');
    expect(component.activeReplies.length).toBe(1);
    expect(component.activeReplies[0].snippet).toContain('screening call');
  });

  it('should update automation settings via settings modal', () => {
    component.openSettingsModal();
    expect(component.showSettingsModal).toBe(true);

    component.settingsModel!.daily_limit = 25;
    component.settingsModel!.is_paused = true;
    component.saveSettings();

    expect(gmailServiceSpy.updateSettings).toHaveBeenCalledWith(expect.objectContaining({
      daily_limit: 25,
      is_paused: true
    }));
    expect(component.showSettingsModal).toBe(false);
    expect(component.successMessage).toContain('settings updated');
  });

  it('should create a new AI draft when generating from a clean form', () => {
    component.startNewDraft();
    component.formOpportunityId = 'opp-1';
    component.formRecipientName = 'Dr. Sarah Lin';
    component.onGenerateClick();

    expect(outreachServiceSpy.createDraft).toHaveBeenCalledWith(
      expect.objectContaining({
        opportunity_id: 'opp-1',
        generate_immediately: true,
        recipient_name: 'Dr. Sarah Lin'
      })
    );
    expect(component.selectedDraft?.id).toBe('draft-new');
    expect(component.successMessage).toContain('created successfully');
  });

  it('should prompt confirmation modal when regenerating an edited draft and proceed on confirmation', () => {
    component.selectDraft(mockDrafts[0]);
    component.selectedDraft!.is_user_edited = true;

    component.onGenerateClick();
    expect(component.showRegenerateConfirmModal).toBe(true);

    component.proceedWithRegeneration();
    expect(component.showRegenerateConfirmModal).toBe(false);
    expect(outreachServiceSpy.regenerateDraft).toHaveBeenCalledWith('draft-1', expect.any(Object));
    expect(component.formSubject).toBe('Regenerated Subject Line');
  });

  it('should delete a draft and update the drafts list', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    component.confirmDeleteDraft(mockDrafts[0], new MouseEvent('click'));
    expect(outreachServiceSpy.deleteDraft).toHaveBeenCalledWith('draft-1');
    expect(component.drafts.length).toBe(0);
    expect(component.selectedDraft).toBeNull();
  });

  it('should auto-select target opportunity when navigating via opportunityId query param', () => {
    (component as any).pendingOpportunityId = 'opp-2';
    (component as any).applyPendingOpportunity();
    expect(component.activeTab).toBe('editor');
    expect(component.formOpportunityId).toBe('opp-2');
  });

  it('should auto-select specific draft when navigating via draftId query param', () => {
    (component as any).pendingDraftId = 'draft-1';
    (component as any).applyPendingDraft();
    expect(component.selectedDraft?.id).toBe('draft-1');
    expect(component.formSubject).toBe('Inquiry regarding Senior AI Engineer at NexusAI');
  });
});

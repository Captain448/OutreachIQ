import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { OutreachService } from '../../core/services/outreach.service';
import { ResumeService } from '../../core/services/resume.service';
import { GmailService } from '../../core/services/gmail.service';
import {
  OutreachDraft,
  EligibleOpportunitySummary,
  OutreachPurpose,
  RecipientType,
  OutreachRevision
} from '../../core/models/outreach.model';
import { Resume } from '../../core/models/resume.model';
import {
  GmailConnection,
  OutreachEmailMessage,
  OutreachEmailReply,
  OutreachAutomationSettings,
  OutreachEmailPreviewResponse,
  SendingMode
} from '../../core/models/gmail.model';

@Component({
  selector: 'app-outreach',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="outreach-page">
      <!-- Page Header -->
      <header class="page-header">
        <div class="header-left">
          <div class="mode-badge-wrap">
            <span class="iq-pill iq-pill-accent">Phase 6</span>
            <span class="iq-pill iq-pill-neutral">Controlled Gmail Automation</span>
            <span class="iq-pill iq-pill-success" *ngIf="gmailConnection?.is_active">
              Gmail: {{ gmailConnection?.email_address }}
            </span>
            <span class="iq-pill iq-pill-warning" *ngIf="!gmailConnection?.is_active">
              Gmail Disconnected
            </span>
          </div>
          <h1 class="page-title">Personalized AI Outreach & Controlled Email Engine</h1>
          <p class="page-subtitle">
            Ground outreach strictly in your verified profile, preview cryptographic approval hashes, send through Gmail, and monitor responses without blind retries.
          </p>
        </div>
        <div class="header-actions">
          <!-- Gmail Connect / Disconnect -->
          <button
            *ngIf="!gmailConnection?.is_active"
            class="btn btn-gmail-connect"
            (click)="openConnectModal()"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
            </svg>
            Connect Gmail
          </button>

          <button
            *ngIf="gmailConnection?.is_active"
            class="btn btn-gmail-disconnect"
            (click)="disconnectGmail()"
            title="Disconnect authorized Gmail account"
          >
            Disconnect Gmail
          </button>

          <!-- Settings Button -->
          <button class="btn btn-secondary" (click)="openSettingsModal()">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            Automation Settings
          </button>

          <!-- Refresh Button -->
          <button class="btn btn-secondary" (click)="loadAllData()" [disabled]="loading">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh
          </button>

          <!-- New Draft -->
          <button class="btn btn-primary" (click)="startNewDraft()">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New Outreach Draft
          </button>
        </div>
      </header>

      <!-- Feedback Banners -->
      <div *ngIf="successMessage" class="feedback-banner success-banner">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>{{ successMessage }}</span>
        <button class="banner-close" (click)="successMessage = null">×</button>
      </div>

      <div *ngIf="errorMessage" class="feedback-banner error-banner">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>{{ errorMessage }}</span>
        <button class="banner-close" (click)="errorMessage = null">×</button>
      </div>

      <!-- Navigation Tabs -->
      <div class="tabs-nav">
        <button
          class="tab-btn"
          [class.active]="activeTab === 'editor'"
          (click)="activeTab = 'editor'"
        >
          Drafts & Generator
          <span class="tab-badge">{{ drafts.length }}</span>
        </button>
        <button
          class="tab-btn"
          [class.active]="activeTab === 'history'"
          (click)="activeTab = 'history'"
        >
          Sending History & Replies
          <span class="tab-badge" [class.badge-alert]="totalRepliesCount > 0">{{ sentMessages.length }}</span>
        </button>
      </div>

      <!-- TAB 1: Main Dual-Pane Workspace (Drafts & Editor) -->
      <div class="workspace-grid" *ngIf="activeTab === 'editor'">
        <!-- Left Sidebar: Saved Drafts -->
        <aside class="sidebar-pane">
          <div class="sidebar-header">
            <h2 class="sidebar-title">
              Saved Drafts
              <span class="count-pill">{{ drafts.length }}</span>
            </h2>
            <div class="search-box">
              <input
                type="text"
                placeholder="Filter drafts..."
                [(ngModel)]="searchQuery"
                class="search-input"
              />
            </div>
          </div>

          <div *ngIf="loading && drafts.length === 0" class="sidebar-loading">
            <div class="spinner-sm"></div>
            <span>Loading outreach drafts...</span>
          </div>

          <div *ngIf="!loading && filteredDrafts.length === 0" class="sidebar-empty">
            <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
              <polyline points="22,6 12,13 2,6"></polyline>
            </svg>
            <p class="empty-title">No Drafts Found</p>
            <p class="empty-desc">Create your first personalized draft for a discovered opportunity.</p>
            <button class="btn btn-sm btn-primary" (click)="startNewDraft()">+ Start Draft</button>
          </div>

          <div class="drafts-list" *ngIf="filteredDrafts.length > 0">
            <div
              *ngFor="let draft of filteredDrafts"
              class="draft-card"
              [class.active]="selectedDraft?.id === draft.id"
              (click)="selectDraft(draft)"
            >
              <div class="draft-card-header">
                <span class="recipient-tag">{{ formatRecipient(draft.recipient_type) }}</span>
                <span class="status-pill" [class]="'status-' + draft.generation_status.toLowerCase()">
                  {{ draft.generation_status }}
                </span>
              </div>
              <h3 class="draft-company">{{ draft.company_name || 'Target Company' }}</h3>
              <p class="draft-role">{{ draft.job_title || 'Target Role' }}</p>
              <p class="draft-subject-preview">{{ draft.subject || '(Untitled subject)' }}</p>
              <div class="draft-card-footer">
                <span class="draft-time">{{ draft.updated_at | date:'MMM d, h:mm a' }}</span>
                <span class="detached-pill" *ngIf="!draft.opportunity_id" title="Saved draft preserved after opportunity deletion">
                  Detached Snapshot
                </span>
                <button
                  class="btn-icon-delete"
                  (click)="confirmDeleteDraft(draft, $event)"
                  title="Delete draft"
                >
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </aside>

        <!-- Right Pane: Outreach Editor & Context Inspector -->
        <main class="editor-pane">
          <!-- Configuration Card -->
          <section class="iq-card config-card">
            <div class="config-header">
              <h2 class="section-title">
                <span *ngIf="selectedDraft">Draft: {{ selectedDraft.company_name || 'Opportunity' }}</span>
                <span *ngIf="!selectedDraft">New Grounded Outreach Draft</span>
              </h2>
              <div class="status-meta" *ngIf="selectedDraft">
                <span class="meta-label">ID:</span>
                <code class="meta-code">{{ selectedDraft.id.slice(0, 8) }}...</code>
                <span class="iq-pill iq-pill-neutral" *ngIf="selectedDraft.is_user_edited">Manually Edited</span>
                <span class="iq-pill iq-pill-accent" *ngIf="!selectedDraft.is_user_edited && selectedDraft.generation_status === 'AI_GENERATED'">AI Synthesized</span>
                <span class="iq-pill iq-pill-warning" *ngIf="!selectedDraft.opportunity_id">Archived Historical Context</span>
              </div>
            </div>

            <!-- Historical Snapshot Notice -->
            <div *ngIf="selectedDraft && !selectedDraft.opportunity_id" class="historical-snapshot-notice">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>
                <strong>Historical Opportunity Preserved:</strong> The original job opportunity record was deleted or dismissed, but your outreach draft and contextual snapshot remain intact. You can still regenerate, edit, and send this email.
              </span>
            </div>

            <!-- Configuration Form Grid -->
            <div class="config-grid">
              <!-- Target Opportunity Dropdown -->
              <div class="form-group col-span-2">
                <label class="form-label">
                  Target Opportunity
                  <span class="req">*</span>
                </label>
                <select
                  class="form-control"
                  [(ngModel)]="formOpportunityId"
                  (change)="onOpportunityChange()"
                  [disabled]="generating"
                >
                  <option value="" disabled>-- Select a target opportunity --</option>
                  <option *ngIf="selectedDraft && !selectedDraft.opportunity_id" [value]="''" disabled selected>
                    [Preserved Snapshot: {{ selectedDraft.company_name || 'Company' }} - {{ selectedDraft.job_title || 'Role' }}]
                  </option>
                  <option *ngFor="let opp of opportunities" [value]="opp.id">
                    {{ opp.job_title }} @ {{ opp.company_name }} (Match: {{ (opp.match_score * 100) | number:'1.0-0' }}%{{ opp.is_verified ? ' • Verified Open' : ' • Unverified' }})
                  </option>
                </select>
                <div *ngIf="opportunities.length === 0 && !loadingOpportunities" class="field-hint warning-hint">
                  No saved opportunities found. Visit <a routerLink="/opportunities">Opportunities</a> to discover jobs first.
                </div>
              </div>

              <!-- Outreach Purpose Dropdown -->
              <div class="form-group">
                <label class="form-label">Outreach Purpose</label>
                <select class="form-control" [(ngModel)]="formPurpose" [disabled]="generating">
                  <option value="full_time_application">Full-Time Application Pitch</option>
                  <option value="internship_application">Internship / Entry Inquiry</option>
                  <option value="recruiter_introduction">Recruiter Introduction</option>
                  <option value="referral_request">Internal Referral / Alum Request</option>
                  <option value="follow_up">Application Follow-Up</option>
                </select>
              </div>

              <!-- Recipient Type Dropdown -->
              <div class="form-group">
                <label class="form-label">Recipient Category</label>
                <select class="form-control" [(ngModel)]="formRecipientType" [disabled]="generating">
                  <option value="hiring_manager">Hiring Manager / Tech Lead</option>
                  <option value="recruiter">Technical / Talent Recruiter</option>
                  <option value="peer_engineer">Peer Engineer / Future Teammate</option>
                  <option value="alumnus_referral">School / Alumni Connection</option>
                  <option value="general_hr">General HR / Talent Operations</option>
                </select>
              </div>

              <!-- Recipient Name (Optional) -->
              <div class="form-group">
                <label class="form-label">Recipient Name <span class="opt">(Optional)</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formRecipientName"
                  placeholder="e.g., Alex Mercer (Leave blank for professional greeting)"
                  [disabled]="generating"
                />
              </div>

              <!-- Recipient Role (Optional) -->
              <div class="form-group">
                <label class="form-label">Recipient Role / Team <span class="opt">(Optional)</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="formRecipientRole"
                  placeholder="e.g., Director of Platform Engineering"
                  [disabled]="generating"
                />
              </div>

              <!-- Resume Source (Optional) -->
              <div class="form-group col-span-2" *ngIf="resumes.length > 0">
                <label class="form-label">Grounding Resume <span class="opt">(Optional)</span></label>
                <select class="form-control" [(ngModel)]="formResumeId" [disabled]="generating">
                  <option value="">Default (Primary Candidate Profile & Projects)</option>
                  <option *ngFor="let resume of resumes" [value]="resume.id">
                    {{ resume.title || 'Untitled Resume' }} (Target: {{ resume.target_role || 'General' }})
                  </option>
                </select>
              </div>
            </div>

            <!-- Grounding Evidence Inspector Card -->
            <div class="grounding-inspector" *ngIf="selectedOpportunity">
              <div class="grounding-header">
                <span class="grounding-badge">Evidence Grounding Baseline</span>
                <span
                  class="verification-tag"
                  [class.verified]="selectedOpportunity.is_verified"
                  [class.unverified]="!selectedOpportunity.is_verified"
                >
                  {{ selectedOpportunity.is_verified ? 'Verified Open Opening' : 'Unverified / Exploratory Opening' }}
                </span>
              </div>
              <div class="grounding-details">
                <div class="detail-row" *ngIf="selectedOpportunity.matched_skills && selectedOpportunity.matched_skills.length > 0">
                  <span class="detail-label">Verified Candidate Skills Cited:</span>
                  <div class="skill-tags">
                    <span *ngFor="let skill of selectedOpportunity.matched_skills" class="skill-tag">
                      {{ skill }}
                    </span>
                  </div>
                </div>
                <div class="detail-row" *ngIf="selectedOpportunity.location">
                  <span class="detail-label">Location / Arrangement:</span>
                  <span class="detail-value">{{ selectedOpportunity.location }}</span>
                </div>
                <div class="grounding-assurance">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                  <span>
                    <strong>Strict Critic Guarantee:</strong> No invented metrics, false job titles, or unverified skills. All outreach claims are grounded strictly in your verified profile and target company signals.
                  </span>
                </div>
              </div>
            </div>

            <!-- Primary Generator Actions -->
            <div class="action-buttons-row">
              <button
                class="btn btn-primary"
                (click)="onGenerateClick()"
                [disabled]="(!formOpportunityId && !selectedDraft) || generating"
              >
                <span *ngIf="generating" class="spinner-sm"></span>
                <svg *ngIf="!generating" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                </svg>
                {{ generating ? 'Synthesizing Draft...' : (selectedDraft ? 'Regenerate AI Draft' : 'Generate AI Draft') }}
              </button>

              <button
                *ngIf="!selectedDraft"
                class="btn btn-secondary"
                (click)="createManualDraft()"
                [disabled]="!formOpportunityId || generating"
              >
                <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                Create Manual Starter
              </button>

              <button
                *ngIf="selectedDraft"
                class="btn btn-secondary"
                (click)="saveChanges()"
                [disabled]="saving || generating"
              >
                <span *ngIf="saving" class="spinner-sm"></span>
                <svg *ngIf="!saving" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                  <polyline points="17 21 17 13 7 13 7 21"></polyline>
                  <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                {{ saving ? 'Saving...' : 'Save Changes' }}
              </button>

              <!-- PROMINENT GMAIL SEND BUTTON -->
              <button
                *ngIf="selectedDraft && (formSubject || formBody)"
                class="btn btn-gmail-send"
                (click)="openSendPreviewModal()"
                [disabled]="generating || saving"
              >
                <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
                Preview & Send via Gmail
              </button>

              <div class="auxiliary-actions" *ngIf="formSubject || formBody">
                <button
                  class="btn btn-outline"
                  (click)="copyFullEmail()"
                  [class.btn-copied]="copyFeedbackAll"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  {{ copyFeedbackAll ? 'Copied Full Email!' : 'Copy Full Email' }}
                </button>
                <button class="btn btn-outline" (click)="exportTxt()">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                  </svg>
                  Export (.txt)
                </button>
                <button
                  *ngIf="revisions.length > 0"
                  class="btn btn-outline"
                  (click)="showRevisionHistory = !showRevisionHistory"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  History ({{ revisions.length }})
                </button>
              </div>
            </div>
          </section>

          <!-- Revision History Panel (Expandable) -->
          <section *ngIf="showRevisionHistory && revisions.length > 0" class="iq-card history-panel">
            <div class="history-header">
              <h3 class="history-title">Archived Prior Revisions</h3>
              <p class="history-subtitle">
                Regenerating an AI draft automatically archives your previous version so you never lose manual edits.
              </p>
            </div>
            <div class="revisions-list">
              <div *ngFor="let rev of revisions; let i = index" class="revision-card">
                <div class="rev-header">
                  <span class="rev-tag">Revision #{{ revisions.length - i }}</span>
                  <span class="rev-date">{{ rev.archived_at | date:'medium' }}</span>
                  <button class="btn btn-xs btn-secondary" (click)="restoreRevision(rev)">Restore This Version</button>
                </div>
                <p class="rev-subject"><strong>Subject:</strong> {{ rev.subject }}</p>
                <div class="rev-body-preview">{{ rev.body }}</div>
              </div>
            </div>
          </section>

          <!-- Interactive Email Editor Card -->
          <section class="iq-card editor-card" *ngIf="selectedDraft || formSubject || formBody || generating">
            <div class="editor-header">
              <div class="header-status-wrap">
                <h3 class="editor-title">Outreach Message Content</h3>
                <span class="iq-pill iq-pill-neutral">Plain-Text Professional Format</span>
              </div>
              <div class="char-metrics">
                <span class="metric-pill">{{ wordCount }} words</span>
                <span class="metric-pill">{{ charCount }} characters</span>
              </div>
            </div>

            <!-- Subject Line Input -->
            <div class="form-group subject-group">
              <div class="subject-header">
                <label class="form-label">Email Subject</label>
                <button
                  class="btn-copy-inline"
                  (click)="copySubject()"
                  [class.copied]="copyFeedbackSubject"
                >
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  {{ copyFeedbackSubject ? 'Copied' : 'Copy Subject' }}
                </button>
              </div>
              <input
                type="text"
                class="form-control subject-input"
                [(ngModel)]="formSubject"
                (ngModelChange)="onContentEdited()"
                placeholder="Subject line..."
                [disabled]="generating"
              />
            </div>

            <!-- Email Body Input -->
            <div class="form-group body-group">
              <div class="body-header">
                <label class="form-label">Email Body</label>
                <button
                  class="btn-copy-inline"
                  (click)="copyBody()"
                  [class.copied]="copyFeedbackBody"
                >
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                  {{ copyFeedbackBody ? 'Copied' : 'Copy Body' }}
                </button>
              </div>
              <textarea
                class="form-control body-textarea"
                rows="14"
                [(ngModel)]="formBody"
                (ngModelChange)="onContentEdited()"
                placeholder="Draft body content..."
                [disabled]="generating"
              ></textarea>
            </div>

            <!-- Candidate Personal Tracking Notes -->
            <div class="form-group notes-group">
              <label class="form-label">Personal Follow-up Notes <span class="opt">(Private to your account)</span></label>
              <textarea
                class="form-control notes-textarea"
                rows="2"
                [(ngModel)]="formUserNotes"
                placeholder="e.g. Sent connection request on LinkedIn, following up next Tuesday..."
                [disabled]="generating"
              ></textarea>
            </div>
          </section>
        </main>
      </div>

      <!-- TAB 2: Sending History & Reply Tracking -->
      <div class="history-view-pane" *ngIf="activeTab === 'history'">
        <div class="history-toolbar">
          <div class="toolbar-left">
            <h2 class="section-title">Outreach Email Transmissions & Reply Log</h2>
            <p class="section-desc">
              All messages sent via Gmail with status auditing, idempotency validation, and thread-scoped reply monitoring.
            </p>
          </div>
          <div class="toolbar-actions">
            <button
              class="btn btn-secondary"
              (click)="syncReplies()"
              [disabled]="syncingReplies || !gmailConnection?.is_active"
            >
              <span *ngIf="syncingReplies" class="spinner-sm"></span>
              <svg *ngIf="!syncingReplies" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
              </svg>
              {{ syncingReplies ? 'Checking Replies...' : 'Sync Replies' }}
            </button>
            <button class="btn btn-secondary" (click)="loadSentMessages()">
              Refresh History
            </button>
          </div>
        </div>

        <div *ngIf="loadingMessages" class="loading-state">
          <div class="spinner-sm"></div>
          <span>Loading email history...</span>
        </div>

        <div *ngIf="!loadingMessages && sentMessages.length === 0" class="empty-history-card iq-card">
          <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="4" width="20" height="16" rx="2"></rect>
            <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"></path>
          </svg>
          <h3>No Sent Emails Yet</h3>
          <p>Once you approve and send messages via Gmail, their delivery status and recruiter responses will appear here.</p>
        </div>

        <div class="sent-messages-list" *ngIf="sentMessages.length > 0">
          <div
            *ngFor="let msg of sentMessages"
            class="sent-message-card iq-card"
            [class.card-has-reply]="msg.has_reply"
          >
            <div class="msg-card-header">
              <div class="msg-status-group">
                <span class="status-badge" [class]="'badge-' + msg.status.toLowerCase()">
                  {{ msg.status }}
                </span>
                <span class="reply-badge" *ngIf="msg.has_reply">
                  Reply Detected ({{ msg.reply_count }})
                </span>
                <span class="no-reply-badge" *ngIf="!msg.has_reply">
                  No replies yet
                </span>
              </div>
              <span class="msg-timestamp">{{ msg.sent_at ? (msg.sent_at | date:'medium') : (msg.created_at | date:'medium') }}</span>
            </div>

            <div class="msg-recipient-row">
              <span class="msg-to-label">To:</span>
              <strong class="msg-to-email">{{ msg.recipient_name ? msg.recipient_name + ' &lt;' + msg.recipient_email + '&gt;' : msg.recipient_email }}</strong>
              <span class="sender-pill">From: {{ msg.sender_email }}</span>
            </div>

            <h4 class="msg-subject">{{ msg.subject }}</h4>
            <div class="msg-body-preview">{{ msg.body }}</div>

            <!-- Thread & Identifier Metadata -->
            <div class="msg-metadata-footer">
              <span class="meta-item" *ngIf="msg.gmail_message_id">
                Gmail Msg ID: <code>{{ msg.gmail_message_id }}</code>
              </span>
              <span class="meta-item" *ngIf="msg.gmail_thread_id">
                Thread: <code>{{ msg.gmail_thread_id }}</code>
              </span>
              <span class="meta-item">
                Hash: <code>{{ msg.content_hash.slice(0, 12) }}...</code>
              </span>

              <button
                *ngIf="msg.has_reply"
                class="btn btn-xs btn-outline view-replies-btn"
                (click)="toggleRepliesView(msg)"
              >
                {{ expandedMessageId === msg.id ? 'Hide Replies' : 'View Replies (' + msg.reply_count + ')' }}
              </button>
            </div>

            <!-- Replies Accordion -->
            <div class="replies-accordion" *ngIf="expandedMessageId === msg.id">
              <div class="replies-loading" *ngIf="loadingReplies">
                <div class="spinner-sm"></div>
                <span>Loading thread replies...</span>
              </div>
              <div *ngIf="!loadingReplies && activeReplies.length === 0" class="no-replies-found">
                No individual reply bodies found. Try syncing replies.
              </div>
              <div *ngFor="let rep of activeReplies" class="reply-card">
                <div class="reply-card-header">
                  <strong>{{ rep.from_name || rep.from_email }}</strong>
                  <span class="reply-time">{{ rep.received_at | date:'medium' }}</span>
                </div>
                <div class="reply-subject"><em>{{ rep.subject }}</em></div>
                <p class="reply-snippet">{{ rep.snippet || rep.body_preview || '(No body preview available)' }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- SEND PREVIEW & APPROVAL MODAL -->
      <div class="modal-backdrop" *ngIf="showSendModal">
        <div class="modal-card modal-lg">
          <div class="modal-header">
            <h3 class="modal-title">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
              Review & Approve Gmail Outreach
            </h3>
            <button class="modal-close" (click)="closeSendModal()">×</button>
          </div>

          <div class="modal-body">
            <!-- Warning / Alert Banner -->
            <div *ngIf="!gmailConnection?.is_active" class="modal-alert alert-danger">
              No active Gmail account is connected. You must connect your Gmail account before sending.
            </div>

            <div *ngIf="previewWarnings.length > 0" class="modal-warnings-list">
              <div *ngFor="let warn of previewWarnings" class="modal-alert alert-warning">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                  <line x1="12" y1="9" x2="12" y2="13"></line>
                  <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
                <span>{{ warn }}</span>
              </div>
            </div>

            <!-- Hash Invalidation Alert -->
            <div *ngIf="hashInvalidated" class="modal-alert alert-warning">
              <strong>Approval Outdated:</strong> Message content or recipient was edited. You must regenerate the preview approval hash before transmitting.
            </div>

            <div class="send-form-grid">
              <div class="form-group">
                <label class="form-label">Recipient Email Address <span class="req">*</span></label>
                <input
                  type="email"
                  class="form-control"
                  [(ngModel)]="sendRecipientEmail"
                  (ngModelChange)="onModalContentChanged()"
                  placeholder="e.g. recruiter@company.com"
                  [disabled]="isSending"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Recipient Name <span class="opt">(Optional)</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="sendRecipientName"
                  (ngModelChange)="onModalContentChanged()"
                  placeholder="e.g. Sarah Lin"
                  [disabled]="isSending"
                />
              </div>

              <div class="form-group col-span-2">
                <label class="form-label">Subject Line <span class="req">*</span></label>
                <input
                  type="text"
                  class="form-control"
                  [(ngModel)]="sendSubject"
                  (ngModelChange)="onModalContentChanged()"
                  [disabled]="isSending"
                />
              </div>

              <div class="form-group col-span-2">
                <label class="form-label">Message Body (Plain Text) <span class="req">*</span></label>
                <textarea
                  class="form-control"
                  rows="9"
                  [(ngModel)]="sendBody"
                  (ngModelChange)="onModalContentChanged()"
                  [disabled]="isSending"
                ></textarea>
              </div>
            </div>

            <!-- Cryptographic Verification Box -->
            <div class="hash-verification-box" *ngIf="approvedContentHash">
              <div class="hash-header">
                <span class="hash-label">Cryptographic Content Hash (SHA-256):</span>
                <span class="hash-status-pill" [class.valid]="!hashInvalidated" [class.invalid]="hashInvalidated">
                  {{ hashInvalidated ? 'INVALIDATED' : 'APPROVED & VERIFIED' }}
                </span>
              </div>
              <code class="hash-code">{{ approvedContentHash }}</code>
              <p class="hash-desc">
                Guarantees transmission integrity. Any alteration to recipient, subject, or body invalidates this hash.
              </p>
            </div>

            <!-- Duplicate Suppression Override Checkbox -->
            <div class="form-check-group" *ngIf="showDuplicateOverrideOption">
              <label class="check-label">
                <input type="checkbox" [(ngModel)]="allowDuplicateOverride" />
                <span>Authorize recent duplicate outreach to this recipient anyway</span>
              </label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="closeSendModal()" [disabled]="isSending">
              Cancel
            </button>

            <!-- Re-calculate / Preview Hash Button -->
            <button
              class="btn btn-outline"
              (click)="calculatePreviewHash()"
              [disabled]="isSending || !sendRecipientEmail || !sendSubject || !sendBody"
            >
              <span *ngIf="calculatingHash" class="spinner-sm"></span>
              {{ approvedContentHash && !hashInvalidated ? 'Refresh Approval Hash' : 'Calculate Approval Hash' }}
            </button>

            <!-- Final Send Button -->
            <button
              class="btn btn-gmail-send"
              (click)="executeSend()"
              [disabled]="isSending || !approvedContentHash || hashInvalidated || !canSendWithoutOverride"
            >
              <span *ngIf="isSending" class="spinner-sm"></span>
              {{ isSending ? 'Transmitting via Gmail...' : 'Approve & Send via Gmail' }}
            </button>
          </div>
        </div>
      </div>

      <!-- GMAIL CONNECT MODAL -->
      <div class="modal-backdrop" *ngIf="showConnectModal">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="modal-title">Connect Your Gmail Account</h3>
            <button class="modal-close" (click)="showConnectModal = false">×</button>
          </div>
          <div class="modal-body">
            <p>
              Authorize OutReachIQ to draft and send approved outreach emails and monitor responses.
            </p>
            <div class="oauth-box">
              <p class="oauth-desc">
                Step 1: Open Google OAuth to grant authorized sending and read-only thread access.
              </p>
              <button class="btn btn-primary" (click)="launchOAuthFlow()">
                Open Google Authorization Window
              </button>
            </div>

            <div class="oauth-manual-step">
              <p class="manual-step-title">Step 2: Enter Authorization Code</p>
              <p class="manual-step-desc">
                Paste the verification authorization code returned after logging in with Google:
              </p>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="oauthAuthCode"
                placeholder="Paste code here (e.g., 4/0Af... or auth_code_success)"
              />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="showConnectModal = false">Cancel</button>
            <button
              class="btn btn-primary"
              (click)="completeOAuthCallback()"
              [disabled]="!oauthAuthCode.trim() || connectingOAuth"
            >
              <span *ngIf="connectingOAuth" class="spinner-sm"></span>
              {{ connectingOAuth ? 'Linking Account...' : 'Complete Connection' }}
            </button>
          </div>
        </div>
      </div>

      <!-- AUTOMATION SETTINGS MODAL -->
      <div class="modal-backdrop" *ngIf="showSettingsModal" (click)="showSettingsModal = false">
        <div class="modal-card modal-settings-dialog" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <div class="modal-header-titles">
              <h3 class="modal-title">Gmail Automation & Safety Controls</h3>
              <p class="modal-header-sub">Configure global safety boundaries, sending mode, and transmission limits</p>
            </div>
            <button class="modal-close" (click)="showSettingsModal = false" title="Close modal">×</button>
          </div>

          <div class="modal-body" *ngIf="settingsModel">
            <!-- SECTION 1: GLOBAL SAFETY -->
            <div class="settings-section">
              <div class="section-badge-header">
                <span class="section-num">1</span>
                <div>
                  <h4 class="section-heading">Global Safety & Master Kill Switch</h4>
                  <p class="section-subtext">Immediate account-wide safeguard to stop all outgoing emails</p>
                </div>
              </div>

              <div class="pause-switch-card" [class.paused]="settingsModel.is_paused">
                <div class="switch-status-left">
                  <div class="status-indicator-row">
                    <span class="safety-status-pill" [class.paused]="settingsModel.is_paused">
                      {{ settingsModel.is_paused ? 'KILL SWITCH ARMED • SENDING HALTED' : 'SYSTEM OPERATIONAL • ACTIVE' }}
                    </span>
                  </div>
                  <strong class="switch-title">Emergency Transmission Kill Switch</strong>
                  <p class="switch-detail">
                    {{ settingsModel.is_paused 
                      ? 'All email dispatching is paused immediately. No queued or manually approved emails will be sent through Gmail.'
                      : 'Sending engine is running within configured safety quotas. Toggle to instantly freeze all outbound outreach.' }}
                  </p>
                </div>
                <div class="switch-toggle-col">
                  <label class="toggle-switch">
                    <input type="checkbox" [(ngModel)]="settingsModel.is_paused" />
                    <span class="slider round"></span>
                  </label>
                  <span class="toggle-label-hint">{{ settingsModel.is_paused ? 'Paused' : 'Active' }}</span>
                </div>
              </div>
            </div>

            <!-- SECTION 2: SENDING MODE -->
            <div class="settings-section">
              <div class="section-badge-header">
                <span class="section-num">2</span>
                <div>
                  <h4 class="section-heading">Sending Mode & Human Verification</h4>
                  <p class="section-subtext">Determine whether outreach requires manual inspection and hash locking</p>
                </div>
              </div>

              <div class="mode-options-grid">
                <label class="mode-card-option" [class.selected]="settingsModel.sending_mode === 'DRAFT_ONLY'">
                  <input
                    type="radio"
                    name="sending_mode"
                    value="DRAFT_ONLY"
                    [(ngModel)]="settingsModel.sending_mode"
                    class="mode-radio-input"
                  />
                  <div class="mode-card-content">
                    <div class="mode-card-top">
                      <span class="mode-name">Draft Only</span>
                      <span class="mode-pill pill-neutral">Safe Sandbox</span>
                    </div>
                    <p class="mode-desc">
                      Autonomous and Gmail sending are fully disabled. Drafts are generated and refined for manual export only.
                    </p>
                  </div>
                </label>

                <label class="mode-card-option" [class.selected]="settingsModel.sending_mode === 'REVIEW_BEFORE_SEND'">
                  <input
                    type="radio"
                    name="sending_mode"
                    value="REVIEW_BEFORE_SEND"
                    [(ngModel)]="settingsModel.sending_mode"
                    class="mode-radio-input"
                  />
                  <div class="mode-card-content">
                    <div class="mode-card-top">
                      <span class="mode-name">Review Before Send</span>
                      <span class="mode-pill pill-accent">Recommended</span>
                    </div>
                    <p class="mode-desc">
                      Requires explicit candidate inspection and an unforgeable cryptographic SHA-256 hash preview before transmission.
                    </p>
                  </div>
                </label>

                <label class="mode-card-option" [class.selected]="settingsModel.sending_mode === 'AUTO_SEND_OPT_IN'">
                  <input
                    type="radio"
                    name="sending_mode"
                    value="AUTO_SEND_OPT_IN"
                    [(ngModel)]="settingsModel.sending_mode"
                    class="mode-radio-input"
                  />
                  <div class="mode-card-content">
                    <div class="mode-card-top">
                      <span class="mode-name">Direct Send</span>
                      <span class="mode-pill pill-warning">Single Click</span>
                    </div>
                    <p class="mode-desc">
                      Enables direct dispatch upon candidate send trigger without a secondary hash verification preview step.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            <!-- SECTION 3: SENDING LIMITS & RATE CONTROLS -->
            <div class="settings-section">
              <div class="section-badge-header">
                <span class="section-num">3</span>
                <div>
                  <h4 class="section-heading">Sending Limits & Throttle Policies</h4>
                  <p class="section-subtext">Prevent rapid burst transmissions and protect your Gmail domain reputation</p>
                </div>
              </div>

              <div class="limits-inputs-grid">
                <div class="form-group limit-field">
                  <div class="limit-label-row">
                    <label class="form-label">Daily Sending Limit</label>
                    <span class="quota-counter">
                      {{ settingsModel.emails_sent_today }} / {{ settingsModel.daily_limit }} used
                    </span>
                  </div>
                  <div class="input-with-unit">
                    <input
                      type="number"
                      min="1"
                      max="100"
                      class="form-control"
                      [(ngModel)]="settingsModel.daily_limit"
                    />
                    <span class="input-unit">emails/day</span>
                  </div>
                  <span class="field-hint">Max allowable outbound transmissions per 24 hours (capped at 100).</span>
                </div>

                <div class="form-group limit-field">
                  <label class="form-label">Minimum Delay Between Sends</label>
                  <div class="input-with-unit">
                    <input
                      type="number"
                      min="0"
                      max="1440"
                      class="form-control"
                      [(ngModel)]="settingsModel.cooldown_minutes"
                    />
                    <span class="input-unit">minutes</span>
                  </div>
                  <span class="field-hint">Enforces quiet spacing between messages to avoid spam filters.</span>
                </div>

                <div class="form-group limit-field">
                  <label class="form-label">Duplicate Suppression Window</label>
                  <div class="input-with-unit">
                    <input
                      type="number"
                      min="1"
                      max="365"
                      class="form-control"
                      [(ngModel)]="settingsModel.duplicate_suppression_days"
                    />
                    <span class="input-unit">days</span>
                  </div>
                  <span class="field-hint">Blocks sending duplicate outreach to the same recipient in this period.</span>
                </div>
              </div>
            </div>
          </div>

          <!-- SECTION 4: ACTION FOOTER -->
          <div class="modal-footer settings-modal-footer">
            <button type="button" class="btn btn-secondary" (click)="showSettingsModal = false">
              Cancel
            </button>
            <button
              type="button"
              class="btn btn-primary"
              (click)="saveSettings()"
              [disabled]="savingSettings"
            >
              <span *ngIf="savingSettings" class="spinner-sm"></span>
              {{ savingSettings ? 'Saving Settings...' : 'Save Settings' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Regenerate Confirmation Modal -->
      <div class="modal-backdrop" *ngIf="showRegenerateConfirmModal">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="modal-title">Regenerate AI Draft?</h3>
            <button class="modal-close" (click)="showRegenerateConfirmModal = false">×</button>
          </div>
          <div class="modal-body">
            <p>
              You have previously edited this draft. Regenerating will generate a fresh response using the latest opportunity and profile context.
            </p>
            <p class="modal-note">
              <strong>Your current manual version will NOT be lost:</strong> it will be safely saved into your <em>Revision History</em> and can be restored at any time.
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="showRegenerateConfirmModal = false">Cancel</button>
            <button class="btn btn-primary" (click)="proceedWithRegeneration()">Archive & Regenerate</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .outreach-page {
      padding: 28px;
      max-width: 1360px;
      margin: 0 auto;
    }

    @media (max-width: 768px) {
      .outreach-page {
        padding: 16px;
      }
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      gap: 16px;
      flex-wrap: wrap;
    }

    .mode-badge-wrap {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }

    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 4px;
      letter-spacing: -0.02em;
    }

    .page-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
      max-width: 820px;
      line-height: 1.5;
    }

    .header-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    /* Tabs Navigation */
    .tabs-nav {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 2px;
    }

    .tab-btn {
      padding: 10px 18px;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-secondary);
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .tab-btn:hover {
      color: var(--text-primary);
    }

    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
    }

    .tab-badge {
      font-size: 11px;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      padding: 2px 7px;
      border-radius: 10px;
    }

    .tab-badge.badge-alert {
      background: #10b981;
      color: #fff;
    }

    .btn-gmail-connect {
      background: #ea4335;
      color: #ffffff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 8px 14px;
      font-size: 13px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }

    .btn-gmail-connect:hover {
      background: #d33828;
    }

    .btn-gmail-disconnect {
      background: transparent;
      border: 1px solid #ea4335;
      color: #ea4335;
      border-radius: var(--radius-sm);
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-gmail-send {
      background: #0284c7;
      color: #ffffff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }

    .btn-gmail-send:hover:not(:disabled) {
      background: #0369a1;
    }

    .feedback-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      margin-bottom: 16px;
      font-size: 14px;
    }

    .success-banner {
      background: var(--success-bg);
      color: var(--success-text);
      border: 1px solid var(--success-border);
    }

    .error-banner {
      background: var(--danger-bg);
      color: var(--danger-text);
      border: 1px solid var(--danger-border);
    }

    .banner-close {
      margin-left: auto;
      background: none;
      border: none;
      font-size: 18px;
      cursor: pointer;
      color: inherit;
    }

    /* Dual-Pane Layout */
    .workspace-grid {
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 20px;
      align-items: start;
    }

    @media (max-width: 1024px) {
      .workspace-grid {
        grid-template-columns: 1fr;
      }
    }

    /* Sidebar */
    .sidebar-pane {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 200px);
    }

    .sidebar-header {
      padding: 14px;
      border-bottom: 1px solid var(--border-color);
    }

    .sidebar-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 10px;
    }

    .count-pill {
      font-size: 11px;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 500;
    }

    .search-box {
      width: 100%;
    }

    .search-input {
      width: 100%;
      padding: 7px 10px;
      font-size: 13px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: var(--bg-surface);
      color: var(--text-primary);
      box-sizing: border-box;
    }

    .sidebar-loading, .sidebar-empty {
      padding: 32px 16px;
      text-align: center;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    .empty-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .empty-desc {
      font-size: 12px;
      margin: 0;
      max-width: 200px;
    }

    .drafts-list {
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .draft-card {
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      border: 1px solid transparent;
      background: var(--bg-surface);
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .draft-card:hover {
      background: var(--bg-hover);
      border-color: var(--border-color);
    }

    .draft-card.active {
      border-color: var(--accent);
      background: var(--accent-subtle);
    }

    .draft-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .recipient-tag {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .status-pill {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
    }

    .status-ai_generated {
      background: #e0e7ff;
      color: #3730a3;
    }

    .status-manually_edited {
      background: #fef3c7;
      color: #92400e;
    }

    .status-draft {
      background: var(--bg-subtle);
      color: var(--text-muted);
    }

    .detached-pill {
      font-size: 10px;
      background: #fef3c7;
      color: #92400e;
      padding: 2px 5px;
      border-radius: 3px;
      font-weight: 600;
    }

    .draft-company {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 2px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .draft-role {
      font-size: 12px;
      color: var(--text-secondary);
      margin: 0 0 4px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .draft-subject-preview {
      font-size: 11px;
      color: var(--text-muted);
      margin: 0 0 6px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .draft-card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
    }

    .draft-time {
      font-size: 10px;
      color: var(--text-muted);
    }

    .btn-icon-delete {
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 2px;
      border-radius: 3px;
    }

    .btn-icon-delete:hover {
      color: var(--danger-text);
      background: var(--danger-bg);
    }

    /* Editor Pane */
    .editor-pane {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .iq-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 20px;
    }

    .config-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 8px;
    }

    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .status-meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .meta-code {
      font-family: monospace;
      font-size: 11px;
      background: var(--bg-subtle);
      padding: 2px 6px;
      border-radius: 4px;
    }

    .historical-snapshot-notice {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 10px 14px;
      background: #fffbeb;
      border: 1px solid #fef3c7;
      color: #92400e;
      border-radius: var(--radius-sm);
      margin-bottom: 16px;
      font-size: 13px;
      line-height: 1.4;
    }

    .config-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
      margin-bottom: 16px;
    }

    .col-span-2 {
      grid-column: span 2;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .form-control {
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: var(--bg-surface);
      color: var(--text-primary);
      font-size: 13px;
      font-family: inherit;
    }

    .form-control:focus {
      outline: none;
      border-color: var(--accent);
    }

    .req {
      color: #ea4335;
    }

    .opt {
      font-weight: 400;
      color: var(--text-muted);
    }

    .field-hint {
      font-size: 11px;
      color: var(--text-muted);
    }

    .field-hint.warning-hint {
      color: #b45309;
    }

    .grounding-inspector {
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 14px;
      margin-bottom: 16px;
    }

    .grounding-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }

    .grounding-badge {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--accent);
      letter-spacing: 0.5px;
    }

    .verification-tag {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .verification-tag.verified {
      background: #ecfdf5;
      color: #047857;
      border: 1px solid #a7f3d0;
    }

    .verification-tag.unverified {
      background: #fffbeb;
      color: #b45309;
      border: 1px solid #fde68a;
    }

    .grounding-details {
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 12px;
    }

    .detail-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .detail-label {
      font-weight: 600;
      color: var(--text-secondary);
    }

    .skill-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }

    .skill-tag {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 11px;
      color: var(--text-primary);
    }

    .grounding-assurance {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-secondary);
      font-size: 12px;
      padding-top: 6px;
      border-top: 1px dashed var(--border-color);
    }

    .action-buttons-row {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .auxiliary-actions {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }

    .btn {
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }

    .btn-primary {
      background: var(--accent);
      color: #ffffff;
    }

    .btn-secondary {
      background: var(--bg-surface);
      border-color: var(--border-color);
      color: var(--text-primary);
    }

    .btn-outline {
      background: transparent;
      border-color: var(--border-color);
      color: var(--text-secondary);
    }

    .btn-xs {
      padding: 4px 8px;
      font-size: 11px;
    }

    .btn-sm {
      padding: 6px 12px;
      font-size: 12px;
    }

    .btn-copied {
      background: #ecfdf5 !important;
      color: #047857 !important;
      border-color: #a7f3d0 !important;
    }

    /* History & Revisions */
    .history-panel {
      border-left: 3px solid var(--accent);
    }

    .history-header {
      margin-bottom: 12px;
    }

    .history-title {
      font-size: 14px;
      font-weight: 600;
      margin: 0 0 2px 0;
    }

    .history-subtitle {
      font-size: 12px;
      color: var(--text-muted);
      margin: 0;
    }

    .revisions-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .revision-card {
      background: var(--bg-subtle);
      padding: 10px;
      border-radius: var(--radius-sm);
      font-size: 12px;
    }

    .rev-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .rev-tag {
      font-weight: 600;
      color: var(--accent);
    }

    .rev-date {
      color: var(--text-muted);
    }

    .rev-header button {
      margin-left: auto;
    }

    .rev-subject {
      margin: 0 0 4px 0;
    }

    .rev-body-preview {
      white-space: pre-wrap;
      color: var(--text-secondary);
      max-height: 80px;
      overflow-y: auto;
      background: var(--bg-card);
      padding: 6px 8px;
      border-radius: 4px;
      border: 1px solid var(--border-color);
    }

    /* Editor Card */
    .editor-card {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
    }

    .header-status-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .editor-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .char-metrics {
      display: flex;
      gap: 8px;
    }

    .metric-pill {
      font-size: 11px;
      font-weight: 500;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      padding: 3px 8px;
      border-radius: 4px;
    }

    .subject-header, .body-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .btn-copy-inline {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
    }

    .subject-input {
      font-weight: 600;
    }

    .body-textarea {
      font-family: inherit;
      line-height: 1.6;
      resize: vertical;
    }

    /* Sending History Tab */
    .history-view-pane {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .history-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }

    .section-desc {
      font-size: 13px;
      color: var(--text-secondary);
      margin: 2px 0 0 0;
    }

    .toolbar-actions {
      display: flex;
      gap: 8px;
    }

    .empty-history-card {
      text-align: center;
      padding: 48px 24px;
      color: var(--text-muted);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    .sent-messages-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .sent-message-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: all 0.2s ease;
    }

    .sent-message-card.card-has-reply {
      border-left: 4px solid #10b981;
    }

    .msg-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .msg-status-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-badge {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .badge-sent {
      background: #ecfdf5;
      color: #047857;
    }

    .badge-outcome_unknown {
      background: #fffbeb;
      color: #b45309;
    }

    .badge-failed {
      background: #fef2f2;
      color: #b91c1c;
    }

    .reply-badge {
      font-size: 11px;
      font-weight: 700;
      background: #10b981;
      color: #ffffff;
      padding: 2px 8px;
      border-radius: 12px;
    }

    .no-reply-badge {
      font-size: 11px;
      color: var(--text-muted);
    }

    .msg-timestamp {
      font-size: 11px;
      color: var(--text-muted);
    }

    .msg-recipient-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    .msg-to-label {
      color: var(--text-muted);
    }

    .sender-pill {
      font-size: 11px;
      color: var(--text-secondary);
      background: var(--bg-subtle);
      padding: 1px 6px;
      border-radius: 4px;
      margin-left: auto;
    }

    .msg-subject {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .msg-body-preview {
      font-size: 12px;
      color: var(--text-secondary);
      white-space: pre-wrap;
      max-height: 60px;
      overflow-y: hidden;
      line-height: 1.4;
    }

    .msg-metadata-footer {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 11px;
      color: var(--text-muted);
      border-top: 1px solid var(--border-color);
      padding-top: 8px;
      flex-wrap: wrap;
    }

    .view-replies-btn {
      margin-left: auto;
    }

    .replies-accordion {
      background: var(--bg-subtle);
      padding: 12px;
      border-radius: var(--radius-sm);
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 4px;
    }

    .reply-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px;
      font-size: 12px;
    }

    .reply-card-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 2px;
    }

    .reply-time {
      font-size: 10px;
      color: var(--text-muted);
    }

    .reply-subject {
      color: var(--text-secondary);
      font-size: 11px;
      margin-bottom: 4px;
    }

    .reply-snippet {
      margin: 0;
      color: var(--text-primary);
      line-height: 1.4;
    }

    /* Modals */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 16px;
    }

    .modal-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      max-width: 540px;
      width: 100%;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    }

    .modal-lg {
      max-width: 760px;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color);
    }

    .modal-title {
      font-size: 16px;
      font-weight: 600;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .modal-close {
      background: none;
      border: none;
      font-size: 20px;
      cursor: pointer;
      color: var(--text-muted);
    }

    .modal-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      max-height: calc(85vh - 120px);
      overflow-y: auto;
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      padding: 14px 20px;
      border-top: 1px solid var(--border-color);
      background: var(--bg-surface);
    }

    .modal-alert {
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .alert-danger {
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }

    .alert-warning {
      background: #fffbeb;
      color: #92400e;
      border: 1px solid #fef3c7;
    }

    .hash-verification-box {
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      font-size: 12px;
    }

    .hash-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .hash-label {
      font-weight: 600;
      color: var(--text-primary);
    }

    .hash-status-pill {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .hash-status-pill.valid {
      background: #ecfdf5;
      color: #047857;
    }

    .hash-status-pill.invalid {
      background: #fef2f2;
      color: #b91c1c;
    }

    .hash-code {
      display: block;
      background: var(--bg-card);
      padding: 6px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 11px;
      word-break: break-all;
      color: var(--accent);
      margin-bottom: 4px;
    }

    .hash-desc {
      font-size: 11px;
      color: var(--text-muted);
      margin: 0;
    }

    .send-form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }

    .form-check-group {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    .check-label {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
    }

    .oauth-box {
      background: var(--bg-subtle);
      padding: 16px;
      border-radius: var(--radius-sm);
      text-align: center;
    }

    .oauth-desc {
      font-size: 13px;
      color: var(--text-secondary);
      margin-bottom: 12px;
    }

    .oauth-manual-step {
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
    }

    .manual-step-title {
      font-size: 13px;
      font-weight: 600;
      margin: 0 0 4px 0;
    }

    .manual-step-desc {
      font-size: 12px;
      color: var(--text-muted);
      margin: 0 0 8px 0;
    }

    /* Pause Switch */
    .pause-switch-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-radius: var(--radius-sm);
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
    }

    .pause-switch-card.paused {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }

    .switch-info strong {
      font-size: 14px;
    }

    .switch-info p {
      font-size: 12px;
      color: var(--text-muted);
      margin: 2px 0 0 0;
    }

    /* Toggle slider */
    .toggle-switch {
      position: relative;
      display: inline-block;
      width: 44px;
      height: 24px;
    }

    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #ccc;
      transition: .3s;
      border-radius: 24px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 18px; width: 18px;
      left: 3px; bottom: 3px;
      background-color: white;
      transition: .3s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: #ea4335;
    }

    input:checked + .slider:before {
      transform: translateX(20px);
    }

    .spinner-sm {
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: currentColor;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Automation Settings 4-Section Redesign */
    .modal-settings-dialog {
      max-width: 680px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
    }
    .modal-header-titles {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .modal-header-sub {
      font-size: 12.5px;
      color: var(--text-secondary);
      margin: 0;
    }
    .settings-section {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .section-badge-header {
      display: flex;
      align-items: flex-start;
      gap: 10px;
    }
    .section-num {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: var(--primary);
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      margin-top: 2px;
    }
    .section-heading {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }
    .section-subtext {
      font-size: 12px;
      color: var(--text-muted);
      margin: 2px 0 0 0;
    }
    .safety-status-pill {
      font-size: 10.5px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
      background: #ecfdf5;
      color: #047857;
      border: 1px solid #a7f3d0;
      letter-spacing: 0.03em;
      display: inline-block;
      margin-bottom: 4px;
    }
    .safety-status-pill.paused {
      background: #fef2f2;
      color: #b91c1c;
      border-color: #fecaca;
    }
    .switch-status-left {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .switch-title {
      font-size: 13.5px;
      font-weight: 600;
    }
    .switch-detail {
      font-size: 12px;
      color: var(--text-secondary);
      margin: 0;
      line-height: 1.4;
    }
    .switch-toggle-col {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
      margin-left: 16px;
    }
    .toggle-label-hint {
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 500;
    }
    .mode-options-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }
    @media (max-width: 640px) {
      .mode-options-grid {
        grid-template-columns: 1fr;
      }
    }
    .mode-card-option {
      position: relative;
      cursor: pointer;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      background: var(--bg-app);
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
    }
    .mode-card-option:hover {
      border-color: var(--accent);
      background: #ffffff;
    }
    .mode-card-option.selected {
      border-color: var(--accent);
      background: #f0fdf4;
      box-shadow: 0 0 0 1px var(--accent);
    }
    .mode-radio-input {
      position: absolute;
      top: 10px;
      right: 10px;
      accent-color: var(--accent);
    }
    .mode-card-content {
      display: flex;
      flex-direction: column;
    }
    .mode-card-top {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 6px;
      padding-right: 20px;
    }
    .mode-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .mode-pill {
      font-size: 10px;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 4px;
      display: inline-block;
      width: fit-content;
    }
    .pill-neutral { background: #f1f5f9; color: #475569; }
    .pill-accent { background: #ecfdf5; color: #047857; }
    .pill-warning { background: #fffbeb; color: #b45309; }
    .mode-desc {
      font-size: 11.5px;
      color: var(--text-secondary);
      margin: 0;
      line-height: 1.35;
    }
    .limits-inputs-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }
    @media (max-width: 640px) {
      .limits-inputs-grid {
        grid-template-columns: 1fr;
      }
    }
    .limit-field {
      margin-bottom: 0;
    }
    .limit-label-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .quota-counter {
      font-size: 11px;
      color: var(--accent);
      font-weight: 600;
    }
    .input-with-unit {
      position: relative;
      display: flex;
      align-items: center;
    }
    .input-with-unit input {
      padding-right: 76px;
    }
    .input-unit {
      position: absolute;
      right: 10px;
      font-size: 11px;
      color: var(--text-muted);
      pointer-events: none;
    }
    .settings-modal-footer {
      position: sticky;
      bottom: 0;
      background: var(--bg-surface);
      z-index: 10;
    }
  `]
})
export class OutreachComponent implements OnInit {
  private outreachService = inject(OutreachService);
  private resumeService = inject(ResumeService);
  private gmailService = inject(GmailService);
  private route = inject(ActivatedRoute, { optional: true });
  private cd = inject(ChangeDetectorRef);

  activeTab: 'editor' | 'history' = 'editor';

  opportunities: EligibleOpportunitySummary[] = [];
  drafts: OutreachDraft[] = [];
  resumes: Resume[] = [];
  selectedDraft: OutreachDraft | null = null;
  pendingOpportunityId: string | null = null;
  pendingDraftId: string | null = null;

  // Gmail and Messaging State
  gmailConnection: GmailConnection | null = null;
  sentMessages: OutreachEmailMessage[] = [];
  settingsModel: OutreachAutomationSettings | null = null;
  activeReplies: OutreachEmailReply[] = [];
  expandedMessageId: string | null = null;

  // Active form model
  formOpportunityId: string = '';
  formResumeId: string = '';
  formPurpose: OutreachPurpose = 'full_time_application';
  formRecipientType: RecipientType = 'hiring_manager';
  formRecipientName: string = '';
  formRecipientRole: string = '';
  formSubject: string = '';
  formBody: string = '';
  formUserNotes: string = '';

  // UI state
  loading: boolean = false;
  loadingOpportunities: boolean = false;
  loadingMessages: boolean = false;
  loadingReplies: boolean = false;
  generating: boolean = false;
  saving: boolean = false;
  syncingReplies: boolean = false;
  savingSettings: boolean = false;
  connectingOAuth: boolean = false;

  searchQuery: string = '';
  errorMessage: string | null = null;
  successMessage: string | null = null;
  copyFeedbackSubject: boolean = false;
  copyFeedbackBody: boolean = false;
  copyFeedbackAll: boolean = false;
  showRegenerateConfirmModal: boolean = false;
  showRevisionHistory: boolean = false;

  // Send Modal state
  showSendModal: boolean = false;
  showConnectModal: boolean = false;
  showSettingsModal: boolean = false;

  sendRecipientEmail: string = '';
  sendRecipientName: string = '';
  sendSubject: string = '';
  sendBody: string = '';
  approvedContentHash: string = '';
  hashInvalidated: boolean = false;
  previewWarnings: string[] = [];
  canSendRaw: boolean = false;
  isSending: boolean = false;
  calculatingHash: boolean = false;
  allowDuplicateOverride: boolean = false;
  showDuplicateOverrideOption: boolean = false;

  // OAuth Connect State
  oauthAuthCode: string = '';
  oauthState: string = '';

  ngOnInit(): void {
    this.loadAllData();
    if (this.route) {
      this.route.queryParams.subscribe(params => {
        const draftId = params['draftId'];
        const oppId = params['opportunityId'];
        if (draftId) {
          this.pendingDraftId = draftId;
          this.applyPendingDraft();
        } else if (oppId) {
          this.pendingOpportunityId = oppId;
          this.applyPendingOpportunity();
        }
      });
    }
  }

  private applyPendingDraft(): void {
    if (!this.pendingDraftId) return;
    this.activeTab = 'editor';
    const draft = this.drafts.find(d => d.id === this.pendingDraftId);
    if (draft) {
      this.selectDraft(draft);
    }
    this.cd.markForCheck();
  }

  private applyPendingOpportunity(): void {
    if (!this.pendingOpportunityId) return;
    this.activeTab = 'editor';
    this.formOpportunityId = this.pendingOpportunityId;
    const existingDraft = this.drafts.find(d => d.opportunity_id === this.pendingOpportunityId);
    if (existingDraft) {
      this.selectDraft(existingDraft);
    } else {
      this.startNewDraft();
      this.formOpportunityId = this.pendingOpportunityId;
    }
    this.cd.markForCheck();
  }

  loadAllData(): void {
    this.loading = true;
    this.errorMessage = null;
    this.loadOpportunities();
    this.loadDrafts();
    this.loadResumes();
    this.loadGmailConnection();
    this.loadSentMessages();
    this.loadAutomationSettings();
  }

  loadOpportunities(): void {
    this.loadingOpportunities = true;
    this.outreachService.getEligibleOpportunities().subscribe({
      next: (opps) => {
        this.opportunities = opps || [];
        this.loadingOpportunities = false;
        if (this.pendingOpportunityId) {
          this.formOpportunityId = this.pendingOpportunityId;
        } else if (!this.formOpportunityId && this.opportunities.length > 0) {
          this.formOpportunityId = this.opportunities[0].id;
        }
        this.cd.markForCheck();
      },
      error: () => {
        this.loadingOpportunities = false;
        this.errorMessage = 'Failed to load eligible opportunities.';
        this.cd.markForCheck();
      }
    });
  }

  loadDrafts(): void {
    this.outreachService.getDrafts().subscribe({
      next: (res) => {
        this.drafts = res?.items ? [...res.items] : [];
        this.loading = false;
        if (this.pendingDraftId) {
          this.applyPendingDraft();
        } else if (this.pendingOpportunityId) {
          this.applyPendingOpportunity();
        } else if (!this.selectedDraft && this.drafts.length > 0) {
          this.selectDraft(this.drafts[0]);
        }
        this.cd.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'Failed to load saved outreach drafts.';
        this.cd.markForCheck();
      }
    });
  }

  loadResumes(): void {
    this.resumeService.getResumes().subscribe({
      next: (resumes) => {
        this.resumes = resumes || [];
        this.cd.markForCheck();
      },
      error: () => {
        this.resumes = [];
      }
    });
  }

  loadGmailConnection(): void {
    this.gmailService.getConnection().subscribe({
      next: (conn) => {
        this.gmailConnection = conn;
        this.cd.markForCheck();
      },
      error: () => {
        this.gmailConnection = null;
      }
    });
  }

  loadSentMessages(): void {
    this.loadingMessages = true;
    this.gmailService.getMessages(50, 0).subscribe({
      next: (msgs) => {
        this.sentMessages = msgs || [];
        this.loadingMessages = false;
        this.cd.markForCheck();
      },
      error: () => {
        this.loadingMessages = false;
      }
    });
  }

  loadAutomationSettings(): void {
    this.gmailService.getSettings().subscribe({
      next: (st) => {
        this.settingsModel = st;
        this.cd.markForCheck();
      },
      error: () => {
        // Soft fail
      }
    });
  }

  get filteredDrafts(): OutreachDraft[] {
    if (!this.searchQuery.trim()) return this.drafts;
    const q = this.searchQuery.toLowerCase();
    return this.drafts.filter(d =>
      (d.company_name && d.company_name.toLowerCase().includes(q)) ||
      (d.job_title && d.job_title.toLowerCase().includes(q)) ||
      (d.subject && d.subject.toLowerCase().includes(q))
    );
  }

  get selectedOpportunity(): EligibleOpportunitySummary | undefined {
    return this.opportunities.find(o => o.id === this.formOpportunityId);
  }

  get wordCount(): number {
    if (!this.formBody.trim()) return 0;
    return this.formBody.trim().split(/\s+/).length;
  }

  get charCount(): number {
    return this.formBody ? this.formBody.length : 0;
  }

  get revisions(): OutreachRevision[] {
    return this.selectedDraft?.context_snapshot?.previous_revisions || [];
  }

  get totalRepliesCount(): number {
    return this.sentMessages.reduce((acc, m) => acc + (m.reply_count || 0), 0);
  }

  get canSendWithoutOverride(): boolean {
    if (this.canSendRaw) return true;
    if (this.showDuplicateOverrideOption && this.allowDuplicateOverride) return true;
    return false;
  }

  selectDraft(draft: OutreachDraft): void {
    this.selectedDraft = draft;
    this.formOpportunityId = draft.opportunity_id || '';
    this.formResumeId = draft.resume_id || '';
    this.formPurpose = draft.purpose;
    this.formRecipientType = draft.recipient_type;
    this.formRecipientName = draft.recipient_name || '';
    this.formRecipientRole = draft.recipient_role || '';
    this.formSubject = draft.subject || '';
    this.formBody = draft.body || '';
    this.formUserNotes = draft.user_notes || '';
    this.errorMessage = null;
    this.successMessage = null;
    this.showRevisionHistory = false;
    this.cd.markForCheck();
  }

  startNewDraft(): void {
    this.activeTab = 'editor';
    this.selectedDraft = null;
    this.formSubject = '';
    this.formBody = '';
    this.formUserNotes = '';
    this.formRecipientName = '';
    this.formRecipientRole = '';
    this.errorMessage = null;
    this.successMessage = null;
    this.showRevisionHistory = false;
    if (this.opportunities.length > 0 && !this.formOpportunityId) {
      this.formOpportunityId = this.opportunities[0].id;
    }
    this.cd.markForCheck();
  }

  onOpportunityChange(): void {
    this.errorMessage = null;
  }

  onContentEdited(): void {
    if (this.selectedDraft && !this.selectedDraft.is_user_edited) {
      this.selectedDraft.is_user_edited = true;
    }
  }

  onGenerateClick(): void {
    if (this.selectedDraft && this.selectedDraft.is_user_edited) {
      this.showRegenerateConfirmModal = true;
    } else {
      this.executeGeneration();
    }
  }

  proceedWithRegeneration(): void {
    this.showRegenerateConfirmModal = false;
    this.executeGeneration();
  }

  private executeGeneration(): void {
    if (!this.formOpportunityId && !this.selectedDraft) {
      this.errorMessage = 'Please select a target opportunity first.';
      return;
    }

    this.generating = true;
    this.errorMessage = null;
    this.successMessage = null;

    if (this.selectedDraft) {
      this.outreachService.regenerateDraft(this.selectedDraft.id, {
        purpose: this.formPurpose,
        recipient_type: this.formRecipientType,
        recipient_name: this.formRecipientName || null,
        recipient_role: this.formRecipientRole || null,
        resume_id: this.formResumeId || null
      }).subscribe({
        next: (updated) => {
          this.generating = false;
          this.selectedDraft = updated;
          this.formSubject = updated.subject;
          this.formBody = updated.body;
          this.successMessage = 'AI Outreach draft regenerated successfully with latest profile evidence.';
          this.updateDraftInList(updated);
          this.cd.markForCheck();
        },
        error: (err) => {
          this.generating = false;
          this.errorMessage = err?.error?.detail || 'Failed to regenerate outreach draft.';
          this.cd.markForCheck();
        }
      });
    } else {
      this.outreachService.createDraft({
        opportunity_id: this.formOpportunityId,
        resume_id: this.formResumeId || null,
        purpose: this.formPurpose,
        recipient_type: this.formRecipientType,
        recipient_name: this.formRecipientName || null,
        recipient_role: this.formRecipientRole || null,
        generate_immediately: true
      }).subscribe({
        next: (created) => {
          this.generating = false;
          this.selectedDraft = created;
          this.formSubject = created.subject;
          this.formBody = created.body;
          this.drafts = [created, ...this.drafts];
          this.successMessage = 'Personalized AI Outreach draft created successfully.';
          this.cd.markForCheck();
        },
        error: (err) => {
          this.generating = false;
          this.errorMessage = err?.error?.detail || 'Failed to generate outreach draft.';
          this.cd.markForCheck();
        }
      });
    }
  }

  createManualDraft(): void {
    if (!this.formOpportunityId) {
      this.errorMessage = 'Please select a target opportunity first.';
      return;
    }

    this.generating = true;
    this.errorMessage = null;

    this.outreachService.createDraft({
      opportunity_id: this.formOpportunityId,
      resume_id: this.formResumeId || null,
      purpose: this.formPurpose,
      recipient_type: this.formRecipientType,
      recipient_name: this.formRecipientName || null,
      recipient_role: this.formRecipientRole || null,
      generate_immediately: false
    }).subscribe({
      next: (created) => {
        this.generating = false;
        this.selectedDraft = created;
        this.formSubject = created.subject;
        this.formBody = created.body;
        this.drafts = [created, ...this.drafts];
        this.successMessage = 'Manual starter draft created. Fill in your message and save.';
        this.cd.markForCheck();
      },
      error: (err) => {
        this.generating = false;
        this.errorMessage = err?.error?.detail || 'Failed to create manual starter draft.';
        this.cd.markForCheck();
      }
    });
  }

  saveChanges(): void {
    if (!this.selectedDraft) return;

    this.saving = true;
    this.errorMessage = null;
    this.successMessage = null;

    this.outreachService.updateDraft(this.selectedDraft.id, {
      subject: this.formSubject,
      body: this.formBody,
      purpose: this.formPurpose,
      recipient_type: this.formRecipientType,
      recipient_name: this.formRecipientName || null,
      recipient_role: this.formRecipientRole || null,
      user_notes: this.formUserNotes || null
    }).subscribe({
      next: (updated) => {
        this.saving = false;
        this.selectedDraft = updated;
        this.successMessage = 'Changes saved successfully.';
        this.updateDraftInList(updated);
        this.cd.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.errorMessage = err?.error?.detail || 'Failed to save changes.';
        this.cd.markForCheck();
      }
    });
  }

  confirmDeleteDraft(draft: OutreachDraft, event: Event): void {
    event.stopPropagation();
    const promptMsg = 'Are you sure you want to delete the outreach draft for ' + (draft.company_name || 'this opportunity') + '?';
    if (!confirm(promptMsg)) {
      return;
    }

    this.outreachService.deleteDraft(draft.id).subscribe({
      next: () => {
        this.drafts = this.drafts.filter(d => d.id !== draft.id);
        if (this.selectedDraft?.id === draft.id) {
          this.selectedDraft = this.drafts.length > 0 ? this.drafts[0] : null;
          if (this.selectedDraft) {
            this.selectDraft(this.selectedDraft);
          } else {
            this.startNewDraft();
          }
        }
        this.successMessage = 'Draft deleted successfully.';
        this.cd.markForCheck();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Failed to delete draft.';
        this.cd.markForCheck();
      }
    });
  }

  // --- SEND VIA GMAIL APPROVAL FLOW ---

  openSendPreviewModal(): void {
    if (!this.selectedDraft) return;
    this.sendRecipientEmail = '';
    this.sendRecipientName = this.formRecipientName || this.selectedDraft.recipient_name || '';
    this.sendSubject = this.formSubject;
    this.sendBody = this.formBody;
    this.approvedContentHash = '';
    this.hashInvalidated = false;
    this.previewWarnings = [];
    this.canSendRaw = false;
    this.allowDuplicateOverride = false;
    this.showDuplicateOverrideOption = false;
    this.showSendModal = true;

    // Check if draft user notes contain an email address to prefill
    if (this.formUserNotes) {
      const match = this.formUserNotes.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
      if (match) {
        this.sendRecipientEmail = match[0];
      }
    }

    this.cd.markForCheck();
  }

  closeSendModal(): void {
    this.showSendModal = false;
  }

  onModalContentChanged(): void {
    if (this.approvedContentHash) {
      this.hashInvalidated = true;
    }
  }

  calculatePreviewHash(): void {
    if (!this.selectedDraft || !this.sendRecipientEmail.trim()) {
      this.errorMessage = 'Please provide a valid recipient email address.';
      return;
    }

    this.calculatingHash = true;
    this.gmailService.previewEmail({
      draft_id: this.selectedDraft.id,
      recipient_email: this.sendRecipientEmail,
      recipient_name: this.sendRecipientName || null,
      subject: this.sendSubject,
      body: this.sendBody
    }).subscribe({
      next: (res: OutreachEmailPreviewResponse) => {
        this.calculatingHash = false;
        this.approvedContentHash = res.content_hash;
        this.hashInvalidated = false;
        this.previewWarnings = res.warnings || [];
        this.canSendRaw = res.can_send;
        this.showDuplicateOverrideOption = this.previewWarnings.some(w => w.toLowerCase().includes('already sent'));
        this.cd.markForCheck();
      },
      error: (err) => {
        this.calculatingHash = false;
        this.errorMessage = err?.error?.detail || 'Failed to calculate message approval hash.';
        this.cd.markForCheck();
      }
    });
  }

  executeSend(): void {
    if (!this.selectedDraft || !this.approvedContentHash || this.hashInvalidated) {
      return;
    }

    this.isSending = true;
    this.errorMessage = null;

    this.gmailService.sendEmail({
      draft_id: this.selectedDraft.id,
      recipient_email: this.sendRecipientEmail,
      recipient_name: this.sendRecipientName || null,
      subject: this.sendSubject,
      body: this.sendBody,
      approved_content_hash: this.approvedContentHash,
      allow_recent_duplicate: this.allowDuplicateOverride
    }).subscribe({
      next: (msg: OutreachEmailMessage) => {
        this.isSending = false;
        this.showSendModal = false;
        this.successMessage = `Outreach message sent successfully via Gmail! (ID: ${msg.gmail_message_id || msg.id})`;
        this.sentMessages = [msg, ...this.sentMessages];
        if (this.settingsModel) {
          this.settingsModel.emails_sent_today += 1;
        }
        this.cd.markForCheck();
      },
      error: (err) => {
        this.isSending = false;
        const detail = err?.error?.detail || err?.message || 'Failed to transmit outreach email.';
        this.errorMessage = detail;
        if (detail.toLowerCase().includes('outcome unknown')) {
          this.showSendModal = false;
          this.loadSentMessages();
        }
        this.cd.markForCheck();
      }
    });
  }

  // --- GMAIL OAUTH MODAL ---

  openConnectModal(): void {
    this.oauthAuthCode = '';
    this.oauthState = '';
    this.showConnectModal = true;
    this.gmailService.getOAuthUrl().subscribe({
      next: (res) => {
        this.oauthState = res.state;
      },
      error: () => {
        this.errorMessage = 'Failed to initialize Gmail OAuth session.';
      }
    });
  }

  launchOAuthFlow(): void {
    this.gmailService.getOAuthUrl().subscribe({
      next: (res) => {
        this.oauthState = res.state;
        window.open(res.authorization_url, '_blank', 'width=600,height=700');
      },
      error: () => {
        this.errorMessage = 'Failed to generate Google authorization URL.';
      }
    });
  }

  completeOAuthCallback(): void {
    if (!this.oauthAuthCode.trim()) return;
    this.connectingOAuth = true;
    this.errorMessage = null;

    this.gmailService.exchangeCallback(this.oauthAuthCode.trim(), this.oauthState).subscribe({
      next: (conn) => {
        this.connectingOAuth = false;
        this.gmailConnection = conn;
        this.showConnectModal = false;
        this.successMessage = `Gmail connected successfully (${conn.email_address})!`;
        this.cd.markForCheck();
      },
      error: (err) => {
        this.connectingOAuth = false;
        this.errorMessage = err?.error?.detail || 'Failed to complete Gmail connection.';
        this.cd.markForCheck();
      }
    });
  }

  disconnectGmail(): void {
    if (!confirm('Are you sure you want to disconnect your Gmail account? You will not be able to send emails until you reconnect.')) {
      return;
    }

    this.gmailService.disconnect().subscribe({
      next: () => {
        this.gmailConnection = null;
        this.successMessage = 'Gmail account disconnected successfully.';
        this.cd.markForCheck();
      },
      error: () => {
        this.errorMessage = 'Failed to disconnect Gmail account.';
        this.cd.markForCheck();
      }
    });
  }

  // --- AUTOMATION SETTINGS MODAL ---

  openSettingsModal(): void {
    this.showSettingsModal = true;
    if (!this.settingsModel) {
      this.loadAutomationSettings();
    }
  }

  saveSettings(): void {
    if (!this.settingsModel) return;
    this.savingSettings = true;
    this.gmailService.updateSettings({
      sending_mode: this.settingsModel.sending_mode,
      daily_limit: this.settingsModel.daily_limit,
      cooldown_minutes: this.settingsModel.cooldown_minutes,
      duplicate_suppression_days: this.settingsModel.duplicate_suppression_days,
      is_paused: this.settingsModel.is_paused,
      auto_followup_enabled: this.settingsModel.auto_followup_enabled,
      followup_delay_days: this.settingsModel.followup_delay_days
    }).subscribe({
      next: (st) => {
        this.savingSettings = false;
        this.settingsModel = st;
        this.showSettingsModal = false;
        this.successMessage = 'Outreach automation settings updated successfully.';
        this.cd.markForCheck();
      },
      error: (err) => {
        this.savingSettings = false;
        this.errorMessage = err?.error?.detail || 'Failed to update automation settings.';
        this.cd.markForCheck();
      }
    });
  }

  // --- REPLIES MONITORING ---

  syncReplies(): void {
    this.syncingReplies = true;
    this.errorMessage = null;
    this.gmailService.syncReplies().subscribe({
      next: (res) => {
        this.syncingReplies = false;
        this.successMessage = `Reply sync complete: checked ${res.synced_threads_count} thread(s), found ${res.new_replies_count} new reply(ies).`;
        this.loadSentMessages();
        this.cd.markForCheck();
      },
      error: (err) => {
        this.syncingReplies = false;
        this.errorMessage = err?.error?.detail || 'Failed to synchronize Gmail replies.';
        this.cd.markForCheck();
      }
    });
  }

  toggleRepliesView(msg: OutreachEmailMessage): void {
    if (this.expandedMessageId === msg.id) {
      this.expandedMessageId = null;
      this.activeReplies = [];
      return;
    }

    this.expandedMessageId = msg.id;
    this.loadingReplies = true;
    this.gmailService.getReplies(msg.id).subscribe({
      next: (reps) => {
        this.activeReplies = reps || [];
        this.loadingReplies = false;
        this.cd.markForCheck();
      },
      error: () => {
        this.loadingReplies = false;
        this.activeReplies = [];
      }
    });
  }

  // --- CLIPBOARD & EXPORT ---

  copySubject(): void {
    if (!this.formSubject) return;
    navigator.clipboard.writeText(this.formSubject).then(() => {
      this.copyFeedbackSubject = true;
      setTimeout(() => (this.copyFeedbackSubject = false), 2000);
      this.cd.markForCheck();
    });
  }

  copyBody(): void {
    if (!this.formBody) return;
    navigator.clipboard.writeText(this.formBody).then(() => {
      this.copyFeedbackBody = true;
      setTimeout(() => (this.copyFeedbackBody = false), 2000);
      this.cd.markForCheck();
    });
  }

  copyFullEmail(): void {
    const full = 'Subject: ' + this.formSubject + '\n\n' + this.formBody;
    navigator.clipboard.writeText(full).then(() => {
      this.copyFeedbackAll = true;
      setTimeout(() => (this.copyFeedbackAll = false), 2000);
      this.cd.markForCheck();
    });
  }

  exportTxt(): void {
    const full = 'Subject: ' + this.formSubject + '\n\n' + this.formBody;
    const blob = new Blob([full], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    const company = (this.selectedDraft?.company_name || 'outreach').toLowerCase().replace(/[^a-z0-9]/g, '_');
    a.href = url;
    a.download = 'outreach_' + company + '_' + new Date().toISOString().slice(0, 10) + '.txt';
    a.click();
    window.URL.revokeObjectURL(url);
  }

  restoreRevision(rev: OutreachRevision): void {
    this.formSubject = rev.subject;
    this.formBody = rev.body;
    this.onContentEdited();
    this.successMessage = 'Prior revision restored into editor. Remember to save changes.';
    this.cd.markForCheck();
  }

  private updateDraftInList(updated: OutreachDraft): void {
    const idx = this.drafts.findIndex(d => d.id === updated.id);
    if (idx !== -1) {
      this.drafts[idx] = updated;
    }
  }

  formatRecipient(type: RecipientType): string {
    switch (type) {
      case 'hiring_manager': return 'Hiring Mgr';
      case 'recruiter': return 'Recruiter';
      case 'peer_engineer': return 'Peer';
      case 'alumnus_referral': return 'Alum';
      case 'general_hr': return 'HR';
      default: return 'Contact';
    }
  }
}

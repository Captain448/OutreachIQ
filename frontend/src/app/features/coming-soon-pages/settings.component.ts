import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ProfileService } from '../../core/services/profile.service';
import { GmailService } from '../../core/services/gmail.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { ResumeService } from '../../core/services/resume.service';
import { OutreachService } from '../../core/services/outreach.service';
import { Profile, Preferences } from '../../core/models/profile.model';
import {
  GmailConnection,
  OutreachAutomationSettings,
  SendingMode
} from '../../core/models/gmail.model';
import { ProviderHealth } from '../../core/models/provider.model';

@Component({
  selector: 'app-settings-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="settings-page">
      <!-- Page Header -->
      <header class="page-header">
        <div class="header-left">
          <div class="mode-badge-wrap">
            <span class="iq-pill iq-pill-accent">System Configuration</span>
            <span class="iq-pill iq-pill-neutral">Security & Governance</span>
            <span class="iq-pill iq-pill-success" *ngIf="gmailConnection?.is_active">
              Gmail Active: {{ gmailConnection?.email_address }}
            </span>
          </div>
          <h1 class="page-title">Settings & Governance Control</h1>
          <p class="page-subtitle">
            Configure candidate preferences, Gmail email dispatch limits, agent autonomy modes, and inspect external search provider health.
          </p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" (click)="loadAllSettings()" [disabled]="loading">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6"></path>
              <path d="M1 20v-6h6"></path>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh Settings
          </button>
        </div>
      </header>

      <!-- Feedback Banner -->
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

      <div class="settings-grid">
        <!-- 1. OUTREACH & GMAIL AUTONOMY GOVERNANCE -->
        <section class="iq-card">
          <div class="card-header">
            <div class="card-header-icon gmail-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
              </svg>
            </div>
            <div>
              <h2 class="card-title">Outreach & Gmail Sending Governance</h2>
              <p class="card-desc">Control automated email transmission thresholds and emergency safety policies.</p>
            </div>
          </div>

          <!-- Global Pause Switch -->
          <div class="pause-switch-banner" [class.paused]="automationSettings?.is_paused">
            <div class="pause-info">
              <span class="pause-title">Global Outreach Transmission Killswitch</span>
              <p class="pause-desc">
                {{ automationSettings?.is_paused ? 'OUTREACH SENDING IS CURRENTLY PAUSED. No emails can be transmitted.' : 'Sending is active. Emails can be transmitted according to your autonomy policy.' }}
              </p>
            </div>
            <label class="toggle-switch">
              <input
                type="checkbox"
                [ngModel]="automationSettings?.is_paused"
                (ngModelChange)="toggleGlobalPause($event)"
              />
              <span class="slider round"></span>
            </label>
          </div>

          <!-- Gmail Account Status -->
          <div class="account-status-box">
            <div class="status-left">
              <span class="status-label">Gmail OAuth Account:</span>
              <strong *ngIf="gmailConnection?.is_active" class="account-email text-success">
                ● Connected: {{ gmailConnection?.email_address }}
              </strong>
              <strong *ngIf="!gmailConnection?.is_active" class="account-email text-muted">
                ○ No Gmail Account Linked
              </strong>
            </div>
            <div class="status-actions">
              <button
                *ngIf="!gmailConnection?.is_active"
                class="btn btn-sm btn-gmail-connect"
                (click)="openConnectModal()"
              >
                Connect Gmail
              </button>
              <button
                *ngIf="gmailConnection?.is_active"
                class="btn btn-sm btn-outline-danger"
                (click)="disconnectGmail()"
              >
                Disconnect
              </button>
            </div>
          </div>

          <!-- Autonomy Policies Form -->
          <div class="form-section" *ngIf="automationSettings">
            <div class="form-group">
              <label class="form-label">
                Agent Autonomy Mode
                <span class="info-tag">Enforces Approval Guardrails</span>
              </label>
              <select class="form-control" [(ngModel)]="automationSettings.sending_mode">
                <option value="DRAFT_ONLY">Draft Only (Autonomous sending completely disabled)</option>
                <option value="REVIEW_BEFORE_SEND">Review Before Send (Manual review & cryptographic approval hash required)</option>
                <option value="AUTO_SEND_OPT_IN">Auto-Send Opt-In (Direct send upon candidate trigger)</option>
              </select>
              <span class="field-hint">
                Current mode: <strong>{{ formatMode(automationSettings.sending_mode) }}</strong>
              </span>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Daily Sending Quota</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  class="form-control"
                  [(ngModel)]="automationSettings.daily_limit"
                />
                <span class="field-hint">
                  Sent today: <strong>{{ automationSettings.emails_sent_today }} / {{ automationSettings.daily_limit }}</strong>
                </span>
              </div>

              <div class="form-group">
                <label class="form-label">Burst Cooldown (Minutes)</label>
                <input
                  type="number"
                  min="0"
                  max="1440"
                  class="form-control"
                  [(ngModel)]="automationSettings.cooldown_minutes"
                />
                <span class="field-hint">Minimum interval enforced between transmissions</span>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Duplicate Suppression Window (Days)</label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  class="form-control"
                  [(ngModel)]="automationSettings.duplicate_suppression_days"
                />
                <span class="field-hint">Suppresses sending repeated emails to identical addresses</span>
              </div>

              <div class="form-group">
                <label class="form-label">Automated Follow-up Delay (Days)</label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  class="form-control"
                  [(ngModel)]="automationSettings.followup_delay_days"
                />
                <span class="field-hint">Follow-ups auto-suppressed if recruiter replies</span>
              </div>
            </div>

            <div class="action-bar">
              <button
                class="btn btn-primary"
                (click)="saveAutomationSettings()"
                [disabled]="savingSettings"
              >
                <span *ngIf="savingSettings" class="spinner-sm"></span>
                {{ savingSettings ? 'Saving Governance...' : 'Save Outreach Policies' }}
              </button>
            </div>
          </div>
        </section>

        <!-- 2. CAREER PREFERENCES & PROFILE SETTINGS -->
        <section class="iq-card">
          <div class="card-header">
            <div class="card-header-icon profile-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>
            <div>
              <h2 class="card-title">Candidate Career Preferences</h2>
              <p class="card-desc">Grounding constraints used for discovery query generation and match scoring.</p>
            </div>
          </div>

          <div class="form-section" *ngIf="profileModel && profileModel.preferences">
            <div class="form-group">
              <label class="form-label">Candidate Name & Headline</label>
              <div class="static-val-box">
                <strong>{{ (authService.currentUser$ | async)?.full_name || 'Candidate' }}</strong>
                <span class="sub-val">{{ profileModel.headline || 'No headline specified' }}</span>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Work Arrangement</label>
                <select class="form-control" [(ngModel)]="profileModel.preferences.remote_preference">
                  <option value="flexible">Flexible / Any</option>
                  <option value="remote">Strictly Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">On-site Only</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Experience Level</label>
                <select class="form-control" [(ngModel)]="profileModel.preferences.experience_level">
                  <option value="entry">Entry-Level / Graduate</option>
                  <option value="mid">Mid-Level Engineer</option>
                  <option value="senior">Senior Engineer</option>
                  <option value="lead">Tech Lead / Staff</option>
                  <option value="executive">Director / VP</option>
                </select>
              </div>
            </div>

            <div class="form-row-2">
              <div class="form-group">
                <label class="form-label">Employment Preference</label>
                <select class="form-control" [(ngModel)]="profileModel.preferences.employment_preference">
                  <option value="full-time">Full-Time Direct Hire</option>
                  <option value="internship">Internship / Apprenticeship</option>
                  <option value="contract">Contract / Freelance</option>
                  <option value="part-time">Part-Time</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Target Locations (comma separated)</label>
                <input
                  type="text"
                  class="form-control"
                  [ngModel]="profileModel.preferences.preferred_locations.join(', ')"
                  (ngModelChange)="onPreferredLocationsChange($event)"
                  placeholder="e.g. San Francisco, CA, Remote, New York, NY"
                />
              </div>
            </div>

            <div class="action-bar">
              <button
                class="btn btn-primary"
                (click)="saveProfilePreferences()"
                [disabled]="savingProfile"
              >
                <span *ngIf="savingProfile" class="spinner-sm"></span>
                {{ savingProfile ? 'Updating Profile...' : 'Save Career Preferences' }}
              </button>
              <a routerLink="/profile" class="btn btn-secondary">
                Edit Full Profile & Skills ↗
              </a>
            </div>
          </div>
        </section>

        <!-- 3. RESEARCH & DISCOVERY PROVIDER TELEMETRY -->
        <section class="iq-card col-span-2">
          <div class="card-header">
            <div class="card-header-icon provider-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
            </div>
            <div>
              <h2 class="card-title">Job Discovery & Web Research Provider Telemetry</h2>
              <p class="card-desc">Real-time health status of external search APIs and listing extraction adapters.</p>
            </div>
          </div>

          <div class="provider-cards-grid">
            <div *ngFor="let p of providerStatuses" class="provider-status-card">
              <div class="prov-top">
                <strong class="prov-name">{{ p.display_name || p.provider_name }}</strong>
                <span class="prov-badge" [class.badge-healthy]="p.status === 'active'" [class.badge-degraded]="p.status !== 'active'">
                  {{ p.status === 'active' ? 'HEALTHY' : (p.status | uppercase) }}
                </span>
              </div>
              <p class="prov-desc">{{ p.quota_limit_info || getProviderDescription(p.provider_name) }}</p>
              <div class="prov-meta">
                <span>Latency: <strong>{{ p.latency_ms ? p.latency_ms + 'ms' : 'N/A' }}</strong></span>
                <span>Configured: <strong>{{ p.is_configured ? 'YES' : 'NO' }}</strong></span>
              </div>
            </div>
          </div>
        </section>

        <!-- 4. WORKSPACE DATA RETENTION SUMMARY -->
        <section class="iq-card col-span-2">
          <div class="card-header">
            <div class="card-header-icon storage-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
            </div>
            <div>
              <h2 class="card-title">Account Inventory & Data Retention</h2>
              <p class="card-desc">Summary of candidate documents, evidence records, and outreach logs stored in OutReachIQ.</p>
            </div>
          </div>

          <div class="stats-counters-row">
            <div class="stat-box">
              <span class="stat-number">{{ resumeCount }}</span>
              <span class="stat-title">Targeted Resumes</span>
              <a routerLink="/resumes" class="stat-link">Manage →</a>
            </div>
            <div class="stat-box">
              <span class="stat-number">{{ opportunityCount }}</span>
              <span class="stat-title">Discovered Opportunities</span>
              <a routerLink="/opportunities" class="stat-link">Explore →</a>
            </div>
            <div class="stat-box">
              <span class="stat-number">{{ draftCount }}</span>
              <span class="stat-title">Grounded Outreach Drafts</span>
              <a routerLink="/outreach" class="stat-link">View Drafts →</a>
            </div>
            <div class="stat-box">
              <span class="stat-number">{{ sentMessagesCount }}</span>
              <span class="stat-title">Gmail Transmissions</span>
              <a routerLink="/outreach" class="stat-link">View Audit →</a>
            </div>
          </div>
        </section>
      </div>

      <!-- CONNECT GMAIL MODAL -->
      <div class="modal-backdrop" *ngIf="showConnectModal">
        <div class="modal-card">
          <div class="modal-header">
            <h3 class="modal-title">Link Authorized Gmail Account</h3>
            <button class="modal-close" (click)="showConnectModal = false">×</button>
          </div>
          <div class="modal-body">
            <p>
              Grant OutReachIQ permission to transmit approved outreach messages and monitor thread replies.
            </p>
            <div class="oauth-box">
              <p class="oauth-desc">Step 1: Open Google OAuth authorization window:</p>
              <button class="btn btn-primary" (click)="launchOAuthFlow()">
                Open Google Login Window
              </button>
            </div>
            <div class="oauth-manual-step">
              <p class="manual-step-title">Step 2: Enter Authorization Code</p>
              <input
                type="text"
                class="form-control"
                [(ngModel)]="oauthAuthCode"
                placeholder="Paste authorization code here"
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
              {{ connectingOAuth ? 'Linking...' : 'Complete Connection' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .settings-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }

    @media (max-width: 768px) {
      .settings-page {
        padding: 16px;
      }
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
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
      font-size: 13.5px;
      color: var(--text-secondary);
      max-width: 820px;
      line-height: 1.5;
    }

    .feedback-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      margin-bottom: 20px;
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

    .settings-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 24px;
    }

    @media (max-width: 1024px) {
      .settings-grid {
        grid-template-columns: 1fr;
      }
      .col-span-2 {
        grid-column: span 1 !important;
      }
    }

    .col-span-2 {
      grid-column: span 2;
    }

    .iq-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .card-header {
      display: flex;
      align-items: flex-start;
      gap: 14px;
    }

    .card-header-icon {
      width: 40px;
      height: 40px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .gmail-icon {
      background: #fef2f2;
      color: #ea4335;
    }

    .profile-icon {
      background: #eff6ff;
      color: #2563eb;
    }

    .provider-icon {
      background: #ecfdf5;
      color: #059669;
    }

    .storage-icon {
      background: #fdf4ff;
      color: #c026d3;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 2px 0;
    }

    .card-desc {
      font-size: 13px;
      color: var(--text-secondary);
      margin: 0;
    }

    /* Pause switch banner */
    .pause-switch-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 18px;
      border-radius: var(--radius-sm);
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
    }

    .pause-switch-banner.paused {
      background: #fef2f2;
      border-color: #fecaca;
    }

    .pause-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      display: block;
      margin-bottom: 2px;
    }

    .pause-desc {
      font-size: 12px;
      color: var(--text-secondary);
      margin: 0;
    }

    .toggle-switch {
      position: relative;
      display: inline-block;
      width: 48px;
      height: 26px;
      flex-shrink: 0;
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
      background-color: #cbd5e1;
      transition: .3s;
      border-radius: 26px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 20px; width: 20px;
      left: 3px; bottom: 3px;
      background-color: white;
      transition: .3s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: #ea4335;
    }

    input:checked + .slider:before {
      transform: translateX(22px);
    }

    /* Account status box */
    .account-status-box {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-radius: var(--radius-sm);
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
    }

    .status-label {
      font-size: 12px;
      color: var(--text-secondary);
      display: block;
      margin-bottom: 2px;
    }

    .account-email {
      font-size: 13px;
    }

    .btn-gmail-connect {
      background: #ea4335;
      color: #fff;
      border: none;
      font-weight: 600;
    }

    .btn-outline-danger {
      background: transparent;
      border: 1px solid #ea4335;
      color: #ea4335;
      font-weight: 600;
    }

    /* Form section */
    .form-section {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-row-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
      display: flex;
      justify-content: space-between;
    }

    .info-tag {
      font-size: 11px;
      font-weight: 500;
      color: var(--text-muted);
    }

    .form-control {
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: var(--bg-surface);
      color: var(--text-primary);
      font-size: 13px;
    }

    .field-hint {
      font-size: 11px;
      color: var(--text-muted);
    }

    .static-val-box {
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: var(--bg-subtle);
      display: flex;
      flex-direction: column;
      gap: 2px;
      font-size: 13px;
    }

    .sub-val {
      font-size: 12px;
      color: var(--text-muted);
    }

    .action-bar {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 6px;
    }

    /* Provider telemetry cards */
    .provider-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }

    .provider-status-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .prov-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .prov-name {
      font-size: 13px;
      color: var(--text-primary);
    }

    .prov-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .badge-healthy {
      background: #ecfdf5;
      color: #059669;
    }

    .badge-degraded {
      background: #fef2f2;
      color: #b91c1c;
    }

    .prov-desc {
      font-size: 11px;
      color: var(--text-secondary);
      margin: 0;
      line-height: 1.4;
    }

    .prov-meta {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-muted);
      border-top: 1px solid var(--border-color);
      padding-top: 6px;
      margin-top: 4px;
    }

    /* Stats row */
    .stats-counters-row {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }

    @media (max-width: 768px) {
      .stats-counters-row {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .stat-box {
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 4px;
    }

    .stat-number {
      font-size: 24px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-title {
      font-size: 12px;
      color: var(--text-secondary);
    }

    .stat-link {
      font-size: 12px;
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      margin-top: 4px;
    }

    /* Modals */
    .modal-backdrop {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.5);
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
      max-width: 500px;
      width: 100%;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0,0,0,0.2);
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
    }

    .modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      padding: 14px 20px;
      border-top: 1px solid var(--border-color);
      background: var(--bg-surface);
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
      margin-bottom: 10px;
    }

    .oauth-manual-step {
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
    }

    .manual-step-title {
      font-size: 13px;
      font-weight: 600;
      margin: 0 0 6px 0;
    }

    .spinner-sm {
      display: inline-block;
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
  `]
})
export class SettingsComponent implements OnInit {
  authService = inject(AuthService);
  private profileService = inject(ProfileService);
  private gmailService = inject(GmailService);
  private oppService = inject(OpportunityService);
  private resumeService = inject(ResumeService);
  private outreachService = inject(OutreachService);
  private cd = inject(ChangeDetectorRef);

  loading: boolean = false;
  savingSettings: boolean = false;
  savingProfile: boolean = false;
  connectingOAuth: boolean = false;

  successMessage: string | null = null;
  errorMessage: string | null = null;

  // Gmail & Automation
  gmailConnection: GmailConnection | null = null;
  automationSettings: OutreachAutomationSettings | null = null;

  // Profile Preferences
  profileModel: Profile | null = null;

  // Telemetry & Inventory
  providerStatuses: ProviderHealth[] = [];
  resumeCount: number = 0;
  opportunityCount: number = 0;
  draftCount: number = 0;
  sentMessagesCount: number = 0;

  // Modal
  showConnectModal: boolean = false;
  oauthAuthCode: string = '';
  oauthState: string = '';

  ngOnInit(): void {
    this.loadAllSettings();
  }

  loadAllSettings(): void {
    this.loading = true;
    this.errorMessage = null;

    // Load Profile
    this.profileService.getProfile().subscribe({
      next: (prof) => {
        this.profileModel = prof;
        if (!this.profileModel.preferences) {
          this.profileModel.preferences = {
            desired_roles: [],
            preferred_industries: [],
            preferred_locations: [],
            remote_preference: 'flexible',
            experience_level: 'mid',
            employment_preference: 'full-time'
          };
        }
        this.cd.markForCheck();
      },
      error: () => {}
    });

    // Load Gmail Connection & Settings
    this.gmailService.getConnection().subscribe({
      next: (conn) => {
        this.gmailConnection = conn;
        this.cd.markForCheck();
      },
      error: () => {
        this.gmailConnection = null;
      }
    });

    this.gmailService.getSettings().subscribe({
      next: (st) => {
        this.automationSettings = st;
        this.cd.markForCheck();
      },
      error: () => {}
    });

    // Load Provider Health
    this.oppService.getProviderHealth().subscribe({
      next: (statuses) => {
        this.providerStatuses = statuses || [];
        this.cd.markForCheck();
      },
      error: () => {
        this.providerStatuses = [];
      }
    });

    // Load Inventory Stats
    this.resumeService.getResumes().subscribe({
      next: (res) => { this.resumeCount = res?.length || 0; this.cd.markForCheck(); },
      error: () => {}
    });

    this.oppService.getOpportunities().subscribe({
      next: (opps) => { this.opportunityCount = opps?.length || 0; this.cd.markForCheck(); },
      error: () => {}
    });

    this.outreachService.getDrafts().subscribe({
      next: (res) => { this.draftCount = res?.items?.length || 0; this.cd.markForCheck(); },
      error: () => {}
    });

    this.gmailService.getMessages(1, 0).subscribe({
      next: (msgs) => { this.sentMessagesCount = msgs?.length || 0; this.cd.markForCheck(); },
      error: () => {}
    });

    this.loading = false;
  }

  formatMode(mode: SendingMode): string {
    switch (mode) {
      case 'DRAFT_ONLY': return 'Draft Only';
      case 'REVIEW_BEFORE_SEND': return 'Review Before Send';
      case 'AUTO_SEND_OPT_IN': return 'Auto-Send Opt-In';
      default: return mode;
    }
  }

  getProviderDescription(name: string): string {
    const n = name.toLowerCase();
    if (n.includes('tavily')) return 'Deep company signal intelligence & web search adapter.';
    if (n.includes('exa')) return 'Neural web search & targeted company discovery engine.';
    if (n.includes('jsearch')) return 'Aggregated search API for LinkedIn, Indeed & Glassdoor.';
    if (n.includes('adzuna')) return 'Direct multi-country advertised job search feed.';
    if (n.includes('jooble')) return 'International jobs index and publisher network.';
    return 'External discovery and listing verification provider.';
  }

  toggleGlobalPause(newPausedVal: boolean): void {
    if (!this.automationSettings) return;
    this.automationSettings.is_paused = newPausedVal;
    this.saveAutomationSettings();
  }

  saveAutomationSettings(): void {
    if (!this.automationSettings) return;
    this.savingSettings = true;
    this.errorMessage = null;

    this.gmailService.updateSettings({
      sending_mode: this.automationSettings.sending_mode,
      daily_limit: this.automationSettings.daily_limit,
      cooldown_minutes: this.automationSettings.cooldown_minutes,
      duplicate_suppression_days: this.automationSettings.duplicate_suppression_days,
      is_paused: this.automationSettings.is_paused,
      followup_delay_days: this.automationSettings.followup_delay_days
    }).subscribe({
      next: (st) => {
        this.savingSettings = false;
        this.automationSettings = st;
        this.successMessage = 'Outreach automation & governance policies saved successfully.';
        this.cd.markForCheck();
      },
      error: (err) => {
        this.savingSettings = false;
        this.errorMessage = err?.error?.detail || 'Failed to save automation settings.';
        this.cd.markForCheck();
      }
    });
  }

  onPreferredLocationsChange(val: string): void {
    if (this.profileModel?.preferences) {
      this.profileModel.preferences.preferred_locations = val.split(',').map(s => s.trim()).filter(Boolean);
    }
  }

  saveProfilePreferences(): void {
    if (!this.profileModel) return;
    this.savingProfile = true;
    this.errorMessage = null;

    this.profileService.updateProfile({
      preferences: this.profileModel.preferences
    }).subscribe({
      next: (prof) => {
        this.savingProfile = false;
        this.profileModel = prof;
        this.successMessage = 'Candidate career preferences saved successfully.';
        this.cd.markForCheck();
      },
      error: (err) => {
        this.savingProfile = false;
        this.errorMessage = err?.error?.detail || 'Failed to update preferences.';
        this.cd.markForCheck();
      }
    });
  }

  openConnectModal(): void {
    this.oauthAuthCode = '';
    this.oauthState = '';
    this.showConnectModal = true;
    this.gmailService.getOAuthUrl().subscribe({
      next: (res) => { this.oauthState = res.state; },
      error: () => { this.errorMessage = 'Failed to generate OAuth URL.'; }
    });
  }

  launchOAuthFlow(): void {
    this.gmailService.getOAuthUrl().subscribe({
      next: (res) => {
        this.oauthState = res.state;
        window.open(res.authorization_url, '_blank', 'width=600,height=700');
      },
      error: () => { this.errorMessage = 'Failed to launch Google authorization window.'; }
    });
  }

  completeOAuthCallback(): void {
    if (!this.oauthAuthCode.trim()) return;
    this.connectingOAuth = true;
    this.gmailService.exchangeCallback(this.oauthAuthCode.trim(), this.oauthState).subscribe({
      next: (conn) => {
        this.connectingOAuth = false;
        this.gmailConnection = conn;
        this.showConnectModal = false;
        this.successMessage = `Gmail linked successfully (${conn.email_address})!`;
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
    if (!confirm('Are you sure you want to disconnect your Gmail account?')) return;
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
}

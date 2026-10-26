import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ProfileService } from '../../core/services/profile.service';
import { ResumeService } from '../../core/services/resume.service';
import { IntelligenceService } from '../../core/services/intelligence.service';
import { OpportunityService } from '../../core/services/opportunity.service';
import { CosgoService } from '../../core/services/cosgo.service';
import { OutreachService } from '../../core/services/outreach.service';
import { GmailService } from '../../core/services/gmail.service';
import { Profile } from '../../core/models/profile.model';
import { Resume } from '../../core/models/resume.model';
import { CandidateIntelligenceRepresentation } from '../../core/models/intelligence.model';
import { Opportunity } from '../../core/models/opportunity.model';
import { CosgoRun } from '../../core/models/cosgo.model';
import { OutreachDraft } from '../../core/models/outreach.model';
import { GmailConnection, OutreachEmailMessage } from '../../core/models/gmail.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="dashboard-page">
      <!-- Top Header / Welcome -->
      <header class="page-header">
        <div>
          <h1 class="page-title">
            Welcome back, {{ (authService.currentUser$ | async)?.full_name || 'Candidate' }}
          </h1>
          <p class="page-subtitle">
            OutReachIQ Autonomous Career Agent — Evidence-Grounded Unified Mission Control
          </p>
        </div>
        <div class="header-actions">
          <a routerLink="/opportunities" class="btn btn-secondary">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Find Opportunities
          </a>
          <a routerLink="/outreach" class="btn btn-primary">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
              <polyline points="22,6 12,13 2,6"></polyline>
            </svg>
            Craft Outreach
          </a>
        </div>
      </header>

      <!-- Key Platform Metrics Banner -->
      <div class="metrics-strip">
        <div class="metric-card">
          <span class="metric-val">{{ profile?.completeness_score || 0 }}%</span>
          <span class="metric-lbl">Profile Completeness</span>
          <span class="metric-sub">{{ profile?.skills?.length || 0 }} verified skill(s)</span>
        </div>
        <div class="metric-card">
          <span class="metric-val">{{ resumes.length }}</span>
          <span class="metric-lbl">Active Resumes</span>
          <span class="metric-sub">{{ preferredResume ? preferredResume.target_role : 'General' }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-val">{{ opportunities.length }}</span>
          <span class="metric-lbl">Discovered Roles</span>
          <span class="metric-sub">{{ verifiedOpportunitiesCount }} verified active</span>
        </div>
        <div class="metric-card">
          <span class="metric-val text-accent">
            {{ latestCosgoRun ? (latestCosgoRun.projected_coverage * 100).toFixed(0) + '%' : 'N/A' }}
          </span>
          <span class="metric-lbl">COSGO Target Fit</span>
          <span class="metric-sub">{{ latestCosgoRun ? latestCosgoRun.actions.length + ' roadmap skills' : 'Not run' }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-val" [class.text-success]="repliesCount > 0">
            {{ outreachDrafts.length }}
          </span>
          <span class="metric-lbl">Outreach Drafts</span>
          <span class="metric-sub" *ngIf="repliesCount === 0">{{ sentMessages.length }} sent via Gmail</span>
          <span class="metric-sub text-success" *ngIf="repliesCount > 0">
            <strong>{{ repliesCount }} recruiter reply(ies)</strong>
          </span>
        </div>
      </div>

      <!-- Main Dashboard Grid -->
      <div class="dashboard-grid">
        <!-- 1. Top Target Opportunities Card -->
        <div class="iq-card">
          <div class="card-header-row">
            <div>
              <h3 class="card-title">Top Matched Opportunities</h3>
              <p class="card-desc">Grounded opportunities aligned with your verified candidate evidence</p>
            </div>
            <a routerLink="/opportunities" class="link-action">Explore All ({{ opportunities.length }}) →</a>
          </div>

          <div *ngIf="opportunities.length === 0" class="empty-state-box">
            <p>No discovered opportunities found yet. Run an automated or targeted search across multiple locations.</p>
            <a routerLink="/opportunities" class="btn btn-secondary btn-sm" style="margin-top: 10px;">
              Discover Opportunities
            </a>
          </div>

          <div *ngIf="opportunities.length > 0" class="opp-mini-list">
            <div *ngFor="let opp of topOpportunities" class="opp-mini-item">
              <div class="opp-info">
                <div class="opp-title-line">
                  <span class="opp-job-title">{{ opp.job ? opp.job.title : (opp.company ? opp.company.name : 'Target Role') }}</span>
                  <span class="fit-badge" [class.fit-high]="opp.match_score >= 0.75">
                    {{ (opp.match_score * 100).toFixed(0) }}% Fit
                  </span>
                </div>
                <div class="opp-meta-line">
                  <span>{{ opp.company?.name || opp.job?.company_name }}</span>
                  <span>•</span>
                  <span>{{ opp.job?.location || opp.company?.headquarters || 'Remote' }}</span>
                  <span *ngIf="opp.job?.verification_status === 'VERIFIED_OPEN'" class="verified-tag">
                    ✓ Verified Open
                  </span>
                </div>
              </div>
              <div class="opp-actions">
                <a
                  [routerLink]="['/outreach']"
                  [queryParams]="{ opportunityId: opp.id }"
                  class="btn btn-sm btn-primary"
                  title="Draft personalized AI outreach for this role"
                >
                  Draft Outreach
                </a>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. COSGO Skill Gap & Roadmap Optimization Card -->
        <div class="iq-card">
          <div class="card-header-row">
            <div>
              <h3 class="card-title">COSGO Skill Gap Optimization</h3>
              <p class="card-desc">Maximized multi-opportunity coverage within candidate learning budget</p>
            </div>
            <a routerLink="/skill-gap" class="link-action">View Roadmap →</a>
          </div>

          <div *ngIf="!latestCosgoRun" class="empty-state-box">
            <p>No skill-gap optimization generated yet. Analyze your cross-opportunity gaps to build a learning roadmap.</p>
            <a routerLink="/skill-gap" class="btn btn-secondary btn-sm" style="margin-top: 10px;">
              Run COSGO Optimizer
            </a>
          </div>

          <div *ngIf="latestCosgoRun" class="cosgo-summary-content">
            <div class="cosgo-stat-row">
              <div class="cosgo-coverage-box">
                <span class="cosgo-stat-num text-success">
                  {{ (latestCosgoRun.projected_coverage * 100).toFixed(1) }}%
                </span>
                <span class="cosgo-stat-lbl">Projected Coverage</span>
              </div>
              <div class="cosgo-coverage-box">
                <span class="cosgo-stat-num">
                  +{{ (latestCosgoRun.marginal_coverage_increase * 100).toFixed(1) }} pp
                </span>
                <span class="cosgo-stat-lbl">Coverage Gain</span>
              </div>
              <div class="cosgo-coverage-box">
                <span class="cosgo-stat-num">
                  {{ latestCosgoRun.diagnostics?.budget_hours_used ?? latestCosgoRun.budget_hours }} hrs
                </span>
                <span class="cosgo-stat-lbl">Budget Used</span>
              </div>
            </div>

            <div class="cosgo-actions-preview" *ngIf="latestCosgoRun.actions.length > 0">
              <span class="sub-header-lbl">High-Leverage Skill Investments:</span>
              <div *ngFor="let act of latestCosgoRun.actions.slice(0, 3)" class="cosgo-mini-action">
                <div class="act-name-col">
                  <strong>#{{ act.priority_rank }} {{ act.skill_name }}</strong>
                  <span class="act-why">{{ act.why_recommended }}</span>
                </div>
                <div class="act-effort-col">
                  <span class="badge badge-hours">{{ act.estimated_hours }}h</span>
                  <span class="gain-sub">+{{ (act.marginal_coverage_gain * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 3. Outreach & Gmail Controlled Automation Card -->
        <div class="iq-card">
          <div class="card-header-row">
            <div>
              <h3 class="card-title">Outreach & Gmail Automation</h3>
              <p class="card-desc">Grounding drafts, cryptographic hash approval, and thread reply monitoring</p>
            </div>
            <a routerLink="/outreach" class="link-action">Open Workspace →</a>
          </div>

          <div class="outreach-dashboard-box">
            <div class="gmail-conn-status" [class.status-connected]="gmailConnection?.is_active">
              <div class="conn-dot"></div>
              <div class="conn-text">
                <strong *ngIf="gmailConnection?.is_active">
                  Gmail Account Active: {{ gmailConnection?.email_address }}
                </strong>
                <strong *ngIf="!gmailConnection?.is_active" class="text-muted">
                  Gmail Disconnected (Drafts ready to review)
                </strong>
              </div>
              <a routerLink="/settings" class="btn btn-xs btn-secondary">
                Configure
              </a>
            </div>

            <div class="outreach-stats-mini-row">
              <div class="mini-stat">
                <span class="stat-big">{{ outreachDrafts.length }}</span>
                <span class="stat-small">Grounded Drafts</span>
              </div>
              <div class="mini-stat">
                <span class="stat-big">{{ sentMessages.length }}</span>
                <span class="stat-small">Emails Sent</span>
              </div>
              <div class="mini-stat" [class.stat-highlight]="repliesCount > 0">
                <span class="stat-big">{{ repliesCount }}</span>
                <span class="stat-small">Replies Logged</span>
              </div>
            </div>

            <div class="recent-drafts-mini" *ngIf="outreachDrafts.length > 0">
              <span class="sub-header-lbl">Recent Draft:</span>
              <div class="draft-preview-strip" (click)="goToDraft(outreachDrafts[0])">
                <div class="draft-title-box">
                  <strong>{{ outreachDrafts[0].company_name || 'Target Company' }}</strong>
                  <span class="draft-subj">{{ outreachDrafts[0].subject || '(Untitled subject)' }}</span>
                </div>
                <span class="status-pill status-{{ (outreachDrafts[0].generation_status || 'draft').toLowerCase() }}">
                  {{ outreachDrafts[0].generation_status || 'DRAFT' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 4. Unified Next Steps / Workflow Progress -->
        <div class="iq-card">
          <div class="card-header-row">
            <div>
              <h3 class="card-title">Candidate Journey Progress</h3>
              <p class="card-desc">Track your end-to-end autonomous opportunity workflow</p>
            </div>
          </div>

          <div class="next-steps-list">
            <!-- Step 1: Profile -->
            <div class="step-item" [class.step-done]="profile?.headline && profile?.bio">
              <span class="step-check">{{ (profile?.headline && profile?.bio) ? '✓' : '1' }}</span>
              <div class="step-body">
                <span class="step-name">Complete Profile & Verified Skills</span>
                <span class="step-sub">{{ profile?.skills?.length || 0 }} skills recorded</span>
              </div>
              <a *ngIf="!profile?.headline || !profile?.bio" routerLink="/profile" class="btn btn-secondary btn-sm">Start</a>
            </div>

            <!-- Step 2: Resume -->
            <div class="step-item" [class.step-done]="resumes.length > 0">
              <span class="step-check">{{ (resumes.length > 0) ? '✓' : '2' }}</span>
              <div class="step-body">
                <span class="step-name">Upload Targeted Resume</span>
                <span class="step-sub">{{ resumes.length }} version(s) uploaded</span>
              </div>
              <a *ngIf="resumes.length === 0" routerLink="/resumes" class="btn btn-secondary btn-sm">Upload</a>
            </div>

            <!-- Step 3: Discover -->
            <div class="step-item" [class.step-done]="opportunities.length > 0">
              <span class="step-check">{{ (opportunities.length > 0) ? '✓' : '3' }}</span>
              <div class="step-body">
                <span class="step-name">Discover Opportunities</span>
                <span class="step-sub">{{ opportunities.length }} opportunities discovered</span>
              </div>
              <a *ngIf="opportunities.length === 0" routerLink="/opportunities" class="btn btn-secondary btn-sm">Discover</a>
            </div>

            <!-- Step 4: COSGO -->
            <div class="step-item" [class.step-done]="!!latestCosgoRun">
              <span class="step-check">{{ latestCosgoRun ? '✓' : '4' }}</span>
              <div class="step-body">
                <span class="step-name">Optimize Skill Gaps (COSGO)</span>
                <span class="step-sub">{{ latestCosgoRun ? 'Roadmap computed' : 'Unbudgeted' }}</span>
              </div>
              <a *ngIf="!latestCosgoRun" routerLink="/skill-gap" class="btn btn-secondary btn-sm">Optimize</a>
            </div>

            <!-- Step 5: Outreach & Dispatch -->
            <div class="step-item" [class.step-done]="outreachDrafts.length > 0">
              <span class="step-check">{{ (outreachDrafts.length > 0) ? '✓' : '5' }}</span>
              <div class="step-body">
                <span class="step-name">Synthesize Grounded Outreach</span>
                <span class="step-sub">{{ outreachDrafts.length }} drafts, {{ sentMessages.length }} sent</span>
              </div>
              <a *ngIf="outreachDrafts.length === 0" routerLink="/outreach" class="btn btn-secondary btn-sm">Draft</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Grounding Notice Footer -->
      <div class="grounding-footer-note">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 16v-4"></path>
          <path d="M12 8h.01"></path>
        </svg>
        <span>
          <strong>Evidence Grounding Guarantee:</strong> OutReachIQ enforces strict critic verification across all modules. No fabricated skill metrics, false employer identities, or unverified claims are permitted.
        </span>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }

    @media (max-width: 768px) {
      .dashboard-page {
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

    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.02em;
      margin: 0 0 4px 0;
    }

    .page-subtitle {
      font-size: 13.5px;
      color: var(--text-secondary);
      margin: 0;
    }

    .header-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    /* Metrics Strip */
    .metrics-strip {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      margin-bottom: 24px;
    }

    @media (max-width: 1100px) {
      .metrics-strip {
        grid-template-columns: repeat(3, 1fr);
      }
    }

    @media (max-width: 680px) {
      .metrics-strip {
        grid-template-columns: 1fr 1fr;
      }
    }

    @media (max-width: 440px) {
      .metrics-strip {
        grid-template-columns: 1fr;
      }
    }

    .metric-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 96px;
      box-shadow: var(--shadow-xs);
      transition: all 0.15s ease;
    }

    .metric-card:hover {
      border-color: var(--border-strong);
      box-shadow: var(--shadow-card);
    }

    .metric-val {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      line-height: 1.2;
    }

    .metric-lbl {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-top: 4px;
    }

    .metric-sub {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Dashboard Grid */
    .dashboard-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 20px;
      align-items: stretch;
    }

    @media (max-width: 900px) {
      .dashboard-grid {
        grid-template-columns: 1fr;
      }
    }

    .iq-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 22px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: var(--shadow-card);
    }

    .card-header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }

    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 2px 0;
    }

    .card-desc {
      font-size: 12.5px;
      color: var(--text-secondary);
      margin: 0;
    }

    .link-action {
      font-size: 12.5px;
      color: var(--accent);
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
    }

    .empty-state-box {
      text-align: center;
      padding: 24px 16px;
      color: var(--text-muted);
      font-size: 13px;
    }

    /* Opportunities mini list */
    .opp-mini-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .opp-mini-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      gap: 12px;
    }

    .opp-info {
      display: flex;
      flex-direction: column;
      gap: 3px;
      min-width: 0;
    }

    .opp-title-line {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .opp-job-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .fit-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 1px 6px;
      border-radius: 4px;
      background: var(--bg-subtle);
      color: var(--text-secondary);
    }

    .fit-high {
      background: #ecfdf5;
      color: #059669;
    }

    .opp-meta-line {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11.5px;
      color: var(--text-secondary);
    }

    .verified-tag {
      color: #059669;
      font-weight: 600;
    }

    /* COSGO Card */
    .cosgo-stat-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      padding: 12px;
      background: var(--bg-subtle);
      border-radius: var(--radius-sm);
      text-align: center;
    }

    .cosgo-stat-num {
      font-size: 18px;
      font-weight: 700;
      display: block;
    }

    .cosgo-stat-lbl {
      font-size: 11px;
      color: var(--text-secondary);
    }

    .sub-header-lbl {
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.3px;
      display: block;
      margin-top: 10px;
      margin-bottom: 6px;
    }

    .cosgo-mini-action {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 10px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      margin-bottom: 6px;
      font-size: 12.5px;
    }

    .act-name-col {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .act-why {
      font-size: 11px;
      color: var(--text-muted);
    }

    .act-effort-col {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-hours {
      background: var(--bg-subtle);
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }

    .gain-sub {
      color: #059669;
      font-weight: 600;
      font-size: 11px;
    }

    /* Outreach card */
    .outreach-dashboard-box {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .gmail-conn-status {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 12.5px;
    }

    .conn-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #94a3b8;
    }

    .status-connected .conn-dot {
      background: #10b981;
    }

    .conn-text {
      flex: 1;
    }

    .outreach-stats-mini-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      text-align: center;
    }

    .mini-stat {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px;
    }

    .stat-highlight {
      border-color: #10b981;
      background: #ecfdf5;
    }

    .stat-big {
      font-size: 18px;
      font-weight: 700;
      display: block;
    }

    .stat-small {
      font-size: 11px;
      color: var(--text-secondary);
    }

    .draft-preview-strip {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      cursor: pointer;
      background: var(--bg-surface);
    }

    .draft-preview-strip:hover {
      border-color: var(--accent);
    }

    .draft-title-box {
      display: flex;
      flex-direction: column;
      font-size: 12.5px;
    }

    .draft-subj {
      font-size: 11px;
      color: var(--text-muted);
    }

    .status-pill {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }

    .status-ai_generated {
      background: #e0e7ff;
      color: #3730a3;
    }

    /* Next Steps */
    .next-steps-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .step-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: var(--bg-surface);
    }

    .step-check {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .step-item.step-done .step-check {
      background: var(--success-bg);
      color: var(--success-text);
    }

    .step-body {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .step-name {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-primary);
    }

    .step-sub {
      font-size: 11.5px;
      color: var(--text-muted);
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
      text-decoration: none;
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

    .btn-xs {
      padding: 3px 8px;
      font-size: 11px;
    }

    .btn-sm {
      padding: 5px 10px;
      font-size: 12px;
    }

    .grounding-footer-note {
      margin-top: 32px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 12.5px;
      color: var(--text-secondary);
    }

    .grounding-footer-note svg {
      color: var(--accent);
      flex-shrink: 0;
    }

    .text-accent {
      color: var(--accent);
    }

    .text-success {
      color: #059669;
    }

    .text-muted {
      color: var(--text-muted);
    }
  `]
})
export class DashboardComponent implements OnInit {
  authService = inject(AuthService);
  private profileService = inject(ProfileService);
  private resumeService = inject(ResumeService);
  private intelligenceService = inject(IntelligenceService);
  private oppService = inject(OpportunityService);
  private cosgoService = inject(CosgoService);
  private outreachService = inject(OutreachService);
  private gmailService = inject(GmailService);
  private router = inject(Router);
  private cd = inject(ChangeDetectorRef);

  profile: Profile | null = null;
  resumes: Resume[] = [];
  intelligence: CandidateIntelligenceRepresentation | null = null;
  opportunities: Opportunity[] = [];
  latestCosgoRun: CosgoRun | null = null;
  outreachDrafts: OutreachDraft[] = [];
  gmailConnection: GmailConnection | null = null;
  sentMessages: OutreachEmailMessage[] = [];

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.profileService.getProfile().subscribe({
      next: (p) => { this.profile = p; this.cd.markForCheck(); },
      error: () => {}
    });

    this.resumeService.getResumes().subscribe({
      next: (r) => { this.resumes = r || []; this.cd.markForCheck(); },
      error: () => {}
    });

    this.intelligenceService.getIntelligence().subscribe({
      next: (intel) => { this.intelligence = intel; this.cd.markForCheck(); },
      error: () => {}
    });

    this.oppService.getOpportunities().subscribe({
      next: (opps) => { this.opportunities = opps || []; this.cd.markForCheck(); },
      error: () => {}
    });

    this.cosgoService.getLatestRun().subscribe({
      next: (run) => { this.latestCosgoRun = run; this.cd.markForCheck(); },
      error: () => {}
    });

    this.outreachService.getDrafts().subscribe({
      next: (res) => { this.outreachDrafts = res?.items || []; this.cd.markForCheck(); },
      error: () => {}
    });

    this.gmailService.getConnection().subscribe({
      next: (conn) => { this.gmailConnection = conn; this.cd.markForCheck(); },
      error: () => {}
    });

    this.gmailService.getMessages(5, 0).subscribe({
      next: (msgs) => { this.sentMessages = msgs || []; this.cd.markForCheck(); },
      error: () => {}
    });
  }

  get preferredResume(): Resume | undefined {
    return this.resumes.find(r => r.is_preferred) || (this.resumes.length > 0 ? this.resumes[0] : undefined);
  }

  get topOpportunities(): Opportunity[] {
    return this.opportunities.slice(0, 3);
  }

  get verifiedOpportunitiesCount(): number {
    return this.opportunities.filter(o => o.job?.verification_status === 'VERIFIED_OPEN').length;
  }

  get repliesCount(): number {
    return this.sentMessages.reduce((acc, m) => acc + (m.reply_count || 0), 0);
  }

  hasProfessionalLinks(): boolean {
    if (!this.profile?.links) return false;
    return !!(this.profile.links['linkedin'] || this.profile.links['github'] || this.profile.links['portfolio']);
  }

  goToDraft(draft: OutreachDraft): void {
    this.router.navigate(['/outreach'], { queryParams: { draftId: draft.id } });
  }
}

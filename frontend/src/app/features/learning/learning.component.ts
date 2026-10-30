import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs';
import { LearningService } from '../../core/services/learning.service';
import {
  CosgoLearningDashboardResponse,
  SkillPlan,
  CosgoSkillSummary,
  RoadmapStage,
  PracticalExercise,
  CourseItem,
  CertificationEntry,
  VideoItem,
  ProjectBlueprint,
  LearningProgressPayload
} from '../../core/models/learning.model';

@Component({
  selector: 'app-learning',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="learning-page">
      <!-- Page Header -->
      <header class="page-header">
        <div class="header-left">
          <div class="badge-row">
            <span class="iq-pill iq-pill-accent">COSGO Execution Layer</span>
            <span class="iq-pill iq-pill-neutral">Algorithm {{ dashboardData?.algorithm_version || 'cosgo-v1.1-verified' }}</span>
            <span class="iq-pill iq-pill-success">Zero Paid APIs</span>
          </div>
          <h1 class="page-title">Personalized Learning & Project Recommendations</h1>
          <p class="page-subtitle">
            Execution layer of Cross-Opportunity Skill Gap Optimization. Strictly curated roadmaps, verified free resources, and practical projects for your highest-impact skill gaps.
          </p>
        </div>
        <div class="header-actions">
          <a routerLink="/skill-gap" class="btn btn-secondary">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            Skill Gap & Roadmap
          </a>
          <button class="btn btn-secondary" (click)="reloadCurrentSkill()" [disabled]="loading">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            {{ loading ? 'Loading...' : 'Refresh Plan' }}
          </button>
        </div>
      </header>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <div class="spinner"></div>
        <p class="loading-text">Synthesizing candidate profile, skill gaps, and verified learning catalogs...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="!loading && loadError" class="error-banner">
        <div class="error-msg">
          <strong>Unable to load learning plan:</strong> {{ loadError }}
        </div>
        <button class="btn btn-secondary btn-sm" (click)="reloadCurrentSkill()">Retry</button>
      </div>

      <!-- EMPTY STATE: No COSGO Optimization Run -->
      <div *ngIf="!loading && !loadError && dashboardData?.is_cosgo_empty_state" class="cosgo-empty-card">
        <div class="empty-icon-box">🎯</div>
        <h2 class="empty-title">No Active COSGO Recommendations Found</h2>
        <p class="empty-desc">
          {{ dashboardData?.empty_state_message || 'OutReachIQ Learning & Projects operates exclusively as the execution layer of Cross-Opportunity Skill Gap Optimization (COSGO). Run an optimization in Skill Gap & Roadmap to identify the highest-impact skills for your target opportunities.' }}
        </p>
        <div class="empty-features-note">
          <span>✓ Grounded in real vacancy requirements</span>
          <span>✓ Budget-constrained greedy optimization</span>
          <span>✓ Zero arbitrary skill lists</span>
        </div>
        <div class="empty-actions">
          <a routerLink="/skill-gap" class="btn btn-primary">
            Run Skill Gap Optimization (COSGO) →
          </a>
        </div>
      </div>

      <!-- MAIN CONTENT: COSGO EXECUTION PLAN -->
      <div *ngIf="!loading && !loadError && !dashboardData?.is_cosgo_empty_state && selectedSkillPlan" class="plan-content">

        <!-- Diagnostic Fallback Banner (if requested skill was stale) -->
        <div *ngIf="selectedSkillPlan.diagnostic_note" class="diagnostic-banner">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>{{ selectedSkillPlan.diagnostic_note }}</span>
        </div>

        <!-- 1. COSGO Skill Selector Queue -->
        <section class="skill-selector-section">
          <div class="section-title-row">
            <div class="selector-heading">
              <span class="selector-label">COSGO Prioritized Queue</span>
              <span class="selector-sub">Select a skill to view its verified execution roadmap</span>
            </div>
            <div class="overall-coverage-badge">
              <span>Projected Coverage:</span>
              <strong>{{ ((dashboardData?.projected_coverage || 0) * 100).toFixed(1) }}%</strong>
              <small class="gain-badge">+{{ ((dashboardData?.marginal_coverage_increase || 0) * 100).toFixed(1) }} pp</small>
            </div>
          </div>

          <div class="skill-cards-scroll">
            <div
              *ngFor="let s of dashboardData?.recommended_skills"
              class="queue-skill-card"
              [class.active]="s.skill_name === selectedSkillName"
              (click)="selectSkill(s.skill_name)"
            >
              <div class="queue-rank">#{{ s.priority_rank }}</div>
              <div class="queue-info">
                <span class="queue-name">{{ s.skill_name }}</span>
                <div class="queue-meta">
                  <span class="queue-gain">+{{ (s.marginal_coverage_gain * 100).toFixed(1) }} pp</span>
                  <span class="queue-jobs">{{ s.opportunities_count }} jobs</span>
                </div>
              </div>
              <span class="queue-state state-chip" [ngClass]="'state-' + s.progress_state.toLowerCase()">
                {{ s.progress_state }}
              </span>
            </div>
          </div>
        </section>

        <!-- 2. Selected Skill Overview Hero -->
        <div class="skill-hero-card">
          <div class="hero-header">
            <div class="hero-left">
              <div class="hero-badge-row">
                <span class="rank-pill">Priority Rank #{{ selectedSkillPlan.priority_rank }}</span>
                <span class="category-pill">{{ selectedSkillPlan.category }}</span>
              </div>
              <h2 class="selected-skill-title">{{ selectedSkillPlan.skill_name }}</h2>
              <p class="why-recommended-text">
                <span class="why-prefix">Why COSGO Selected This:</span>
                {{ selectedSkillPlan.why_recommended }}
              </p>
            </div>
            <div class="hero-right">
              <div class="overall-progress-box">
                <span class="ctrl-heading">Roadmap Status:</span>
                <div class="btn-group-prog">
                  <button
                    class="btn-prog"
                    [class.active]="currentOverallState === 'RECOMMENDED'"
                    (click)="changeOverallProgressState('RECOMMENDED')"
                  >
                    Recommended
                  </button>
                  <button
                    class="btn-prog"
                    [class.active]="currentOverallState === 'PLANNED'"
                    (click)="changeOverallProgressState('PLANNED')"
                  >
                    Planned
                  </button>
                  <button
                    class="btn-prog"
                    [class.active]="currentOverallState === 'IN_PROGRESS'"
                    (click)="changeOverallProgressState('IN_PROGRESS')"
                  >
                    In Progress
                  </button>
                  <button
                    class="btn-prog btn-prog-complete"
                    [class.active]="currentOverallState === 'COMPLETED'"
                    (click)="changeOverallProgressState('COMPLETED')"
                  >
                    ✓ Completed
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- KPI Metric Cards Grid -->
          <div class="metrics-grid">
            <div class="metric-card">
              <span class="metric-label">Marginal Coverage Gain</span>
              <span class="metric-value highlight">+{{ (selectedSkillPlan.marginal_coverage_gain * 100).toFixed(1) }} pp</span>
              <span class="metric-subtext">Cumulative: {{ (selectedSkillPlan.cumulative_coverage * 100).toFixed(1) }}% total</span>
            </div>
            <div class="metric-card">
              <span class="metric-label">Opportunities Helped</span>
              <span class="metric-value">{{ selectedSkillPlan.opportunities_count }} <small>target roles</small></span>
              <button class="text-btn" (click)="toggleJobsExpanded()">
                {{ showJobsTable ? '▲ Hide breakdown' : '▼ View opportunities' }}
              </button>
            </div>
            <div class="metric-card">
              <span class="metric-label">Estimated Effort</span>
              <span class="metric-value">{{ selectedSkillPlan.estimated_hours }} <small>hrs</small></span>
              <span class="metric-subtext">
                {{ selectedSkillPlan.effort_uncertainty_range.min_hours || (selectedSkillPlan.estimated_hours * 0.8).toFixed(0) }}-{{ selectedSkillPlan.effort_uncertainty_range.max_hours || (selectedSkillPlan.estimated_hours * 1.3).toFixed(0) }} hrs range
              </span>
            </div>
            <div class="metric-card">
              <span class="metric-label">Dedicated Weekly Pacing</span>
              <span class="metric-value">{{ weeklyBudget }} <small>hrs/wk</small></span>
              <span class="metric-subtext">~{{ getCalculatedWeeks() }} weeks to master</span>
            </div>
          </div>

          <!-- Prerequisites Row -->
          <div class="prereq-row" *ngIf="selectedSkillPlan.prerequisites && selectedSkillPlan.prerequisites.length > 0">
            <span class="prereq-label">Prerequisites:</span>
            <div class="prereq-tags">
              <span *ngFor="let p of selectedSkillPlan.prerequisites" class="prereq-chip">
                {{ p }}
              </span>
            </div>
          </div>

          <!-- Expandable Opportunities Benefited Breakdown -->
          <div *ngIf="showJobsTable" class="jobs-breakdown-panel">
            <div class="breakdown-header">
              <h4>Target Opportunities Benefiting from {{ selectedSkillPlan.skill_name }}</h4>
              <span class="count-note">{{ selectedSkillPlan.target_opportunities_summary.length }} vacancy matches</span>
            </div>
            <div class="jobs-table-wrap">
              <table class="jobs-table">
                <thead>
                  <tr>
                    <th>Target Role</th>
                    <th>Company</th>
                    <th>Current Match</th>
                    <th>Salary Range</th>
                    <th>Key Requirements</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let opp of selectedSkillPlan.target_opportunities_summary">
                    <td class="bold-text">{{ opp.title }}</td>
                    <td>{{ opp.company }}</td>
                    <td>
                      <span class="score-pill">{{ (opp.match_score * 100).toFixed(0) }}%</span>
                    </td>
                    <td>{{ opp.salary_range || 'Competitive' }}</td>
                    <td>
                      <div class="req-tags">
                        <span *ngFor="let req of opp.required_skills" class="req-tag" [class.highlight-req]="req.toLowerCase() === selectedSkillName.toLowerCase()">
                          {{ req }}
                        </span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Weekly Budget Pacer Slider -->
          <div class="budget-bar-section">
            <div class="budget-bar-label">
              <span>Study Velocity Adjuster: <strong>{{ weeklyBudget }} hrs/week</strong> (~{{ getCalculatedWeeks() }} weeks)</span>
            </div>
            <div class="budget-slider-row">
              <input
                type="range"
                min="2"
                max="40"
                step="1"
                [(ngModel)]="weeklyBudget"
                class="budget-slider"
                id="budgetSlider"
              />
              <button class="btn btn-secondary btn-sm" (click)="saveBudget()" [disabled]="updatingBudget">
                {{ updatingBudget ? 'Saving...' : 'Save Budget' }}
              </button>
            </div>
            <div *ngIf="budgetSuccessMsg" class="budget-success-toast">
              {{ budgetSuccessMsg }}
            </div>
          </div>
        </div>

        <!-- 3. Navigation Tabs for Execution -->
        <div class="tab-nav">
          <button
            class="tab-btn"
            [class.active]="activeTab === 'roadmap'"
            (click)="activeTab = 'roadmap'"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
              <path d="M2 17l10 5 10-5"></path>
              <path d="M2 12l10 5 10-5"></path>
            </svg>
            Structured Roadmap ({{ selectedSkillPlan.roadmap_stages.length }} Milestones)
          </button>
          <button
            class="tab-btn"
            [class.active]="activeTab === 'docs'"
            (click)="activeTab = 'docs'"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            Verified Docs & Courses ({{ (selectedSkillPlan.resources.documentation ? 1 : 0) + selectedSkillPlan.resources.courses.length }})
          </button>
          <button
            class="tab-btn"
            [class.active]="activeTab === 'certs'"
            (click)="activeTab = 'certs'"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="8" r="7"></circle>
              <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
            </svg>
            Certifications & Video Guides ({{ selectedSkillPlan.resources.certifications.length + selectedSkillPlan.resources.videos.length }})
          </button>
          <button
            class="tab-btn"
            [class.active]="activeTab === 'projects'"
            (click)="activeTab = 'projects'"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            Portfolio Projects & Exercises ({{ selectedSkillPlan.projects.length + selectedSkillPlan.resources.practical_exercises.length }})
          </button>
        </div>

        <!-- TAB 1: STRUCTURED ROADMAP -->
        <div *ngIf="activeTab === 'roadmap'" class="tab-pane">
          <div class="tab-intro-banner">
            <h3>4-Stage Progressive Curriculum for {{ selectedSkillPlan.skill_name }}</h3>
            <p>Master {{ selectedSkillPlan.skill_name }} through four structured milestones. Mark milestones as completed as you progress.</p>
          </div>

          <div class="roadmap-timeline">
            <div
              *ngFor="let stage of selectedSkillPlan.roadmap_stages; let idx = index"
              class="milestone-card"
              [class.completed]="isMilestoneCompleted(stage.stage_id)"
            >
              <div class="milestone-left">
                <div class="milestone-num-circle">
                  <span *ngIf="!isMilestoneCompleted(stage.stage_id)">{{ stage.stage_number }}</span>
                  <span *ngIf="isMilestoneCompleted(stage.stage_id)">✓</span>
                </div>
                <div class="timeline-stem" *ngIf="idx < selectedSkillPlan.roadmap_stages.length - 1"></div>
              </div>

              <div class="milestone-body">
                <div class="milestone-header">
                  <div>
                    <span class="stage-tag">STAGE {{ stage.stage_number }}</span>
                    <h4 class="stage-title">{{ stage.title }}</h4>
                  </div>
                  <div class="stage-meta">
                    <span class="hours-chip">~{{ stage.estimated_hours }} hrs</span>
                    <button
                      class="btn-toggle-done"
                      [class.done]="isMilestoneCompleted(stage.stage_id)"
                      (click)="toggleMilestone(stage.stage_id)"
                      [disabled]="updatingProgress"
                    >
                      {{ isMilestoneCompleted(stage.stage_id) ? '✓ Milestone Completed' : 'Mark as Completed' }}
                    </button>
                  </div>
                </div>

                <p class="stage-focus"><strong>Focus:</strong> {{ stage.focus }}</p>

                <div class="concepts-box">
                  <span class="concepts-label">Core Concepts Checklist:</span>
                  <ul class="concepts-checklist">
                    <li *ngFor="let c of stage.core_concepts">
                      <span class="check-bullet">◽</span> {{ c }}
                    </li>
                  </ul>
                </div>

                <div class="deliverable-banner">
                  <span class="deliv-tag">Stage Milestone Deliverable:</span>
                  <span class="deliv-text">{{ stage.key_deliverable }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: VERIFIED DOCS & COURSES -->
        <div *ngIf="activeTab === 'docs'" class="tab-pane">
          <!-- Official Documentation Card -->
          <div class="catalog-section">
            <div class="section-badge-header">
              <span class="category-indicator">PRIMARY REFERENCE</span>
              <h3>Official Technical Documentation</h3>
            </div>

            <div *ngIf="selectedSkillPlan.resources.documentation as doc" class="resource-card official-doc-card" [class.completed]="isResourceCompleted(doc.url)">
              <div class="res-card-top">
                <div class="res-info">
                  <div class="res-domain-pill">{{ doc.domain }}</div>
                  <h4 class="res-title">{{ doc.title }}</h4>
                  <p class="res-desc">{{ doc.description }}</p>
                </div>
                <div class="res-actions">
                  <a [href]="doc.url" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">
                    Read Official Docs ↗
                  </a>
                  <button
                    class="btn btn-secondary btn-sm"
                    [class.btn-active-check]="isResourceCompleted(doc.url)"
                    (click)="toggleResource(doc.url)"
                    [disabled]="updatingProgress"
                  >
                    {{ isResourceCompleted(doc.url) ? '✓ Studied' : 'Mark as Read' }}
                  </button>
                </div>
              </div>
            </div>

            <div *ngIf="!selectedSkillPlan.resources.documentation" class="honest-empty-notice">
              Official documentation index for {{ selectedSkillPlan.skill_name }} is pending verification.
            </div>
          </div>

          <!-- Verified Free or Auditable Courses -->
          <div class="catalog-section">
            <div class="section-badge-header">
              <span class="category-indicator">STRUCTURED CURRICULA</span>
              <h3>Verified Free & Free-to-Audit Courses</h3>
            </div>

            <div *ngIf="selectedSkillPlan.resources.courses.length > 0" class="courses-grid">
              <div
                *ngFor="let c of selectedSkillPlan.resources.courses"
                class="resource-card course-card"
                [class.completed]="isResourceCompleted(c.url)"
              >
                <div class="course-badge-row">
                  <span class="provider-pill">{{ c.provider_name || c.provider }}</span>
                  <span class="access-pill">{{ c.access_type }}</span>
                </div>

                <h4 class="res-title">{{ c.title }}</h4>
                <p class="res-desc">{{ c.description }}</p>

                <div class="course-meta-row">
                  <span class="meta-item">⏱ {{ c.estimated_hours }} hrs</span>
                  <span class="meta-item">🎓 {{ c.difficulty_level }}</span>
                  <span class="meta-item" *ngIf="c.certificate_included">📜 Free Certificate</span>
                </div>

                <div class="skills-covered-row">
                  <span *ngFor="let s of c.covered_skills || c.target_skills" class="skill-tag">{{ s }}</span>
                </div>

                <div class="card-footer-btns">
                  <a [href]="c.url" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">
                    Open Course ↗
                  </a>
                  <button
                    class="btn btn-secondary btn-sm"
                    [class.btn-active-check]="isResourceCompleted(c.url)"
                    (click)="toggleResource(c.url)"
                    [disabled]="updatingProgress"
                  >
                    {{ isResourceCompleted(c.url) ? '✓ Completed' : 'Mark Done' }}
                  </button>
                </div>
              </div>
            </div>

            <div *ngIf="selectedSkillPlan.resources.courses.length === 0" class="honest-empty-notice">
              <div class="notice-icon">ℹ️</div>
              <div class="notice-content">
                <strong>No separate 3rd-party courses required for {{ selectedSkillPlan.skill_name }}.</strong>
                <p>The official documentation, progressive milestone roadmap, and hands-on portfolio project blueprints provide comprehensive, verifiable coverage without unnecessary secondary courses.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: CERTIFICATIONS & VIDEO GUIDES -->
        <div *ngIf="activeTab === 'certs'" class="tab-pane">
          <!-- Certifications -->
          <div class="catalog-section">
            <div class="section-badge-header">
              <span class="category-indicator">INDUSTRY CREDENTIALS</span>
              <h3>Vendor Certifications & Zero-Cost Study Materials</h3>
            </div>

            <div *ngIf="selectedSkillPlan.resources.certifications.length > 0" class="certs-grid">
              <div
                *ngFor="let cert of selectedSkillPlan.resources.certifications"
                class="resource-card cert-card"
                [class.completed]="isResourceCompleted(cert.official_url)"
              >
                <div class="cert-header">
                  <span class="vendor-tag">{{ cert.vendor }}</span>
                  <span class="fee-tag" [class.fee-free]="cert.exam_fee_status === 'FREE'">
                    {{ cert.exam_fee_status === 'PAID' ? 'Exam Fee: ~$' + (cert.estimated_cost_usd || 150) : 'Free Exam' }}
                  </span>
                </div>

                <h4 class="res-title">{{ cert.title }} ({{ cert.code }})</h4>
                <p class="res-desc">{{ cert.notes }}</p>

                <div class="free-materials-box" *ngIf="cert.free_learning_materials_available">
                  <span class="free-badge">✓ Free Preparation Materials Available</span>
                  <a [href]="cert.free_materials_url" target="_blank" rel="noopener noreferrer" class="study-link">
                    Access Official Study Guide ↗
                  </a>
                </div>

                <div class="card-footer-btns">
                  <a [href]="cert.official_url" target="_blank" rel="noopener noreferrer" class="btn btn-secondary btn-sm">
                    Exam Overview ↗
                  </a>
                  <button
                    class="btn btn-secondary btn-sm"
                    [class.btn-active-check]="isResourceCompleted(cert.official_url)"
                    (click)="toggleResource(cert.official_url)"
                    [disabled]="updatingProgress"
                  >
                    {{ isResourceCompleted(cert.official_url) ? '✓ Certified' : 'Mark Achieved' }}
                  </button>
                </div>
              </div>
            </div>

            <div *ngIf="selectedSkillPlan.resources.certifications.length === 0" class="honest-empty-notice">
              <div class="notice-icon">ℹ️</div>
              <div class="notice-content">
                <strong>No direct vendor certification exists for {{ selectedSkillPlan.skill_name }}.</strong>
                <p>Engineering employers evaluate {{ selectedSkillPlan.skill_name }} through demonstrable production code, architecture blueprints, and GitHub repositories rather than standardized multiple-choice certificates.</p>
              </div>
            </div>
          </div>

          <!-- Video Tutorials -->
          <div class="catalog-section">
            <div class="section-badge-header">
              <span class="category-indicator">VISUAL LEARNING</span>
              <h3>Educational Video Tutorials & Walkthroughs</h3>
            </div>

            <div *ngIf="selectedSkillPlan.resources.videos.length > 0" class="videos-grid">
              <div
                *ngFor="let vid of selectedSkillPlan.resources.videos"
                class="resource-card video-card"
                [class.completed]="isResourceCompleted(vid.url)"
              >
                <div class="video-thumb-wrap">
                  <img [src]="vid.thumbnail_url" [alt]="vid.title" class="video-thumb" />
                  <span *ngIf="vid.is_curated_fallback" class="curated-pill">Curated</span>
                </div>
                <div class="video-body">
                  <span class="channel-name">{{ vid.channel_title }}</span>
                  <h4 class="video-title">{{ vid.title }}</h4>
                  <div class="card-footer-btns">
                    <a [href]="vid.url" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">
                      Watch on YouTube ↗
                    </a>
                    <button
                      class="btn btn-secondary btn-sm"
                      [class.btn-active-check]="isResourceCompleted(vid.url)"
                      (click)="toggleResource(vid.url)"
                      [disabled]="updatingProgress"
                    >
                      {{ isResourceCompleted(vid.url) ? '✓ Watched' : 'Mark Watched' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 4: PORTFOLIO PROJECTS & EXERCISES -->
        <div *ngIf="activeTab === 'projects'" class="tab-pane">
          <!-- Portfolio Projects -->
          <div class="catalog-section">
            <div class="section-badge-header">
              <span class="category-indicator">PRODUCTION PORTFOLIO</span>
              <h3>Portfolio Project Blueprints Targeting {{ selectedSkillPlan.skill_name }}</h3>
            </div>

            <div *ngFor="let proj of selectedSkillPlan.projects" class="project-blueprint-card" [class.completed]="isProjectCompleted()">
              <div class="proj-header">
                <div>
                  <div class="proj-badges">
                    <span class="diff-tag" [ngClass]="(proj.difficulty_level || proj.difficulty || '').toLowerCase()">
                      {{ proj.difficulty_level || proj.difficulty }}
                    </span>
                    <span class="hours-tag">⏱ ~{{ proj.estimated_hours }} hrs</span>
                  </div>
                  <h3 class="proj-title">{{ proj.title }}</h3>
                </div>
                <button
                  class="btn-toggle-done"
                  [class.done]="isProjectCompleted()"
                  (click)="toggleProject(proj.project_id || proj.id || '')"
                  [disabled]="updatingProgress"
                >
                  {{ isProjectCompleted() ? '✓ Project Completed' : 'Mark Project Complete' }}
                </button>
              </div>

              <p class="proj-purpose">{{ proj.purpose || proj.summary || proj.problem_statement }}</p>

              <!-- Milestones Checklist -->
              <div class="proj-milestones-box">
                <span class="box-title">Implementation Milestones:</span>
                <div class="milestones-steps">
                  <div
                    *ngFor="let m of proj.milestones"
                    class="step-item"
                    [class.step-completed]="isProjectMilestoneCompleted(m.step_number || m.step || 1)"
                  >
                    <div class="step-ctrl">
                      <input
                        type="checkbox"
                        [checked]="isProjectMilestoneCompleted(m.step_number || m.step || 1)"
                        (change)="toggleProjectMilestone(m.step_number || m.step || 1)"
                        class="step-checkbox"
                        id="mstep-{{ m.step_number || m.step }}"
                      />
                    </div>
                    <div class="step-info">
                      <span class="step-title">Step {{ m.step_number || m.step }}: {{ m.title }} (~{{ m.estimated_hours || m.hours }} hrs)</span>
                      <p *ngIf="m.description" class="step-desc">{{ m.description }}</p>
                      <ul *ngIf="m.deliverables && m.deliverables.length > 0" class="step-deliverables">
                        <li *ngFor="let d of m.deliverables">✓ {{ d }}</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Validation Checklist -->
              <div class="validation-box" *ngIf="proj.validation_checklist && proj.validation_checklist.length > 0">
                <span class="box-title">Validation & Verification Checklist:</span>
                <ul class="validation-list">
                  <li *ngFor="let v of proj.validation_checklist">
                    <span class="bullet">🔍</span> {{ v }}
                  </li>
                </ul>
              </div>

              <div class="impact-box" *ngIf="proj.career_impact_rationale">
                <strong>Career Impact Rationale:</strong> {{ proj.career_impact_rationale }}
              </div>
            </div>
          </div>

          <!-- Practical Exercises & Mini-Challenges -->
          <div class="catalog-section" *ngIf="selectedSkillPlan.resources.practical_exercises.length > 0">
            <div class="section-badge-header">
              <span class="category-indicator">HANDS-ON REINFORCEMENT</span>
              <h3>Practical Exercises & Mini-Challenges</h3>
            </div>

            <div class="exercises-grid">
              <div
                *ngFor="let ex of selectedSkillPlan.resources.practical_exercises"
                class="resource-card exercise-card"
                [class.completed]="isExerciseCompleted(ex.id)"
              >
                <div class="ex-header">
                  <span class="ex-tag">CHALLENGE (~{{ ex.estimated_hours }} hrs)</span>
                  <button
                    class="btn btn-secondary btn-sm"
                    [class.btn-active-check]="isExerciseCompleted(ex.id)"
                    (click)="toggleExercise(ex.id)"
                    [disabled]="updatingProgress"
                  >
                    {{ isExerciseCompleted(ex.id) ? '✓ Completed' : 'Mark Done' }}
                  </button>
                </div>

                <h4 class="ex-title">{{ ex.title }}</h4>
                <p class="ex-scenario"><strong>Scenario:</strong> {{ ex.scenario }}</p>
                <p class="ex-obj"><strong>Objective:</strong> {{ ex.objective }}</p>

                <div class="code-hints-box" *ngIf="ex.commands_or_code_hints && ex.commands_or_code_hints.length > 0">
                  <span class="hints-lbl">Command / Code Hints:</span>
                  <div *ngFor="let h of ex.commands_or_code_hints" class="code-snippet">
                    <code>{{ h }}</code>
                  </div>
                </div>

                <div class="criteria-box" *ngIf="ex.acceptance_criteria && ex.acceptance_criteria.length > 0">
                  <span class="criteria-lbl">Acceptance Criteria:</span>
                  <ul class="criteria-list">
                    <li *ngFor="let ac of ex.acceptance_criteria">✓ {{ ac }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .learning-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .learning-page { padding: 16px; }
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .badge-row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }
    .iq-pill {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .iq-pill-accent {
      background: #eff6ff;
      color: #2563eb;
      border: 1px solid #bfdbfe;
    }
    .iq-pill-neutral {
      background: #f1f5f9;
      color: #64748b;
    }
    .iq-pill-success {
      background: #dcfce7;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }
    .page-title {
      font-size: 26px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 6px 0;
    }
    .page-subtitle {
      font-size: 14px;
      color: #475569;
      margin: 0;
      max-width: 820px;
      line-height: 1.5;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn-primary {
      background: #2563eb;
      color: #ffffff;
      border-color: #1d4ed8;
    }
    .btn-primary:hover:not(:disabled) { background: #1d4ed8; }
    .btn-secondary {
      background: #ffffff;
      color: #334155;
      border-color: #cbd5e1;
    }
    .btn-secondary:hover:not(:disabled) {
      background: #f8fafc;
      border-color: #94a3b8;
    }
    .btn-sm {
      padding: 5px 10px;
      font-size: 12px;
    }
    .btn-active-check {
      background: #dcfce7 !important;
      color: #15803d !important;
      border-color: #86efac !important;
      font-weight: 700;
    }
    .loading-state {
      padding: 60px 20px;
      text-align: center;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .spinner {
      width: 36px;
      height: 36px;
      border: 3px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 16px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-text { font-size: 14px; color: #64748b; margin: 0; }
    .error-banner {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #991b1b;
    }

    /* COSGO Empty State */
    .cosgo-empty-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 48px 32px;
      text-align: center;
      max-width: 680px;
      margin: 40px auto;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .empty-icon-box {
      font-size: 48px;
      margin-bottom: 16px;
    }
    .empty-title {
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 12px;
    }
    .empty-desc {
      font-size: 14px;
      color: #475569;
      line-height: 1.6;
      margin: 0 0 24px;
    }
    .empty-features-note {
      display: flex;
      justify-content: center;
      gap: 16px;
      font-size: 12.5px;
      color: #64748b;
      margin-bottom: 28px;
      flex-wrap: wrap;
    }
    .diagnostic-banner {
      display: flex;
      align-items: center;
      gap: 10px;
      background: #fef3c7;
      color: #92400e;
      border: 1px solid #fde68a;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 20px;
    }

    /* COSGO Prioritized Queue Selector */
    .skill-selector-section {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 18px 20px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .section-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .selector-label {
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
      display: block;
    }
    .selector-sub {
      font-size: 12px;
      color: #64748b;
    }
    .overall-coverage-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      background: #f8fafc;
      padding: 5px 12px;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
      font-size: 12.5px;
    }
    .gain-badge {
      background: #dcfce7;
      color: #15803d;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }
    .skill-cards-scroll {
      display: flex;
      gap: 12px;
      overflow-x: auto;
      padding-bottom: 6px;
    }
    .queue-skill-card {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      min-width: 220px;
      flex-shrink: 0;
      transition: all 0.15s ease;
    }
    .queue-skill-card:hover {
      background: #f1f5f9;
      border-color: #94a3b8;
    }
    .queue-skill-card.active {
      background: #eff6ff;
      border-color: #2563eb;
      box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
    }
    .queue-rank {
      font-size: 14px;
      font-weight: 800;
      color: #2563eb;
      background: #ffffff;
      width: 32px;
      height: 32px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid #bfdbfe;
    }
    .queue-info {
      flex: 1;
    }
    .queue-name {
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
      display: block;
    }
    .queue-meta {
      display: flex;
      gap: 8px;
      font-size: 11.5px;
    }
    .queue-gain { color: #15803d; font-weight: 600; }
    .queue-jobs { color: #64748b; }
    .state-chip {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .state-recommended { background: #eff6ff; color: #2563eb; }
    .state-planned { background: #fef3c7; color: #b45309; }
    .state-in_progress { background: #fef3c7; color: #d97706; }
    .state-completed { background: #dcfce7; color: #15803d; }

    /* Selected Skill Hero Card */
    .skill-hero-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .hero-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .hero-badge-row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }
    .rank-pill {
      background: #eff6ff;
      color: #2563eb;
      font-weight: 700;
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .category-pill {
      background: #f1f5f9;
      color: #475569;
      font-weight: 500;
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: 4px;
    }
    .selected-skill-title {
      font-size: 28px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 8px;
    }
    .why-recommended-text {
      font-size: 14px;
      color: #334155;
      margin: 0;
      line-height: 1.5;
    }
    .why-prefix {
      font-weight: 700;
      color: #2563eb;
    }
    .overall-progress-box {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
    }
    .ctrl-heading {
      font-size: 11.5px;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
    }
    .btn-group-prog {
      display: flex;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      overflow: hidden;
    }
    .btn-prog {
      background: #ffffff;
      border: none;
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
      color: #475569;
      cursor: pointer;
      border-right: 1px solid #cbd5e1;
      transition: all 0.15s ease;
    }
    .btn-prog:last-child { border-right: none; }
    .btn-prog:hover { background: #f8fafc; }
    .btn-prog.active { background: #2563eb; color: #ffffff; }
    .btn-prog-complete.active { background: #15803d; color: #ffffff; }

    /* Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .metric-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
    }
    .metric-label {
      font-size: 11.5px;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 4px;
    }
    .metric-value {
      font-size: 22px;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 2px;
    }
    .metric-value.highlight { color: #15803d; }
    .metric-value small { font-size: 13px; font-weight: 600; color: #64748b; }
    .metric-subtext { font-size: 11.5px; color: #64748b; }
    .text-btn {
      background: none;
      border: none;
      color: #2563eb;
      font-size: 11.5px;
      font-weight: 600;
      padding: 0;
      cursor: pointer;
      text-align: left;
      margin-top: 2px;
    }
    .prereq-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: #f8fafc;
      border-radius: 6px;
      font-size: 12.5px;
      margin-bottom: 16px;
    }
    .prereq-label { font-weight: 600; color: #475569; }
    .prereq-tags { display: flex; gap: 6px; flex-wrap: wrap; }
    .prereq-chip {
      background: #e2e8f0;
      color: #1e293b;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11.5px;
    }

    /* Jobs Breakdown Panel */
    .jobs-breakdown-panel {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 18px;
    }
    .breakdown-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .breakdown-header h4 { margin: 0; font-size: 14px; font-weight: 700; color: #0f172a; }
    .count-note { font-size: 12px; color: #64748b; }
    .jobs-table-wrap { overflow-x: auto; }
    .jobs-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
      background: #ffffff;
      border-radius: 6px;
      overflow: hidden;
    }
    .jobs-table th {
      background: #e2e8f0;
      padding: 8px 12px;
      text-align: left;
      font-weight: 600;
      color: #334155;
    }
    .jobs-table td {
      padding: 8px 12px;
      border-bottom: 1px solid #f1f5f9;
      color: #334155;
    }
    .score-pill {
      background: #dbeafe;
      color: #1d4ed8;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }
    .req-tags { display: flex; gap: 4px; flex-wrap: wrap; }
    .req-tag {
      background: #f1f5f9;
      color: #475569;
      padding: 1px 5px;
      border-radius: 3px;
      font-size: 11px;
    }
    .req-tag.highlight-req {
      background: #fef08a;
      color: #854d0e;
      font-weight: 700;
    }

    /* Budget Section */
    .budget-bar-section {
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      padding-top: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .budget-bar-label { font-size: 13px; color: #334155; }
    .budget-slider-row {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .budget-slider {
      flex: 1;
      max-width: 320px;
    }
    .budget-success-toast {
      font-size: 12px;
      color: #15803d;
      font-weight: 600;
    }

    /* Navigation Tabs */
    .tab-nav {
      display: flex;
      gap: 10px;
      border-bottom: 2px solid #e2e8f0;
      margin-bottom: 24px;
      overflow-x: auto;
    }
    .tab-btn {
      padding: 12px 18px;
      background: none;
      border: none;
      border-bottom: 3px solid transparent;
      margin-bottom: -2px;
      font-size: 13.5px;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }
    .tab-btn:hover { color: #1e293b; }
    .tab-btn.active {
      color: #2563eb;
      border-bottom-color: #2563eb;
    }

    /* Roadmap Timeline */
    .tab-intro-banner {
      margin-bottom: 20px;
    }
    .tab-intro-banner h3 { margin: 0 0 4px; font-size: 18px; font-weight: 800; color: #0f172a; }
    .tab-intro-banner p { margin: 0; font-size: 13.5px; color: #475569; }
    .roadmap-timeline {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .milestone-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 20px;
      display: flex;
      gap: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      border-left: 4px solid #2563eb;
    }
    .milestone-card.completed {
      border-left-color: #10b981;
      background: #fbfdfc;
    }
    .milestone-left {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .milestone-num-circle {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #eff6ff;
      color: #2563eb;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      border: 2px solid #bfdbfe;
    }
    .milestone-card.completed .milestone-num-circle {
      background: #dcfce7;
      color: #15803d;
      border-color: #86efac;
    }
    .timeline-stem {
      width: 2px;
      flex: 1;
      background: #e2e8f0;
      margin-top: 10px;
    }
    .milestone-body { flex: 1; }
    .milestone-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .stage-tag {
      font-size: 10.5px;
      font-weight: 700;
      color: #64748b;
      letter-spacing: 0.04em;
    }
    .stage-title {
      font-size: 17px;
      font-weight: 700;
      color: #0f172a;
      margin: 2px 0 0;
    }
    .stage-meta {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .hours-chip {
      background: #f1f5f9;
      color: #475569;
      font-size: 12px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
    }
    .btn-toggle-done {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      color: #334155;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .btn-toggle-done:hover { background: #f8fafc; }
    .btn-toggle-done.done {
      background: #dcfce7;
      border-color: #86efac;
      color: #15803d;
      font-weight: 700;
    }
    .stage-focus {
      font-size: 13.5px;
      color: #334155;
      margin: 0 0 12px;
    }
    .concepts-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 12px;
    }
    .concepts-label {
      font-size: 11.5px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      display: block;
      margin-bottom: 6px;
    }
    .concepts-checklist {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 6px;
      font-size: 12.5px;
      color: #334155;
    }
    .check-bullet { color: #94a3b8; }
    .deliverable-banner {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 12.5px;
    }
    .deliv-tag { font-weight: 700; color: #1d4ed8; margin-right: 6px; }
    .deliv-text { color: #1e3a8a; }

    /* Catalog Sections */
    .catalog-section {
      margin-bottom: 32px;
    }
    .section-badge-header {
      margin-bottom: 16px;
    }
    .category-indicator {
      font-size: 10.5px;
      font-weight: 700;
      color: #2563eb;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      display: block;
      margin-bottom: 2px;
    }
    .section-badge-header h3 {
      font-size: 18px;
      font-weight: 800;
      color: #0f172a;
      margin: 0;
    }
    .resource-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      transition: all 0.15s ease;
    }
    .resource-card.completed {
      border-color: #86efac;
      background: #fbfdfc;
    }
    .official-doc-card {
      border-left: 4px solid #2563eb;
    }
    .res-card-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .res-info { flex: 1; }
    .res-domain-pill {
      font-size: 11px;
      font-weight: 600;
      color: #64748b;
      margin-bottom: 4px;
    }
    .res-title {
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
      margin: 0 0 6px;
    }
    .res-desc {
      font-size: 13px;
      color: #475569;
      line-height: 1.5;
      margin: 0;
    }
    .res-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex-shrink: 0;
    }
    .honest-empty-notice {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px 18px;
      font-size: 13px;
      color: #475569;
    }
    .notice-icon { font-size: 18px; }
    .notice-content p { margin: 4px 0 0; }

    /* Courses Grid */
    .courses-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }
    .course-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .course-badge-row {
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
    }
    .provider-pill { font-weight: 700; color: #334155; }
    .access-pill {
      background: #dcfce7;
      color: #15803d;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 10.5px;
    }
    .course-meta-row {
      display: flex;
      gap: 12px;
      font-size: 11.5px;
      color: #64748b;
    }
    .skills-covered-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .skill-tag {
      background: #f1f5f9;
      color: #475569;
      font-size: 11px;
      padding: 1px 6px;
      border-radius: 4px;
    }
    .card-footer-btns {
      display: flex;
      gap: 8px;
      margin-top: auto;
      padding-top: 10px;
    }

    /* Certs Grid */
    .certs-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }
    .cert-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .cert-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .vendor-tag {
      font-size: 11px;
      font-weight: 700;
      color: #2563eb;
      text-transform: uppercase;
    }
    .fee-tag {
      background: #fee2e2;
      color: #991b1b;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .fee-tag.fee-free {
      background: #dcfce7;
      color: #15803d;
    }
    .free-materials-box {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 11.5px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .free-badge { color: #15803d; font-weight: 700; }
    .study-link { color: #2563eb; text-decoration: none; font-weight: 600; }
    .study-link:hover { text-decoration: underline; }

    /* Videos Grid */
    .videos-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }
    .video-card {
      display: flex;
      flex-direction: column;
      padding: 0;
      overflow: hidden;
    }
    .video-thumb-wrap {
      position: relative;
      height: 160px;
      background: #0f172a;
    }
    .video-thumb {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .curated-pill {
      position: absolute;
      top: 8px;
      right: 8px;
      background: rgba(15, 23, 42, 0.85);
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .video-body {
      padding: 14px;
      display: flex;
      flex-direction: column;
      flex: 1;
      gap: 6px;
    }
    .channel-name { font-size: 11px; font-weight: 600; color: #64748b; }
    .video-title {
      font-size: 13.5px;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
      line-height: 1.4;
      flex: 1;
    }

    /* Project Blueprints */
    .project-blueprint-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 22px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      border-left: 4px solid #10b981;
    }
    .project-blueprint-card.completed {
      background: #fbfdfc;
      border-color: #86efac;
    }
    .proj-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .proj-badges { display: flex; gap: 8px; margin-bottom: 4px; }
    .diff-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .diff-tag.intermediate { background: #fef3c7; color: #b45309; }
    .diff-tag.advanced { background: #fee2e2; color: #991b1b; }
    .diff-tag.beginner { background: #dcfce7; color: #15803d; }
    .hours-tag {
      background: #f1f5f9;
      color: #475569;
      font-size: 11px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .proj-title { font-size: 19px; font-weight: 800; color: #0f172a; margin: 0; }
    .proj-purpose { font-size: 13.5px; color: #334155; margin: 0 0 16px; line-height: 1.5; }
    .proj-milestones-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .box-title {
      font-size: 12px;
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      display: block;
      margin-bottom: 10px;
    }
    .milestones-steps {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .step-item {
      display: flex;
      gap: 12px;
      align-items: flex-start;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 12px;
    }
    .step-item.step-completed {
      background: #f0fdf4;
      border-color: #bbf7d0;
    }
    .step-checkbox { width: 16px; height: 16px; cursor: pointer; margin-top: 2px; }
    .step-info { flex: 1; }
    .step-title { font-size: 13px; font-weight: 700; color: #0f172a; display: block; }
    .step-desc { font-size: 12px; color: #475569; margin: 2px 0 4px; }
    .step-deliverables {
      list-style: none;
      padding: 0;
      margin: 0;
      font-size: 11.5px;
      color: #15803d;
      font-weight: 500;
    }
    .validation-box {
      background: #fefce8;
      border: 1px solid #fef08a;
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 14px;
    }
    .validation-list {
      list-style: none;
      padding: 0;
      margin: 6px 0 0;
      font-size: 12.5px;
      color: #713f12;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .impact-box {
      font-size: 12.5px;
      color: #475569;
      background: #f8fafc;
      padding: 10px 12px;
      border-radius: 6px;
    }

    /* Practical Exercises */
    .exercises-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }
    .exercise-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .ex-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .ex-tag {
      font-size: 10.5px;
      font-weight: 700;
      color: #2563eb;
    }
    .ex-title { font-size: 15px; font-weight: 700; color: #0f172a; margin: 0; }
    .ex-scenario, .ex-obj { font-size: 12.5px; color: #334155; margin: 0; line-height: 1.4; }
    .code-hints-box {
      background: #0f172a;
      border-radius: 6px;
      padding: 10px 12px;
    }
    .hints-lbl {
      font-size: 10.5px;
      font-weight: 700;
      color: #94a3b8;
      text-transform: uppercase;
      display: block;
      margin-bottom: 6px;
    }
    .code-snippet code {
      font-family: monospace;
      font-size: 11.5px;
      color: #38bdf8;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .criteria-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px 10px;
    }
    .criteria-lbl {
      font-size: 11px;
      font-weight: 700;
      color: #64748b;
      display: block;
      margin-bottom: 4px;
    }
    .criteria-list {
      list-style: none;
      padding: 0;
      margin: 0;
      font-size: 11.5px;
      color: #334155;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
  `]
})
export class LearningComponent implements OnInit {
  private learningService = inject(LearningService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  loading: boolean = true;
  loadError: string | null = null;
  dashboardData: CosgoLearningDashboardResponse | null = null;
  selectedSkillName: string = '';
  selectedSkillPlan: SkillPlan | null = null;
  activeTab: 'roadmap' | 'docs' | 'certs' | 'projects' = 'roadmap';
  showJobsTable: boolean = false;

  weeklyBudget: number = 10;
  updatingBudget: boolean = false;
  budgetSuccessMsg: string | null = null;

  updatingProgress: boolean = false;
  currentOverallState: string = 'RECOMMENDED';

  // Completion Tracking Sets (O(1) lookups for UI binding)
  completedResources: Set<string> = new Set();
  completedMilestones: Set<string> = new Set();
  completedExercises: Set<string> = new Set();
  projectMilestonesCompleted: Set<number> = new Set();

  ngOnInit(): void {
    this.route.queryParamMap.subscribe((params) => {
      const skillParam = params.get('skill');
      this.loadPlan(skillParam || undefined);
    });
  }

  loadPlan(requestedSkill?: string): void {
    this.loading = true;
    this.loadError = null;
    this.cdr.markForCheck();

    this.learningService
      .getCosgoLearningPlan(requestedSkill)
      .pipe(
        finalize(() => {
          this.loading = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (resp) => {
          this.dashboardData = resp;
          if (resp.is_cosgo_empty_state || !resp.skill_plan) {
            this.selectedSkillPlan = null;
            this.selectedSkillName = '';
            this.cdr.markForCheck();
            return;
          }

          this.selectedSkillPlan = resp.skill_plan;
          this.selectedSkillName = resp.skill_plan.skill_name;
          this.weeklyBudget = resp.weekly_hours_budget || 10;
          this.currentOverallState = resp.skill_plan.progress_state || 'RECOMMENDED';

          // Initialize completed sets from persisted progress
          const prog = resp.skill_plan.progress || {};
          this.completedResources = new Set(prog.completed_resources || []);
          this.completedMilestones = new Set(prog.completed_milestones || []);
          this.completedExercises = new Set(prog.completed_exercises || []);
          this.projectMilestonesCompleted = new Set(prog.project_milestones_completed || []);

          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loadError = err?.error?.detail || err?.message || 'Unable to load COSGO learning plan.';
          this.cdr.markForCheck();
        }
      });
  }

  reloadCurrentSkill(): void {
    this.loadPlan(this.selectedSkillName || undefined);
  }

  selectSkill(skillName: string): void {
    if (this.selectedSkillName === skillName) return;
    this.selectedSkillName = skillName;
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { skill: skillName },
      queryParamsHandling: 'merge'
    });
    this.loadPlan(skillName);
  }

  toggleJobsExpanded(): void {
    this.showJobsTable = !this.showJobsTable;
    this.cdr.markForCheck();
  }

  getCalculatedWeeks(): number {
    const totalHours = this.selectedSkillPlan?.estimated_hours || 0;
    const pace = this.weeklyBudget > 0 ? this.weeklyBudget : 10;
    return Math.max(1, Math.ceil(totalHours / pace));
  }

  saveBudget(): void {
    if (this.weeklyBudget < 2 || this.weeklyBudget > 60) return;
    this.updatingBudget = true;
    this.cdr.markForCheck();

    this.learningService
      .updateWeeklyBudget(this.weeklyBudget)
      .pipe(
        finalize(() => {
          this.updatingBudget = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.budgetSuccessMsg = `Weekly study budget updated to ${res.weekly_hours_budget} hrs/week.`;
          this.cdr.markForCheck();
          setTimeout(() => {
            this.budgetSuccessMsg = null;
            this.cdr.markForCheck();
          }, 4000);
        },
        error: (err) => {
          this.budgetSuccessMsg = `Failed to update budget: ${err?.error?.detail || err?.message}`;
          this.cdr.markForCheck();
        }
      });
  }

  // --- PROGRESS TRACKING TOGGLES ---

  isResourceCompleted(url?: string): boolean {
    return !!url && this.completedResources.has(url);
  }

  toggleResource(url?: string): void {
    if (!url || !this.selectedSkillName) return;
    this.updatingProgress = true;

    if (this.completedResources.has(url)) {
      this.completedResources.delete(url);
    } else {
      this.completedResources.add(url);
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      toggle_resource_url: url
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          // Revert on error
          if (this.completedResources.has(url)) {
            this.completedResources.delete(url);
          } else {
            this.completedResources.add(url);
          }
          this.cdr.markForCheck();
        }
      });
  }

  isMilestoneCompleted(stageId: string): boolean {
    return this.completedMilestones.has(stageId);
  }

  toggleMilestone(stageId: string): void {
    if (!stageId || !this.selectedSkillName) return;
    this.updatingProgress = true;

    if (this.completedMilestones.has(stageId)) {
      this.completedMilestones.delete(stageId);
    } else {
      this.completedMilestones.add(stageId);
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      toggle_milestone_id: stageId
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          if (this.completedMilestones.has(stageId)) {
            this.completedMilestones.delete(stageId);
          } else {
            this.completedMilestones.add(stageId);
          }
          this.cdr.markForCheck();
        }
      });
  }

  isExerciseCompleted(exId: string): boolean {
    return this.completedExercises.has(exId);
  }

  toggleExercise(exId: string): void {
    if (!exId || !this.selectedSkillName) return;
    this.updatingProgress = true;

    if (this.completedExercises.has(exId)) {
      this.completedExercises.delete(exId);
    } else {
      this.completedExercises.add(exId);
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      toggle_exercise_id: exId
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          if (this.completedExercises.has(exId)) {
            this.completedExercises.delete(exId);
          } else {
            this.completedExercises.add(exId);
          }
          this.cdr.markForCheck();
        }
      });
  }

  isProjectCompleted(): boolean {
    return !!this.selectedSkillPlan?.progress?.project_completed;
  }

  toggleProject(projectId: string): void {
    if (!this.selectedSkillName) return;
    this.updatingProgress = true;

    if (this.selectedSkillPlan && this.selectedSkillPlan.progress) {
      this.selectedSkillPlan.progress.project_completed = !this.selectedSkillPlan.progress.project_completed;
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      toggle_project_id: projectId
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          if (this.selectedSkillPlan && this.selectedSkillPlan.progress) {
            this.selectedSkillPlan.progress.project_completed = !this.selectedSkillPlan.progress.project_completed;
          }
          this.cdr.markForCheck();
        }
      });
  }

  isProjectMilestoneCompleted(step: number): boolean {
    return this.projectMilestonesCompleted.has(step);
  }

  toggleProjectMilestone(step: number): void {
    if (!this.selectedSkillName) return;
    this.updatingProgress = true;

    if (this.projectMilestonesCompleted.has(step)) {
      this.projectMilestonesCompleted.delete(step);
    } else {
      this.projectMilestonesCompleted.add(step);
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      toggle_project_milestone_step: step
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          if (this.projectMilestonesCompleted.has(step)) {
            this.projectMilestonesCompleted.delete(step);
          } else {
            this.projectMilestonesCompleted.add(step);
          }
          this.cdr.markForCheck();
        }
      });
  }

  changeOverallProgressState(newState: string): void {
    if (!this.selectedSkillName || this.currentOverallState === newState) return;
    this.updatingProgress = true;
    this.currentOverallState = newState;

    if (this.selectedSkillPlan) {
      this.selectedSkillPlan.progress_state = newState;
    }

    // Also update queue card
    const queueCard = (this.dashboardData?.recommended_skills || []).find(
      (s) => s.skill_name.toLowerCase() === this.selectedSkillName.toLowerCase()
    );
    if (queueCard) {
      queueCard.progress_state = newState;
    }
    this.cdr.markForCheck();

    const payload: LearningProgressPayload = {
      skill_name: this.selectedSkillName,
      progress_state: newState
    };

    this.learningService
      .updateLearningProgress(payload)
      .pipe(
        finalize(() => {
          this.updatingProgress = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.syncProgressState(res);
        },
        error: () => {
          this.cdr.markForCheck();
        }
      });
  }

  private syncProgressState(res: any): void {
    if (res?.cosgo_action_progress?.progress_state) {
      const p = res.cosgo_action_progress.progress_state;
      this.currentOverallState = p;
      if (this.selectedSkillPlan) {
        this.selectedSkillPlan.progress_state = p;
      }
      const queueCard = (this.dashboardData?.recommended_skills || []).find(
        (s) => s.skill_name.toLowerCase() === this.selectedSkillName.toLowerCase()
      );
      if (queueCard) {
        queueCard.progress_state = p;
      }
    }
    this.cdr.markForCheck();
  }
}

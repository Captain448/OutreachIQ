import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { CosgoService } from '../../core/services/cosgo.service';
import {
  CosgoRun,
  CosgoAction,
  CosgoProgressState,
  CosgoCoverageMatrixResponse,
  CosgoBenchmarkResponse
} from '../../core/models/cosgo.model';

@Component({
  selector: 'app-skill-gap',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="cosgo-page">
      <!-- Page Header -->
      <header class="page-header">
        <div class="header-left">
          <div class="mode-badge-wrap">
            <span class="iq-pill iq-pill-accent">COSGO Engine</span>
            <span class="iq-pill iq-pill-neutral">Algorithm {{ latestRun?.algorithm_version || 'cosgo-v1.1-verified' }}</span>
            <span class="iq-pill iq-pill-warning" *ngIf="latestRun && latestRun.algorithm_version !== 'cosgo-v1.1-verified'">Legacy Calculation</span>
          </div>
          <h1 class="page-title">Cross-Opportunity Skill Gap Optimization</h1>
          <p class="page-subtitle">
            Personalized, evidence-grounded skill development roadmap maximizing weighted coverage across your target opportunities.
          </p>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-secondary"
            (click)="activeTab = 'benchmark'; loadBenchmark()"
            [disabled]="loading"
          >
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            Research Benchmarks
          </button>
          <button
            class="btn btn-primary"
            (click)="triggerOptimization()"
            [disabled]="loading || optimizing"
          >
            <span *ngIf="optimizing" class="spinner-sm"></span>
            {{ optimizing ? 'Optimizing...' : 'Re-optimize Plan' }}
          </button>
        </div>
      </header>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-state">
        <div class="spinner"></div>
        <p class="loading-text">Analyzing target opportunities and solving budgeted coverage...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="!loading && loadError" class="error-banner">
        <div class="error-msg">
          <strong>Unable to load COSGO plan:</strong> {{ loadError }}
        </div>
        <button class="btn btn-secondary btn-sm" (click)="loadPlan()">Retry</button>
      </div>

      <!-- Empty / Insufficient Opportunities State -->
      <div *ngIf="!loading && !loadError && (!latestRun || latestRun.eligible_opportunities_count === 0)" class="empty-state-card">
        <div class="empty-icon">📊</div>
        <h3 class="empty-title">Insufficient Opportunity Data</h3>
        <p class="empty-desc">
          COSGO requires verified target opportunities in your workspace to analyze skill gaps and compute cross-opportunity coverage.
        </p>
        <div class="empty-actions">
          <a routerLink="/opportunities" class="btn btn-primary">Find Opportunities</a>
          <button class="btn btn-secondary" (click)="triggerOptimization()">Retry Analysis</button>
        </div>
      </div>

      <!-- Main Plan Content -->
      <div *ngIf="!loading && !loadError && latestRun && latestRun.eligible_opportunities_count > 0" class="plan-content">
        <!-- Top Metrics KPI Summary Bar -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">Target Jobs Analyzed</span>
            <div class="kpi-value-row">
              <span class="kpi-val">{{ latestRun.eligible_opportunities_count }}</span>
              <span class="kpi-sub">eligible vacancies</span>
            </div>
            <div class="kpi-footer-note" *ngIf="latestRun.excluded_opportunities_count > 0">
              {{ latestRun.excluded_opportunities_count }} excluded (duplicates / low info)
            </div>
          </div>

          <div class="kpi-card">
            <span class="kpi-label">Requirement Coverage</span>
            <div class="kpi-value-row">
              <span class="kpi-val highlight">{{ (latestRun.projected_coverage * 100).toFixed(1) }}%</span>
              <span class="kpi-badge-gain" title="Percentage-point gain in weighted requirement coverage">+{{ (latestRun.marginal_coverage_increase * 100).toFixed(1) }} pp</span>
            </div>
            <div class="coverage-bar-track">
              <div
                class="coverage-bar-base"
                [style.width.%]="latestRun.baseline_coverage * 100"
                title="Baseline: {{ (latestRun.baseline_coverage * 100).toFixed(1) }}%"
              ></div>
              <div
                class="coverage-bar-gain"
                [style.width.%]="latestRun.marginal_coverage_increase * 100"
                title="Gain: +{{ (latestRun.marginal_coverage_increase * 100).toFixed(1) }}%"
              ></div>
            </div>
            <div class="kpi-bar-labels">
              <span>Baseline: {{ (latestRun.baseline_coverage * 100).toFixed(1) }}%</span>
              <span>Projected: {{ (latestRun.projected_coverage * 100).toFixed(1) }}%</span>
            </div>
          </div>

          <div class="kpi-card">
            <span class="kpi-label">High-Fit Opportunities (≥75%)</span>
            <div class="kpi-value-row">
              <span class="kpi-val">{{ latestRun.opportunities_at_threshold_projected }}</span>
              <span class="kpi-sub">from {{ latestRun.opportunities_at_threshold_baseline }} baseline</span>
            </div>
            <div class="kpi-footer-note text-success">
              +{{ latestRun.opportunities_at_threshold_projected - latestRun.opportunities_at_threshold_baseline }} newly qualifying
            </div>
          </div>

          <div class="kpi-card">
            <span class="kpi-label">Study Budget Allocated</span>
            <div class="kpi-value-row">
              <span class="kpi-val">{{ latestRun.diagnostics.budget_hours_used || totalEstimatedHours }} hrs</span>
              <span class="kpi-sub">of {{ latestRun.budget_hours }} hrs</span>
            </div>
            <div class="kpi-footer-note">
              ~{{ latestRun.diagnostics.estimated_weeks_to_complete || 4 }} weeks at {{ latestRun.weekly_budget_hours }} hrs/wk
            </div>
          </div>
        </div>

        <!-- Budget Configuration Bar -->
        <div class="budget-bar">
          <div class="budget-info">
            <span class="budget-title">Learning-Time Budget Settings</span>
            <span class="budget-subtitle">Adjust total study hours or weekly pace to rebalance recommendations.</span>
          </div>
          <div class="budget-controls">
            <div class="ctrl-group">
              <label>Total Budget</label>
              <div class="input-with-unit">
                <input
                  type="number"
                  [(ngModel)]="customTotalBudget"
                  min="10"
                  max="200"
                  step="5"
                  class="budget-num-input"
                />
                <span class="unit-tag">hrs</span>
              </div>
            </div>
            <div class="ctrl-group">
              <label>Weekly Pace</label>
              <div class="input-with-unit">
                <input
                  type="number"
                  [(ngModel)]="customWeeklyBudget"
                  min="2"
                  max="40"
                  step="2"
                  class="budget-num-input"
                />
                <span class="unit-tag">hrs/wk</span>
              </div>
            </div>
            <button
              class="btn btn-secondary btn-sm"
              (click)="updateBudget()"
              [disabled]="optimizing"
            >
              Update Budget
            </button>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-bar">
          <button
            class="tab-btn"
            [class.active]="activeTab === 'roadmap'"
            (click)="activeTab = 'roadmap'"
          >
            📋 Recommended Actions & Roadmap ({{ latestRun.actions.length }})
          </button>
          <button
            class="tab-btn"
            [class.active]="activeTab === 'matrix'"
            (click)="activeTab = 'matrix'; loadMatrix()"
          >
            📊 Coverage Gap Matrix
          </button>
          <button
            class="tab-btn"
            [class.active]="activeTab === 'benchmark'"
            (click)="activeTab = 'benchmark'; loadBenchmark()"
          >
            🔬 Academic Baselines Evaluation
          </button>
        </div>

        <!-- TAB 1: ROADMAP & RECOMMENDED ACTIONS -->
        <div *ngIf="activeTab === 'roadmap'" class="tab-pane">
          <div *ngIf="latestRun.actions.length === 0" class="empty-actions-note">
            No skill gaps found within the selected budget. Your verified profile already satisfies requirements for the eligible roles.
          </div>

          <div class="actions-list">
            <div
              *ngFor="let act of latestRun.actions; let idx = index"
              class="action-card"
              [class.completed]="act.progress_state === 'COMPLETED'"
              [class.in-progress]="act.progress_state === 'IN_PROGRESS'"
            >
              <!-- Action Top Header -->
              <div class="action-header">
                <div class="rank-badge">#{{ act.priority_rank }}</div>
                <div class="action-title-block">
                  <div class="title-row">
                    <h3 class="skill-name">{{ act.skill_name }}</h3>
                    <span class="category-chip">{{ act.category }}</span>
                    <span
                      class="state-chip"
                      [ngClass]="'state-' + act.progress_state.toLowerCase()"
                    >
                      {{ act.progress_state }}
                    </span>
                  </div>
                  <p class="why-text">{{ act.why_recommended }}</p>
                </div>
                <div class="effort-badge-wrap">
                  <div class="hours-badge">{{ act.estimated_hours }} hrs</div>
                  <div class="effort-range">
                    {{ act.effort_uncertainty_range.min_hours }}-{{ act.effort_uncertainty_range.max_hours }} hrs range
                  </div>
                </div>
              </div>

              <!-- Metrics & Prerequisites Strip -->
              <div class="action-strip">
                <div class="strip-item">
                  <span class="strip-lbl">Marginal Coverage Gain:</span>
                  <span class="strip-val text-success" title="Percentage-point contribution to weighted coverage">+{{ (act.marginal_coverage_gain * 100).toFixed(1) }} pp</span>
                </div>
                <div class="strip-item">
                  <span class="strip-lbl">Opportunities Helped:</span>
                  <span class="strip-val">{{ act.opportunities_count }} target roles</span>
                </div>
                <div class="strip-item" *ngIf="act.prerequisites && act.prerequisites.length > 0">
                  <span class="strip-lbl">Prerequisites:</span>
                  <span class="prereq-chip" *ngFor="let p of act.prerequisites">{{ p }}</span>
                </div>
              </div>

              <!-- Practical Multi-Skill Project Box -->
              <div class="project-box" *ngIf="act.practical_project && act.practical_project.title">
                <div class="project-header">
                  <span class="project-tag">PRACTICAL PORTFOLIO PROJECT</span>
                  <span class="project-difficulty">{{ act.practical_project.difficulty_level || 'Intermediate' }}</span>
                </div>
                <h4 class="project-title">{{ act.practical_project.title }}</h4>
                <p class="project-desc">{{ act.practical_project.description }}</p>

                <div class="project-skills-row" *ngIf="act.practical_project.overlapping_skills">
                  <span class="skills-label">Demonstrates Multiple Competencies:</span>
                  <span class="overlap-pill" *ngFor="let s of act.practical_project.overlapping_skills">{{ s }}</span>
                </div>

                <div class="deliverables-wrap" *ngIf="act.practical_project.deliverables">
                  <span class="deliverables-title">Target Deliverables:</span>
                  <ul class="deliverables-list">
                    <li *ngFor="let d of act.practical_project.deliverables">{{ d }}</li>
                  </ul>
                </div>
              </div>

              <!-- Verifiable Learning Resources -->
              <div class="resources-box" *ngIf="act.learning_resources && act.learning_resources.length > 0">
                <span class="resources-label">Verified Learning Resources:</span>
                <div class="resource-links">
                  <a
                    *ngFor="let res of act.learning_resources"
                    [href]="res.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="resource-link"
                  >
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                      <polyline points="15 3 21 3 21 9"></polyline>
                      <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    <span>{{ res.title }}</span>
                    <span class="provider-tag">({{ res.provider }})</span>
                  </a>
                </div>
              </div>

              <!-- Expandable Jobs Helped Toggle -->
              <div class="expand-jobs-section">
                <button class="expand-jobs-btn" (click)="toggleJobsExpanded(act.id)">
                  {{ isJobsExpanded(act.id) ? '▲ Hide' : '▼ View' }} {{ act.opportunities_count }} Target Opportunities Helped
                </button>

                <div *ngIf="isJobsExpanded(act.id)" class="expanded-jobs-table">
                  <div *ngFor="let opp of act.target_opportunities_summary" class="job-mini-row">
                    <div class="job-info">
                      <span class="job-t">{{ opp.title }}</span>
                      <span class="job-c">{{ opp.company_name }}</span>
                    </div>
                    <div class="job-meta">
                      <span class="fit-score">{{ (opp.match_score * 100).toFixed(0) }}% Match</span>
                      <a *ngIf="opp.primary_url" [href]="opp.primary_url" target="_blank" class="job-link">
                        Listing ↗
                      </a>
                      <a [routerLink]="['/outreach']" [queryParams]="{ opportunityId: opp.id }" class="job-link outreach-link" title="Draft personalized AI outreach for this opportunity">
                        Draft Outreach →
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Action Footer / Progress Controls -->
              <div class="action-footer">
                <div class="progress-ctrls">
                  <span class="ctrl-label">Update Progress:</span>
                  <div class="btn-group-sm">
                    <button
                      class="btn-prog"
                      [class.active]="act.progress_state === 'RECOMMENDED'"
                      (click)="changeActionProgress(act, 'RECOMMENDED')"
                    >
                      Recommended
                    </button>
                    <button
                      class="btn-prog"
                      [class.active]="act.progress_state === 'PLANNED'"
                      (click)="changeActionProgress(act, 'PLANNED')"
                    >
                      Planned
                    </button>
                    <button
                      class="btn-prog"
                      [class.active]="act.progress_state === 'IN_PROGRESS'"
                      (click)="changeActionProgress(act, 'IN_PROGRESS')"
                    >
                      In Progress
                    </button>
                    <button
                      class="btn-prog btn-prog-complete"
                      [class.active]="act.progress_state === 'COMPLETED'"
                      (click)="changeActionProgress(act, 'COMPLETED')"
                    >
                      ✓ Completed
                    </button>
                  </div>
                </div>
                <div class="footer-notice">
                  <em>Note: Completing an action updates your roadmap tracking. It does not automatically modify your verified profile.</em>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: COVERAGE GAP MATRIX -->
        <div *ngIf="activeTab === 'matrix'" class="tab-pane">
          <div *ngIf="loadingMatrix" class="loading-state">
            <div class="spinner"></div>
            <p>Constructing opportunity coverage matrix...</p>
          </div>

          <div *ngIf="!loadingMatrix && matrixData" class="matrix-container">
            <div class="matrix-legend">
              <span class="legend-item"><span class="badge-v">✓</span> Already Demonstrated (Verified)</span>
              <span class="legend-item"><span class="badge-i">~</span> Inferred / Partial Evidence</span>
              <span class="legend-item"><span class="badge-c">★</span> Covered by COSGO Action</span>
              <span class="legend-item"><span class="badge-g">-</span> Remaining Uncovered Gap</span>
            </div>

            <div class="table-wrap">
              <table class="matrix-table">
                <thead>
                  <tr>
                    <th class="th-opp">Target Opportunity</th>
                    <th class="th-cov">Coverage</th>
                    <th *ngFor="let s of matrixData.skills_header" class="th-skill">{{ s }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let row of matrixData.matrix">
                    <td class="td-opp">
                      <div class="opp-main">{{ row.job_title }}</div>
                      <div class="opp-sub">{{ row.company_name }} &bull; {{ (row.match_score * 100).toFixed(0) }}% Fit</div>
                    </td>
                    <td class="td-cov">
                      <div class="cov-prog-wrap">
                        <span class="cov-pct">{{ (row.baseline_coverage * 100).toFixed(0) }}% → {{ (row.projected_coverage * 100).toFixed(0) }}%</span>
                        <div class="cov-mini-bar">
                          <div class="cov-mini-fill" [style.width.%]="row.projected_coverage * 100"></div>
                        </div>
                      </div>
                    </td>
                    <td *ngFor="let s of matrixData.skills_header" class="td-status">
                      <span *ngIf="isSkillVerified(row, s)" class="badge-v" title="Verified in Profile">✓</span>
                      <span *ngIf="isSkillInferred(row, s)" class="badge-i" title="Inferred in Profile">~</span>
                      <span *ngIf="isSkillCovered(row, s)" class="badge-c" title="Covered by COSGO Roadmap">★</span>
                      <span *ngIf="isSkillGap(row, s)" class="badge-g" title="Remaining Gap">-</span>
                      <span *ngIf="!isSkillInJob(row, s)" class="badge-none">&middot;</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- TAB 3: ACADEMIC BENCHMARKS EVALUATION -->
        <div *ngIf="activeTab === 'benchmark'" class="tab-pane">
          <div *ngIf="loadingBenchmark" class="loading-state">
            <div class="spinner"></div>
            <p>Running benchmark simulation across baseline algorithms...</p>
          </div>

          <div *ngIf="!loadingBenchmark && benchmarkData" class="benchmark-container">
            <div class="benchmark-header-box">
              <div class="bench-meta-row">
                <span class="iq-pill iq-pill-accent">Canonical Benchmark V1</span>
                <span class="iq-pill iq-pill-neutral">Standard Budget: 35.0 hrs</span>
                <span class="iq-pill iq-pill-neutral">Normalized Knapsack Coverage</span>
              </div>
              <h3 class="bench-h3">Academic Reproducibility & Mathematical Evaluation</h3>
              <p class="bench-p">
                COSGO optimizes the submodular weighted coverage objective under a knapsack effort constraint.
                Below is a fair, deterministic comparison against frequency-ranked and independent per-job baseline heuristics on identical opportunity and candidate data.
              </p>
              <div class="reconciliation-callout">
                <strong>Benchmark Discrepancy Reconciliation:</strong>
                The canonical comparative benchmark is fixed at <strong>35.0 hours</strong> to evaluate all strategies on an identical level playing field.
                Sensitivity demonstrations (e.g. 40.0 hours) evaluate expanded capacity and naturally achieve higher coverage due to submodular budget expansion; they represent distinct parameter studies and are not mixed with this comparative table.
              </div>
            </div>

            <!-- Comparison Table -->
            <div class="table-wrap">
              <table class="benchmark-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Actions</th>
                    <th>Effort (Hrs)</th>
                    <th>Projected Coverage</th>
                    <th>Marginal Gain (pp)</th>
                    <th>Efficiency (Gain/Hr)</th>
                    <th>Jobs ≥75% Fit</th>
                    <th>Distinct Jobs Helped</th>
                    <th>COSGO Overlap</th>
                  </tr>
                </thead>
                <tbody>
                  <!-- COSGO -->
                  <tr class="row-highlight">
                    <td><strong>COSGO (Budgeted Coverage)</strong></td>
                    <td>{{ benchmarkData.cosgo.skills_count }}</td>
                    <td>{{ benchmarkData.cosgo.hours_spent }}</td>
                    <td class="text-success font-bold">{{ (benchmarkData.cosgo.final_coverage * 100).toFixed(1) }}%</td>
                    <td class="text-success font-bold">+{{ (benchmarkData.cosgo.coverage_gain * 100).toFixed(1) }} pp</td>
                    <td class="font-bold text-accent">{{ (benchmarkData.cosgo.gain_per_hour * 1000).toFixed(2) }}</td>
                    <td>{{ benchmarkData.cosgo.opportunities_qualifying }}</td>
                    <td>{{ benchmarkData.cosgo.unique_opportunities_improved }}</td>
                    <td>100%</td>
                  </tr>
                  <!-- Frequency Baseline -->
                  <tr>
                    <td>Frequency-Ranked Skill Baseline</td>
                    <td>{{ benchmarkData.frequency_baseline.skills_count }}</td>
                    <td>{{ benchmarkData.frequency_baseline.hours_spent }}</td>
                    <td>{{ (benchmarkData.frequency_baseline.final_coverage * 100).toFixed(1) }}%</td>
                    <td>+{{ (benchmarkData.frequency_baseline.coverage_gain * 100).toFixed(1) }} pp</td>
                    <td>{{ (benchmarkData.frequency_baseline.gain_per_hour * 1000).toFixed(2) }}</td>
                    <td>{{ benchmarkData.frequency_baseline.opportunities_qualifying }}</td>
                    <td>{{ benchmarkData.frequency_baseline.unique_opportunities_improved }}</td>
                    <td>{{ (benchmarkData.frequency_baseline.jaccard_similarity_with_cosgo * 100).toFixed(0) }}%</td>
                  </tr>
                  <!-- Independent Per Job -->
                  <tr>
                    <td>Independent Per-Job Baseline</td>
                    <td>{{ benchmarkData.independent_per_job.skills_count }}</td>
                    <td>{{ benchmarkData.independent_per_job.hours_spent }}</td>
                    <td>{{ (benchmarkData.independent_per_job.final_coverage * 100).toFixed(1) }}%</td>
                    <td>+{{ (benchmarkData.independent_per_job.coverage_gain * 100).toFixed(1) }} pp</td>
                    <td>{{ (benchmarkData.independent_per_job.gain_per_hour * 1000).toFixed(2) }}</td>
                    <td>{{ benchmarkData.independent_per_job.opportunities_qualifying }}</td>
                    <td>{{ benchmarkData.independent_per_job.unique_opportunities_improved }}</td>
                    <td>{{ (benchmarkData.independent_per_job.jaccard_similarity_with_cosgo * 100).toFixed(0) }}%</td>
                  </tr>
                  <!-- Greedy No Effort -->
                  <tr>
                    <td>Greedy Frequency (No Effort Accounting)</td>
                    <td>{{ benchmarkData.greedy_frequency_no_effort.skills_count }}</td>
                    <td>{{ benchmarkData.greedy_frequency_no_effort.hours_spent }}</td>
                    <td>{{ (benchmarkData.greedy_frequency_no_effort.final_coverage * 100).toFixed(1) }}%</td>
                    <td>+{{ (benchmarkData.greedy_frequency_no_effort.coverage_gain * 100).toFixed(1) }} pp</td>
                    <td>{{ (benchmarkData.greedy_frequency_no_effort.gain_per_hour * 1000).toFixed(2) }}</td>
                    <td>{{ benchmarkData.greedy_frequency_no_effort.opportunities_qualifying }}</td>
                    <td>{{ benchmarkData.greedy_frequency_no_effort.unique_opportunities_improved }}</td>
                    <td>{{ (benchmarkData.greedy_frequency_no_effort.jaccard_similarity_with_cosgo * 100).toFixed(0) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Conclusion Box -->
            <div class="conclusion-box" *ngIf="benchmarkData.comparison_summary">
              <span class="conclusion-title">Evaluation Summary:</span>
              <p class="conclusion-text">{{ benchmarkData.comparison_summary.conclusion }}</p>
              <div class="lift-badges">
                <span class="lift-badge">
                  Relative Coverage Lift vs Frequency: <strong>{{ benchmarkData.comparison_summary.cosgo_relative_coverage_gain_lift_vs_frequency || benchmarkData.comparison_summary.cosgo_coverage_gain_lift_vs_frequency }}</strong>
                </span>
                <span class="lift-badge">
                  Relative Efficiency Lift vs Frequency: <strong>{{ benchmarkData.comparison_summary.cosgo_relative_efficiency_lift_vs_frequency || benchmarkData.comparison_summary.cosgo_efficiency_lift_vs_frequency }}</strong>
                </span>
                <span class="lift-badge" *ngIf="benchmarkData.comparison_summary.budget_utilization_explanation">
                  Capacity: <strong>{{ benchmarkData.comparison_summary.budget_utilization_explanation }}</strong>
                </span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .cosgo-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .cosgo-page {
        padding: 16px;
      }
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .mode-badge-wrap {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
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
    .iq-pill-warning {
      background: #fef3c7;
      color: #b45309;
      border: 1px solid #fde68a;
    }
    .modeled-disclaimer-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 18px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-left: 4px solid #3b82f6;
      border-radius: 6px;
      margin-bottom: 24px;
      font-size: 13px;
      color: #334155;
      line-height: 1.45;
    }
    .disclaimer-icon {
      color: #2563eb;
      flex-shrink: 0;
    }
    .bench-meta-row {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }
    .reconciliation-callout {
      margin-top: 14px;
      padding: 12px 16px;
      background: #f8fafc;
      border: 1px dashed #94a3b8;
      border-radius: 6px;
      font-size: 12.5px;
      color: #334155;
      line-height: 1.5;
    }
    .page-title {
      font-size: 26px;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 6px 0;
      letter-spacing: -0.02em;
    }
    .page-subtitle {
      font-size: 14px;
      color: #475569;
      margin: 0;
      max-width: 720px;
      line-height: 1.5;
    }
    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      border-radius: 6px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      border: 1px solid transparent;
      text-decoration: none;
    }
    .btn-primary {
      background: #2563eb;
      color: #ffffff;
      border-color: #1d4ed8;
    }
    .btn-primary:hover:not(:disabled) {
      background: #1d4ed8;
    }
    .btn-secondary {
      background: #ffffff;
      color: #334155;
      border-color: #cbd5e1;
    }
    .btn-secondary:hover:not(:disabled) {
      background: #f8fafc;
      border-color: #94a3b8;
    }
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .btn-sm {
      padding: 6px 12px;
      font-size: 12.5px;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .kpi-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      display: flex;
      flex-direction: column;
    }
    .kpi-label {
      font-size: 12px;
      font-weight: 600;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 8px;
    }
    .kpi-value-row {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 8px;
    }
    .kpi-val {
      font-size: 26px;
      font-weight: 800;
      color: #0f172a;
    }
    .kpi-val.highlight {
      color: #2563eb;
    }
    .kpi-sub {
      font-size: 13px;
      color: #64748b;
    }
    .kpi-badge-gain {
      background: #dcfce7;
      color: #15803d;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }
    .coverage-bar-track {
      height: 8px;
      background: #f1f5f9;
      border-radius: 4px;
      overflow: hidden;
      display: flex;
      margin: 8px 0 6px 0;
    }
    .coverage-bar-base {
      background: #94a3b8;
      height: 100%;
    }
    .coverage-bar-gain {
      background: #10b981;
      height: 100%;
    }
    .kpi-bar-labels {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #64748b;
    }
    .kpi-footer-note {
      font-size: 12px;
      color: #64748b;
      margin-top: auto;
    }
    .text-success { color: #16a34a !important; }
    .text-accent { color: #2563eb !important; }
    .font-bold { font-weight: 700 !important; }
    .budget-bar {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .budget-title {
      display: block;
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
    }
    .budget-subtitle {
      font-size: 12.5px;
      color: #64748b;
    }
    .budget-controls {
      display: flex;
      align-items: flex-end;
      gap: 14px;
    }
    .ctrl-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .ctrl-group label {
      font-size: 11.5px;
      font-weight: 600;
      color: #475569;
    }
    .input-with-unit {
      display: flex;
      align-items: center;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      padding-right: 8px;
    }
    .budget-num-input {
      border: none;
      background: transparent;
      padding: 6px 10px;
      font-size: 13px;
      width: 70px;
      outline: none;
    }
    .unit-tag {
      font-size: 11px;
      color: #94a3b8;
    }
    .tab-bar {
      display: flex;
      gap: 10px;
      border-bottom: 1px solid #e2e8f0;
      margin-bottom: 24px;
    }
    .tab-btn {
      padding: 10px 18px;
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      font-size: 14px;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tab-btn.active {
      color: #2563eb;
      border-bottom-color: #2563eb;
    }
    .actions-list {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .action-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
      display: flex;
      flex-direction: column;
      gap: 16px;
      border-left: 4px solid #2563eb;
    }
    .action-card.completed {
      border-left-color: #10b981;
      background: #fafcfb;
    }
    .action-card.in-progress {
      border-left-color: #f59e0b;
    }
    .action-header {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }
    .rank-badge {
      background: #eff6ff;
      color: #2563eb;
      font-size: 14px;
      font-weight: 800;
      width: 38px;
      height: 38px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .action-title-block {
      flex: 1;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 4px;
      flex-wrap: wrap;
    }
    .skill-name {
      font-size: 18px;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
    }
    .category-chip {
      font-size: 11.5px;
      background: #f1f5f9;
      color: #475569;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 500;
    }
    .state-chip {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .state-recommended { background: #eff6ff; color: #2563eb; }
    .state-planned { background: #fef3c7; color: #b45309; }
    .state-in_progress { background: #fef3c7; color: #d97706; }
    .state-completed { background: #dcfce7; color: #15803d; }
    .why-text {
      font-size: 13.5px;
      color: #334155;
      margin: 0;
    }
    .effort-badge-wrap {
      text-align: right;
      flex-shrink: 0;
    }
    .hours-badge {
      font-size: 16px;
      font-weight: 800;
      color: #0f172a;
    }
    .effort-range {
      font-size: 11.5px;
      color: #64748b;
    }
    .action-strip {
      display: flex;
      gap: 20px;
      padding: 10px 14px;
      background: #f8fafc;
      border-radius: 6px;
      font-size: 12.5px;
      flex-wrap: wrap;
      align-items: center;
    }
    .strip-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .strip-lbl { color: #64748b; }
    .strip-val { font-weight: 600; color: #0f172a; }
    .prereq-chip {
      background: #e2e8f0;
      color: #334155;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 11px;
    }
    .project-box {
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 16px 18px;
    }
    .project-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .project-tag {
      font-size: 11px;
      font-weight: 700;
      color: #2563eb;
      letter-spacing: 0.03em;
    }
    .project-difficulty {
      font-size: 11px;
      color: #64748b;
    }
    .project-title {
      font-size: 15px;
      font-weight: 700;
      color: #0f172a;
      margin: 0 0 6px 0;
    }
    .project-desc {
      font-size: 13px;
      color: #475569;
      margin: 0 0 10px 0;
      line-height: 1.5;
    }
    .project-skills-row {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    .skills-label {
      font-size: 12px;
      color: #64748b;
      font-weight: 500;
    }
    .overlap-pill {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11.5px;
      font-weight: 600;
    }
    .deliverables-title {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: #334155;
      margin-bottom: 4px;
    }
    .deliverables-list {
      margin: 0;
      padding-left: 18px;
      font-size: 12.5px;
      color: #475569;
      line-height: 1.6;
    }
    .resources-box {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .resources-label {
      font-size: 12px;
      font-weight: 600;
      color: #475569;
    }
    .resource-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .resource-link {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12.5px;
      color: #2563eb;
      text-decoration: none;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      padding: 5px 10px;
      border-radius: 4px;
      transition: background 0.15s;
    }
    .resource-link:hover {
      background: #eff6ff;
    }
    .provider-tag {
      font-size: 11px;
      color: #64748b;
    }
    .expand-jobs-section {
      margin-top: 4px;
    }
    .expand-jobs-btn {
      background: none;
      border: none;
      color: #2563eb;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      padding: 0;
    }
    .expanded-jobs-table {
      margin-top: 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      max-height: 220px;
      overflow-y: auto;
    }
    .job-mini-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      border-bottom: 1px solid #f1f5f9;
      font-size: 12.5px;
    }
    .job-mini-row:last-child { border-bottom: none; }
    .job-t { font-weight: 600; color: #0f172a; margin-right: 6px; }
    .job-c { color: #64748b; }
    .job-meta { display: flex; align-items: center; gap: 8px; }
    .fit-score {
      font-size: 11.5px;
      color: #2563eb;
      font-weight: 600;
    }
    .job-link {
      font-size: 11.5px;
      color: #2563eb;
    }
    .action-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 12px;
      border-top: 1px solid #f1f5f9;
      flex-wrap: wrap;
      gap: 12px;
    }
    .progress-ctrls {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .ctrl-label {
      font-size: 12px;
      font-weight: 600;
      color: #64748b;
    }
    .btn-group-sm {
      display: flex;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      overflow: hidden;
    }
    .btn-prog {
      border: none;
      background: #ffffff;
      padding: 5px 10px;
      font-size: 12px;
      cursor: pointer;
      color: #475569;
      border-right: 1px solid #cbd5e1;
    }
    .btn-prog:last-child { border-right: none; }
    .btn-prog.active {
      background: #2563eb;
      color: #ffffff;
      font-weight: 600;
    }
    .btn-prog-complete.active {
      background: #10b981;
      color: #ffffff;
    }
    .footer-notice {
      font-size: 11.5px;
      color: #94a3b8;
    }
    .matrix-legend {
      display: flex;
      gap: 20px;
      margin-bottom: 16px;
      font-size: 12.5px;
      color: #475569;
      flex-wrap: wrap;
    }
    .badge-v { color: #16a34a; font-weight: 800; }
    .badge-i { color: #d97706; font-weight: 800; }
    .badge-c { color: #2563eb; font-weight: 800; }
    .badge-g { color: #94a3b8; font-weight: 800; }
    .badge-none { color: #cbd5e1; }
    .table-wrap {
      overflow-x: auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .matrix-table, .benchmark-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .matrix-table th, .benchmark-table th {
      background: #f8fafc;
      padding: 10px 14px;
      text-align: left;
      font-size: 12px;
      color: #64748b;
      font-weight: 600;
      border-bottom: 1px solid #e2e8f0;
      white-space: nowrap;
    }
    .matrix-table td, .benchmark-table td {
      padding: 10px 14px;
      border-bottom: 1px solid #f1f5f9;
    }
    .td-opp { min-width: 220px; }
    .opp-main { font-weight: 600; color: #0f172a; }
    .opp-sub { font-size: 11.5px; color: #64748b; }
    .cov-prog-wrap { min-width: 100px; }
    .cov-pct { font-size: 12px; font-weight: 600; color: #0f172a; display: block; margin-bottom: 2px; }
    .cov-mini-bar {
      height: 4px;
      background: #e2e8f0;
      border-radius: 2px;
      overflow: hidden;
    }
    .cov-mini-fill {
      height: 100%;
      background: #10b981;
    }
    .td-status {
      text-align: center;
      min-width: 60px;
    }
    .benchmark-header-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 18px;
    }
    .bench-h3 {
      font-size: 16px;
      font-weight: 700;
      color: #0f172a;
      margin: 0 0 6px 0;
    }
    .bench-p {
      font-size: 13.5px;
      color: #475569;
      margin: 0;
      line-height: 1.5;
    }
    .row-highlight {
      background: #f0fdf4 !important;
    }
    .conclusion-box {
      margin-top: 18px;
      padding: 16px 20px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .conclusion-title {
      font-size: 13px;
      font-weight: 700;
      color: #0f172a;
      display: block;
      margin-bottom: 4px;
    }
    .conclusion-text {
      font-size: 13px;
      color: #475569;
      margin: 0 0 10px 0;
      line-height: 1.5;
    }
    .lift-badges {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .lift-badge {
      font-size: 12px;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      padding: 4px 10px;
      border-radius: 4px;
      color: #334155;
    }
    .empty-state-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 48px 24px;
      text-align: center;
      max-width: 540px;
      margin: 40px auto;
    }
    .empty-icon { font-size: 36px; margin-bottom: 12px; }
    .empty-title { font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 8px 0; }
    .empty-desc { font-size: 13.5px; color: #64748b; margin: 0 0 20px 0; line-height: 1.5; }
    .empty-actions { display: flex; justify-content: center; gap: 12px; }
    .error-banner {
      background: #fef2f2;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 12px 16px;
      color: #991b1b;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .loading-state {
      padding: 60px 20px;
      text-align: center;
      color: #64748b;
    }
    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #e2e8f0;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 12px auto;
    }
    .spinner-sm {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.4);
      border-top-color: #ffffff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class SkillGapComponent implements OnInit {
  private cosgoService = inject(CosgoService);
  private cdr = inject(ChangeDetectorRef);

  latestRun: CosgoRun | null = null;
  matrixData: CosgoCoverageMatrixResponse | null = null;
  benchmarkData: CosgoBenchmarkResponse | null = null;

  loading = true;
  optimizing = false;
  loadingMatrix = false;
  loadingBenchmark = false;
  loadError: string | null = null;

  activeTab: 'roadmap' | 'matrix' | 'benchmark' = 'roadmap';
  customTotalBudget = 40;
  customWeeklyBudget = 10;

  expandedJobCardIds: Set<string> = new Set();

  get totalEstimatedHours(): number {
    if (!this.latestRun?.actions) return 0;
    return this.latestRun.actions.reduce((acc, a) => acc + (a.estimated_hours || 0), 0);
  }

  ngOnInit(): void {
    this.loadPlan();
  }

  loadPlan(): void {
    this.loading = true;
    this.loadError = null;
    this.cdr.markForCheck();

    this.cosgoService.getLatestRun().subscribe({
      next: (run) => {
        this.latestRun = run;
        this.customTotalBudget = run.budget_hours || 40;
        this.customWeeklyBudget = run.weekly_budget_hours || 10;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.loadError = err?.error?.detail || 'Failed to load skill gap plan. Please ensure target opportunities exist.';
        this.cdr.markForCheck();
      }
    });
  }

  triggerOptimization(): void {
    this.optimizing = true;
    this.cdr.markForCheck();

    this.cosgoService.runOptimization({
      budget_hours: this.customTotalBudget,
      weekly_budget_hours: this.customWeeklyBudget
    }).subscribe({
      next: (run) => {
        this.latestRun = run;
        this.optimizing = false;
        if (this.activeTab === 'matrix') {
          this.loadMatrix();
        }
        if (this.activeTab === 'benchmark') {
          this.loadBenchmark();
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.optimizing = false;
        alert(err?.error?.detail || 'Optimization failed. Please try again.');
        this.cdr.markForCheck();
      }
    });
  }

  updateBudget(): void {
    this.optimizing = true;
    this.cdr.markForCheck();

    this.cosgoService.updateBudget({
      budget_hours: this.customTotalBudget,
      weekly_budget_hours: this.customWeeklyBudget
    }).subscribe({
      next: (run) => {
        this.latestRun = run;
        this.optimizing = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.optimizing = false;
        alert(err?.error?.detail || 'Failed to update budget.');
        this.cdr.markForCheck();
      }
    });
  }

  changeActionProgress(action: CosgoAction, newState: CosgoProgressState): void {
    const oldState = action.progress_state;
    action.progress_state = newState;
    this.cdr.markForCheck();

    this.cosgoService.updateActionProgress(action.id, { progress_state: newState }).subscribe({
      next: (updated) => {
        action.progress_state = updated.progress_state;
        action.completed_at = updated.completed_at;
        this.cdr.markForCheck();
      },
      error: (err) => {
        action.progress_state = oldState;
        alert(err?.error?.detail || 'Failed to update action progress.');
        this.cdr.markForCheck();
      }
    });
  }

  loadMatrix(): void {
    if (!this.latestRun) return;
    this.loadingMatrix = true;
    this.cdr.markForCheck();

    this.cosgoService.getCoverageMatrix(this.latestRun.id).subscribe({
      next: (res) => {
        this.matrixData = res;
        this.loadingMatrix = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingMatrix = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadBenchmark(): void {
    this.loadingBenchmark = true;
    this.cdr.markForCheck();

    this.cosgoService.getBenchmark(this.customTotalBudget, this.customWeeklyBudget).subscribe({
      next: (res) => {
        this.benchmarkData = res;
        this.loadingBenchmark = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingBenchmark = false;
        this.cdr.markForCheck();
      }
    });
  }

  toggleJobsExpanded(actionId: string): void {
    if (this.expandedJobCardIds.has(actionId)) {
      this.expandedJobCardIds.delete(actionId);
    } else {
      this.expandedJobCardIds.add(actionId);
    }
    this.cdr.markForCheck();
  }

  isJobsExpanded(actionId: string): boolean {
    return this.expandedJobCardIds.has(actionId);
  }

  // Matrix cell helpers
  isSkillVerified(row: any, skill: string): boolean {
    return (row.verified_skills || []).some((s: string) => s.toLowerCase() === skill.toLowerCase());
  }

  isSkillInferred(row: any, skill: string): boolean {
    return (row.inferred_skills || []).some((s: string) => s.toLowerCase() === skill.toLowerCase());
  }

  isSkillCovered(row: any, skill: string): boolean {
    return (row.actions_covering || []).some((s: string) => s.toLowerCase() === skill.toLowerCase());
  }

  isSkillGap(row: any, skill: string): boolean {
    return (row.remaining_gaps || []).some((s: string) => s.toLowerCase() === skill.toLowerCase());
  }

  isSkillInJob(row: any, skill: string): boolean {
    return (row.requirements || []).some((s: string) => s.toLowerCase() === skill.toLowerCase());
  }
}

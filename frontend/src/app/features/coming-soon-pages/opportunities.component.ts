import { Component, OnInit, OnDestroy, HostListener, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Subscription, interval, of } from 'rxjs';
import { switchMap, takeWhile, catchError } from 'rxjs/operators';
import { OpportunityService } from '../../core/services/opportunity.service';
import { ProfileService } from '../../core/services/profile.service';
import {
  Opportunity,
  OpportunityType,
  OpportunityStatus,
  RecommendedAction,
  CompanyClassification
} from '../../core/models/opportunity.model';
import { DiscoveryRun } from '../../core/models/discovery.model';
import { ProviderHealth } from '../../core/models/provider.model';
import { Profile } from '../../core/models/profile.model';

export interface SourceCategory {
  label: string;
  status: 'active' | 'standby';
  statusText: string;
  description: string;
}

@Component({
  selector: 'app-opportunities-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="opportunities-page">
      <!-- Header -->
      <header class="page-header">
        <div>
          <h1 class="page-title">Opportunity Intelligence Engine</h1>
          <p class="page-subtitle">
            Multi-source discovery of advertised jobs and unadvertised company targets with evidence grounding
          </p>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-primary"
            (click)="openDiscoveryModal()"
            [disabled]="activeRun?.status === 'running' || startingDiscovery"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <span>Find New Opportunities</span>
          </button>
        </div>
      </header>

      <!-- Operating Mode Indicator & Switcher (Visible only in Exploration Mode) -->
      <div *ngIf="currentMode === 'EXPLORATION'" class="iq-card mode-status-banner mode-explore">
        <div class="mode-info">
          <span class="mode-badge">EXPLORATION MODE</span>
          <div class="mode-text-box">
            <h4 class="mode-title">
              Exploration Results: {{ customRole || 'Custom Search' }}
              <span *ngIf="selectedLocations.length > 0"> in {{ selectedLocations.join(', ') }}</span>
            </h4>
            <p class="mode-sub">
              Showing custom search results. Your permanent career profile and preferences remain unchanged.
            </p>
          </div>
        </div>
        <div class="mode-action">
          <button class="btn btn-secondary btn-sm" (click)="switchToProfileMode()">
            ← Back to Profile Recommendations
          </button>
        </div>
      </div>

      <!-- Incomplete Profile Warning (if auto-discovery needed but profile lacking) -->
      <div *ngIf="profileMissingWarning" class="iq-card profile-notice-card">
        <div class="notice-content">
          <div class="notice-icon">📋</div>
          <div>
            <h4 class="notice-title">Profile Information Needed</h4>
            <p class="notice-desc">{{ profileMissingWarning }}</p>
          </div>
        </div>
        <div class="notice-actions">
          <a routerLink="/profile" class="btn btn-secondary btn-sm">Update Profile</a>
          <a routerLink="/resumes" class="btn btn-primary btn-sm">Upload Resume</a>
        </div>
      </div>

      <!-- Discovery Error Banner -->
      <div *ngIf="discoveryError" class="discovery-error-banner">
        <span>⚠️ {{ discoveryError }}</span>
        <button class="btn btn-secondary btn-sm" (click)="triggerDiscovery()">Retry</button>
      </div>

      <!-- Live Discovery Run Progress (Active in-flight runs only) -->
      <div *ngIf="activeRun && activeRun.status === 'running'" class="iq-card run-progress-card running">
        <div class="run-header">
          <div class="run-title-box">
            <span class="run-badge" [ngClass]="activeRun.status">{{ activeRun.status | uppercase }}</span>
            <span class="run-name">Discovery Run #{{ activeRun.id.substring(0, 8) }}</span>
          </div>
          <span class="run-time">{{ activeRun.execution_time_seconds }}s elapsed</span>
        </div>

        <div class="run-metrics-grid">
          <div class="run-metric">
            <span class="metric-val">{{ activeRun.providers_queried.length }}</span>
            <span class="metric-lbl">Source Feeds Queried</span>
          </div>
          <div class="run-metric">
            <span class="metric-val">{{ activeRun.results_discovered_count }}</span>
            <span class="metric-lbl">Raw Discovered</span>
          </div>
          <div class="run-metric">
            <span class="metric-val">{{ activeRun.results_deduplicated_count }}</span>
            <span class="metric-lbl">Deduplicated</span>
          </div>
          <div class="run-metric">
            <span class="metric-val">{{ activeRun.opportunities_created_count }}</span>
            <span class="metric-lbl">Opportunities Formed</span>
          </div>
        </div>

        <div *ngIf="activeRun.error_summary" class="run-error-note">
          ℹ️ {{ getCandidateFriendlyRunNote(activeRun.error_summary) }}
        </div>
      </div>

      <!-- Filter Controls Bar -->
      <div class="filters-bar">
        <!-- Type Tabs -->
        <div class="type-tabs">
          <button
            class="tab-btn"
            [class.active]="selectedType === null && selectedStatus !== 'SAVED'"
            (click)="setTypeFilter(null)"
          >
            All Opportunities
          </button>
          <button
            class="tab-btn"
            [class.active]="selectedType === 'ADVERTISED' && selectedStatus !== 'SAVED'"
            (click)="setTypeFilter('ADVERTISED')"
          >
            Advertised Jobs
          </button>
          <button
            class="tab-btn"
            [class.active]="selectedType === 'EMERGING' && selectedStatus !== 'SAVED'"
            (click)="setTypeFilter('EMERGING')"
          >
            Emerging Companies
          </button>
          <button
            class="tab-btn"
            [class.active]="selectedType === 'STRATEGIC' && selectedStatus !== 'SAVED'"
            (click)="setTypeFilter('STRATEGIC')"
          >
            Strategic Fit
          </button>
          <button
            class="tab-btn"
            [class.active]="selectedStatus === 'SAVED'"
            (click)="setSavedFilter()"
          >
            Saved ({{ savedCount }})
          </button>
        </div>

        <!-- Filter Toggle & Search -->
        <div class="secondary-controls">
          <button class="btn btn-secondary btn-sm" (click)="toggleFilterPanel()">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            Filters
            <span *ngIf="activeFiltersCount > 0" class="filter-count-badge">{{ activeFiltersCount }}</span>
          </button>

          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Search role, company, or keyword..."
            class="search-input"
          />
        </div>
      </div>

      <!-- Comprehensive Collapsible Filter Panel (Client-side) -->
      <div *ngIf="showFilterPanel" class="iq-card filter-panel">
        <div class="filter-panel-header">
          <div class="filter-title-wrap">
            <span class="filter-panel-title">Filter Discovered Opportunities (Client-side)</span>
            <p class="filter-panel-help">
              Narrows already loaded opportunities without searching external job boards.
              To search the web for new roles or additional locations, click <strong>Find New Opportunities</strong> above.
            </p>
          </div>
          <button class="clear-all-link" (click)="clearAllFilters()" *ngIf="activeFiltersCount > 0">
            Clear All ({{ activeFiltersCount }})
          </button>
        </div>

        <div class="filter-grid">
          <!-- Work Arrangement -->
          <div class="filter-group">
            <label class="filter-label">Work Arrangement</label>
            <select [(ngModel)]="filterWorkArrangement" class="filter-select">
              <option value="">All Arrangements</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">On-site</option>
            </select>
          </div>

          <!-- Employment Type -->
          <div class="filter-group">
            <label class="filter-label">Employment Type</label>
            <select [(ngModel)]="filterEmploymentType" class="filter-select">
              <option value="">All Types</option>
              <option value="full-time">Full-time</option>
              <option value="internship">Internship</option>
              <option value="contract">Contract</option>
              <option value="part-time">Part-time</option>
            </select>
          </div>

          <!-- Company Classification -->
          <div class="filter-group">
            <label class="filter-label">Company Classification</label>
            <select [(ngModel)]="filterClassification" class="filter-select">
              <option value="">All Classifications</option>
              <option value="startup">Startup</option>
              <option value="smb">Small & Medium Business</option>
              <option value="mid_sized">Mid-sized Company</option>
              <option value="enterprise">MNC / Enterprise</option>
              <option value="unknown">Unspecified</option>
            </select>
          </div>

          <!-- Minimum Match Score -->
          <div class="filter-group">
            <label class="filter-label">Minimum Match Score</label>
            <select [(ngModel)]="filterMinScore" class="filter-select">
              <option [ngValue]="null">Any Score</option>
              <option [ngValue]="0.70">70%+ (High Fit)</option>
              <option [ngValue]="0.50">50%+ (Moderate Fit)</option>
              <option [ngValue]="0.40">40%+ (Exploratory)</option>
            </select>
          </div>

          <!-- Recommendation Action -->
          <div class="filter-group">
            <label class="filter-label">Recommendation</label>
            <select [(ngModel)]="selectedAction" class="filter-select">
              <option [ngValue]="null">All Actions</option>
              <option value="CONTACT_NOW">Contact Now</option>
              <option value="IMPROVE_FIRST">Improve First</option>
              <option value="SKIP">Skip</option>
            </select>
          </div>

          <!-- Location Filter with Autocomplete Combobox -->
          <div class="filter-group combobox-group" (click)="$event.stopPropagation()">
            <label class="filter-label">City / Region (In-Memory Filter)</label>
            <div class="combobox-wrapper">
              <input
                type="text"
                [(ngModel)]="filterLocation"
                (focus)="showLocationSuggestions = true"
                (input)="showLocationSuggestions = true"
                (keydown)="onLocationKeydown($event)"
                placeholder="e.g. Mohali, Bengaluru..."
                class="filter-input"
                role="combobox"
                [attr.aria-expanded]="showLocationSuggestions"
                aria-autocomplete="list"
              />
              <button
                *ngIf="filterLocation"
                type="button"
                class="combobox-clear"
                (click)="filterLocation = ''; showLocationSuggestions = false"
                title="Clear location filter"
              >✕</button>
            </div>
            <small class="filter-hint">Filters loaded opportunities by canonical job location</small>

            <!-- Location Suggestions Dropdown -->
            <ul
              *ngIf="showLocationSuggestions && filteredLocationSuggestions.length > 0"
              class="autocomplete-dropdown"
              role="listbox"
            >
              <li
                *ngFor="let loc of filteredLocationSuggestions; let i = index"
                [class.selected]="i === selectedLocationIndex"
                (mousedown)="selectLocationSuggestion(loc)"
                role="option"
                class="autocomplete-item"
              >
                <span class="suggestion-text">{{ loc }}</span>
              </li>
            </ul>
          </div>

          <!-- Skill Filter with Autocomplete Combobox -->
          <div class="filter-group combobox-group" (click)="$event.stopPropagation()">
            <label class="filter-label">Matched Skill</label>
            <div class="combobox-wrapper">
              <input
                type="text"
                [(ngModel)]="filterSkill"
                (focus)="showSkillSuggestions = true"
                (input)="showSkillSuggestions = true"
                (keydown)="onSkillKeydown($event)"
                placeholder="e.g. Python, PyTorch..."
                class="filter-input"
                role="combobox"
                [attr.aria-expanded]="showSkillSuggestions"
                aria-autocomplete="list"
              />
              <button
                *ngIf="filterSkill"
                type="button"
                class="combobox-clear"
                (click)="filterSkill = ''; showSkillSuggestions = false"
                title="Clear skill filter"
              >✕</button>
            </div>

            <!-- Skill Suggestions Dropdown -->
            <ul
              *ngIf="showSkillSuggestions && filteredSkillSuggestions.length > 0"
              class="autocomplete-dropdown"
              role="listbox"
            >
              <li
                *ngFor="let sk of filteredSkillSuggestions; let i = index"
                [class.selected]="i === selectedSkillIndex"
                (mousedown)="selectSkillSuggestion(sk)"
                role="option"
                class="autocomplete-item"
              >
                <span class="suggestion-text">{{ sk }}</span>
              </li>
            </ul>
          </div>

          <!-- Sort Order -->
          <div class="filter-group">
            <label class="filter-label">Sort Order</label>
            <select [(ngModel)]="sortOrder" class="filter-select">
              <option value="match_score">Highest Match Score</option>
              <option value="recent">Most Recently Discovered</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Active Filters Summary Bar -->
      <div class="active-filters-row">
        <div class="results-counter">
          Showing <strong>{{ filteredOpportunities.length }}</strong> of <strong>{{ opportunities.length }}</strong> opportunities
        </div>

        <div *ngIf="activeFiltersCount > 0" class="active-chips">
          <span *ngIf="filterWorkArrangement" class="filter-chip">
            {{ filterWorkArrangement | titlecase }}
            <button (click)="filterWorkArrangement = ''">✕</button>
          </span>
          <span *ngIf="filterEmploymentType" class="filter-chip">
            {{ filterEmploymentType | titlecase }}
            <button (click)="filterEmploymentType = ''">✕</button>
          </span>
          <span *ngIf="filterClassification" class="filter-chip">
            {{ filterClassification | titlecase }}
            <button (click)="filterClassification = ''">✕</button>
          </span>
          <span *ngIf="filterMinScore !== null" class="filter-chip">
            ≥{{ (filterMinScore * 100).toFixed(0) }}% Match
            <button (click)="filterMinScore = null">✕</button>
          </span>
          <span *ngIf="selectedAction" class="filter-chip">
            {{ selectedAction }}
            <button (click)="selectedAction = null">✕</button>
          </span>
          <span *ngIf="filterLocation" class="filter-chip">
            Location: {{ filterLocation }}
            <button (click)="filterLocation = ''">✕</button>
          </span>
          <span *ngIf="filterSkill" class="filter-chip">
            Skill: {{ filterSkill }}
            <button (click)="filterSkill = ''">✕</button>
          </span>
          <span *ngIf="searchQuery" class="filter-chip">
            "{{ searchQuery }}"
            <button (click)="searchQuery = ''">✕</button>
          </span>

          <button class="btn-clear-inline" (click)="clearAllFilters()">Clear All</button>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="loading" class="loading-box">
        <div class="spinner-inline" style="margin: 0 auto 10px auto;"></div>
        <p>Loading opportunities & research...</p>
      </div>

      <!-- Error State with Retry -->
      <div *ngIf="!loading && loadError" class="iq-card error-card" style="margin-bottom: 24px;">
        <div class="error-msg-box">
          <span class="error-icon">⚠️</span>
          <span class="error-text">{{ loadError }}</span>
        </div>
        <button class="btn btn-secondary btn-sm" (click)="loadOpportunities()">
          Retry Loading Opportunities
        </button>
      </div>

      <!-- Empty State -->
      <div *ngIf="!loading && !loadError && filteredOpportunities.length === 0" class="empty-box">
        <h3>{{ opportunities.length === 0 ? 'No opportunities discovered yet' : 'No opportunities match your active filters' }}</h3>
        <p *ngIf="opportunities.length === 0">
          OutReachIQ discovers both verified advertised job vacancies and unadvertised company opportunities with public expansion signals.
          Initiate discovery using your profile preferences.
        </p>
        <p *ngIf="opportunities.length > 0">
          Try broadening your filter criteria or clearing active filters to view all {{ opportunities.length }} discovered opportunities.
        </p>

        <div class="empty-actions" style="margin-top: 16px;">
          <button
            *ngIf="opportunities.length === 0"
            class="btn btn-primary"
            (click)="openDiscoveryModal()"
            [disabled]="activeRun?.status === 'running' || startingDiscovery"
          >
            Find New Opportunities
          </button>
          <button
            *ngIf="opportunities.length > 0"
            class="btn btn-secondary"
            (click)="clearAllFilters()"
          >
            Clear All Filters
          </button>
        </div>
      </div>

      <!-- Opportunities Grid -->
      <div *ngIf="!loading && !loadError && filteredOpportunities.length > 0" class="opportunities-grid">
        <div
          *ngFor="let opp of filteredOpportunities"
          class="iq-card opp-card"
          [class.opp-saved]="opp.status === 'SAVED'"
        >
          <!-- Card Top Bar -->
          <div class="card-top">
            <div class="badges-row">
              <span
                class="badge"
                [ngClass]="{
                  'badge-advertised': opp.opportunity_type === 'ADVERTISED',
                  'badge-emerging': opp.opportunity_type === 'EMERGING',
                  'badge-strategic': opp.opportunity_type === 'STRATEGIC'
                }"
              >
                {{ opp.opportunity_type === 'ADVERTISED' ? 'ADVERTISED JOB' : (opp.opportunity_type === 'EMERGING' ? 'EMERGING COMPANY' : 'STRATEGIC FIT') }}
              </span>

              <span
                class="badge"
                [ngClass]="{
                  'action-contact': opp.recommended_action === 'CONTACT_NOW',
                  'action-improve': opp.recommended_action === 'IMPROVE_FIRST',
                  'action-skip': opp.recommended_action === 'SKIP'
                }"
              >
                {{ opp.recommended_action === 'CONTACT_NOW' ? 'CONTACT NOW' : (opp.recommended_action === 'IMPROVE_FIRST' ? 'IMPROVE FIRST' : 'SKIP') }}
              </span>

              <span
                *ngIf="opp.job?.verification_status"
                class="badge verification-badge"
                [ngClass]="{
                  'verification-verified': opp.job?.verification_status === 'VERIFIED_OPEN',
                  'verification-unverified': opp.job?.verification_status === 'LISTING_FOUND_STATUS_UNVERIFIED',
                  'verification-closed': opp.job?.verification_status === 'EXPIRED_OR_CLOSED'
                }"
              >
                {{ opp.job?.verification_status === 'VERIFIED_OPEN' ? '✓ Verified Open' : (opp.job?.verification_status === 'EXPIRED_OR_CLOSED' ? 'Closed / Expired' : 'Listing Found') }}
              </span>

              <span class="match-score-pill">
                Fit: {{ (opp.match_score * 100).toFixed(0) }}%
              </span>
            </div>

            <button
              class="icon-save-btn"
              [class.saved]="opp.status === 'SAVED'"
              (click)="toggleSave(opp)"
              [title]="opp.status === 'SAVED' ? 'Remove from saved' : 'Save opportunity'"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
              </svg>
            </button>
          </div>

          <!-- Role & Organization -->
          <div class="opp-role-block">
            <h3 class="opp-title">
              {{ opp.job ? getCleanDisplayTitle(opp.job.title) : (opp.company ? opp.company.name : 'Target Opportunity') }}
            </h3>
            <div class="opp-meta-line">
              <span class="meta-company">{{ opp.company?.name || opp.job?.company_name || 'Direct Employer' }}</span>
              <span class="meta-sep">•</span>
              <span class="meta-location">{{ getCanonicalLocation(opp) }}</span>
              <span *ngIf="opp.job?.work_arrangement" class="meta-arrangement">({{ opp.job?.work_arrangement | titlecase }})</span>
            </div>
          </div>

          <!-- Classification & Provenance Badges -->
          <div class="classification-row">
            <span class="class-tag" [ngClass]="getCompanyClassification(opp)">
              {{ formatClassification(getCompanyClassification(opp)) }}
            </span>
            <span *ngIf="opp.company?.size_range" class="work-tag">
              👥 {{ opp.company?.size_range }}
            </span>
            <span *ngIf="opp.job?.employment_type" class="work-tag">
              {{ opp.job?.employment_type | titlecase }}
            </span>
            <span *ngIf="opp.job?.salary_range" class="salary-tag">
              💰 {{ opp.job?.salary_range }}
            </span>
            <span *ngIf="opp.job?.experience_required" class="salary-tag">
              💼 {{ opp.job?.experience_required }}
            </span>
            <span class="provenance-tag">
              {{ getSourceCategoryLabel(opp.job?.source_name || opp.evidence_items[0]?.source_url) }}
            </span>
          </div>

          <!-- Explanation Snippet -->
          <p class="opp-explanation">
            {{ opp.explanation }}
          </p>

          <!-- Matched Skills Chips -->
          <div class="skills-block" *ngIf="opp.matched_skills.length > 0">
            <span class="skills-label">Matched Profile Evidence:</span>
            <div class="skills-chips">
              <span *ngFor="let sk of opp.matched_skills.slice(0, 4)" class="skill-chip matched">
                ✓ {{ sk }}
              </span>
              <span *ngIf="opp.matched_skills.length > 4" class="skill-chip more">
                +{{ opp.matched_skills.length - 4 }} more
              </span>
            </div>
          </div>

          <!-- Missing Skills / Gaps -->
          <div class="skills-block gaps" *ngIf="opp.missing_skills.length > 0">
            <span class="skills-label">Identified Gaps:</span>
            <div class="skills-chips">
              <span *ngFor="let sk of opp.missing_skills.slice(0, 3)" class="skill-chip missing">
                {{ sk }}
              </span>
            </div>
          </div>

          <!-- Card Footer Actions -->
          <div class="card-footer-row">
            <div class="confidence-indicator" title="Evidence grounding score">
              <span class="conf-dot"></span>
              <span class="conf-label">Evidence Conf: {{ (opp.evidence_confidence * 100).toFixed(0) }}%</span>
            </div>

            <div class="footer-btn-group">
              <a
                *ngIf="opp.job?.application_url || opp.job?.primary_url"
                [href]="opp.job?.application_url || opp.job?.primary_url"
                target="_blank"
                rel="noopener"
                class="btn btn-secondary btn-sm"
              >
                Apply ↗
              </a>
              <a
                [routerLink]="['/outreach']"
                [queryParams]="{ opportunityId: opp.id }"
                class="btn btn-primary btn-sm btn-outreach-quick"
                title="Draft personalized AI outreach for this opportunity"
              >
                Draft Outreach
              </a>
              <button class="btn btn-secondary btn-sm" (click)="openDetailModal(opp)">
                Full Intel
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Modal -->
      <div *ngIf="selectedOppForDetail" class="modal-backdrop" (click)="closeDetailModal()">
        <div class="modal-content" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <div>
              <h3 class="modal-title">
                {{ selectedOppForDetail.job ? getCleanDisplayTitle(selectedOppForDetail.job.title) : selectedOppForDetail.company?.name }}
              </h3>
              <p class="modal-subtitle">
                {{ selectedOppForDetail.company?.name }} • {{ getCanonicalLocation(selectedOppForDetail) }}
              </p>
            </div>
            <button class="modal-close-btn" (click)="closeDetailModal()">✕</button>
          </div>

          <div class="modal-body">
            <!-- Calibrated Fit Explanation -->
            <div class="iq-card section-box">
              <h4>Explainable Match Assessment</h4>
              <p class="section-p">{{ selectedOppForDetail.explanation }}</p>
              <div *ngIf="selectedOppForDetail.critical_failures.length > 0" class="critical-fail-box">
                <strong>Critical Friction Points:</strong>
                <ul>
                  <li *ngFor="let cf of selectedOppForDetail.critical_failures">{{ cf }}</li>
                </ul>
              </div>
            </div>

            <!-- Job Description / Details -->
            <div *ngIf="selectedOppForDetail.job" class="iq-card section-box">
              <h4>Role Details & Requirements</h4>
              <p class="section-p" *ngIf="selectedOppForDetail.job.description">
                {{ selectedOppForDetail.job.description }}
              </p>
              <div class="meta-attributes" style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px;">
                <span><strong>Arrangement:</strong> {{ selectedOppForDetail.job.work_arrangement | titlecase }}</span>
                <span><strong>Type:</strong> {{ selectedOppForDetail.job.employment_type | titlecase }}</span>
                <span *ngIf="selectedOppForDetail.job.salary_range"><strong>Salary:</strong> {{ selectedOppForDetail.job.salary_range }}</span>
                <span *ngIf="selectedOppForDetail.job.experience_required"><strong>Comp/Exp:</strong> {{ selectedOppForDetail.job.experience_required }}</span>
                <span *ngIf="selectedOppForDetail.job.verification_status">
                  <strong>Verification:</strong>
                  {{ selectedOppForDetail.job.verification_status === 'VERIFIED_OPEN' ? '✓ Verified Open Listing' : selectedOppForDetail.job.verification_status }}
                </span>
              </div>
              <div *ngIf="selectedOppForDetail.job.application_url" style="margin-top: 12px;">
                <a [href]="selectedOppForDetail.job.application_url" target="_blank" rel="noopener" class="btn btn-primary btn-sm">
                  Go to Official Application Route ↗
                </a>
              </div>
            </div>

            <!-- Company Intelligence Signals -->
            <div *ngIf="selectedOppForDetail.company" class="iq-card section-box">
              <h4>Organization Intelligence & Public Signals</h4>
              <p class="section-p">{{ selectedOppForDetail.company.description }}</p>
              <div class="meta-attributes" style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px;">
                <span><strong>Classification:</strong> {{ formatClassification(getCompanyClassification(selectedOppForDetail)) }}</span>
                <span *ngIf="selectedOppForDetail.company.size_range"><strong>Estimated Scale:</strong> {{ selectedOppForDetail.company.size_range }}</span>
                <span *ngIf="selectedOppForDetail.company.headquarters"><strong>Headquarters:</strong> {{ selectedOppForDetail.company.headquarters }}</span>
              </div>
              <div class="why-rows">
                <div class="why-item contact-why" *ngIf="selectedOppForDetail.company.why_contact">
                  <strong>Recommended Approach:</strong> {{ selectedOppForDetail.company.why_contact }}
                </div>
                <div class="why-item wait-why" *ngIf="selectedOppForDetail.company.why_wait">
                  <strong>Preparation Advisory:</strong> {{ selectedOppForDetail.company.why_wait }}
                </div>
              </div>
            </div>

            <!-- Grounded Evidence Citations -->
            <div class="iq-card section-box">
              <h4>Grounded Evidence Citations ({{ selectedOppForDetail.evidence_items.length }})</h4>
              <div *ngIf="selectedOppForDetail.evidence_items.length === 0" class="text-muted">
                No citations recorded.
              </div>
              <div *ngFor="let ev of selectedOppForDetail.evidence_items" class="evidence-card">
                <div class="evidence-top">
                  <span class="claim-type-badge">{{ ev.claim_type }}</span>
                  <span class="conf-badge">Confidence: {{ (ev.confidence * 100).toFixed(0) }}%</span>
                </div>
                <p class="evidence-claim">{{ ev.claim_text }}</p>
                <blockquote *ngIf="ev.supporting_excerpt" class="evidence-quote">
                  "{{ ev.supporting_excerpt }}"
                </blockquote>
                <a [href]="ev.source_url" target="_blank" rel="noopener" class="evidence-url">
                  {{ ev.source_url }} ↗
                </a>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="closeDetailModal()">Close</button>
            <a
              [routerLink]="['/outreach']"
              [queryParams]="{ opportunityId: selectedOppForDetail.id }"
              (click)="closeDetailModal()"
              class="btn btn-primary"
            >
              Draft AI Outreach for this Opportunity →
            </a>
            <button
              class="btn btn-secondary"
              (click)="toggleSave(selectedOppForDetail)"
            >
              {{ selectedOppForDetail.status === 'SAVED' ? 'Remove from Saved' : 'Save Opportunity' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Discovery Run Parameters Modal (Mode B: Exploration) -->
      <div *ngIf="showDiscoveryModal" class="modal-backdrop" (click)="closeDiscoveryModal()">
        <div class="modal-content modal-md" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <div>
              <h3 class="modal-title">Discover Opportunities</h3>
              <p class="modal-subtitle">Explore vacancies and target companies across selected locations without altering your permanent career profile.</p>
            </div>
            <button class="modal-close-btn" (click)="closeDiscoveryModal()">✕</button>
          </div>

          <div class="modal-body">
            <!-- Target Role -->
            <div class="form-group">
              <label class="form-label">Target Role or Job Title</label>
              <input
                type="text"
                [(ngModel)]="customRole"
                class="form-control"
                placeholder="e.g. Backend Developer, AI/ML Engineer, Data Scientist"
              />
            </div>

            <!-- Multi-Location Selector -->
            <div class="form-group">
              <div class="location-header-row">
                <label class="form-label">Target Locations (Multi-Select)</label>
                <button
                  type="button"
                  class="clear-all-link-sm"
                  *ngIf="selectedLocations.length > 0"
                  (click)="clearAllLocations()"
                >
                  Clear All
                </button>
              </div>

              <!-- Selected Location Chips -->
              <div class="selected-locations-chips" *ngIf="selectedLocations.length > 0">
                <span *ngFor="let loc of selectedLocations; let i = index" class="loc-chip">
                  {{ loc }}
                  <button type="button" class="loc-remove-btn" (click)="removeLocation(i)" title="Remove location">✕</button>
                </span>
              </div>
              <div *ngIf="selectedLocations.length === 0" class="no-locs-hint">
                No location selected (will default to national search).
              </div>

              <!-- Searchable Add Predefined City & Custom City Input -->
              <div class="loc-selector-row">
                <div class="loc-dropdown-container">
                  <input
                    type="text"
                    [(ngModel)]="locationSearchInput"
                    (focus)="showLocationDropdown = true"
                    placeholder="Search city to add (e.g. Mohali, Noida)..."
                    class="form-control loc-search-input"
                  />
                  <!-- Dropdown list -->
                  <div class="loc-dropdown" *ngIf="showLocationDropdown && filteredCities.length > 0">
                    <button
                      type="button"
                      *ngFor="let city of filteredCities"
                      class="loc-option-btn"
                      (click)="addLocation(city)"
                    >
                      + {{ city }}
                    </button>
                  </div>
                </div>

                <!-- Custom location input -->
                <div class="custom-loc-box">
                  <input
                    type="text"
                    [(ngModel)]="customLocationInput"
                    (keydown.enter)="$event.preventDefault(); addCustomLocation()"
                    placeholder="Other / Enter custom city..."
                    class="form-control custom-loc-input"
                  />
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    (click)="addCustomLocation()"
                    [disabled]="!customLocationInput.trim()"
                  >
                    Add
                  </button>
                </div>
              </div>
              <small class="form-help-text">
                Select one or more cities. "Noida" and "Greater Noida" are kept distinct. Custom cities can be entered using the "Other" field above.
              </small>
            </div>

            <!-- Work Arrangement & Employment Type (2 Columns) -->
            <div class="form-row-2col">
              <div class="form-group">
                <label class="form-label">Work Arrangement</label>
                <select [(ngModel)]="customWorkArrangement" class="form-control">
                  <option value="Any">Any / Flexible</option>
                  <option value="remote">Remote Only</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">On-site</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Employment Type</label>
                <select [(ngModel)]="customEmploymentType" class="form-control">
                  <option value="Any">Any / All Types</option>
                  <option value="internship">Internship</option>
                  <option value="full-time">Full-time</option>
                  <option value="contract">Contract</option>
                  <option value="part-time">Part-time</option>
                </select>
              </div>
            </div>

            <!-- Experience Level & Limit (2 Columns) -->
            <div class="form-row-2col">
              <div class="form-group">
                <label class="form-label">Experience Level</label>
                <select [(ngModel)]="customExperienceLevel" class="form-control">
                  <option value="Any">Any Experience</option>
                  <option value="entry">Entry / Fresher / Student</option>
                  <option value="mid">Mid-level (1-4 yrs)</option>
                  <option value="senior">Senior (5+ yrs)</option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Result Limit</label>
                <input type="number" [(ngModel)]="customLimit" class="form-control" min="5" max="50" />
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="closeDiscoveryModal()">Cancel</button>
            <button
              class="btn btn-primary"
              (click)="submitDiscoveryRun()"
              [disabled]="activeRun?.status === 'running' || startingDiscovery"
            >
              {{ (activeRun?.status === 'running' || startingDiscovery) ? 'Discovering...' : 'Run Discovery' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .opportunities-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .opportunities-page {
        padding: 16px;
      }
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 16px;
    }
    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }
    .page-subtitle {
      font-size: 13.5px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .provider-banner {
      margin-bottom: 20px;
      padding: 16px 20px;
      background: #ffffff;
      border: 1px solid var(--border-color);
    }
    .banner-title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }
    .banner-heading {
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }
    .banner-sub {
      font-size: 12px;
      color: var(--text-secondary);
    }
    .provider-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .provider-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      padding: 5px 10px;
      border-radius: var(--radius-sm);
      font-size: 12px;
    }
    .provider-pill.active {
      border-color: var(--success-border);
      background: var(--success-bg);
    }
    .provider-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-muted);
    }
    .provider-pill.active .provider-dot {
      background: #059669;
    }
    .provider-pill.standby {
      border-color: var(--border-color);
      background: var(--bg-app);
    }
    .provider-pill.standby .provider-dot {
      background: #94a3b8;
    }
    .profile-notice-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      margin-bottom: 20px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: var(--radius-sm);
    }
    .notice-content {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .notice-icon {
      font-size: 24px;
    }
    .notice-title {
      font-size: 14px;
      font-weight: 600;
      color: #1e3a8a;
      margin-bottom: 2px;
    }
    .notice-desc {
      font-size: 13px;
      color: #1e40af;
    }
    .notice-actions {
      display: flex;
      gap: 10px;
    }
    .discovery-error-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 18px;
      margin-bottom: 20px;
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      border-radius: var(--radius-sm);
      color: var(--danger-text);
      font-size: 13px;
    }
    .error-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      border-radius: var(--radius-md);
    }
    .error-msg-box {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--danger-text);
      font-size: 13.5px;
    }
    .spinner-inline {
      width: 20px;
      height: 20px;
      border: 2px solid var(--border-color);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .run-progress-card {
      margin-bottom: 24px;
      border-left: 3px solid var(--accent);
      padding: 18px 20px;
      background: #ffffff;
    }
    .run-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .run-title-box {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .run-badge {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
      background: var(--bg-subtle);
    }
    .run-badge.running {
      background: #eff6ff;
      color: #2563eb;
    }
    .run-badge.completed {
      background: var(--success-bg);
      color: var(--success-text);
    }
    .run-badge.partial {
      background: var(--warning-bg);
      color: var(--warning-text);
    }
    .run-badge.failed {
      background: var(--danger-bg);
      color: var(--danger-text);
    }
    .run-name {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .run-time {
      font-size: 12px;
      color: var(--text-muted);
    }
    .run-metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      background: var(--bg-app);
      padding: 12px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }
    .run-metric {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }
    .metric-val {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .metric-lbl {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .run-error-note {
      margin-top: 10px;
      font-size: 12px;
      color: var(--text-secondary);
      background: var(--bg-subtle);
      padding: 6px 10px;
      border-radius: var(--radius-sm);
    }
    .filters-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .type-tabs {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .tab-btn {
      padding: 8px 14px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tab-btn:hover {
      background: var(--bg-subtle);
      color: var(--text-primary);
    }
    .tab-btn.active {
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
    }
    .secondary-controls {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .filter-count-badge {
      background: var(--accent);
      color: white;
      font-size: 10px;
      font-weight: 700;
      border-radius: 9999px;
      padding: 1px 6px;
      margin-left: 4px;
    }
    .search-input {
      padding: 7px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 13px;
      min-width: 220px;
      background: #ffffff;
    }
    .filter-panel {
      padding: 18px 20px;
      margin-bottom: 16px;
      background: #ffffff;
      border: 1px solid var(--border-color);
    }
    .filter-panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border-color);
    }
    .filter-panel-title {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .clear-all-link {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 12px;
      cursor: pointer;
      font-weight: 500;
    }
    .clear-all-link:hover {
      text-decoration: underline;
    }
    .filter-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 14px;
    }
    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .filter-label {
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .filter-select, .filter-input {
      padding: 7px 10px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 12.5px;
      background: #ffffff;
      color: var(--text-primary);
      width: 100%;
      box-sizing: border-box;
    }
    .combobox-group {
      position: relative;
    }
    .combobox-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      width: 100%;
    }
    .combobox-wrapper .filter-input {
      padding-right: 28px;
    }
    .combobox-clear {
      position: absolute;
      right: 8px;
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 12px;
      padding: 2px 4px;
      border-radius: var(--radius-sm);
      line-height: 1;
    }
    .combobox-clear:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }
    .autocomplete-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      z-index: 1000;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
      max-height: 220px;
      overflow-y: auto;
      list-style: none;
      padding: 4px 0;
      margin: 4px 0 0 0;
    }
    .autocomplete-item {
      padding: 8px 12px;
      font-size: 12.5px;
      color: var(--text-primary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: background 0.12s ease;
    }
    .autocomplete-item:hover, .autocomplete-item.selected {
      background: var(--bg-hover);
      color: var(--accent);
      font-weight: 600;
    }
    .suggestion-text {
      font-weight: 500;
    }
    .active-filters-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .results-counter {
      font-size: 13px;
      color: var(--text-secondary);
    }
    .active-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }
    .filter-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      border-radius: 9999px;
      padding: 3px 10px;
      font-size: 12px;
      color: var(--text-primary);
    }
    .filter-chip button {
      background: none;
      border: none;
      font-size: 11px;
      cursor: pointer;
      color: var(--text-muted);
      padding: 0;
      display: flex;
      align-items: center;
    }
    .filter-chip button:hover {
      color: var(--danger-text);
    }
    .btn-clear-inline {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      margin-left: 6px;
    }
    .loading-box, .empty-box {
      text-align: center;
      padding: 48px 20px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      margin-bottom: 24px;
    }
    .empty-box h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }
    .empty-box p {
      font-size: 13px;
      color: var(--text-secondary);
      max-width: 500px;
      margin: 0 auto;
      line-height: 1.5;
    }
    .opportunities-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
    }
    @media (max-width: 640px) {
      .opportunities-grid {
        grid-template-columns: 1fr;
      }
    }
    .opp-card {
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: var(--shadow-xs);
      transition: box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .opp-card:hover {
      box-shadow: var(--shadow-card);
      border-color: var(--border-strong);
    }
    .opp-card.opp-saved {
      border-left: 3px solid #2563eb;
    }
    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .badges-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }
    .badge {
      font-size: 10.5px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: var(--radius-sm);
      letter-spacing: 0.02em;
    }
    .badge-advertised {
      background: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }
    .badge-emerging {
      background: #fef3c7;
      color: #92400e;
      border: 1px solid #fde68a;
    }
    .badge-strategic {
      background: #eff6ff;
      color: #1e40af;
      border: 1px solid #bfdbfe;
    }
    .verification-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: var(--radius-sm);
      letter-spacing: 0.02em;
    }
    .verification-verified {
      background: #ecfdf5;
      color: #047857;
      border: 1px solid #a7f3d0;
    }
    .verification-unverified {
      background: #f8fafc;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .verification-closed {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }
    .action-contact {
      background: #ecfdf5;
      color: #047857;
      font-weight: 700;
    }
    .action-improve {
      background: #fffbeb;
      color: #b45309;
    }
    .action-skip {
      background: #f8fafc;
      color: #64748b;
    }
    .match-score-pill {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-primary);
      background: var(--bg-subtle);
      padding: 2px 7px;
      border-radius: var(--radius-sm);
    }
    .icon-save-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
      border-radius: var(--radius-sm);
      transition: color 0.15s ease;
    }
    .icon-save-btn:hover {
      color: #2563eb;
    }
    .icon-save-btn.saved {
      color: #2563eb;
    }
    .opp-role-block {
      margin-bottom: 8px;
    }
    .opp-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.35;
      margin-bottom: 4px;
    }
    .opp-meta-line {
      font-size: 12.5px;
      color: var(--text-secondary);
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
    }
    .meta-company {
      font-weight: 600;
      color: var(--text-primary);
    }
    .meta-sep {
      color: var(--text-muted);
    }
    .classification-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0;
      align-items: center;
    }
    .class-tag {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: var(--radius-sm);
      font-weight: 500;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
    }
    .class-tag.enterprise {
      background: #f0fdf4;
      color: #166534;
      border-color: #bbf7d0;
    }
    .class-tag.startup {
      background: #faf5ff;
      color: #6b21a8;
      border-color: #e9d5ff;
    }
    .class-tag.mid_sized {
      background: #f0f9ff;
      color: #075985;
      border-color: #bae6fd;
    }
    .class-tag.smb {
      background: #fffbeb;
      color: #92400e;
      border-color: #fde68a;
    }
    .class-tag.unknown {
      background: var(--bg-subtle);
      color: var(--text-muted);
      border-color: var(--border-color);
    }
    .work-tag, .salary-tag {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: var(--radius-sm);
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      color: var(--text-secondary);
    }
    .salary-tag {
      background: #ecfdf5;
      color: #065f46;
      border-color: #a7f3d0;
      font-weight: 500;
    }
    .provenance-tag {
      font-size: 10.5px;
      color: var(--text-muted);
      margin-left: auto;
    }
    .opp-explanation {
      font-size: 12.5px;
      color: var(--text-secondary);
      line-height: 1.45;
      margin: 8px 0;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .skills-block {
      margin-top: 6px;
    }
    .skills-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      display: block;
      margin-bottom: 4px;
    }
    .skills-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }
    .skill-chip {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: var(--radius-sm);
    }
    .skill-chip.matched {
      background: #ecfdf5;
      color: #047857;
      border: 1px solid #a7f3d0;
    }
    .skill-chip.missing {
      background: #fff1f2;
      color: #be123c;
      border: 1px solid #fecdd3;
    }
    .skill-chip.more {
      background: var(--bg-subtle);
      color: var(--text-muted);
      border: 1px solid var(--border-color);
    }
    .card-footer-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--border-color);
    }
    .confidence-indicator {
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .conf-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #059669;
    }
    .conf-label {
      font-size: 11px;
      color: var(--text-muted);
    }
    .footer-btn-group {
      display: flex;
      gap: 8px;
    }
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 24px;
    }
    .modal-content {
      background: #ffffff;
      border-radius: var(--radius-md);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
      width: 100%;
      max-width: 750px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
    }
    .modal-sm {
      max-width: 480px;
    }
    .modal-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    .modal-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .modal-subtitle {
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .modal-close-btn {
      background: none;
      border: none;
      font-size: 16px;
      color: var(--text-muted);
      cursor: pointer;
    }
    .modal-body {
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      background: #fafafa;
    }
    .section-box {
      padding: 16px;
    }
    .section-box h4 {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }
    .section-p {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.5;
    }
    .critical-fail-box {
      margin-top: 10px;
      padding: 8px 12px;
      background: var(--danger-bg);
      color: var(--danger-text);
      border-radius: var(--radius-sm);
      font-size: 12px;
    }
    .critical-fail-box ul {
      margin-top: 4px;
      padding-left: 18px;
    }
    .why-rows {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 10px;
    }
    .why-item {
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      font-size: 12.5px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .contact-why {
      background: var(--success-bg);
      color: var(--success-text);
    }
    .wait-why {
      background: var(--warning-bg);
      color: var(--warning-text);
    }
    .evidence-card {
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      margin-top: 8px;
    }
    .evidence-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .claim-type-badge {
      font-size: 10.5px;
      font-weight: 700;
      color: var(--text-secondary);
      text-transform: uppercase;
    }
    .conf-badge {
      font-size: 11px;
      color: var(--success-text);
      font-weight: 600;
    }
    .evidence-claim {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-primary);
      margin-bottom: 4px;
    }
    .evidence-quote {
      font-size: 12px;
      color: var(--text-secondary);
      border-left: 2px solid var(--accent);
      padding-left: 8px;
      margin: 6px 0;
      font-style: italic;
    }
    .evidence-url {
      font-size: 11.5px;
      color: var(--accent);
      word-break: break-all;
      text-decoration: none;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }
    .form-label {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
    }
    .form-control {
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      font-size: 13px;
    }
    .mode-status-banner {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 18px;
      margin-bottom: 20px;
      border-radius: var(--radius-sm);
      gap: 16px;
      flex-wrap: wrap;
    }
    .mode-status-banner.mode-recommend {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
    }
    .mode-status-banner.mode-explore {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
    }
    .mode-info {
      display: flex;
      align-items: flex-start;
      gap: 12px;
    }
    .mode-badge {
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.05em;
      padding: 3px 8px;
      border-radius: 4px;
      background: #ffffff;
      border: 1px solid currentColor;
      white-space: nowrap;
      margin-top: 2px;
    }
    .mode-recommend .mode-badge {
      color: #15803d;
    }
    .mode-explore .mode-badge {
      color: #1d4ed8;
    }
    .mode-title {
      font-size: 14.5px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0;
    }
    .mode-sub {
      font-size: 12.5px;
      color: var(--text-secondary);
      margin: 3px 0 0 0;
    }
    .filter-title-wrap {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .filter-panel-help {
      font-size: 12px;
      color: var(--text-muted);
      margin: 0;
    }
    .filter-hint {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .modal-md {
      max-width: 580px;
      width: 100%;
    }
    .location-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .clear-all-link-sm {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 11.5px;
      cursor: pointer;
      padding: 0;
    }
    .selected-locations-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }
    .loc-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #eff6ff;
      color: #1e40af;
      border: 1px solid #bfdbfe;
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 500;
    }
    .loc-remove-btn {
      background: none;
      border: none;
      color: #3b82f6;
      cursor: pointer;
      font-size: 11px;
      padding: 0;
      line-height: 1;
    }
    .loc-remove-btn:hover {
      color: #1e3a8a;
    }
    .no-locs-hint {
      font-size: 12px;
      color: var(--text-muted);
      font-style: italic;
      margin-bottom: 6px;
    }
    .loc-selector-row {
      display: flex;
      gap: 8px;
      position: relative;
    }
    .loc-dropdown-container {
      flex: 1;
      position: relative;
    }
    .loc-dropdown {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      max-height: 180px;
      overflow-y: auto;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      z-index: 100;
      display: flex;
      flex-direction: column;
    }
    .loc-option-btn {
      text-align: left;
      background: none;
      border: none;
      padding: 7px 12px;
      font-size: 12.5px;
      cursor: pointer;
      color: var(--text-primary);
    }
    .loc-option-btn:hover {
      background: #f1f5f9;
      color: var(--accent);
    }
    .custom-loc-box {
      display: flex;
      gap: 6px;
      flex: 1;
    }
    .custom-loc-input {
      flex: 1;
    }
    .form-help-text {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }
    .form-row-2col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
  `]
})
export class OpportunitiesComponent implements OnInit, OnDestroy {
  private oppService = inject(OpportunityService);
  private profileService = inject(ProfileService);
  private cdr = inject(ChangeDetectorRef);

  profile: Profile | null = null;
  opportunities: Opportunity[] = [];
  providers: ProviderHealth[] = [];
  activeRun: DiscoveryRun | null = null;
  selectedOppForDetail: Opportunity | null = null;

  loading = false;
  loadError: string | null = null;
  startingDiscovery = false;
  discoveryError: string | null = null;
  profileMissingWarning: string | null = null;

  // Active Category & Tab Filters
  selectedType: OpportunityType | null = null;
  selectedStatus: OpportunityStatus | null = null;
  selectedAction: RecommendedAction | null = null;
  searchQuery = '';

  // Secondary Filter Panel Controls
  showFilterPanel = false;
  filterWorkArrangement = '';
  filterEmploymentType = '';
  filterClassification = '';
  filterMinScore: number | null = null;
  filterLocation = '';
  filterSkill = '';
  sortOrder: 'match_score' | 'recent' = 'match_score';

  // Autocomplete Suggestions State
  locationSuggestions: string[] = [];
  skillSuggestions: string[] = [];
  showLocationSuggestions = false;
  showSkillSuggestions = false;
  selectedLocationIndex = -1;
  selectedSkillIndex = -1;

  savedCount = 0;
  showDiscoveryModal = false;

  // Operating Mode: A (Automatic Profile Recommendations) vs B (Exploration)
  currentMode: 'RECOMMENDATIONS' | 'EXPLORATION' = 'RECOMMENDATIONS';

  // Multi-Location Selector State
  selectedLocations: string[] = ['Bengaluru', 'Hyderabad', 'Remote'];
  locationSearchInput = '';
  customLocationInput = '';
  showLocationDropdown = false;
  availableCities: string[] = [
    'Bengaluru',
    'Hyderabad',
    'Delhi',
    'New Delhi',
    'Noida',
    'Greater Noida',
    'Gurugram',
    'Mumbai',
    'Pune',
    'Chennai',
    'Kolkata',
    'Mohali',
    'Chandigarh',
    'Jaipur',
    'Ahmedabad',
    'Kochi',
    'Lucknow',
    'Indore',
    'Coimbatore',
    'Visakhapatnam',
    'Remote'
  ];

  // Exploration Form Parameters
  customRole = '';
  customLocation = '';
  customRemotePref = 'flexible';
  customWorkArrangement = 'Any';
  customEmploymentType = 'Any';
  customExperienceLevel = 'Any';
  customLimit = 20;

  private pollSubscription?: Subscription;

  get sourceCategories(): SourceCategory[] {
    const hasLiveSearch = this.providers.some(
      (p) => ['tavily', 'exa'].includes(p.provider_name.toLowerCase()) && p.is_configured
    );
    const hasPortals = this.providers.some(
      (p) => ['serpapi'].includes(p.provider_name.toLowerCase()) && p.is_configured
    ) || hasLiveSearch;
    const hasFeeds = this.providers.some(
      (p) => ['jsearch', 'adzuna', 'jooble'].includes(p.provider_name.toLowerCase()) && p.is_configured
    ) || hasLiveSearch;
    const hasGrowth = this.providers.some(
      (p) => ['tavily'].includes(p.provider_name.toLowerCase()) && p.is_configured
    );
    const hasSemantic = this.providers.some(
      (p) => ['exa'].includes(p.provider_name.toLowerCase()) && p.is_configured
    );

    return [
      {
        label: 'Direct Company Portals',
        status: hasPortals ? 'active' : 'standby',
        statusText: hasPortals ? 'ACTIVE & READY' : 'STANDBY',
        description: 'Internal career sites & employer direct listings'
      },
      {
        label: 'Public Career Feeds',
        status: hasFeeds ? 'active' : 'standby',
        statusText: hasFeeds ? 'ACTIVE & READY' : 'STANDBY',
        description: 'Aggregated talent networks & industry feeds'
      },
      {
        label: 'Strategic Growth Signals',
        status: hasGrowth ? 'active' : 'standby',
        statusText: hasGrowth ? 'ACTIVE & READY' : 'STANDBY',
        description: 'Expansion cues, funding events & public initiatives'
      },
      {
        label: 'Semantic Technology Feeds',
        status: hasSemantic ? 'active' : 'standby',
        statusText: hasSemantic ? 'ACTIVE & READY' : 'STANDBY',
        description: 'Deep neural matching across technical stacks & repos'
      }
    ];
  }

  get activeFiltersCount(): number {
    let count = 0;
    if (this.filterWorkArrangement) count++;
    if (this.filterEmploymentType) count++;
    if (this.filterClassification) count++;
    if (this.filterMinScore !== null) count++;
    if (this.selectedAction) count++;
    if (this.filterLocation) count++;
    if (this.filterSkill) count++;
    if (this.searchQuery) count++;
    return count;
  }

  get filteredOpportunities(): Opportunity[] {
    let list = [...this.opportunities];

    // 1. Category / Status Filter
    if (this.selectedStatus === 'SAVED') {
      list = list.filter((o) => o.status === 'SAVED');
    } else if (this.selectedType) {
      list = list.filter((o) => o.opportunity_type === this.selectedType);
    }

    // 2. Recommendation Action Filter
    if (this.selectedAction) {
      list = list.filter((o) => o.recommended_action === this.selectedAction);
    }

    // 3. Work Arrangement Filter
    if (this.filterWorkArrangement) {
      list = list.filter((o) => {
        const arr = (o.job?.work_arrangement || '').toLowerCase();
        if (this.filterWorkArrangement === 'remote') {
          return arr.includes('remote') || o.job?.is_remote;
        }
        return arr.includes(this.filterWorkArrangement);
      });
    }

    // 4. Employment Type Filter
    if (this.filterEmploymentType) {
      list = list.filter((o) =>
        (o.job?.employment_type || '').toLowerCase().includes(this.filterEmploymentType)
      );
    }

    // 5. Company Classification Filter
    if (this.filterClassification) {
      list = list.filter((o) => {
        const c = this.getCompanyClassification(o);
        return c === this.filterClassification;
      });
    }

    // 6. Minimum Score Filter
    if (this.filterMinScore !== null) {
      list = list.filter((o) => o.match_score >= this.filterMinScore!);
    }

    // 7. Location Filter (Canonical location matching with boundary disambiguation)
    if (this.filterLocation) {
      const q = this.filterLocation.toLowerCase().trim();
      list = list.filter((o) => {
        const canonical = this.getCanonicalLocation(o).toLowerCase();
        if (q === 'noida') {
          return canonical.includes('noida') && !canonical.includes('greater noida');
        }
        if (q === 'delhi') {
          return canonical.includes('delhi') && !canonical.includes('new delhi');
        }
        return canonical.includes(q);
      });
    }

    // 8. Skill Filter
    if (this.filterSkill) {
      const q = this.filterSkill.toLowerCase().trim();
      list = list.filter((o) =>
        o.matched_skills.some((sk) => sk.toLowerCase().includes(q)) ||
        (o.job?.requirements || []).some((r) => r.description.toLowerCase().includes(q))
      );
    }

    // 9. Free-text Search Filter
    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase().trim();
      list = list.filter((o) => {
        const title = (o.job?.title || '').toLowerCase();
        const comp = (o.company?.name || o.job?.company_name || '').toLowerCase();
        const expl = (o.explanation || '').toLowerCase();
        return title.includes(q) || comp.includes(q) || expl.includes(q);
      });
    }

    // 10. Sort Order
    if (this.sortOrder === 'recent') {
      list.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    } else {
      list.sort((a, b) => b.match_score - a.match_score);
    }

    return list;
  }

  getCleanDisplayTitle(rawTitle?: string): string {
    if (!rawTitle) return 'Opportunity';
    const firstLine = rawTitle.includes('\n') ? rawTitle.split('\n')[0] : rawTitle;
    return firstLine.replace(/^[^\w\s]+/, '').trim();
  }

  getCompanyClassification(opp: Opportunity): string {
    if (opp.company?.classification && opp.company.classification !== 'unknown') {
      return opp.company.classification;
    }
    const desc = (opp.company?.description || '').toLowerCase();
    const signals = opp.company?.signals_data || [];
    for (const s of signals) {
      if (s.classification && s.classification !== 'unknown') return s.classification;
    }
    if (desc.includes('startup') || desc.includes('early-stage') || desc.includes('seed')) return 'startup';
    if (desc.includes('enterprise') || desc.includes('multinational') || desc.includes('fortune 500')) return 'enterprise';
    if (desc.includes('mid-sized') || desc.includes('mid_sized')) return 'mid_sized';
    if (desc.includes('small business') || desc.includes('smb')) return 'smb';
    return opp.company?.classification || 'unknown';
  }

  formatClassification(classification: string): string {
    switch (classification) {
      case 'enterprise':
        return '🏢 MNC / Enterprise';
      case 'startup':
        return '🚀 Startup';
      case 'mid_sized':
        return '🏢 Mid-sized Company';
      case 'smb':
        return '🏬 Small/Medium Business';
      case 'unknown':
      default:
        return '🏛️ Unspecified';
    }
  }

  getSourceCategoryLabel(rawSource?: string | null): string {
    if (!rawSource) return 'Direct Research Target';
    const s = rawSource.toLowerCase();
    if (s.includes('tavily') || s.includes('growth')) return 'Strategic Growth Signal';
    if (s.includes('exa') || s.includes('semantic')) return 'Semantic Tech Discovery';
    if (s.includes('serpapi') || s.includes('google') || s.includes('portal')) return 'Direct Company Portal';
    if (s.includes('jsearch') || s.includes('adzuna') || s.includes('jooble') || s.includes('feed')) return 'Public Career Feed';
    return rawSource;
  }

  getCandidateFriendlyRunNote(rawSummary?: string | null): string {
    if (!rawSummary) return '';
    if (rawSummary.includes('No external API keys') || rawSummary.includes('TAVILY_API_KEY') || rawSummary.includes('EXA_API_KEY')) {
      return 'Notice: No external search credentials configured. Configure TAVILY_API_KEY / EXA_API_KEY to search live web portals.';
    }
    if (rawSummary.includes('Partial discovery')) {
      return 'Multi-source discovery completed. Displaying all verified and deduplicated opportunities.';
    }
    if (rawSummary.includes('failed') || rawSummary.includes('failure')) {
      return 'Discovery run completed with errors on some source channels. Displaying all verified records.';
    }
    return rawSummary;
  }

  ngOnInit(): void {
    this.loadProfile();
    this.loadProviders();
    this.loadFilterSuggestions();
    this.initializeRunsAndOpportunities();
  }

  ngOnDestroy(): void {
    this.pollSubscription?.unsubscribe();
  }

  loadFilterSuggestions(): void {
    this.oppService.getFilterSuggestions().subscribe({
      next: (data) => {
        if (data) {
          this.locationSuggestions = data.locations || [];
          this.skillSuggestions = data.skills || [];
          this.cdr.markForCheck();
        }
      },
      error: () => {}
    });
  }

  get filteredLocationSuggestions(): string[] {
    const q = (this.filterLocation || '').toLowerCase().trim();
    if (!q) return this.locationSuggestions.slice(0, 15);
    return this.locationSuggestions.filter((l) => l.toLowerCase().includes(q)).slice(0, 15);
  }

  get filteredSkillSuggestions(): string[] {
    const q = (this.filterSkill || '').toLowerCase().trim();
    if (!q) return this.skillSuggestions.slice(0, 20);
    return this.skillSuggestions.filter((s) => s.toLowerCase().includes(q)).slice(0, 20);
  }

  selectLocationSuggestion(loc: string): void {
    this.filterLocation = loc;
    this.showLocationSuggestions = false;
    this.selectedLocationIndex = -1;
    this.cdr.markForCheck();
  }

  selectSkillSuggestion(skill: string): void {
    this.filterSkill = skill;
    this.showSkillSuggestions = false;
    this.selectedSkillIndex = -1;
    this.cdr.markForCheck();
  }

  onLocationKeydown(event: KeyboardEvent): void {
    const items = this.filteredLocationSuggestions;
    if (!this.showLocationSuggestions) {
      if (event.key === 'ArrowDown' || event.key === 'Enter') {
        this.showLocationSuggestions = true;
      }
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.selectedLocationIndex = (this.selectedLocationIndex + 1) % items.length;
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.selectedLocationIndex = (this.selectedLocationIndex - 1 + items.length) % items.length;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (this.selectedLocationIndex >= 0 && this.selectedLocationIndex < items.length) {
        this.selectLocationSuggestion(items[this.selectedLocationIndex]);
      } else {
        this.showLocationSuggestions = false;
      }
    } else if (event.key === 'Escape') {
      this.showLocationSuggestions = false;
      this.selectedLocationIndex = -1;
    }
  }

  onSkillKeydown(event: KeyboardEvent): void {
    const items = this.filteredSkillSuggestions;
    if (!this.showSkillSuggestions) {
      if (event.key === 'ArrowDown' || event.key === 'Enter') {
        this.showSkillSuggestions = true;
      }
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.selectedSkillIndex = (this.selectedSkillIndex + 1) % items.length;
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.selectedSkillIndex = (this.selectedSkillIndex - 1 + items.length) % items.length;
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (this.selectedSkillIndex >= 0 && this.selectedSkillIndex < items.length) {
        this.selectSkillSuggestion(items[this.selectedSkillIndex]);
      } else {
        this.showSkillSuggestions = false;
      }
    } else if (event.key === 'Escape') {
      this.showSkillSuggestions = false;
      this.selectedSkillIndex = -1;
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.combobox-group')) {
      this.showLocationSuggestions = false;
      this.showSkillSuggestions = false;
      this.cdr.markForCheck();
    }
  }

  deduplicateOpportunitiesClientSide(opps: Opportunity[]): Opportunity[] {
    const seen = new Set<string>();
    const unique: Opportunity[] = [];
    for (const opp of opps) {
      let key = opp.id;
      if (opp.job?.primary_url) {
        key = opp.job.primary_url.replace(/[?&](utm_[^&]+|ref=[^&]+|trk=[^&]+|fbclid=[^&]+)/g, '').replace(/\/$/, '').toLowerCase();
      } else if (opp.company?.id) {
        key = `comp::${opp.company.id}::${opp.opportunity_type}`;
      }
      if (!seen.has(key)) {
        seen.add(key);
        unique.push(opp);
      }
    }
    return unique;
  }

  get filteredCities(): string[] {
    const q = this.locationSearchInput.toLowerCase().trim();
    return this.availableCities.filter(
      (c) =>
        (!q || c.toLowerCase().includes(q)) &&
        !this.selectedLocations.some((sl) => sl.toLowerCase() === c.toLowerCase())
    );
  }

  addLocation(city: string): void {
    const norm = city.trim().replace(/\s+/g, ' ');
    if (norm && !this.selectedLocations.some((l) => l.toLowerCase() === norm.toLowerCase())) {
      this.selectedLocations.push(norm);
    }
    this.locationSearchInput = '';
    this.showLocationDropdown = false;
    this.cdr.markForCheck();
  }

  addCustomLocation(): void {
    const norm = this.customLocationInput.trim().replace(/\s+/g, ' ');
    if (norm && !this.selectedLocations.some((l) => l.toLowerCase() === norm.toLowerCase())) {
      this.selectedLocations.push(norm);
    }
    this.customLocationInput = '';
    this.cdr.markForCheck();
  }

  removeLocation(index: number): void {
    this.selectedLocations.splice(index, 1);
    this.cdr.markForCheck();
  }

  clearAllLocations(): void {
    this.selectedLocations = [];
    this.cdr.markForCheck();
  }

  openDiscoveryModal(): void {
    this.showDiscoveryModal = true;
    this.showLocationDropdown = false;
    this.cdr.markForCheck();
  }

  closeDiscoveryModal(): void {
    this.showDiscoveryModal = false;
    this.showLocationDropdown = false;
    this.cdr.markForCheck();
  }

  switchToProfileMode(): void {
    this.currentMode = 'RECOMMENDATIONS';
    this.clearAllFilters();
    this.loadOpportunities();
    this.cdr.markForCheck();
  }

  getCanonicalLocation(opp?: Opportunity | null): string {
    if (!opp) return 'Location Unspecified';
    if (opp.job?.location && opp.job.location.trim().length > 0) {
      return opp.job.location.trim();
    }
    if (opp.company?.headquarters && opp.company.headquarters.trim().length > 0) {
      return opp.company.headquarters.trim();
    }
    return 'Location Unspecified';
  }

  loadProfile(): void {
    this.profileService.getProfile().subscribe({
      next: (p) => {
        this.profile = p;
        if (p.preferences?.desired_roles?.length) {
          this.customRole = p.preferences.desired_roles[0];
        }
        if (p.preferences?.preferred_locations?.length) {
          this.selectedLocations = [...p.preferences.preferred_locations];
        }
        if (p.preferences?.remote_preference) {
          this.customRemotePref = p.preferences.remote_preference;
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    });
  }

  loadProviders(): void {
    this.oppService.getProviderHealth().subscribe({
      next: (res) => {
        this.providers = res;
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    });
  }

  initializeRunsAndOpportunities(): void {
    this.loading = true;
    this.oppService.getDiscoveryRuns(1, 0).subscribe({
      next: (runs) => {
        if (runs && runs.length > 0) {
          this.activeRun = runs[0];
          if (runs[0].status === 'running' || runs[0].status === 'queued') {
            this.startPollingRun(runs[0].id);
          }
        }
        this.loadOpportunitiesAndAutoDiscover();
      },
      error: () => {
        this.loadOpportunitiesAndAutoDiscover();
      }
    });
  }

  loadOpportunitiesAndAutoDiscover(): void {
    this.oppService.getOpportunities().subscribe({
      next: (res) => {
        this.opportunities = this.deduplicateOpportunitiesClientSide(res);
        this.loading = false;
        this.savedCount = this.opportunities.filter((o) => o.status === 'SAVED').length;
        this.cdr.markForCheck();

        // Profile-aware recommendations: If no opportunities exist, attempt auto-discovery once
        if (this.opportunities.length === 0 && (!this.activeRun || (this.activeRun.status !== 'running' && this.activeRun.status !== 'queued'))) {
          this.attemptAutoDiscovery();
        }
      },
      error: (err) => {
        this.loading = false;
        this.loadError = err?.error?.detail || 'Unable to load opportunities. Please check your connection and retry.';
        this.cdr.markForCheck();
      }
    });
  }

  attemptAutoDiscovery(): void {
    this.oppService.autoDiscover().subscribe({
      next: (run) => {
        if (run) {
          this.activeRun = run;
          this.startPollingRun(run.id);
        }
        this.profileMissingWarning = null;
        this.cdr.markForCheck();
      },
      error: (err) => {
        // If profile was incomplete, explain what information is needed
        if (err.status === 400 && err.error?.detail) {
          this.profileMissingWarning = err.error.detail;
        }
        this.cdr.markForCheck();
      }
    });
  }

  loadOpportunities(): void {
    this.loading = true;
    this.loadError = null;
    this.cdr.markForCheck();

    this.oppService
      .getOpportunities({
        opportunity_type: this.selectedType || undefined,
        status: this.selectedStatus || undefined,
        recommended_action: this.selectedAction || undefined,
        search: this.searchQuery ? this.searchQuery : undefined,
        location: this.filterLocation || undefined,
        work_arrangement: this.filterWorkArrangement || undefined,
        employment_type: this.filterEmploymentType || undefined,
        min_score: this.filterMinScore !== null ? this.filterMinScore : undefined,
        sort_by: this.sortOrder
      })
      .subscribe({
        next: (res) => {
          this.opportunities = this.deduplicateOpportunitiesClientSide(res);
          this.loading = false;
          this.savedCount = this.opportunities.filter((o) => o.status === 'SAVED').length;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loading = false;
          this.loadError = err?.error?.detail || 'Unable to load opportunities. Please check your connection and retry.';
          this.cdr.markForCheck();
        }
      });
  }

  setTypeFilter(type: OpportunityType | null): void {
    this.selectedType = type;
    this.selectedStatus = null;
    this.cdr.markForCheck();
  }

  setSavedFilter(): void {
    this.selectedType = null;
    this.selectedStatus = 'SAVED';
    this.cdr.markForCheck();
  }

  toggleFilterPanel(): void {
    this.showFilterPanel = !this.showFilterPanel;
    this.cdr.markForCheck();
  }

  clearAllFilters(): void {
    this.filterWorkArrangement = '';
    this.filterEmploymentType = '';
    this.filterClassification = '';
    this.filterMinScore = null;
    this.selectedAction = null;
    this.filterLocation = '';
    this.filterSkill = '';
    this.searchQuery = '';
    this.selectedType = null;
    this.selectedStatus = null;
    this.cdr.markForCheck();
  }

  submitDiscoveryRun(): void {
    if (this.startingDiscovery || this.activeRun?.status === 'running') return;

    this.startingDiscovery = true;
    this.discoveryError = null;
    this.closeDiscoveryModal();
    this.cdr.markForCheck();

    const roles = this.customRole.trim() ? [this.customRole.trim()] : undefined;
    const locs = this.customLocation.trim()
      ? [this.customLocation.trim()]
      : (this.selectedLocations && this.selectedLocations.length > 0 ? [...this.selectedLocations] : undefined);
    const workArr = this.customWorkArrangement !== 'Any' ? this.customWorkArrangement : undefined;
    const empType = this.customEmploymentType !== 'Any' ? this.customEmploymentType : undefined;
    const expLvl = this.customExperienceLevel !== 'Any' ? this.customExperienceLevel : undefined;

    // Transition to Exploration Mode without altering permanent profile
    this.currentMode = 'EXPLORATION';

    const reqPayload: any = {
      target_roles: roles,
      locations: locs,
      remote_preference: this.customRemotePref,
      opportunity_type: this.selectedType || undefined,
      limit: this.customLimit
    };
    if (workArr) reqPayload.work_arrangement = workArr;
    if (empType) reqPayload.employment_type = empType;
    if (expLvl) reqPayload.experience_level = expLvl;

    this.oppService
      .startDiscovery(reqPayload)
      .subscribe({
        next: (run) => {
          this.startingDiscovery = false;
          this.activeRun = run;
          this.startPollingRun(run.id);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.startingDiscovery = false;
          this.discoveryError = err?.error?.detail || 'Failed to start discovery run. Please try again.';
          this.cdr.markForCheck();
        }
      });
  }

  triggerDiscovery(): void {
    this.submitDiscoveryRun();
  }

  startPollingRun(runId: string): void {
    this.pollSubscription?.unsubscribe();
    let pollCount = 0;
    const maxPollAttempts = 35; // 35 * 2s = 70s max

    this.pollSubscription = interval(2000)
      .pipe(
        switchMap(() =>
          this.oppService.getDiscoveryRunStatus(runId).pipe(
            catchError((err) => {
              console.error('Transient polling error:', err);
              return of(null);
            })
          )
        ),
        takeWhile((run) => {
          pollCount++;
          if (pollCount > maxPollAttempts) {
            return false;
          }
          if (!run) return true;
          return run.status === 'running' || run.status === 'queued';
        }, true)
      )
      .subscribe({
        next: (run) => {
          if (run) {
            this.activeRun = run;
            if (run.status === 'completed' || run.status === 'partial' || run.status === 'failed') {
              this.startingDiscovery = false;
              this.loadOpportunities();
              this.loadProviders();
            }
          }
          if (pollCount > maxPollAttempts && (!run || run.status === 'running' || run.status === 'queued')) {
            this.startingDiscovery = false;
            if (this.activeRun) {
              this.activeRun = {
                ...this.activeRun,
                status: 'partial' as any,
                error_summary: 'Discovery run took longer than expected. Displaying all opportunities ingested so far.'
              };
            }
            this.loadOpportunities();
            this.loadProviders();
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.startingDiscovery = false;
          this.loadOpportunities();
          this.cdr.markForCheck();
        }
      });
  }

  toggleSave(opp: Opportunity): void {
    const nextStatus = opp.status === 'SAVED' ? 'ACTIVE' : 'SAVED';
    this.oppService.updateStatus(opp.id, nextStatus).subscribe({
      next: (updated) => {
        opp.status = updated.status;
        this.savedCount = this.opportunities.filter((o) => o.status === 'SAVED').length;
        this.cdr.markForCheck();
      }
    });
  }

  dismissOpportunity(opp: Opportunity): void {
    this.oppService.updateStatus(opp.id, 'DISMISSED').subscribe({
      next: () => {
        this.opportunities = this.opportunities.filter((o) => o.id !== opp.id);
        this.cdr.markForCheck();
      }
    });
  }

  openDetailModal(opp: Opportunity): void {
    this.selectedOppForDetail = opp;
    this.cdr.markForCheck();
  }

  closeDetailModal(): void {
    this.selectedOppForDetail = null;
    this.cdr.markForCheck();
  }

  toggleDiscoveryModal(): void {
    this.showDiscoveryModal = !this.showDiscoveryModal;
    this.cdr.markForCheck();
  }
}

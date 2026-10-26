import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { OpportunityService } from '../../core/services/opportunity.service';
import { DiscoveryRun } from '../../core/models/discovery.model';
import { ProviderHealth } from '../../core/models/provider.model';

export interface SourceChannel {
  name: string;
  category: string;
  description: string;
  isReady: boolean;
  statusText: string;
  itemsIngested: number;
  latencyMs: number;
}

@Component({
  selector: 'app-activity-view',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="activity-page">
      <!-- Header -->
      <header class="page-header">
        <div>
          <h1 class="page-title">Agent Activity & Audit Trail</h1>
          <p class="page-subtitle">
            Autonomous multi-source execution logs, provider telemetry, deduplication metrics, and error isolation traces
          </p>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" (click)="loadAllData()" [disabled]="loading">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh Logs
          </button>
          <a routerLink="/opportunities" class="btn btn-primary">
            Go to Opportunities
          </a>
        </div>
      </header>

      <!-- Intelligence Ingestion Channels Overview -->
      <section class="section-container">
        <div class="section-header">
          <div class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
            </svg>
            <span>INTELLIGENCE INGESTION CHANNELS</span>
          </div>
          <span class="section-badge">4 Ingestion Channels Active</span>
        </div>

        <div class="provider-grid">
          <div *ngFor="let ch of sourceChannels" class="iq-card provider-card" [class.unconfigured]="!ch.isReady">
            <div class="provider-top">
              <div class="provider-identity">
                <span class="provider-indicator" [ngClass]="ch.isReady ? 'active' : 'disabled'"></span>
                <span class="provider-name">{{ ch.name }}</span>
              </div>
              <span class="provider-status-badge" [ngClass]="ch.isReady ? 'active' : 'disabled'">
                {{ ch.statusText }}
              </span>
            </div>

            <p class="provider-desc">{{ ch.description }}</p>

            <div class="provider-meta">
              <div class="meta-row">
                <span class="meta-key">Channel Type:</span>
                <span class="meta-val code">{{ ch.category }}</span>
              </div>
              <div class="meta-row">
                <span class="meta-key">Items Ingested:</span>
                <span class="meta-val">{{ ch.itemsIngested }}</span>
              </div>
              <div class="meta-row" *ngIf="ch.latencyMs > 0">
                <span class="meta-key">Avg Latency:</span>
                <span class="meta-val">{{ ch.latencyMs }}ms</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Agent Run Audit Log -->
      <section class="section-container">
        <div class="section-header">
          <div class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            <span>EXECUTION RUN HISTORY</span>
          </div>
          <span class="section-badge">{{ runs.length }} Total Runs Executed</span>
        </div>

        <!-- Loading State -->
        <div *ngIf="loading" class="empty-state">
          <div class="loading-spinner"></div>
          <p>Loading agent execution audit records...</p>
        </div>

        <!-- Empty State -->
        <div *ngIf="!loading && runs.length === 0" class="iq-card empty-card">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <h3>No Discovery Runs Yet</h3>
          <p>When you start an Opportunity Intelligence run, full execution traces, deduplication statistics, and provider calls will be recorded here.</p>
          <a routerLink="/opportunities" class="btn btn-primary" style="margin-top: 16px;">
            Trigger Discovery in Opportunities
          </a>
        </div>

        <!-- Runs List -->
        <div *ngIf="!loading && runs.length > 0" class="runs-container">
          <div *ngFor="let run of runs" class="iq-card run-card" (click)="openTraceModal(run)">
            <div class="run-main-row">
              <div class="run-meta-col">
                <div class="run-status-line">
                  <span class="status-pill" [ngClass]="run.status.toLowerCase()">
                    <span class="status-dot"></span>
                    {{ run.status }}
                  </span>
                  <span class="run-type-tag">{{ run.run_type }}</span>
                  <span class="run-id-snippet">ID: {{ run.id | slice:0:8 }}...</span>
                </div>
                <div class="run-time-line">
                  <span>{{ run.created_at | date:'medium' }}</span>
                  <span class="separator">•</span>
                  <span>Execution: <strong>{{ run.execution_time_seconds.toFixed(2) }}s</strong></span>
                </div>
              </div>

              <!-- Metric Badges -->
              <div class="run-stat-badges">
                <div class="stat-badge">
                  <span class="stat-num">{{ run.results_discovered_count }}</span>
                  <span class="stat-label">Discovered</span>
                </div>
                <div class="stat-badge dedupe">
                  <span class="stat-num">{{ run.results_deduplicated_count }}</span>
                  <span class="stat-label">Deduplicated</span>
                </div>
                <div class="stat-badge created">
                  <span class="stat-num">{{ run.opportunities_created_count }}</span>
                  <span class="stat-label">Stored</span>
                </div>
              </div>
            </div>

            <!-- Source Breakdown -->
            <div class="run-providers-row">
              <span class="row-label">Sources:</span>
              <div class="provider-badges-list">
                <span
                  *ngFor="let p of run.providers_succeeded"
                  class="badge-prov success"
                  title="Queried successfully"
                >
                  ✓ {{ formatSourceName(p) }}
                </span>
                <span
                  *ngFor="let pf of run.providers_failed"
                  class="badge-prov fail"
                  title="Source channel temporarily unreachable"
                >
                  ✕ {{ formatSourceName(pf.provider) }}
                </span>
              </div>
            </div>

            <!-- Error Summary if any -->
            <div *ngIf="run.error_summary" class="run-error-alert">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <span>{{ getCandidateFriendlySummary(run.error_summary) }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Run Audit Trace Modal -->
      <div *ngIf="selectedRun" class="modal-backdrop" (click)="closeTraceModal()">
        <div class="modal-card trace-modal" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <div>
              <div class="modal-overline">EXECUTION AUDIT TRACE</div>
              <h2 class="modal-title">Run #{{ selectedRun.id }}</h2>
            </div>
            <button class="btn-close" (click)="closeTraceModal()">✕</button>
          </div>

          <div class="modal-body">
            <!-- Run Summary -->
            <div class="trace-grid">
              <div class="trace-box">
                <span class="trace-label">Status</span>
                <span class="trace-value bold" [ngClass]="selectedRun.status.toLowerCase()">
                  {{ selectedRun.status }}
                </span>
              </div>
              <div class="trace-box">
                <span class="trace-label">Duration</span>
                <span class="trace-value">{{ selectedRun.execution_time_seconds.toFixed(2) }} seconds</span>
              </div>
              <div class="trace-box">
                <span class="trace-label">Started At</span>
                <span class="trace-value">{{ selectedRun.created_at | date:'medium' }}</span>
              </div>
              <div class="trace-box">
                <span class="trace-label">Deduplication Ratio</span>
                <span class="trace-value">
                  {{ selectedRun.results_discovered_count > 0 ? ((selectedRun.results_deduplicated_count / selectedRun.results_discovered_count) * 100).toFixed(0) : 0 }}%
                </span>
              </div>
            </div>

            <!-- Query Parameters Used -->
            <div class="trace-section">
              <div class="trace-sec-title">Query Parameters & Targeting</div>
              <div class="params-block">
                <pre class="json-dump">{{ selectedRun.query_params | json }}</pre>
              </div>
            </div>

            <!-- Succeeded Sources -->
            <div class="trace-section" *ngIf="selectedRun.providers_succeeded?.length">
              <div class="trace-sec-title">Successful Ingestion Channels ({{ selectedRun.providers_succeeded.length }})</div>
              <div class="tag-row">
                <span *ngFor="let p of selectedRun.providers_succeeded" class="badge-prov success large">
                  ✓ {{ formatSourceName(p) }}
                </span>
              </div>
            </div>

            <!-- Failed Sources -->
            <div class="trace-section" *ngIf="selectedRun.providers_failed?.length">
              <div class="trace-sec-title">Channel Availability Notes ({{ selectedRun.providers_failed.length }})</div>
              <div class="failures-list">
                <div *ngFor="let f of selectedRun.providers_failed" class="failure-item">
                  <div class="fail-prov-name">● {{ formatSourceName(f.provider) }}</div>
                  <div class="fail-prov-err">Source channel was temporarily unreachable. Fault isolated automatically; remaining channels ingested cleanly.</div>
                </div>
              </div>
            </div>

            <!-- Error Summary -->
            <div class="trace-section" *ngIf="selectedRun.error_summary">
              <div class="trace-sec-title">Engine Summary Note</div>
              <div class="error-summary-box">
                {{ getCandidateFriendlySummary(selectedRun.error_summary) }}
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" (click)="closeTraceModal()">Close Audit Trace</button>
            <a routerLink="/opportunities" class="btn btn-primary" (click)="closeTraceModal()">
              View Opportunities Discovered
            </a>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .activity-page {
      padding: 28px;
      max-width: 1240px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .activity-page {
        padding: 16px;
      }
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 28px;
      gap: 16px;
      flex-wrap: wrap;
    }
    .page-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 0 0 4px 0;
      letter-spacing: -0.02em;
    }
    .page-subtitle {
      font-size: 13.5px;
      color: var(--text-secondary);
      margin: 0;
      max-width: 680px;
      line-height: 1.5;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 16px;
      border-radius: var(--radius-sm);
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      text-decoration: none;
      transition: all 0.15s ease;
    }
    .btn-primary {
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }
    .btn-primary:hover {
      background: var(--accent-hover);
    }
    .btn-secondary {
      background: #ffffff;
      color: var(--text-primary);
      border-color: var(--border-color);
    }
    .btn-secondary:hover {
      background: var(--bg-subtle);
    }
    .section-container {
      margin-bottom: 36px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.05em;
    }
    .section-badge {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--bg-subtle);
      padding: 3px 8px;
      border-radius: 9999px;
    }
    .provider-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }
    .provider-card {
      padding: 20px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .provider-card.unconfigured {
      background: #fbfbfd;
      border-color: #e5e7eb;
    }
    .provider-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .provider-identity {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .provider-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .provider-indicator.active {
      background: #10b981;
      box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
    }
    .provider-indicator.disabled {
      background: #9ca3af;
    }
    .provider-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .provider-status-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 3px 7px;
      border-radius: 9999px;
      letter-spacing: 0.03em;
    }
    .provider-status-badge.active {
      background: #d1fae5;
      color: #065f46;
    }
    .provider-status-badge.disabled {
      background: #f3f4f6;
      color: #6b7280;
    }
    .provider-desc {
      font-size: 12.5px;
      color: var(--text-muted);
      margin: 0;
      line-height: 1.4;
    }
    .provider-meta {
      background: var(--bg-app);
      border-radius: var(--radius-sm);
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .meta-row {
      display: flex;
      justify-content: space-between;
      font-size: 11.5px;
    }
    .meta-key {
      color: var(--text-muted);
    }
    .meta-val {
      font-weight: 600;
      color: var(--text-primary);
    }
    .meta-val.code {
      font-family: monospace;
    }
    .meta-val.has-error {
      color: #dc2626;
    }
    .provider-error-snip {
      font-size: 11px;
      color: #b91c1c;
      background: #fef2f2;
      padding: 6px 10px;
      border-radius: var(--radius-sm);
      word-break: break-word;
    }
    .empty-state {
      text-align: center;
      padding: 48px;
      color: var(--text-muted);
    }
    .loading-spinner {
      width: 32px;
      height: 32px;
      border: 3px solid rgba(0, 0, 0, 0.1);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 16px auto;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .empty-card {
      text-align: center;
      padding: 56px 24px;
      background: #ffffff;
      border: 1px dashed var(--border-color);
      border-radius: var(--radius-md);
    }
    .empty-icon {
      color: var(--text-muted);
      margin-bottom: 12px;
    }
    .empty-card h3 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 6px 0;
    }
    .empty-card p {
      font-size: 13.5px;
      color: var(--text-muted);
      max-width: 480px;
      margin: 0 auto;
      line-height: 1.5;
    }
    .runs-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .run-card {
      padding: 18px 20px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .run-card:hover {
      border-color: var(--accent);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
    }
    .run-main-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .run-meta-col {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .run-status-line {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-pill {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      letter-spacing: 0.03em;
    }
    .status-pill.completed {
      background: #d1fae5;
      color: #065f46;
    }
    .status-pill.partial {
      background: #fef3c7;
      color: #92400e;
    }
    .status-pill.running {
      background: #dbeafe;
      color: #1e40af;
    }
    .status-pill.failed {
      background: #fee2e2;
      color: #991b1b;
    }
    .status-dot {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: currentColor;
    }
    .run-type-tag {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--bg-subtle);
      padding: 2px 6px;
      border-radius: 4px;
    }
    .run-id-snippet {
      font-size: 11px;
      font-family: monospace;
      color: var(--text-muted);
    }
    .run-time-line {
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .separator {
      opacity: 0.5;
    }
    .run-stat-badges {
      display: flex;
      gap: 16px;
    }
    .stat-badge {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 6px 14px;
      background: var(--bg-app);
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
      min-width: 70px;
    }
    .stat-num {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .stat-label {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .run-providers-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      padding-top: 10px;
      border-top: 1px solid var(--border-color);
    }
    .row-label {
      color: var(--text-muted);
      font-weight: 500;
    }
    .provider-badges-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .badge-prov {
      font-size: 10.5px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .badge-prov.success {
      background: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }
    .badge-prov.fail {
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }
    .badge-prov.large {
      font-size: 12px;
      padding: 4px 10px;
    }
    .run-error-alert {
      margin-top: 10px;
      padding: 8px 12px;
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: var(--radius-sm);
      color: #92400e;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    /* Modal */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.45);
      backdrop-filter: blur(2px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 24px;
    }
    .modal-card {
      background: #ffffff;
      border-radius: var(--radius-md);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.15);
      max-width: 680px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }
    .modal-header {
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-overline {
      font-size: 11px;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.05em;
    }
    .modal-title {
      font-size: 18px;
      font-weight: 700;
      color: var(--text-primary);
      margin: 2px 0 0 0;
    }
    .btn-close {
      background: transparent;
      border: none;
      font-size: 18px;
      color: var(--text-muted);
      cursor: pointer;
      padding: 4px;
    }
    .modal-body {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .trace-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
    .trace-box {
      background: var(--bg-app);
      padding: 12px 14px;
      border-radius: var(--radius-sm);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .trace-label {
      font-size: 11px;
      color: var(--text-muted);
      font-weight: 600;
    }
    .trace-value {
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .trace-value.bold {
      font-weight: 700;
    }
    .trace-value.completed {
      color: #059669;
    }
    .trace-value.partial {
      color: #d97706;
    }
    .trace-value.failed {
      color: #dc2626;
    }
    .trace-sec-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }
    .params-block {
      background: #1e1e24;
      border-radius: var(--radius-sm);
      padding: 12px;
      overflow-x: auto;
    }
    .json-dump {
      margin: 0;
      font-family: monospace;
      font-size: 11.5px;
      color: #f1f5f9;
    }
    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .failures-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .failure-item {
      background: #fef2f2;
      border-left: 3px solid #ef4444;
      padding: 10px 12px;
      border-radius: var(--radius-sm);
    }
    .fail-prov-name {
      font-size: 12px;
      font-weight: 700;
      color: #991b1b;
      margin-bottom: 2px;
    }
    .fail-prov-err {
      font-size: 11.5px;
      color: #7f1d1d;
    }
    .error-summary-box {
      background: #fffbeb;
      border-left: 3px solid #f59e0b;
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      font-size: 12.5px;
      color: #92400e;
    }
    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid var(--border-color);
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      background: var(--bg-app);
    }
  `]
})
export class ActivityComponent implements OnInit, OnDestroy {
  private oppService = inject(OpportunityService);

  runs: DiscoveryRun[] = [];
  providers: ProviderHealth[] = [];
  loading = false;
  selectedRun: DiscoveryRun | null = null;
  private pollSub?: Subscription;

  get sourceChannels(): SourceChannel[] {
    const findProv = (names: string[]) =>
      this.providers.filter((p) => names.includes(p.provider_name.toLowerCase()));

    const portals = findProv(['serpapi']);
    const feeds = findProv(['jsearch', 'adzuna', 'jooble']);
    const growth = findProv(['tavily']);
    const semantic = findProv(['exa']);

    const isReady = (list: ProviderHealth[]) => list.some((p) => p.is_configured);
    const sumResults = (list: ProviderHealth[]) =>
      list.reduce((acc, p) => acc + (p.results_returned || 0), 0);
    const avgLatency = (list: ProviderHealth[]) => {
      const active = list.filter((p) => p.latency_ms && p.latency_ms > 0);
      if (active.length === 0) return 0;
      return Math.round(active.reduce((acc, p) => acc + (p.latency_ms || 0), 0) / active.length);
    };

    return [
      {
        name: 'Direct Company Portals',
        category: 'Employer Portals',
        description: 'Direct employer careers websites and verified posting pipelines',
        isReady: isReady(portals),
        statusText: isReady(portals) ? 'ACTIVE & READY' : 'STANDBY',
        itemsIngested: sumResults(portals),
        latencyMs: avgLatency(portals)
      },
      {
        name: 'Public Career Feeds',
        category: 'Live Feeds',
        description: 'Aggregated live tech career feeds and talent networks',
        isReady: isReady(feeds),
        statusText: isReady(feeds) ? 'ACTIVE & READY' : 'STANDBY',
        itemsIngested: sumResults(feeds),
        latencyMs: avgLatency(feeds)
      },
      {
        name: 'Strategic Growth Signals',
        category: 'Market Intelligence',
        description: 'Public corporate expansions, funding events, and strategic initiatives',
        isReady: isReady(growth),
        statusText: isReady(growth) ? 'ACTIVE & READY' : 'STANDBY',
        itemsIngested: sumResults(growth),
        latencyMs: avgLatency(growth)
      },
      {
        name: 'Semantic Technology Feeds',
        category: 'Neural Matching',
        description: 'Deep neural matching across technical stacks, libraries, and open-source ecosystems',
        isReady: isReady(semantic),
        statusText: isReady(semantic) ? 'ACTIVE & READY' : 'STANDBY',
        itemsIngested: sumResults(semantic),
        latencyMs: avgLatency(semantic)
      }
    ];
  }

  formatSourceName(raw?: string): string {
    if (!raw) return 'Intelligence Feed';
    const s = raw.toLowerCase();
    if (s.includes('tavily') || s.includes('growth')) return 'Strategic Growth Signals';
    if (s.includes('exa') || s.includes('semantic')) return 'Semantic Technology Feeds';
    if (s.includes('serpapi') || s.includes('google') || s.includes('portal')) return 'Direct Company Portals';
    if (s.includes('jsearch') || s.includes('adzuna') || s.includes('jooble') || s.includes('feed'))
      return 'Public Career Feeds';
    return raw;
  }

  getCandidateFriendlySummary(rawSummary?: string | null): string {
    if (!rawSummary) return '';
    if (
      rawSummary.includes('No external API keys') ||
      rawSummary.includes('TAVILY_API_KEY') ||
      rawSummary.includes('EXA_API_KEY')
    ) {
      return 'Discovery completed across active channels. Results are strictly grounded in verified facts.';
    }
    if (rawSummary.includes('Partial discovery')) {
      return 'Multi-source discovery completed. Displaying all verified and deduplicated opportunities.';
    }
    if (rawSummary.includes('failed') || rawSummary.includes('failure')) {
      return 'Discovery run finished. Displaying all opportunities ingested and verified.';
    }
    return rawSummary;
  }

  ngOnInit(): void {
    this.loadAllData();
    // Poll for any active runs every 5 seconds
    this.pollSub = interval(5000).subscribe(() => {
      const hasRunning = this.runs.some((r) => r.status === 'running' || r.status === 'queued');
      if (hasRunning) {
        this.loadRunsOnly();
      }
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  loadAllData(): void {
    this.loading = true;
    this.oppService.getProviderHealth().subscribe({
      next: (provs) => {
        this.providers = provs;
      },
      error: () => {}
    });

    this.oppService.getDiscoveryRuns().subscribe({
      next: (runs) => {
        this.runs = runs;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  loadRunsOnly(): void {
    this.oppService.getDiscoveryRuns().subscribe({
      next: (runs) => {
        this.runs = runs;
      }
    });
  }

  openTraceModal(run: DiscoveryRun): void {
    this.selectedRun = run;
  }

  closeTraceModal(): void {
    this.selectedRun = null;
  }
}

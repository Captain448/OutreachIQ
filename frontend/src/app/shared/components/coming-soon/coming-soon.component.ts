import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-coming-soon',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="coming-soon-wrapper">
      <div class="status-indicator">Stage 2 Milestone</div>
      <h2 class="section-title">{{ featureName }}</h2>
      <p class="section-desc">{{ description }}</p>

      <div class="iq-card info-card">
        <div class="card-heading">
          <svg class="info-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <h4>Architectural Readiness</h4>
        </div>
        <p class="info-text">
          OutReachIQ follows an evidence-grounded research architecture. The underlying foundation (Candidate Profile Intelligence, multi-resume parsing, and LLM provider abstractions) is active in this phase.
        </p>
        <div class="planned-capabilities">
          <div class="cap-item">
            <span class="cap-dot"></span>
            <span>{{ capabilityOne }}</span>
          </div>
          <div class="cap-item">
            <span class="cap-dot"></span>
            <span>{{ capabilityTwo }}</span>
          </div>
          <div class="cap-item">
            <span class="cap-dot"></span>
            <span>{{ capabilityThree }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .coming-soon-wrapper {
      max-width: 680px;
      margin: 40px auto;
      text-align: left;
    }
    .status-indicator {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      padding: 3px 10px;
      border-radius: 9999px;
      margin-bottom: 12px;
    }
    .section-title {
      font-size: 22px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 8px;
    }
    .section-desc {
      font-size: 14px;
      color: var(--text-secondary);
      margin-bottom: 24px;
      line-height: 1.6;
    }
    .info-card {
      border-left: 3px solid var(--accent);
    }
    .card-heading {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
    }
    .info-icon {
      width: 18px;
      height: 18px;
      color: var(--accent);
    }
    .card-heading h4 {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .info-text {
      font-size: 13.5px;
      color: var(--text-secondary);
      margin-bottom: 16px;
      line-height: 1.5;
    }
    .planned-capabilities {
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: var(--bg-app);
      padding: 14px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }
    .cap-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-secondary);
    }
    .cap-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent);
    }
  `]
})
export class ComingSoonComponent {
  @Input() featureName: string = 'Upcoming Feature';
  @Input() description: string = 'This module will be connected in Stage 2.';
  @Input() capabilityOne: string = 'Multi-source discovery and company indexing';
  @Input() capabilityTwo: string = 'Evidence-backed fit scoring without hallucinations';
  @Input() capabilityThree: string = 'User-supervised outreach sequencing';
}

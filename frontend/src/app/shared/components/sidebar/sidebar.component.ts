import { Component, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside class="sidebar">
      <!-- App Brand -->
      <div class="brand">
        <div class="brand-main">
          <div class="brand-badge">IQ</div>
          <div class="brand-text">
            <span class="brand-name">OutReachIQ</span>
            <span class="brand-tag">Autonomous Career Agent</span>
          </div>
        </div>
        <button class="mobile-close-btn" (click)="onNavClick()" aria-label="Close navigation menu">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <!-- Navigation Links -->
      <nav class="nav-menu">
        <div class="nav-section-title">PLATFORM</div>
        
        <a routerLink="/dashboard" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          <span>Dashboard</span>
        </a>

        <a routerLink="/profile" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span>Profile</span>
        </a>

        <a routerLink="/resumes" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span>Resumes</span>
        </a>

        <div class="nav-section-title" style="margin-top: 22px;">EXPLORATION</div>

        <a routerLink="/opportunities" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>
          </svg>
          <span>Opportunities</span>
        </a>

        <a routerLink="/skill-gap" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
          </svg>
          <span>Skill Gap & Roadmap</span>
        </a>

        <a routerLink="/learning" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          <span>Learning & Projects</span>
        </a>

        <a routerLink="/outreach" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
            <polyline points="22,6 12,13 2,6"></polyline>
          </svg>
          <span>Outreach</span>
        </a>

        <a routerLink="/activity" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          <span>Activity</span>
        </a>

        <div class="nav-section-title" style="margin-top: 22px;">SYSTEM</div>

        <a routerLink="/settings" routerLinkActive="active" (click)="onNavClick()" class="nav-item">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
          <span>Settings</span>
        </a>
      </nav>

      <!-- User footer -->
      <div class="user-footer" *ngIf="authService.currentUser$ | async as user">
        <div class="user-info">
          <div class="user-avatar">{{ (user.full_name || user.email).charAt(0).toUpperCase() }}</div>
          <div class="user-meta">
            <span class="user-name">{{ user.full_name || 'Candidate' }}</span>
            <span class="user-email">{{ user.email }}</span>
          </div>
        </div>
        <button class="btn-logout" (click)="onLogout()" title="Sign out" aria-label="Sign out">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
        </button>
      </div>
    </aside>
  `,
  styles: [`
    .sidebar {
      width: 250px;
      min-width: 250px;
      height: 100vh;
      background: #ffffff;
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      padding: 18px 20px 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-color);
    }

    .brand-main {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-badge {
      width: 34px;
      height: 34px;
      background: var(--primary);
      color: #ffffff;
      font-weight: 700;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-sm);
      letter-spacing: -0.02em;
      box-shadow: 0 1px 2px rgba(30, 58, 138, 0.2);
    }

    .brand-text {
      display: flex;
      flex-direction: column;
    }

    .brand-name {
      font-weight: 700;
      font-size: 15px;
      letter-spacing: -0.02em;
      color: var(--text-primary);
      line-height: 1.2;
    }

    .brand-tag {
      font-size: 10.5px;
      color: var(--text-muted);
      font-weight: 500;
      letter-spacing: 0.01em;
    }

    .mobile-close-btn {
      display: none;
      background: none;
      border: none;
      color: var(--text-secondary);
      padding: 6px;
      border-radius: var(--radius-xs);
      align-items: center;
      justify-content: center;
    }

    .mobile-close-btn:hover {
      background: var(--bg-subtle);
      color: var(--text-primary);
    }

    .nav-menu {
      flex: 1;
      padding: 16px 12px;
      overflow-y: auto;
    }

    .nav-section-title {
      font-size: 10px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.06em;
      padding: 0 10px;
      margin-bottom: 6px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 13.5px;
      font-weight: 500;
      border-radius: var(--radius-sm);
      margin-bottom: 3px;
      transition: all 0.15s ease;
    }

    .nav-item:hover {
      background: var(--bg-subtle);
      color: var(--text-primary);
    }

    .nav-item.active {
      background: var(--primary-light);
      color: var(--accent);
      font-weight: 600;
    }

    .nav-icon {
      width: 17px;
      height: 17px;
      flex-shrink: 0;
    }

    .user-footer {
      padding: 14px 16px;
      border-top: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #fafafa;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;
      overflow: hidden;
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--primary);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 13px;
      flex-shrink: 0;
    }

    .user-meta {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .user-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-primary);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }

    .user-email {
      font-size: 11.5px;
      color: var(--text-muted);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }

    .btn-logout {
      background: none;
      border: none;
      color: var(--text-muted);
      padding: 6px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }

    .btn-logout:hover {
      color: var(--danger-text);
      background: var(--danger-bg);
    }

    @media (max-width: 768px) {
      .sidebar {
        position: fixed;
        top: 0;
        bottom: 0;
        left: 0;
        z-index: 1000;
        width: 270px;
        min-width: 270px;
        transform: translateX(-100%);
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: none;
      }

      :host.mobile-open .sidebar,
      .sidebar.mobile-open {
        transform: translateX(0);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.35);
      }

      .mobile-close-btn {
        display: flex;
      }
    }
  `]
})
export class SidebarComponent {
  @Output() navItemClicked = new EventEmitter<void>();
  authService = inject(AuthService);

  onNavClick(): void {
    this.navItemClicked.emit();
  }

  onLogout(): void {
    this.authService.logout();
  }
}

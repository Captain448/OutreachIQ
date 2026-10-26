import { Component, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  template: `
    <div class="auth-page">
      <div class="auth-card">
        <!-- Brand Header -->
        <div class="auth-brand">
          <div class="brand-badge">IQ</div>
          <h2>OutReachIQ</h2>
          <p class="subtitle">Autonomous AI Career & Opportunity Agent</p>
        </div>

        <!-- Notification Banner -->
        <div *ngIf="errorMessage" class="error-banner">
          {{ errorMessage }}
        </div>

        <form [formGroup]="form" (ngSubmit)="onSubmit()">
          <div class="form-group">
            <label class="form-label" for="email">Work / Professional Email</label>
            <input
              id="email"
              type="email"
              formControlName="email"
              class="form-control"
              placeholder="name@domain.com"
              autocomplete="email"
            />
            <div *ngIf="form.get('email')?.touched && form.get('email')?.invalid" class="field-error">
              Valid email is required.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="password">Password</label>
            <div class="password-input-wrapper">
              <input
                id="password"
                [type]="showPassword ? 'text' : 'password'"
                formControlName="password"
                class="form-control password-input"
                placeholder="••••••••"
                autocomplete="current-password"
              />
              <button
                type="button"
                class="eye-toggle-btn"
                (click)="togglePasswordVisibility()"
                [attr.aria-label]="showPassword ? 'Hide password' : 'Show password'"
                [title]="showPassword ? 'Hide password' : 'Show password'"
              >
                <!-- SVG Icon for Eye when password hidden -->
                <svg *ngIf="!showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
                <!-- SVG Icon for Eye-Off when password shown -->
                <svg *ngIf="showPassword" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              </button>
            </div>
            <div *ngIf="form.get('password')?.touched && form.get('password')?.invalid" class="field-error">
              Password must be at least 6 characters.
            </div>
          </div>

          <button
            type="submit"
            class="btn btn-primary btn-submit"
            [disabled]="form.invalid || loading"
          >
            Login
          </button>
        </form>

        <div class="auth-footer">
          <span>Don't have an account?</span>
          <a routerLink="/register" class="link-auth">Create profile</a>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-app);
      padding: 24px;
    }
    @media (max-width: 480px) {
      .auth-page {
        padding: 16px;
      }
      .auth-card {
        padding: 28px 20px !important;
      }
    }
    .auth-card {
      width: 100%;
      max-width: 400px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-md);
      padding: 36px 32px;
    }
    .auth-brand {
      text-align: center;
      margin-bottom: 28px;
    }
    .brand-badge {
      width: 40px;
      height: 40px;
      margin: 0 auto 12px auto;
      background: var(--primary);
      color: white;
      font-weight: 700;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-sm);
    }
    .auth-brand h2 {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-primary);
    }
    .subtitle {
      font-size: 13px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
    .error-banner {
      background: var(--danger-bg);
      color: var(--danger-text);
      border: 1px solid var(--danger-border);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      font-size: 13px;
      margin-bottom: 18px;
    }
    .password-input-wrapper {
      position: relative;
      display: flex;
      align-items: center;
      width: 100%;
    }
    .password-input {
      width: 100%;
      padding-right: 42px !important;
    }
    .eye-toggle-btn {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      background: none;
      border: none;
      cursor: pointer;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 6px;
      border-radius: var(--radius-sm);
      transition: color 0.15s ease, background 0.15s ease;
    }
    .eye-toggle-btn:hover {
      color: var(--text-primary);
      background: var(--bg-subtle);
    }
    .btn-submit {
      width: 100%;
      padding: 10px;
      margin-top: 8px;
      font-size: 14px;
      cursor: pointer;
    }
    .field-error {
      color: var(--danger-text);
      font-size: 12px;
      margin-top: 4px;
    }
    .auth-footer {
      margin-top: 24px;
      text-align: center;
      font-size: 13px;
      color: var(--text-secondary);
      display: flex;
      justify-content: center;
      gap: 6px;
    }
    .link-auth {
      color: var(--accent);
      text-decoration: none;
      font-weight: 500;
    }
    .link-auth:hover {
      text-decoration: underline;
    }
  `]
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  loading = false;
  errorMessage = '';
  showPassword = false;

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
    this.cdr.markForCheck();
  }

  onSubmit(): void {
    if (this.form.invalid || this.loading) return;

    this.loading = true;
    this.errorMessage = '';
    this.cdr.markForCheck();

    const { email, password } = this.form.value;
    this.authService.login({ email: email!.trim(), password: password! }).subscribe({
      next: () => {
        this.loading = false;
        this.cdr.markForCheck();
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading = false;
        const detail = err?.error?.detail;
        if (err.status === 401 || (typeof detail === 'string' && detail.toLowerCase().includes('incorrect'))) {
          this.errorMessage = 'Incorrect email or password. Please check your credentials and try again.';
        } else if (typeof detail === 'string') {
          this.errorMessage = detail;
        } else {
          this.errorMessage = 'Incorrect email or password. Please try again.';
        }
        this.cdr.markForCheck();
      }
    });
  }
}

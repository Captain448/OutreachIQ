import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { ResumeService } from '../../core/services/resume.service';
import { Resume, ParsingStatus } from '../../core/models/resume.model';

@Component({
  selector: 'app-resumes',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="resumes-page">
      <!-- Header -->
      <header class="page-header">
        <div>
          <h1 class="page-title">Resume & Career Portfolio Management</h1>
          <p class="page-subtitle">
            Manage tailored resumes for distinct career directions with transparent, grounded parsing
          </p>
        </div>
      </header>

      <!-- Upload Section -->
      <div class="iq-card upload-card">
        <h3 class="card-title">Upload New Resume</h3>
        <p class="card-desc">Accepts PDF (.pdf) and Microsoft Word (.docx). Text is parsed deterministically.</p>

        <div class="upload-form-grid">
          <div class="form-group">
            <label class="form-label">Resume Title / Direction</label>
            <input
              type="text"
              [(ngModel)]="uploadTitle"
              [disabled]="uploading"
              class="form-control"
              placeholder="e.g. AI/ML Engineering Resume"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Target Role / Category</label>
            <input
              type="text"
              [(ngModel)]="uploadTargetRole"
              [disabled]="uploading"
              class="form-control"
              placeholder="e.g. Machine Learning Engineer"
            />
          </div>

          <div class="form-group file-picker-group">
            <label class="form-label">Select File</label>
            <input
              type="file"
              #fileInput
              (change)="onFileSelected($event)"
              [disabled]="uploading"
              accept=".pdf,.docx"
              class="file-input"
            />
            <div class="file-picked-name" *ngIf="selectedFile">
              📄 {{ selectedFile.name }} ({{ (selectedFile.size / 1024).toFixed(0) }} KB)
            </div>
          </div>
        </div>

        <div class="upload-action-row">
          <label class="pref-checkbox">
            <input type="checkbox" [(ngModel)]="uploadIsPreferred" [disabled]="uploading" />
            <span>Set as primary / preferred resume for general matching</span>
          </label>

          <button
            type="button"
            class="btn btn-primary"
            (click)="submitUpload(fileInput)"
            [disabled]="!selectedFile || uploading"
          >
            <span *ngIf="!uploading">Upload & Parse Evidence</span>
            <span *ngIf="uploading">Parsing document...</span>
          </button>
        </div>

        <div *ngIf="uploadError" class="upload-error">
          {{ uploadError }}
        </div>
      </div>

      <!-- Resumes List -->
      <div class="resumes-list-header">
        <h2 class="subheading">Uploaded Resumes ({{ resumes.length }})</h2>
        <span class="info-tag">Deterministic extraction active — no fabricated skills</span>
      </div>

      <div *ngIf="deleteError" class="upload-error" style="margin-bottom: 16px;">
        ⚠️ {{ deleteError }}
      </div>

      <!-- Loading State -->
      <div *ngIf="loadingResumes" class="iq-card loading-card">
        <div class="spinner-inline"></div>
        <span>Loading your uploaded resumes...</span>
      </div>

      <!-- Error State with Retry -->
      <div *ngIf="!loadingResumes && loadError" class="iq-card error-card">
        <div class="error-msg-box">
          <span class="error-icon">⚠️</span>
          <span class="error-text">{{ loadError }}</span>
        </div>
        <button class="btn btn-secondary btn-sm" (click)="loadResumes()">
          Retry Loading Resumes
        </button>
      </div>

      <!-- Genuine Empty State -->
      <div *ngIf="!loadingResumes && !loadError && resumes.length === 0" class="empty-resumes">
        <p>No resumes uploaded yet. Upload a tailored resume above to begin.</p>
      </div>

      <div class="resumes-grid" *ngIf="!loadingResumes && !loadError && resumes.length > 0">
        <div *ngFor="let resume of resumes" class="iq-card resume-card">
          <!-- Card Header -->
          <div class="resume-card-header">
            <div class="header-left">
              <div class="title-row">
                <h3 *ngIf="editingResumeId !== resume.id" class="resume-title">{{ resume.title }}</h3>
                
                <!-- Inline Rename Form -->
                <div *ngIf="editingResumeId === resume.id" class="rename-box">
                  <input
                    type="text"
                    [(ngModel)]="renameTitle"
                    class="form-control"
                    style="font-size: 13px; padding: 4px 8px;"
                  />
                  <input
                    type="text"
                    [(ngModel)]="renameRole"
                    placeholder="Role"
                    class="form-control"
                    style="font-size: 13px; padding: 4px 8px; width: 130px;"
                  />
                  <button class="btn btn-primary btn-sm" (click)="saveRename(resume.id)">Save</button>
                  <button class="btn btn-secondary btn-sm" (click)="editingResumeId = null">Cancel</button>
                </div>

                <span *ngIf="resume.is_preferred" class="badge badge-preferred">Primary</span>
                <span *ngIf="!resume.is_active" class="badge badge-unverified">Inactive</span>
              </div>
              <div class="meta-row">
                <span>Target Direction: <strong>{{ resume.target_role }}</strong></span>
                <span>•</span>
                <span>{{ resume.original_filename }}</span>
                <span>•</span>
                <span>{{ ((resume.file_size || 0) / 1024).toFixed(0) }} KB</span>
              </div>
            </div>

            <!-- Header Actions -->
            <div class="header-actions">
              <button
                *ngIf="!resume.is_preferred"
                class="btn btn-secondary btn-sm"
                (click)="makePreferred(resume)"
                title="Make Primary"
              >
                Set Primary
              </button>
              <button
                class="btn btn-secondary btn-sm"
                (click)="startRename(resume)"
                *ngIf="editingResumeId !== resume.id"
              >
                Rename
              </button>
              <button
                class="btn btn-danger-outline btn-sm"
                (click)="deleteResume(resume.id)"
                [disabled]="deletingResumeId === resume.id"
                title="Delete resume"
              >
                {{ deletingResumeId === resume.id ? 'Deleting...' : 'Delete' }}
              </button>
            </div>
          </div>

          <!-- Grounded Extraction Metrics -->
          <div class="confidence-bar-row">
            <div class="conf-info">
              <span class="conf-label">Parsing Confidence:</span>
              <span class="conf-score" [class.conf-high]="(resume.parsing_confidence || 0) >= 0.8" [class.conf-low]="(resume.parsing_confidence || 0) < 0.8">
                {{ ((resume.parsing_confidence || 0) * 100).toFixed(0) }}% ({{ (resume.parsing_status || 'PENDING') | uppercase }})
              </span>
            </div>
            <span class="conf-note">{{ resume.parsing_notes }}</span>
          </div>

          <!-- Extracted Skills Section -->
          <div class="extracted-skills-box">
            <div class="box-title">
              Verified Skills Extracted ({{ (resume.extracted_skills?.length || 0) }})
            </div>
            <div class="skills-wrap" *ngIf="(resume.extracted_skills?.length || 0) > 0; else noSkills">
              <span
                *ngFor="let s of resume.extracted_skills"
                class="badge badge-verified skill-tag"
                [title]="s.evidence || 'Extracted from resume'"
              >
                {{ s.name }}
              </span>
            </div>
            <ng-template #noSkills>
              <span class="text-muted" style="font-size: 12.5px;">No standard technical keywords detected.</span>
            </ng-template>
          </div>

          <!-- Extracted Sections Preview -->
          <div class="extracted-preview-grid" *ngIf="(resume.extracted_experience?.length || 0) > 0 || (resume.extracted_education?.length || 0) > 0">
            <div class="preview-col" *ngIf="(resume.extracted_experience?.length || 0) > 0">
              <span class="col-title">Extracted Experience Snippets:</span>
              <ul class="preview-list">
                <li *ngFor="let exp of (resume.extracted_experience || []).slice(0, 3)">
                  {{ exp.raw_entry }}
                </li>
              </ul>
            </div>
            <div class="preview-col" *ngIf="(resume.extracted_education?.length || 0) > 0">
              <span class="col-title">Extracted Education Snippets:</span>
              <ul class="preview-list">
                <li *ngFor="let edu of (resume.extracted_education || []).slice(0, 2)">
                  {{ edu.raw_entry }}
                </li>
              </ul>
            </div>
          </div>

          <!-- Bottom View Text Toggle -->
          <div class="text-toggle-row">
            <button
              class="btn-text-link"
              (click)="toggleTextView(resume.id)"
            >
              {{ expandedTextId === resume.id ? 'Hide Parsed Text ▲' : 'View Raw Parsed Text ▼' }}
            </button>
            <span class="active-toggle">
              <label class="switch-label">
                <input
                  type="checkbox"
                  [checked]="resume.is_active"
                  (change)="toggleActive(resume)"
                />
                <span>Active for matching</span>
              </label>
            </span>
          </div>

          <div *ngIf="expandedTextId === resume.id" class="parsed-raw-text">
            <pre>{{ resume.parsed_text || 'No text extracted.' }}</pre>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .resumes-page {
      padding: 28px;
      max-width: 1140px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .resumes-page {
        padding: 16px;
      }
    }
    .page-header {
      margin-bottom: 24px;
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
    .upload-card {
      margin-bottom: 32px;
      border: 1px solid var(--border-color);
      box-shadow: var(--shadow-card);
    }
    .card-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .card-desc {
      font-size: 12.5px;
      color: var(--text-muted);
      margin-bottom: 16px;
    }
    .upload-form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1.2fr;
      gap: 16px;
    }
    @media (max-width: 768px) {
      .upload-form-grid {
        grid-template-columns: 1fr;
      }
    }
    .file-input {
      display: block;
      width: 100%;
      font-size: 12.5px;
      padding: 6px;
    }
    .file-picked-name {
      margin-top: 4px;
      font-size: 12px;
      color: var(--accent);
      font-weight: 500;
    }
    .upload-action-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--border-color);
      gap: 12px;
      flex-wrap: wrap;
    }
    @media (max-width: 640px) {
      .upload-action-row {
        flex-direction: column;
        align-items: stretch;
      }
    }
    .pref-checkbox {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-secondary);
      cursor: pointer;
    }
    .upload-error {
      margin-top: 12px;
      background: var(--danger-bg);
      color: var(--danger-text);
      padding: 8px 12px;
      border-radius: var(--radius-sm);
      font-size: 12.5px;
      border: 1px solid var(--danger-border);
    }
    .resumes-list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .subheading {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .info-tag {
      font-size: 12px;
      color: var(--text-muted);
    }
    .empty-resumes {
      padding: 40px;
      text-align: center;
      background: #ffffff;
      border: 1px dashed var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: 13.5px;
    }
    .loading-card {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 24px;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: 13.5px;
    }
    .spinner-inline {
      width: 18px;
      height: 18px;
      border: 2px solid var(--border-color);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .error-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      border-radius: var(--radius-md);
      margin-bottom: 16px;
    }
    .error-msg-box {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--danger-text);
      font-size: 13.5px;
    }
    .error-icon {
      font-size: 16px;
    }
    .error-text {
      font-weight: 500;
    }
    .resumes-grid {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .resume-card {
      padding: 20px;
      background: #ffffff;
    }
    .resume-card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .resume-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .rename-box {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .meta-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
      color: var(--text-muted);
      margin-top: 4px;
    }
    .header-actions {
      display: flex;
      gap: 8px;
    }
    .confidence-bar-row {
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12.5px;
      margin-bottom: 14px;
    }
    .conf-score {
      font-weight: 600;
      margin-left: 6px;
    }
    .conf-high {
      color: var(--success-text);
    }
    .conf-low {
      color: var(--warning-text);
    }
    .conf-note {
      color: var(--text-secondary);
      font-size: 12px;
    }
    .extracted-skills-box {
      margin-bottom: 14px;
    }
    .box-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }
    .skills-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .skill-tag {
      cursor: help;
    }
    .extracted-preview-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      margin-bottom: 12px;
    }
    @media (max-width: 768px) {
      .extracted-preview-grid {
        grid-template-columns: 1fr;
      }
    }
    .col-title {
      display: block;
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }
    .preview-list {
      padding-left: 16px;
      font-size: 12px;
      color: var(--text-secondary);
    }
    .preview-list li {
      margin-bottom: 3px;
    }
    .text-toggle-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 10px;
      border-top: 1px solid var(--border-color);
    }
    .btn-text-link {
      background: none;
      border: none;
      color: var(--accent);
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
    }
    .switch-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12.5px;
      color: var(--text-secondary);
      cursor: pointer;
    }
    .parsed-raw-text {
      margin-top: 10px;
      background: #1e293b;
      color: #f1f5f9;
      padding: 14px;
      border-radius: var(--radius-sm);
      max-height: 250px;
      overflow-y: auto;
      font-size: 12px;
    }
    .parsed-raw-text pre {
      white-space: pre-wrap;
      font-family: Consolas, Monaco, monospace;
    }
  `]
})
export class ResumesComponent implements OnInit {
  private resumeService = inject(ResumeService);
  private cdr = inject(ChangeDetectorRef);

  resumes: Resume[] = [];
  loadingResumes = false;
  loadError: string | null = null;
  deletingResumeId: string | null = null;
  deleteError: string | null = null;

  selectedFile: File | null = null;
  uploadTitle = '';
  uploadTargetRole = 'General';
  uploadIsPreferred = false;
  uploading = false;
  uploadError = '';

  editingResumeId: string | null = null;
  renameTitle = '';
  renameRole = '';

  expandedTextId: string | null = null;

  ngOnInit(): void {
    this.loadResumes();
  }

  loadResumes(): void {
    this.loadingResumes = true;
    this.loadError = null;
    this.cdr.markForCheck();

    this.resumeService
      .getResumes()
      .pipe(
        finalize(() => {
          this.loadingResumes = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (res) => {
          this.resumes = (res || []).map((item) => this.normalizeResume(item));
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loadError =
            err?.error?.detail ||
            err?.message ||
            'Unable to load resumes. Please check your connection and retry.';
          this.cdr.markForCheck();
        }
      });
  }

  private normalizeResume(item: any): Resume {
    if (!item) return {} as Resume;
    return {
      ...item,
      extracted_skills: Array.isArray(item.extracted_skills) ? item.extracted_skills : [],
      extracted_experience: Array.isArray(item.extracted_experience) ? item.extracted_experience : [],
      extracted_education: Array.isArray(item.extracted_education) ? item.extracted_education : [],
      extracted_projects: Array.isArray(item.extracted_projects) ? item.extracted_projects : [],
      file_size: typeof item.file_size === 'number' ? item.file_size : 0,
      parsing_confidence: typeof item.parsing_confidence === 'number' ? item.parsing_confidence : 0,
      parsing_status: item.parsing_status || 'pending',
      is_preferred: Boolean(item.is_preferred),
      is_active: item.is_active !== undefined ? Boolean(item.is_active) : true,
      title: item.title || item.original_filename || 'Untitled Resume',
      target_role: item.target_role || 'General'
    };
  }

  onFileSelected(event: any): void {
    const file = event.target.files?.[0];
    if (file) {
      this.selectedFile = file;
      if (!this.uploadTitle) {
        // Remove extension for default title
        const dotIndex = file.name.lastIndexOf('.');
        this.uploadTitle = dotIndex > 0 ? file.name.substring(0, dotIndex) : file.name;
      }
    }
  }

  submitUpload(fileInput: HTMLInputElement): void {
    if (!this.selectedFile || this.uploading) return;

    this.uploading = true;
    this.uploadError = '';
    this.cdr.markForCheck();

    this.resumeService.uploadResume(
      this.selectedFile,
      this.uploadTitle,
      this.uploadTargetRole,
      this.uploadIsPreferred
    ).subscribe({
      next: () => {
        this.uploading = false;
        this.selectedFile = null;
        this.uploadTitle = '';
        this.uploadTargetRole = 'General';
        this.uploadIsPreferred = false;
        fileInput.value = '';
        this.loadResumes();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.uploading = false;
        this.uploadError = err.error?.detail || 'Failed to upload and parse resume.';
        this.cdr.markForCheck();
      }
    });
  }

  makePreferred(resume: Resume): void {
    this.resumeService.updateResume(resume.id, { is_preferred: true }).subscribe({
      next: () => this.loadResumes()
    });
  }

  toggleActive(resume: Resume): void {
    this.resumeService.updateResume(resume.id, { is_active: !resume.is_active }).subscribe({
      next: () => this.loadResumes()
    });
  }

  startRename(resume: Resume): void {
    this.editingResumeId = resume.id;
    this.renameTitle = resume.title;
    this.renameRole = resume.target_role;
    this.cdr.markForCheck();
  }

  saveRename(resumeId: string): void {
    this.resumeService.updateResume(resumeId, {
      title: this.renameTitle,
      target_role: this.renameRole
    }).subscribe({
      next: () => {
        this.editingResumeId = null;
        this.loadResumes();
        this.cdr.markForCheck();
      }
    });
  }

  deleteResume(resumeId: string): void {
    if (confirm('Are you sure you want to delete this resume?')) {
      this.deletingResumeId = resumeId;
      this.deleteError = null;
      this.cdr.markForCheck();
      this.resumeService.deleteResume(resumeId).subscribe({
        next: () => {
          this.deletingResumeId = null;
          this.loadResumes();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.deletingResumeId = null;
          this.deleteError = err?.error?.detail || 'Failed to delete resume.';
          this.cdr.markForCheck();
        }
      });
    }
  }

  toggleTextView(resumeId: string): void {
    this.expandedTextId = this.expandedTextId === resumeId ? null : resumeId;
    this.cdr.markForCheck();
  }
}

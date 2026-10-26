import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { finalize } from 'rxjs';
import { ProfileService } from '../../core/services/profile.service';
import { IntelligenceService } from '../../core/services/intelligence.service';
import { Profile, Education, WorkExperience, Project, Skill, SkillStatus, CustomLink } from '../../core/models/profile.model';
import { CandidateIntelligenceRepresentation } from '../../core/models/intelligence.model';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="profile-page">
      <!-- Header -->
      <header class="profile-header">
        <div>
          <h1 class="page-title">Candidate Career Profile</h1>
          <p class="page-subtitle">Manage your verified background, preferences, and competencies</p>
        </div>
        <div class="header-actions">
          <span *ngIf="saveSuccess" class="save-toast">✓ Changes saved successfully</span>
          <span *ngIf="errorMessage" class="save-error-toast">⚠️ {{ errorMessage }}</span>
          <button type="button" class="btn btn-primary" (click)="saveProfile()" [disabled]="saving">
            <span *ngIf="saving">Saving...</span>
            <span *ngIf="!saving && saveSuccess">✓ Saved</span>
            <span *ngIf="!saving && !saveSuccess">Save Changes</span>
          </button>
        </div>
      </header>

      <!-- Section Navigation Tabs -->
      <div class="tabs-bar">
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'basic'"
          (click)="activeTab = 'basic'"
        >
          Basic Information
        </button>
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'preferences'"
          (click)="activeTab = 'preferences'"
        >
          Career Preferences
        </button>
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'skills'"
          (click)="activeTab = 'skills'"
        >
          Skills & Evidence
        </button>
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'experience'"
          (click)="activeTab = 'experience'"
        >
          Work Experience
        </button>
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'projects'"
          (click)="activeTab = 'projects'"
        >
          Projects
        </button>
        <button
          type="button"
          class="tab-btn"
          [class.active]="activeTab === 'education'"
          (click)="activeTab = 'education'"
        >
          Education & Links
        </button>
      </div>

      <!-- Tab Content Form -->
      <form [formGroup]="form" (ngSubmit)="saveProfile()">
        
        <!-- 1. Basic Info -->
        <div *ngIf="activeTab === 'basic'" class="iq-card tab-content">
          <h3 class="section-title">Personal & Professional Identity</h3>
          <p class="section-desc">Primary contact information and candidate positioning headline.</p>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Full Name</label>
              <input type="text" formControlName="full_name" class="form-control" placeholder="e.g. Maya Patel" />
            </div>
            <div class="form-group">
              <label class="form-label">Email (Account)</label>
              <input type="text" [value]="profile?.email || ''" class="form-control" disabled style="background: var(--bg-subtle);" />
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Phone Number</label>
              <input type="text" formControlName="phone" class="form-control" placeholder="e.g. +1 (555) 234-5678" />
            </div>
            <div class="form-group">
              <label class="form-label">Location (City, Country / State)</label>
              <input type="text" formControlName="location" class="form-control" placeholder="e.g. San Francisco, CA or London, UK" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Professional Headline</label>
            <input
              type="text"
              formControlName="headline"
              class="form-control"
              placeholder="e.g. Senior Backend Engineer | Distributed Systems & High-Throughput APIs"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Candidate Bio / Professional Summary</label>
            <textarea
              formControlName="bio"
              rows="4"
              class="form-control"
              placeholder="A concise summary of your engineering philosophy, domain experience, and career trajectory..."
            ></textarea>
          </div>
        </div>

        <!-- 2. Career Preferences -->
        <div *ngIf="activeTab === 'preferences'" class="iq-card tab-content" formGroupName="preferences">
          <h3 class="section-title">Career Preferences & Opportunity Parameters</h3>
          <p class="section-desc">Defines targeting boundaries for future autonomous matching.</p>

          <div class="form-group">
            <label class="form-label">Desired Roles (comma-separated)</label>
            <input
              type="text"
              formControlName="desired_roles_raw"
              class="form-control"
              placeholder="e.g. Backend Engineer, Systems Software Engineer, Staff Architect"
            />
            <span class="field-hint">Comma-separated list of target positions.</span>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label class="form-label">Preferred Industries (comma-separated)</label>
              <input
                type="text"
                formControlName="preferred_industries_raw"
                class="form-control"
                placeholder="e.g. Developer Tools, Cloud Infrastructure, FinTech"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Preferred Locations (comma-separated)</label>
              <input
                type="text"
                formControlName="preferred_locations_raw"
                class="form-control"
                placeholder="e.g. Remote, San Francisco, New York, Seattle"
              />
            </div>
          </div>

          <div class="grid-3">
            <div class="form-group">
              <label class="form-label">Remote / Onsite Preference</label>
              <select formControlName="remote_preference" class="form-control">
                <option value="remote">Fully Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
                <option value="flexible">Flexible / Any</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Experience Level</label>
              <select formControlName="experience_level" class="form-control">
                <option value="entry">Entry Level</option>
                <option value="mid">Mid Level</option>
                <option value="senior">Senior Level</option>
                <option value="lead">Lead / Staff</option>
                <option value="executive">Director / Executive</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Employment Type</label>
              <select formControlName="employment_preference" class="form-control">
                <option value="full-time">Full-Time</option>
                <option value="contract">Contract / Freelance</option>
                <option value="internship">Internship</option>
                <option value="part-time">Part-Time</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 3. Skills & Evidence -->
        <div *ngIf="activeTab === 'skills'" class="iq-card tab-content">
          <div class="card-header-row">
            <div>
              <h3 class="section-title">Verified Skills & Adjacencies</h3>
              <p class="section-desc">
                OutReachIQ enforces evidence grounding. Verified skills have direct textual citations.
              </p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" (click)="addSkillItem()">
              + Add Skill
            </button>
          </div>

          <!-- Quick Skill Input Form -->
          <div class="skill-input-box">
            <div class="form-group" style="margin-bottom: 0; flex: 1;">
              <input
                type="text"
                #newSkillName
                class="form-control"
                placeholder="Quick add skill (e.g. PostgreSQL, Docker, PyTorch)"
                (keydown.enter)="$event.preventDefault(); addQuickSkill(newSkillName.value); newSkillName.value=''"
              />
            </div>
            <button
              type="button"
              class="btn btn-secondary"
              (click)="addQuickSkill(newSkillName.value); newSkillName.value=''"
            >
              Add
            </button>
          </div>

          <!-- Existing Profile Skills List -->
          <div class="skills-grid" formArrayName="skills">
            <div
              *ngFor="let s of skillsArray.controls; let i = index"
              [formGroupName]="i"
              class="skill-card-item"
            >
              <div class="skill-item-header">
                <input
                  type="text"
                  formControlName="name"
                  class="skill-name-input"
                  placeholder="Skill name"
                />
                <button type="button" class="btn-del" (click)="removeSkillItem(i)" title="Remove">✕</button>
              </div>

              <div class="skill-meta-row">
                <select formControlName="category" class="skill-cat-select">
                  <option value="programming_languages">Language</option>
                  <option value="frameworks">Framework</option>
                  <option value="databases">Database</option>
                  <option value="tools_infrastructure">Infrastructure</option>
                  <option value="ai_data">AI / Data</option>
                  <option value="technical">Technical</option>
                </select>

                <select formControlName="status" class="skill-status-select" [ngClass]="s.get('status')?.value">
                  <option value="VERIFIED">VERIFIED</option>
                  <option value="INFERRED">INFERRED</option>
                  <option value="UNVERIFIED">UNVERIFIED</option>
                </select>
              </div>

              <input
                type="text"
                formControlName="evidence"
                class="skill-evidence-input"
                placeholder="Evidence / citation snippet"
              />
            </div>
          </div>

          <!-- Inferred Skills from Intelligence Engine if available -->
          <div *ngIf="intelligence && intelligence.inferred_skills.length > 0" class="inferred-section">
            <div class="inferred-header">
              <span class="badge badge-inferred">Inferred Adjacencies (Transparent AI Inference)</span>
              <span class="inferred-sub">Derived conservatively from project & framework citations</span>
            </div>
            <div class="inferred-list">
              <div *ngFor="let inf of intelligence.inferred_skills" class="inferred-item">
                <div class="inferred-info">
                  <strong>{{ inf.name }}</strong>
                  <span class="inferred-reason">{{ inf.evidence }}</span>
                </div>
                <button type="button" class="btn btn-secondary btn-sm" (click)="verifyInferredSkill(inf)">
                  Promote to Verified
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 4. Work Experience -->
        <div *ngIf="activeTab === 'experience'" class="iq-card tab-content">
          <div class="card-header-row">
            <div>
              <h3 class="section-title">Work Experience</h3>
              <p class="section-desc">Document roles, organizations, and impact.</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" (click)="addExperienceItem()">
              + Add Experience
            </button>
          </div>

          <div formArrayName="work_experience" class="entity-list">
            <div
              *ngFor="let exp of expArray.controls; let i = index"
              [formGroupName]="i"
              class="entity-card"
            >
              <div class="entity-card-header">
                <span class="entity-index">Position #{{ i + 1 }}</span>
                <button type="button" class="btn-del" (click)="removeExpItem(i)">Remove</button>
              </div>

              <div class="grid-2">
                <div class="form-group">
                  <label class="form-label">Role Title</label>
                  <input type="text" formControlName="role" class="form-control" placeholder="e.g. Senior Software Engineer" />
                </div>
                <div class="form-group">
                  <label class="form-label">Company / Organization</label>
                  <input type="text" formControlName="company" class="form-control" placeholder="e.g. Acronis Labs" />
                </div>
              </div>

              <div class="grid-3">
                <div class="form-group">
                  <label class="form-label">Location</label>
                  <input type="text" formControlName="location" class="form-control" placeholder="e.g. San Francisco (Hybrid)" />
                </div>
                <div class="form-group">
                  <label class="form-label">Start Date</label>
                  <input type="text" formControlName="start_date" class="form-control" placeholder="e.g. 2022-01" />
                </div>
                <div class="form-group">
                  <label class="form-label">End Date</label>
                  <input type="text" formControlName="end_date" class="form-control" placeholder="e.g. Present" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Responsibilities & Achievements</label>
                <textarea formControlName="description" rows="3" class="form-control" placeholder="Summarize key responsibilities, scale handled, and engineering outcomes..."></textarea>
              </div>

              <div class="form-group">
                <label class="form-label">Technologies (comma-separated)</label>
                <input type="text" formControlName="technologies_raw" class="form-control" placeholder="e.g. Python, Docker, PostgreSQL, Redis" />
              </div>
            </div>
          </div>
        </div>

        <!-- 5. Projects -->
        <div *ngIf="activeTab === 'projects'" class="iq-card tab-content">
          <div class="card-header-row">
            <div>
              <h3 class="section-title">Technical Projects</h3>
              <p class="section-desc">Key systems, open-source repositories, and portfolio work.</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" (click)="addProjectItem()">
              + Add Project
            </button>
          </div>

          <div formArrayName="projects" class="entity-list">
            <div
              *ngFor="let proj of projArray.controls; let i = index"
              [formGroupName]="i"
              class="entity-card"
            >
              <div class="entity-card-header">
                <span class="entity-index">Project #{{ i + 1 }}</span>
                <button type="button" class="btn-del" (click)="removeProjItem(i)">Remove</button>
              </div>

              <div class="grid-2">
                <div class="form-group">
                  <label class="form-label">Project Title</label>
                  <input type="text" formControlName="title" class="form-control" placeholder="e.g. Distributed KV Store" />
                </div>
                <div class="form-group">
                  <label class="form-label">Technologies (comma-separated)</label>
                  <input type="text" formControlName="technologies_raw" class="form-control" placeholder="e.g. Go, Raft, gRPC, Docker" />
                </div>
              </div>

              <div class="grid-2">
                <div class="form-group">
                  <label class="form-label">GitHub Repository URL</label>
                  <input type="text" formControlName="github_url" class="form-control" placeholder="https://github.com/username/project" />
                </div>
                <div class="form-group">
                  <label class="form-label">Demo / Production URL</label>
                  <input type="text" formControlName="demo_url" class="form-control" placeholder="https://project-demo.com" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Description & Architecture</label>
                <textarea formControlName="description" rows="2" class="form-control" placeholder="What does this system do and how is it architected?"></textarea>
              </div>

              <div class="form-group">
                <label class="form-label">Your Role / Individual Contribution</label>
                <input type="text" formControlName="role_contribution" class="form-control" placeholder="e.g. Implemented the leader election and log replication logic." />
              </div>
            </div>
          </div>
        </div>

        <!-- 6. Education & Links -->
        <div *ngIf="activeTab === 'education'" class="iq-card tab-content">
          <!-- Education Section -->
          <div class="card-header-row">
            <div>
              <h3 class="section-title">Education & Academic Credentials</h3>
              <p class="section-desc">Degrees, institutions, and graduation timelines.</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" (click)="addEduItem()">
              + Add Degree
            </button>
          </div>

          <div formArrayName="education" class="entity-list">
            <div
              *ngFor="let edu of eduArray.controls; let i = index"
              [formGroupName]="i"
              class="entity-card"
            >
              <div class="entity-card-header">
                <span class="entity-index">Degree #{{ i + 1 }}</span>
                <button type="button" class="btn-del" (click)="removeEduItem(i)">Remove</button>
              </div>

              <div class="grid-2">
                <div class="form-group">
                  <label class="form-label">Institution / College</label>
                  <input type="text" formControlName="institution" class="form-control" placeholder="e.g. University of California, Berkeley" />
                </div>
                <div class="form-group">
                  <label class="form-label">Degree</label>
                  <input type="text" formControlName="degree" class="form-control" placeholder="e.g. B.S. in Computer Science" />
                </div>
              </div>

              <div class="grid-3">
                <div class="form-group">
                  <label class="form-label">Field of Study</label>
                  <input type="text" formControlName="field_of_study" class="form-control" placeholder="e.g. Computer Science" />
                </div>
                <div class="form-group">
                  <label class="form-label">Graduation Year</label>
                  <input type="number" formControlName="graduation_year" class="form-control" placeholder="e.g. 2023" />
                </div>
                <div class="form-group">
                  <label class="form-label">GPA / Distinction</label>
                  <input type="text" formControlName="grade_or_gpa" class="form-control" placeholder="e.g. 3.8 / Summa Cum Laude" />
                </div>
              </div>
            </div>
          </div>

          <!-- Professional Links Section -->
          <div class="links-section" style="margin-top: 32px;">
            <div class="card-header-row" style="margin-bottom: 16px;">
              <div>
                <h3 class="section-title">Professional Links & Evidence Repositories</h3>
                <p class="section-desc" style="margin-bottom: 0;">Public profiles, code repositories, and evidence anchors that support your career achievements.</p>
              </div>
              <button type="button" class="btn btn-secondary btn-sm" (click)="addCustomLinkItem()">
                + Add Link
              </button>
            </div>

            <div class="links-grid">
              <!-- Predefined Links -->
              <div class="link-card" formGroupName="links">
                <label class="form-label">LinkedIn Profile URL</label>
                <input type="url" formControlName="linkedin" class="form-control" placeholder="https://linkedin.com/in/username" />
                <span *ngIf="form.get('links.linkedin')?.errors?.['invalidProtocol'] && form.get('links.linkedin')?.touched" class="field-error-hint">Must begin with http:// or https://</span>
                <span *ngIf="form.get('links.linkedin')?.errors?.['invalidUrl'] && form.get('links.linkedin')?.touched" class="field-error-hint">Please enter a valid URL</span>
              </div>

              <div class="link-card" formGroupName="links">
                <label class="form-label">GitHub Profile URL</label>
                <input type="url" formControlName="github" class="form-control" placeholder="https://github.com/username" />
                <span *ngIf="form.get('links.github')?.errors?.['invalidProtocol'] && form.get('links.github')?.touched" class="field-error-hint">Must begin with http:// or https://</span>
                <span *ngIf="form.get('links.github')?.errors?.['invalidUrl'] && form.get('links.github')?.touched" class="field-error-hint">Please enter a valid URL</span>
              </div>

              <div class="link-card" formGroupName="links">
                <label class="form-label">Portfolio / Personal Website</label>
                <input type="url" formControlName="portfolio" class="form-control" placeholder="https://yourdomain.com" />
                <span *ngIf="form.get('links.portfolio')?.errors?.['invalidProtocol'] && form.get('links.portfolio')?.touched" class="field-error-hint">Must begin with http:// or https://</span>
                <span *ngIf="form.get('links.portfolio')?.errors?.['invalidUrl'] && form.get('links.portfolio')?.touched" class="field-error-hint">Please enter a valid URL</span>
              </div>

              <!-- Dynamic Custom Links directly in the same responsive grid -->
              <ng-container formArrayName="custom_links">
                <div *ngFor="let linkGroup of customLinksArray.controls; let i = index" [formGroupName]="i" class="link-card custom-link-card">
                  <div class="custom-link-header">
                    <input type="text" formControlName="label" class="form-control custom-label-input" placeholder="e.g. LeetCode, Medium, Kaggle" />
                    <button type="button" class="btn-del" (click)="removeCustomLinkItem(i)" title="Remove link">✕</button>
                  </div>
                  <input type="url" formControlName="url" class="form-control" placeholder="https://..." />
                  <span *ngIf="linkGroup.get('label')?.invalid && linkGroup.get('label')?.touched" class="field-error-hint">Label is required</span>
                  <span *ngIf="linkGroup.get('url')?.errors?.['required'] && linkGroup.get('url')?.touched" class="field-error-hint">URL is required</span>
                  <span *ngIf="linkGroup.get('url')?.errors?.['invalidProtocol'] && linkGroup.get('url')?.touched" class="field-error-hint">Must begin with http:// or https://</span>
                  <span *ngIf="linkGroup.get('url')?.errors?.['invalidUrl'] && linkGroup.get('url')?.touched" class="field-error-hint">Please enter a valid URL</span>
                </div>
              </ng-container>
            </div>
          </div>
        </div>

      </form>
    </div>
  `,
  styles: [`
    .profile-page {
      padding: 28px;
      max-width: 1140px;
      margin: 0 auto;
    }
    @media (max-width: 768px) {
      .profile-page {
        padding: 16px;
      }
    }
    .profile-header {
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
    }
    .page-subtitle {
      font-size: 13.5px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .save-toast {
      color: var(--success-text);
      background: var(--success-bg);
      border: 1px solid var(--success-border);
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 500;
    }
    .tabs-bar {
      display: flex;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 24px;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: thin;
    }
    .tab-btn {
      background: none;
      border: none;
      padding: 10px 16px;
      font-size: 13.5px;
      font-weight: 500;
      color: var(--text-secondary);
      border-bottom: 2px solid transparent;
      transition: all 0.15s ease;
      white-space: nowrap;
      cursor: pointer;
    }
    .tab-btn:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
      border-top-left-radius: var(--radius-sm);
      border-top-right-radius: var(--radius-sm);
    }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
      font-weight: 600;
      background: var(--bg-surface);
      border-top-left-radius: var(--radius-sm);
      border-top-right-radius: var(--radius-sm);
    }
    .tab-content {
      padding: 28px;
    }
    @media (max-width: 768px) {
      .tab-content {
        padding: 20px 16px;
      }
    }
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
    .section-desc {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 20px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    @media (max-width: 768px) {
      .grid-2, .grid-3 {
        grid-template-columns: 1fr;
      }
    }
    .field-hint {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 4px;
      display: block;
    }
    .card-header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .skill-input-box {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      background: var(--bg-app);
      padding: 12px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }
    .skills-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }
    .skill-card-item {
      background: var(--bg-app);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .skill-item-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .skill-name-input {
      font-weight: 600;
      font-size: 13.5px;
      border: none;
      background: transparent;
      color: var(--text-primary);
      width: 100%;
    }
    .skill-name-input:focus {
      outline: none;
      border-bottom: 1px solid var(--accent);
    }
    .btn-del {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      padding: 2px 6px;
      border-radius: var(--radius-sm);
    }
    .btn-del:hover {
      color: var(--danger-text);
      background: var(--danger-bg);
    }
    .skill-meta-row {
      display: flex;
      gap: 8px;
    }
    .skill-cat-select, .skill-status-select {
      font-size: 11.5px;
      padding: 3px 6px;
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      background: #ffffff;
    }
    .skill-status-select.VERIFIED {
      color: var(--success-text);
      font-weight: 600;
    }
    .skill-status-select.INFERRED {
      color: var(--warning-text);
      font-weight: 600;
    }
    .skill-evidence-input {
      font-size: 11.5px;
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      padding: 4px 8px;
      border-radius: var(--radius-sm);
      background: #ffffff;
    }
    .inferred-section {
      margin-top: 24px;
      padding-top: 20px;
      border-top: 1px solid var(--border-color);
    }
    .inferred-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }
    .inferred-sub {
      font-size: 12px;
      color: var(--text-muted);
    }
    .inferred-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .inferred-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #ffffff;
      border: 1px solid var(--warning-border);
      border-radius: var(--radius-sm);
    }
    .inferred-info {
      display: flex;
      flex-direction: column;
    }
    .inferred-reason {
      font-size: 11.5px;
      color: var(--text-secondary);
    }
    .entity-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .entity-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 20px;
      box-shadow: var(--shadow-xs);
    }
    .entity-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
    }
    .entity-index {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .save-error-toast {
      color: #b91c1c;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      font-weight: 500;
    }
    .links-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }
    @media (max-width: 992px) {
      .links-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    @media (max-width: 600px) {
      .links-grid {
        grid-template-columns: 1fr;
      }
    }
    .link-card {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .custom-link-card {
      background: var(--bg-surface);
      padding: 12px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
    }
    .custom-link-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .custom-label-input {
      font-size: 13px;
      font-weight: 600;
      padding: 4px 8px;
      height: 32px;
      flex: 1;
    }
    .field-error-hint {
      font-size: 11.5px;
      color: #dc2626;
      margin-top: 3px;
      display: block;
    }
  `]
})
export class ProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private profileService = inject(ProfileService);
  private intelligenceService = inject(IntelligenceService);
  private cdr = inject(ChangeDetectorRef);

  activeTab: 'basic' | 'preferences' | 'skills' | 'experience' | 'projects' | 'education' = 'basic';
  profile: Profile | null = null;
  intelligence: CandidateIntelligenceRepresentation | null = null;
  saving = false;
  saveSuccess = false;
  errorMessage: string | null = null;

  form = this.fb.group({
    full_name: [''],
    headline: [''],
    phone: [''],
    location: [''],
    bio: [''],
    preferences: this.fb.group({
      desired_roles_raw: [''],
      preferred_industries_raw: [''],
      preferred_locations_raw: [''],
      remote_preference: ['flexible'],
      experience_level: ['mid'],
      employment_preference: ['full-time']
    }),
    links: this.fb.group({
      linkedin: ['', [this.optionalUrlValidator]],
      github: ['', [this.optionalUrlValidator]],
      portfolio: ['', [this.optionalUrlValidator]]
    }),
    custom_links: this.fb.array([]),
    education: this.fb.array([]),
    work_experience: this.fb.array([]),
    projects: this.fb.array([]),
    skills: this.fb.array([])
  });

  get eduArray(): FormArray {
    return this.form.get('education') as FormArray;
  }

  get expArray(): FormArray {
    return this.form.get('work_experience') as FormArray;
  }

  get projArray(): FormArray {
    return this.form.get('projects') as FormArray;
  }

  get skillsArray(): FormArray {
    return this.form.get('skills') as FormArray;
  }

  get customLinksArray(): FormArray {
    return this.form.get('custom_links') as FormArray;
  }

  optionalUrlValidator(control: AbstractControl): ValidationErrors | null {
    const val = (control.value || '').trim();
    if (!val) return null;
    const lower = val.toLowerCase();
    if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
      return { invalidProtocol: true };
    }
    if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
      return { invalidProtocol: true };
    }
    try {
      const parsed = new URL(val);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        return { invalidProtocol: true };
      }
      return null;
    } catch {
      return { invalidUrl: true };
    }
  }

  ngOnInit(): void {
    this.loadProfile();
    this.form.valueChanges.subscribe(() => {
      if (this.saveSuccess) {
        this.saveSuccess = false;
        this.cdr.markForCheck();
      }
    });
  }

  loadProfile(): void {
    this.profileService.getProfile().subscribe({
      next: (p) => {
        this.profile = p;
        this.populateForm(p);
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    });

    this.intelligenceService.getIntelligence().subscribe({
      next: (intel) => {
        this.intelligence = intel;
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    });
  }

  populateForm(p: Profile): void {
    this.form.patchValue({
      full_name: p.full_name || '',
      headline: p.headline || '',
      phone: p.phone || '',
      location: p.location || '',
      bio: p.bio || '',
      preferences: {
        desired_roles_raw: (p.preferences?.desired_roles || []).join(', '),
        preferred_industries_raw: (p.preferences?.preferred_industries || []).join(', '),
        preferred_locations_raw: (p.preferences?.preferred_locations || []).join(', '),
        remote_preference: p.preferences?.remote_preference || 'flexible',
        experience_level: p.preferences?.experience_level || 'mid',
        employment_preference: p.preferences?.employment_preference || 'full-time'
      },
      links: {
        linkedin: p.links?.['linkedin'] || '',
        github: p.links?.['github'] || '',
        portfolio: p.links?.['portfolio'] || ''
      }
    });

    // Populate Custom Links
    this.customLinksArray.clear();
    const customLinksList = p.links?.['custom_links'];
    if (Array.isArray(customLinksList) && customLinksList.length > 0) {
      customLinksList.forEach((cl: any) => {
        if (cl && (cl.label || cl.url)) {
          this.addCustomLinkItem({ label: cl.label || '', url: cl.url || '' });
        }
      });
    } else if (p.links?.['other'] && typeof p.links['other'] === 'string' && p.links['other'].trim()) {
      // Gracefully migrate legacy "other" link to the first dynamic custom link
      this.addCustomLinkItem({ label: 'Other', url: p.links['other'].trim() });
    }

    // Populate Arrays
    this.eduArray.clear();
    (p.education || []).forEach((edu) => this.addEduItem(edu));

    this.expArray.clear();
    (p.work_experience || []).forEach((exp) => this.addExperienceItem(exp));

    this.projArray.clear();
    (p.projects || []).forEach((proj) => this.addProjectItem(proj));

    this.skillsArray.clear();
    (p.skills || []).forEach((sk) => this.addSkillItem(sk));

    this.cdr.markForCheck();
  }

  addCustomLinkItem(data?: CustomLink): void {
    this.customLinksArray.push(
      this.fb.group({
        label: [data?.label || '', [Validators.required, Validators.maxLength(100)]],
        url: [data?.url || '', [Validators.required, this.optionalUrlValidator]]
      })
    );
    this.cdr.markForCheck();
  }

  removeCustomLinkItem(index: number): void {
    this.customLinksArray.removeAt(index);
    this.cdr.markForCheck();
  }

  addEduItem(data?: Education): void {
    this.eduArray.push(
      this.fb.group({
        institution: [data?.institution || '', Validators.required],
        degree: [data?.degree || '', Validators.required],
        field_of_study: [data?.field_of_study || ''],
        graduation_year: [data?.graduation_year || null],
        grade_or_gpa: [data?.grade_or_gpa || ''],
        details: [data?.details || '']
      })
    );
    this.cdr.markForCheck();
  }

  removeEduItem(index: number): void {
    this.eduArray.removeAt(index);
    this.cdr.markForCheck();
  }

  addExperienceItem(data?: WorkExperience): void {
    this.expArray.push(
      this.fb.group({
        company: [data?.company || '', Validators.required],
        role: [data?.role || '', Validators.required],
        location: [data?.location || ''],
        start_date: [data?.start_date || ''],
        end_date: [data?.end_date || ''],
        is_current: [data?.is_current || false],
        description: [data?.description || ''],
        technologies_raw: [(data?.technologies || []).join(', ')]
      })
    );
    this.cdr.markForCheck();
  }

  removeExpItem(index: number): void {
    this.expArray.removeAt(index);
    this.cdr.markForCheck();
  }

  addProjectItem(data?: Project): void {
    this.projArray.push(
      this.fb.group({
        title: [data?.title || '', Validators.required],
        description: [data?.description || ''],
        technologies_raw: [(data?.technologies || []).join(', ')],
        role_contribution: [data?.role_contribution || ''],
        github_url: [data?.github_url || ''],
        demo_url: [data?.demo_url || '']
      })
    );
    this.cdr.markForCheck();
  }

  removeProjItem(index: number): void {
    this.projArray.removeAt(index);
    this.cdr.markForCheck();
  }

  addSkillItem(data?: Skill): void {
    this.skillsArray.push(
      this.fb.group({
        name: [data?.name || '', Validators.required],
        category: [data?.category || 'technical'],
        status: [data?.status || 'VERIFIED'],
        source: [data?.source || 'USER_INPUT'],
        evidence: [data?.evidence || 'Explicitly specified by candidate'],
        confidence_score: [data?.confidence_score ?? 1.0]
      })
    );
    this.cdr.markForCheck();
  }

  addQuickSkill(skillName: string): void {
    const trimmed = skillName.trim();
    if (!trimmed) return;
    this.addSkillItem({
      name: trimmed,
      category: 'technical',
      status: 'VERIFIED',
      source: 'USER_INPUT',
      evidence: 'Directly verified by candidate profile input',
      confidence_score: 1.0
    });
  }

  removeSkillItem(index: number): void {
    this.skillsArray.removeAt(index);
    this.cdr.markForCheck();
  }

  verifyInferredSkill(inf: any): void {
    this.addSkillItem({
      name: inf.name,
      category: inf.category,
      status: 'VERIFIED',
      source: 'USER_INPUT',
      evidence: `Promoted from inferred adjacency: ${inf.evidence}`,
      confidence_score: 1.0
    });
  }

  saveProfile(): void {
    // Guard rapid double-clicks
    if (this.saving) return;

    this.saveSuccess = false;
    this.errorMessage = null;

    // Validate form before dispatching
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorMessage = 'Please complete all required fields and verify that all URLs are valid (http:// or https://).';
      this.cdr.markForCheck();
      return;
    }

    this.saving = true;
    this.cdr.markForCheck();

    const val = this.form.value;
    const prefVal = val.preferences as any;

    const parseCsv = (str?: string) =>
      str ? str.split(',').map((s) => s.trim()).filter(Boolean) : [];

    const rawCustomLinks = (this.customLinksArray.value as any[]) || [];
    const customLinksPayload = rawCustomLinks
      .filter((cl: any) => cl && cl.label && cl.url)
      .map((cl: any) => ({
        label: String(cl.label).trim(),
        url: String(cl.url).trim()
      }));

    const linksVal = val.links as any;
    const linksPayload: Record<string, any> = {
      linkedin: (linksVal?.linkedin || '').trim(),
      github: (linksVal?.github || '').trim(),
      portfolio: (linksVal?.portfolio || '').trim(),
      custom_links: customLinksPayload
    };

    const payload = {
      full_name: val.full_name || '',
      headline: val.headline || '',
      phone: val.phone || '',
      location: val.location || '',
      bio: val.bio || '',
      preferences: {
        desired_roles: parseCsv(prefVal?.desired_roles_raw),
        preferred_industries: parseCsv(prefVal?.preferred_industries_raw),
        preferred_locations: parseCsv(prefVal?.preferred_locations_raw),
        remote_preference: prefVal?.remote_preference || 'flexible',
        experience_level: prefVal?.experience_level || 'mid',
        employment_preference: prefVal?.employment_preference || 'full-time'
      },
      links: linksPayload,
      education: ((val.education as any[]) || []).map((e) => ({
        institution: e.institution,
        degree: e.degree,
        field_of_study: e.field_of_study,
        graduation_year: e.graduation_year ? Number(e.graduation_year) : undefined,
        grade_or_gpa: e.grade_or_gpa,
        details: e.details
      })),
      work_experience: ((val.work_experience as any[]) || []).map((w) => ({
        company: w.company,
        role: w.role,
        location: w.location,
        start_date: w.start_date,
        end_date: w.end_date,
        is_current: !!w.is_current,
        description: w.description,
        technologies: parseCsv(w.technologies_raw)
      })),
      projects: ((val.projects as any[]) || []).map((p) => ({
        title: p.title,
        description: p.description,
        technologies: parseCsv(p.technologies_raw),
        role_contribution: p.role_contribution,
        github_url: p.github_url,
        demo_url: p.demo_url
      })),
      skills: ((val.skills as any[]) || []).map((s) => ({
        name: s.name,
        category: s.category,
        status: s.status as SkillStatus,
        source: s.source,
        evidence: s.evidence,
        confidence_score: s.confidence_score
      }))
    };

    this.profileService.updateProfile(payload as any).pipe(
      finalize(() => {
        this.saving = false;
        this.cdr.markForCheck();
      })
    ).subscribe({
      next: (updated) => {
        this.profile = updated;
        this.saveSuccess = true;
        this.errorMessage = null;
        this.cdr.markForCheck();
        setTimeout(() => {
          this.saveSuccess = false;
          this.cdr.markForCheck();
        }, 4000);
      },
      error: (err) => {
        this.saveSuccess = false;
        const detail = err?.error?.detail;
        if (typeof detail === 'string') {
          this.errorMessage = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          this.errorMessage = detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else if (err?.message) {
          this.errorMessage = `Save failed: ${err.message}`;
        } else {
          this.errorMessage = 'Failed to save changes. Please try again.';
        }
        this.cdr.markForCheck();
        setTimeout(() => {
          this.errorMessage = null;
          this.cdr.markForCheck();
        }, 6000);
      }
    });
  }
}

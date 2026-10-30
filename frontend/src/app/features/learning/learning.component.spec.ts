import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError, BehaviorSubject } from 'rxjs';
import { LearningComponent } from './learning.component';
import { LearningService } from '../../core/services/learning.service';
import {
  CosgoLearningDashboardResponse,
  BudgetUpdateResponse
} from '../../core/models/learning.model';

describe('LearningComponent (COSGO Execution Layer)', () => {
  let component: LearningComponent;
  let fixture: ComponentFixture<LearningComponent>;
  let learningService: LearningService;
  let queryParamSubject: BehaviorSubject<any>;

  const mockCosgoResponse: CosgoLearningDashboardResponse = {
    is_cosgo_empty_state: false,
    empty_state_message: null,
    run_id: 'run-cosgo-123',
    algorithm_version: 'cosgo-v1.1-verified',
    budget_hours: 40.0,
    weekly_hours_budget: 10.0,
    baseline_coverage: 0.225,
    projected_coverage: 0.6194,
    marginal_coverage_increase: 0.3944,
    recommended_skills: [
      {
        action_id: 'act-docker',
        skill_name: 'Docker',
        priority_rank: 1,
        marginal_coverage_gain: 0.3944,
        cumulative_coverage: 0.6194,
        opportunities_count: 4,
        estimated_hours: 15.0,
        effort_uncertainty_range: { min_hours: 12.0, max_hours: 18.0 },
        prerequisites: ['Linux Basics'],
        category: 'DevOps / Containers',
        progress_state: 'RECOMMENDED',
        why_recommended: 'Helps qualify for 4 target vacancies (+39.4 pp gain).'
      },
      {
        action_id: 'act-fastapi',
        skill_name: 'FastAPI',
        priority_rank: 2,
        marginal_coverage_gain: 0.15,
        cumulative_coverage: 0.7694,
        opportunities_count: 3,
        estimated_hours: 12.0,
        effort_uncertainty_range: { min_hours: 10.0, max_hours: 15.0 },
        prerequisites: ['Python'],
        category: 'Backend Web Frameworks',
        progress_state: 'PLANNED',
        why_recommended: 'High-speed async API standard for modern Python microservices.'
      }
    ],
    selected_skill_name: 'Docker',
    skill_plan: {
      skill_name: 'Docker',
      action_id: 'act-docker',
      run_id: 'run-cosgo-123',
      priority_rank: 1,
      category: 'DevOps / Containers',
      why_recommended: 'Helps qualify for 4 target vacancies (+39.4 pp gain).',
      opportunities_count: 4,
      target_opportunities_summary: [
        {
          title: 'Senior Backend Engineer',
          company: 'Acme Cloud',
          match_score: 0.82,
          salary_range: '$140k - $165k',
          required_skills: ['Python', 'Docker', 'PostgreSQL']
        }
      ],
      marginal_coverage_gain: 0.3944,
      cumulative_coverage: 0.6194,
      estimated_hours: 15.0,
      effort_uncertainty_range: { min_hours: 12.0, max_hours: 18.0 },
      prerequisites: ['Linux Basics'],
      progress_state: 'RECOMMENDED',
      completed_at: null,
      diagnostic_note: null,
      roadmap_stages: [
        {
          stage_id: 'docker-stg-1',
          stage_number: 1,
          title: 'Containerization Fundamentals',
          focus: 'Images vs containers, Docker Engine architecture',
          estimated_hours: 3.5,
          core_concepts: ['Docker Daemon', 'Dockerfile syntax', 'Container isolation'],
          key_deliverable: 'Running single-container application'
        },
        {
          stage_id: 'docker-stg-2',
          stage_number: 2,
          title: 'Multi-Container Orchestration',
          focus: 'Docker Compose, networking, volume persistence',
          estimated_hours: 4.5,
          core_concepts: ['docker-compose.yml', 'Bridge networks', 'Named volumes'],
          key_deliverable: 'Compose stack with backend & database'
        }
      ],
      resources: {
        documentation: {
          technology: 'Docker',
          title: 'Docker Documentation',
          url: 'https://docs.docker.com',
          description: 'Official Docker containerization guides.',
          domain: 'docs.docker.com',
          doc_type: 'official_documentation',
          is_verified_free: true
        },
        courses: [
          {
            title: 'Docker Training Course for Beginners',
            provider: 'freeCodeCamp',
            url: 'https://www.freecodecamp.org/news/docker-training-tutorial-for-beginners/',
            access_type: '100% Free (Includes Certificate)',
            certificate_included: true,
            difficulty_level: 'Beginner',
            estimated_hours: 15.0,
            target_skills: ['Docker', 'Linux'],
            description: 'Hands-on container training.',
            price_transparency_note: 'Zero cost verified course.'
          }
        ],
        certifications: [
          {
            title: 'Docker Certified Associate (DCA)',
            vendor: 'Docker Inc.',
            code: 'DCA',
            official_url: 'https://www.docker.com/community/certifications/',
            exam_fee_status: 'PAID',
            estimated_cost_usd: 195,
            free_learning_materials_available: true,
            free_materials_url: 'https://docs.docker.com/get-started/',
            skills: ['Docker', 'DevOps'],
            relevant_roles: ['DevOps Engineer', 'Backend Developer'],
            notes: 'Industry standard certification for Docker container orchestration.'
          }
        ],
        videos: [
          {
            title: 'Docker Tutorial for Beginners',
            url: 'https://www.youtube.com/watch?v=fqMOX6JJhGo',
            channel_title: 'Programming with Mosh',
            video_id: 'fqMOX6JJhGo',
            thumbnail_url: 'https://i.ytimg.com/vi/fqMOX6JJhGo/hqdefault.jpg',
            is_curated_fallback: true
          }
        ],
        practical_exercises: [
          {
            id: 'ex-docker-build',
            title: 'Build and Run Containerized Python Service',
            scenario: 'Package a FastAPI service into a Docker container.',
            objective: 'Write multi-stage Dockerfile and test local port mapping.',
            estimated_hours: 2.0,
            commands_or_code_hints: ['docker build -t app:v1 .', 'docker run -p 8000:8000 app:v1'],
            acceptance_criteria: ['Container builds without errors', 'curl localhost:8000 returns 200 OK']
          }
        ]
      },
      projects: [
        {
          id: 'proj-docker-stack',
          project_id: 'proj-docker-stack',
          title: 'Containerized Multi-Service Production Stack',
          difficulty: 'Intermediate',
          difficulty_level: 'Intermediate',
          estimated_hours: 12.0,
          purpose: 'Orchestrate API and database using Docker Compose.',
          target_skills: ['Docker', 'FastAPI'],
          prerequisites: ['Linux Basics'],
          milestones: [
            { step: 1, step_number: 1, title: 'Containerization', estimated_hours: 4.0, deliverables: ['Dockerfile'] }
          ],
          validation_checklist: ['docker compose up starts all containers with healthchecks'],
          career_impact_rationale: 'Demonstrates production deployment readiness.',
          documentation_links: [{ title: 'Docker Docs', url: 'https://docs.docker.com' }]
        }
      ],
      progress: {
        completed_resources: [],
        completed_milestones: [],
        completed_exercises: [],
        project_milestones_completed: [],
        project_completed: false,
        overall_status: 'RECOMMENDED'
      }
    }
  };

  const mockEmptyCosgoResponse: CosgoLearningDashboardResponse = {
    is_cosgo_empty_state: true,
    empty_state_message: 'No active Skill Gap Optimization recommendations found.',
    run_id: null,
    algorithm_version: null,
    budget_hours: 0,
    weekly_hours_budget: 10,
    baseline_coverage: 0,
    projected_coverage: 0,
    marginal_coverage_increase: 0,
    recommended_skills: [],
    selected_skill_name: null,
    skill_plan: null
  };

  beforeEach(async () => {
    queryParamSubject = new BehaviorSubject(convertToParamMap({}));

    await TestBed.configureTestingModule({
      imports: [LearningComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            queryParamMap: queryParamSubject.asObservable(),
            snapshot: { queryParamMap: convertToParamMap({}) }
          }
        }
      ]
    }).compileComponents();

    learningService = TestBed.inject(LearningService);
    fixture = TestBed.createComponent(LearningComponent);
    component = fixture.componentInstance;
  });

  const getMockCosgoResponse = (): CosgoLearningDashboardResponse =>
    JSON.parse(JSON.stringify(mockCosgoResponse));

  it('should initialize and load top-priority COSGO skill by default', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.loading).toBe(false);
    expect(component.dashboardData?.run_id).toBe('run-cosgo-123');
    expect(component.selectedSkillName).toBe('Docker');
    expect(component.selectedSkillPlan?.skill_name).toBe('Docker');
    expect(component.selectedSkillPlan?.priority_rank).toBe(1);
    expect(component.dashboardData?.recommended_skills.length).toBe(2);
  });

  it('should read query parameter ?skill=FastAPI and load that skill plan', () => {
    const fastApiResponse = {
      ...getMockCosgoResponse(),
      selected_skill_name: 'FastAPI',
      skill_plan: {
        ...mockCosgoResponse.skill_plan!,
        skill_name: 'FastAPI',
        priority_rank: 2,
        action_id: 'act-fastapi'
      }
    };
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(fastApiResponse));

    queryParamSubject.next(convertToParamMap({ skill: 'FastAPI' }));
    fixture.detectChanges();

    expect(learningService.getCosgoLearningPlan).toHaveBeenCalledWith('FastAPI');
    expect(component.selectedSkillName).toBe('FastAPI');
    expect(component.selectedSkillPlan?.skill_name).toBe('FastAPI');
  });

  it('should display COSGO empty state when no optimization run exists', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(mockEmptyCosgoResponse));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.loading).toBe(false);
    expect(component.dashboardData?.is_cosgo_empty_state).toBe(true);
    expect(component.selectedSkillPlan).toBeNull();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.cosgo-empty-card')).toBeTruthy();
    expect(compiled.querySelector('.empty-title')?.textContent).toContain('No Active COSGO Recommendations Found');
    expect(compiled.querySelector('a[routerlink="/skill-gap"]')).toBeTruthy();
  });

  it('should switch skills when clicking a skill card in the selector queue', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    component.ngOnInit();
    fixture.detectChanges();

    expect(component.selectedSkillName).toBe('Docker');

    const fastApiResponse = {
      ...getMockCosgoResponse(),
      selected_skill_name: 'FastAPI',
      skill_plan: {
        ...mockCosgoResponse.skill_plan!,
        skill_name: 'FastAPI',
        priority_rank: 2,
        action_id: 'act-fastapi'
      }
    };
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(fastApiResponse));

    component.selectSkill('FastAPI');
    expect(component.selectedSkillName).toBe('FastAPI');
    expect(learningService.getCosgoLearningPlan).toHaveBeenCalledWith('FastAPI');
  });

  it('should toggle milestone completion and sync with backend', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    vi.spyOn(learningService, 'updateLearningProgress').mockReturnValue(of({
      status: 'success',
      skill_progress: { completed_milestones: ['docker-stg-1'] },
      cosgo_action_progress: { progress_state: 'IN_PROGRESS' }
    }));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.isMilestoneCompleted('docker-stg-1')).toBe(false);

    component.toggleMilestone('docker-stg-1');
    expect(learningService.updateLearningProgress).toHaveBeenCalledWith({
      skill_name: 'Docker',
      toggle_milestone_id: 'docker-stg-1'
    });
    expect(component.isMilestoneCompleted('docker-stg-1')).toBe(true);
    expect(component.currentOverallState).toBe('IN_PROGRESS');
  });

  it('should toggle resource completion and sync with backend', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    vi.spyOn(learningService, 'updateLearningProgress').mockReturnValue(of({
      status: 'success',
      skill_progress: { completed_resources: ['https://docs.docker.com'] },
      cosgo_action_progress: { progress_state: 'IN_PROGRESS' }
    }));

    component.ngOnInit();
    fixture.detectChanges();

    const url = 'https://docs.docker.com';
    expect(component.isResourceCompleted(url)).toBe(false);

    component.toggleResource(url);
    expect(learningService.updateLearningProgress).toHaveBeenCalledWith({
      skill_name: 'Docker',
      toggle_resource_url: url
    });
    expect(component.isResourceCompleted(url)).toBe(true);
  });

  it('should toggle practical exercise completion and sync with backend', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    vi.spyOn(learningService, 'updateLearningProgress').mockReturnValue(of({
      status: 'success',
      skill_progress: { completed_exercises: ['ex-docker-build'] },
      cosgo_action_progress: { progress_state: 'IN_PROGRESS' }
    }));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.isExerciseCompleted('ex-docker-build')).toBe(false);

    component.toggleExercise('ex-docker-build');
    expect(learningService.updateLearningProgress).toHaveBeenCalledWith({
      skill_name: 'Docker',
      toggle_exercise_id: 'ex-docker-build'
    });
    expect(component.isExerciseCompleted('ex-docker-build')).toBe(true);
  });

  it('should toggle project step and project completion', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    vi.spyOn(learningService, 'updateLearningProgress').mockReturnValue(of({
      status: 'success',
      skill_progress: { project_milestones_completed: [1], project_completed: true },
      cosgo_action_progress: { progress_state: 'COMPLETED' }
    }));

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.isProjectMilestoneCompleted(1)).toBe(false);
    expect(component.isProjectCompleted()).toBe(false);

    component.toggleProjectMilestone(1);
    expect(component.isProjectMilestoneCompleted(1)).toBe(true);

    component.toggleProject('proj-docker-stack');
    expect(component.isProjectCompleted()).toBe(true);
  });

  it('should update overall roadmap progress state to COMPLETED', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    vi.spyOn(learningService, 'updateLearningProgress').mockReturnValue(of({
      status: 'success',
      skill_progress: {},
      cosgo_action_progress: { progress_state: 'COMPLETED' }
    }));

    component.ngOnInit();
    fixture.detectChanges();

    component.changeOverallProgressState('COMPLETED');
    expect(learningService.updateLearningProgress).toHaveBeenCalledWith({
      skill_name: 'Docker',
      progress_state: 'COMPLETED'
    });
    expect(component.currentOverallState).toBe('COMPLETED');
  });

  it('should update weekly budget and recalculate estimated timeline', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(of(getMockCosgoResponse()));
    const budgetResp: BudgetUpdateResponse = {
      user_id: 'user-1',
      weekly_hours_budget: 15.0,
      updated_at: '2026-10-31T00:00:00Z'
    };
    vi.spyOn(learningService, 'updateWeeklyBudget').mockReturnValue(of(budgetResp));

    component.ngOnInit();
    fixture.detectChanges();

    component.weeklyBudget = 15;
    component.saveBudget();

    expect(learningService.updateWeeklyBudget).toHaveBeenCalledWith(15);
    expect(component.budgetSuccessMsg).toContain('15 hrs/week');
  });

  it('should handle API errors gracefully with error banner', () => {
    vi.spyOn(learningService, 'getCosgoLearningPlan').mockReturnValue(
      throwError(() => new Error('Connection refused'))
    );

    component.ngOnInit();
    fixture.detectChanges();

    expect(component.loading).toBe(false);
    expect(component.loadError).toBe('Connection refused');
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.error-banner')).toBeTruthy();
  });
});

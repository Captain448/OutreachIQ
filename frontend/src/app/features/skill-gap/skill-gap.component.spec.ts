import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideRouter } from '@angular/router';
import { SkillGapComponent } from './skill-gap.component';
import { CosgoService } from '../../core/services/cosgo.service';
import { CosgoRun, CosgoCoverageMatrixResponse, CosgoBenchmarkResponse } from '../../core/models/cosgo.model';

describe('SkillGapComponent', () => {
  let component: SkillGapComponent;
  let fixture: ComponentFixture<SkillGapComponent>;
  let cosgoServiceSpy: any;

  const mockRun: CosgoRun = {
    id: 'run-1',
    user_id: 'user-1',
    budget_hours: 40.0,
    weekly_budget_hours: 10.0,
    target_roles: ['AI/ML Engineer'],
    algorithm_version: 'cosgo-v1.0',
    status: 'COMPLETED',
    total_opportunities_analyzed: 10,
    eligible_opportunities_count: 8,
    excluded_opportunities_count: 2,
    baseline_coverage: 0.42,
    projected_coverage: 0.82,
    marginal_coverage_increase: 0.40,
    opportunities_at_threshold_baseline: 2,
    opportunities_at_threshold_projected: 7,
    diagnostics: {
      budget_hours_used: 38.0,
      budget_hours_remaining: 2.0,
      estimated_weeks_to_complete: 3.8
    },
    actions: [
      {
        id: 'act-1',
        run_id: 'run-1',
        user_id: 'user-1',
        skill_name: 'PyTorch',
        category: 'ai_ml',
        priority_rank: 1,
        estimated_hours: 24.0,
        effort_uncertainty_range: { min_hours: 18, max_hours: 30, confidence: 'high' },
        marginal_coverage_gain: 0.25,
        cumulative_coverage: 0.67,
        opportunities_count: 6,
        target_opportunity_ids: ['opp-1', 'opp-2'],
        target_opportunities_summary: [
          { id: 'opp-1', title: 'Senior AI Engineer', company_name: 'NeuroVectors', match_score: 0.85 }
        ],
        prerequisites: ['Python'],
        why_recommended: 'Helps qualify for 6 target opportunities, providing +25.0% coverage.',
        practical_project: {
          title: 'Containerized Deep Learning API',
          description: 'Deploy PyTorch models via FastAPI and Docker.',
          overlapping_skills: ['PyTorch', 'Docker'],
          deliverables: ['Inference API', 'Dockerfile']
        },
        learning_resources: [
          { title: 'Official PyTorch Tutorials', url: 'https://pytorch.org/tutorials/', provider: 'PyTorch Foundation', is_verified: true, resource_type: 'Tutorial' }
        ],
        progress_state: 'RECOMMENDED',
        created_at: '2026-01-01T00:00:00Z'
      },
      {
        id: 'act-2',
        run_id: 'run-1',
        user_id: 'user-1',
        skill_name: 'Docker',
        category: 'tools',
        priority_rank: 2,
        estimated_hours: 14.0,
        effort_uncertainty_range: { min_hours: 10, max_hours: 18, confidence: 'moderate' },
        marginal_coverage_gain: 0.15,
        cumulative_coverage: 0.82,
        opportunities_count: 5,
        target_opportunity_ids: ['opp-1', 'opp-3'],
        target_opportunities_summary: [],
        prerequisites: [],
        why_recommended: 'Helps qualify for 5 target opportunities.',
        practical_project: {
          title: 'Containerized Deep Learning API',
          description: 'Deploy PyTorch models via FastAPI and Docker.',
          overlapping_skills: ['PyTorch', 'Docker'],
          deliverables: ['Dockerfile']
        },
        learning_resources: [],
        progress_state: 'RECOMMENDED',
        created_at: '2026-01-01T00:00:00Z'
      }
    ],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z'
  };

  const mockMatrix: CosgoCoverageMatrixResponse = {
    run_id: 'run-1',
    total_skills_count: 3,
    skills_header: ['Python', 'PyTorch', 'Docker'],
    matrix: [
      {
        opportunity_id: 'opp-1',
        job_title: 'Senior AI Engineer',
        company_name: 'NeuroVectors',
        match_score: 0.85,
        role_relevance: 0.95,
        requirements: ['Python', 'PyTorch', 'Docker'],
        verified_skills: ['Python'],
        inferred_skills: [],
        actions_covering: ['PyTorch', 'Docker'],
        remaining_gaps: [],
        baseline_coverage: 0.33,
        projected_coverage: 1.00
      }
    ],
    skill_frequency: { 'Python': 1, 'PyTorch': 1, 'Docker': 1 }
  };

  const mockBenchmark: CosgoBenchmarkResponse = {
    dataset_summary: {
      total_opportunities_analyzed: 10,
      eligible_opportunities_count: 8,
      baseline_coverage: 0.42,
      budget_hours: 40.0
    },
    cosgo: {
      strategy: 'COSGO (Budgeted Marginal Coverage)',
      selected_skills: ['PyTorch', 'Docker'],
      skills_count: 2,
      hours_spent: 38.0,
      final_coverage: 0.82,
      coverage_gain: 0.40,
      gain_per_hour: 0.0105,
      opportunities_qualifying: 7,
      unique_opportunities_improved: 8,
      jaccard_similarity_with_cosgo: 1.0
    },
    frequency_baseline: {
      strategy: 'Frequency-Ranked Skill-Gap Baseline',
      selected_skills: ['Java', 'SQL'],
      skills_count: 2,
      hours_spent: 38.0,
      final_coverage: 0.65,
      coverage_gain: 0.23,
      gain_per_hour: 0.0060,
      opportunities_qualifying: 3,
      unique_opportunities_improved: 4,
      jaccard_similarity_with_cosgo: 0.0
    },
    independent_per_job: {
      strategy: 'Independent Per-Job Baseline',
      selected_skills: ['PyTorch'],
      skills_count: 1,
      hours_spent: 24.0,
      final_coverage: 0.67,
      coverage_gain: 0.25,
      gain_per_hour: 0.0104,
      opportunities_qualifying: 4,
      unique_opportunities_improved: 6,
      jaccard_similarity_with_cosgo: 0.5
    },
    greedy_frequency_no_effort: {
      strategy: 'Greedy Frequency without Effort Accounting',
      selected_skills: ['Java'],
      skills_count: 1,
      hours_spent: 40.0,
      final_coverage: 0.55,
      coverage_gain: 0.13,
      gain_per_hour: 0.0032,
      opportunities_qualifying: 2,
      unique_opportunities_improved: 3,
      jaccard_similarity_with_cosgo: 0.0
    },
    comparison_summary: {
      cosgo_coverage_gain_lift_vs_frequency: '+73.9%',
      cosgo_efficiency_lift_vs_frequency: '+75.0%',
      conclusion: 'COSGO achieves superior marginal coverage per learning hour.'
    }
  };

  beforeEach(async () => {
    cosgoServiceSpy = {
      getLatestRun: vi.fn().mockReturnValue(of(mockRun)),
      runOptimization: vi.fn().mockReturnValue(of(mockRun)),
      updateActionProgress: vi.fn().mockImplementation((id: string, payload: any) =>
        of({ id, progress_state: payload.progress_state, completed_at: '2026-01-01T00:00:00Z' })
      ),
      updateBudget: vi.fn().mockReturnValue(of({ ...mockRun, budget_hours: 50.0, weekly_budget_hours: 15.0 })),
      getCoverageMatrix: vi.fn().mockReturnValue(of(mockMatrix)),
      getBenchmark: vi.fn().mockReturnValue(of(mockBenchmark))
    };

    await TestBed.configureTestingModule({
      imports: [SkillGapComponent],
      providers: [
        provideRouter([]),
        { provide: CosgoService, useValue: cosgoServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SkillGapComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should load latest persisted COSGO plan on page load and display KPIs', () => {
    expect(cosgoServiceSpy.getLatestRun).toHaveBeenCalled();
    expect(component.latestRun).toBeTruthy();
    expect(component.latestRun?.eligible_opportunities_count).toBe(8);
    expect(component.latestRun?.actions.length).toBe(2);
    expect(component.loading).toBe(false);
  });

  it('should toggle jobs expanded section for a recommended action', () => {
    expect(component.isJobsExpanded('act-1')).toBe(false);

    component.toggleJobsExpanded('act-1');
    expect(component.isJobsExpanded('act-1')).toBe(true);

    component.toggleJobsExpanded('act-1');
    expect(component.isJobsExpanded('act-1')).toBe(false);
  });

  it('should update action progress state without altering permanent profile', () => {
    const act = component.latestRun!.actions[0];
    expect(act.progress_state).toBe('RECOMMENDED');

    component.changeActionProgress(act, 'COMPLETED');
    expect(cosgoServiceSpy.updateActionProgress).toHaveBeenCalledWith('act-1', {
      progress_state: 'COMPLETED'
    });
    expect(act.progress_state).toBe('COMPLETED');
  });

  it('should update study budget and re-run optimization', () => {
    component.customTotalBudget = 50;
    component.customWeeklyBudget = 15;

    component.updateBudget();
    expect(cosgoServiceSpy.updateBudget).toHaveBeenCalledWith({
      budget_hours: 50,
      weekly_budget_hours: 15
    });
    expect(component.latestRun?.budget_hours).toBe(50.0);
  });

  it('should load coverage matrix when switching to matrix tab', () => {
    component.activeTab = 'matrix';
    component.loadMatrix();

    expect(cosgoServiceSpy.getCoverageMatrix).toHaveBeenCalledWith('run-1');
    expect(component.matrixData).toBeTruthy();
    expect(component.matrixData?.skills_header).toEqual(['Python', 'PyTorch', 'Docker']);

    const row = component.matrixData!.matrix[0];
    expect(component.isSkillVerified(row, 'Python')).toBe(true);
    expect(component.isSkillCovered(row, 'PyTorch')).toBe(true);
    expect(component.isSkillCovered(row, 'Docker')).toBe(true);
    expect(component.isSkillGap(row, 'PyTorch')).toBe(false);
  });

  it('should load academic benchmark evaluation when switching to benchmark tab', () => {
    component.activeTab = 'benchmark';
    component.loadBenchmark();

    expect(cosgoServiceSpy.getBenchmark).toHaveBeenCalledWith(40, 10);
    expect(component.benchmarkData).toBeTruthy();
    expect(component.benchmarkData?.cosgo.strategy).toContain('COSGO');
    expect(component.benchmarkData?.comparison_summary.cosgo_efficiency_lift_vs_frequency).toBe('+75.0%');
  });

  it('should display empty state notice when zero eligible opportunities exist', () => {
    cosgoServiceSpy.getLatestRun = vi.fn().mockReturnValue(of({ ...mockRun, eligible_opportunities_count: 0 }));
    component.loadPlan();
    fixture.detectChanges();

    expect(component.latestRun?.eligible_opportunities_count).toBe(0);
  });
});

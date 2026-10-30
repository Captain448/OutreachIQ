import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { LearningService } from './learning.service';
import {
  LearningOverview,
  BudgetUpdateResponse,
  DocResource,
  VideoSearchResponse,
  CourseItem,
  CertificationEntry,
  ProjectBlueprint,
  LearningProviderHealth
} from '../models/learning.model';

describe('LearningService', () => {
  let service: LearningService;
  let httpMock: HttpTestingController;
  const API_URL = 'http://localhost:8000/api/v1/learning';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        LearningService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(LearningService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should fetch personalized learning overview', () => {
    const mockOverview: LearningOverview = {
      is_onboarding_empty_state: false,
      weekly_hours_budget: 10,
      total_estimated_hours: 35.0,
      total_estimated_weeks: 4,
      target_roles: ['Backend Engineer'],
      candidate_known_skills: ['Python'],
      recommended_skills: [],
      learning_phases: [],
      recommended_projects: [],
      catalog_overview: {
        total_documentation_pages: 26,
        total_verified_courses: 16,
        total_certifications: 12
      }
    };

    service.getLearningOverview().subscribe((res) => {
      expect(res).toEqual(mockOverview);
      expect(res.weekly_hours_budget).toBe(10);
      expect(res.is_onboarding_empty_state).toBe(false);
    });

    const req = httpMock.expectOne(`${API_URL}/overview`);
    expect(req.request.method).toBe('GET');
    req.flush(mockOverview);
  });

  it('should update weekly study budget', () => {
    const mockResponse: BudgetUpdateResponse = {
      user_id: 'usr-123',
      weekly_hours_budget: 15,
      updated_at: '2026-10-27T12:00:00Z'
    };

    service.updateWeeklyBudget(15).subscribe((res) => {
      expect(res.weekly_hours_budget).toBe(15);
      expect(res.user_id).toBe('usr-123');
    });

    const req = httpMock.expectOne(`${API_URL}/budget`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ weekly_hours: 15 });
    req.flush(mockResponse);
  });

  it('should search official documentation with query and limit', () => {
    const mockDocs: DocResource[] = [
      {
        technology: 'FastAPI',
        title: 'FastAPI Official Documentation',
        url: 'https://fastapi.tiangolo.com',
        description: 'Modern, high-performance web framework for Python',
        domain: 'fastapi.tiangolo.com',
        doc_type: 'official_documentation',
        is_verified_free: true
      }
    ];

    service.searchDocs('FastAPI', 10).subscribe((docs) => {
      expect(docs.length).toBe(1);
      expect(docs[0].technology).toBe('FastAPI');
      expect(docs[0].is_verified_free).toBe(true);
    });

    const req = httpMock.expectOne((r) => r.url === `${API_URL}/docs` && r.params.get('query') === 'FastAPI');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('limit')).toBe('10');
    req.flush(mockDocs);
  });

  it('should search educational videos with fallback metadata', () => {
    const mockVideoResponse: VideoSearchResponse = {
      skill: 'Docker',
      provider: 'youtube',
      is_live_api: false,
      circuit_status: 'ok',
      results_count: 1,
      videos: [
        {
          title: 'Docker Full Course',
          url: 'https://www.youtube.com/watch?v=3c-iBn73dDE',
          channel_title: 'freeCodeCamp.org',
          video_id: '3c-iBn73dDE',
          thumbnail_url: 'https://img.youtube.com/vi/3c-iBn73dDE/hqdefault.jpg',
          is_curated_fallback: true
        }
      ]
    };

    service.searchVideos('Docker', 3).subscribe((res) => {
      expect(res.skill).toBe('Docker');
      expect(res.videos.length).toBe(1);
      expect(res.videos[0].is_curated_fallback).toBe(true);
    });

    const req = httpMock.expectOne((r) => r.url === `${API_URL}/videos` && r.params.get('skill') === 'Docker');
    expect(req.request.method).toBe('GET');
    req.flush(mockVideoResponse);
  });

  it('should filter courses by skill and access type', () => {
    const mockCourses: CourseItem[] = [
      {
        title: 'CS50P',
        provider: 'edX / Harvard University',
        url: 'https://cs50.harvard.edu/python/',
        access_type: 'FREE_COURSE',
        certificate_included: true,
        difficulty_level: 'Beginner',
        estimated_hours: 30.0,
        target_skills: ['Python'],
        description: 'Introduction to programming with Python.',
        price_transparency_note: '100% free open-access course with free CS50 certificate.'
      }
    ];

    service.searchCourses('Python', 'FREE_COURSE').subscribe((courses) => {
      expect(courses.length).toBe(1);
      expect(courses[0].access_type).toBe('FREE_COURSE');
      expect(courses[0].certificate_included).toBe(true);
    });

    const req = httpMock.expectOne((r) => r.url === `${API_URL}/courses` && r.params.get('skill') === 'Python');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('access_type')).toBe('FREE_COURSE');
    req.flush(mockCourses);
  });

  it('should fetch vendor certifications with exam fee status', () => {
    const mockCerts: CertificationEntry[] = [
      {
        title: 'AWS Solutions Architect Associate',
        vendor: 'Amazon Web Services',
        code: 'SAA-C03',
        official_url: 'https://aws.amazon.com/certification/certified-solutions-architect-associate/',
        exam_fee_status: 'PAID',
        estimated_cost_usd: 150,
        free_learning_materials_available: true,
        free_materials_url: 'https://explore.skillbuilder.aws/',
        skills: ['AWS', 'Cloud Architecture'],
        relevant_roles: ['Cloud Engineer', 'Backend Developer'],
        notes: 'Exam voucher required; free whitepapers and ramp-up guides provided by AWS.'
      }
    ];

    service.getCertifications('AWS').subscribe((certs) => {
      expect(certs.length).toBe(1);
      expect(certs[0].exam_fee_status).toBe('PAID');
      expect(certs[0].free_learning_materials_available).toBe(true);
    });

    const req = httpMock.expectOne((r) => r.url === `${API_URL}/certifications` && r.params.get('skill') === 'AWS');
    expect(req.request.method).toBe('GET');
    req.flush(mockCerts);
  });

  it('should fetch recommended projects with milestones', () => {
    const mockProjects: ProjectBlueprint[] = [
      {
        id: 'proj-fastapi-docker',
        title: 'Containerized Async REST Service',
        difficulty: 'Intermediate',
        estimated_hours: 18.0,
        summary: 'Build a production microservice.',
        problem_statement: 'High concurrency REST API.',
        target_skills: ['FastAPI', 'Docker'],
        prerequisites: ['Python'],
        milestones: [
          { step: 1, title: 'API scaffolding', hours: 4, deliverables: ['endpoints'] }
        ],
        validation_checklist: ['Docker compose builds cleanly'],
        career_impact_rationale: 'Demonstrates microservices proficiency.',
        documentation_links: [{ title: 'FastAPI Docs', url: 'https://fastapi.tiangolo.com' }]
      }
    ];

    service.getRecommendedProjects().subscribe((projects) => {
      expect(projects.length).toBe(1);
      expect(projects[0].milestones.length).toBe(1);
      expect(projects[0].target_skills).toContain('FastAPI');
    });

    const req = httpMock.expectOne(`${API_URL}/projects`);
    expect(req.request.method).toBe('GET');
    req.flush(mockProjects);
  });

  it('should fetch learning provider health and catalog counts', () => {
    const mockHealth: LearningProviderHealth = {
      youtube: {
        provider_name: 'youtube',
        is_configured: false,
        daily_limit: 25,
        daily_requests_used: 0,
        circuit_status: 'ok'
      },
      documentation_catalog: { total_technologies: 26, status: 'active_curated' },
      course_catalog: { total_courses: 16, status: 'active_curated' },
      certification_directory: { total_certifications: 12, status: 'active_curated' }
    };

    service.getHealth().subscribe((health) => {
      expect(health.youtube.is_configured).toBe(false);
      expect(health.documentation_catalog.total_technologies).toBe(26);
    });

    const req = httpMock.expectOne(`${API_URL}/health`);
    expect(req.request.method).toBe('GET');
    req.flush(mockHealth);
  });
});

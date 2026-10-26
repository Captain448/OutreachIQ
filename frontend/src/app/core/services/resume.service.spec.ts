import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ResumeService } from './resume.service';
import { Resume } from '../models/resume.model';

describe('ResumeService', () => {
  let service: ResumeService;
  let httpMock: HttpTestingController;
  const API_URL = 'http://localhost:8000/api/v1/resumes';

  const mockResume: Resume = {
    id: 'res-123',
    user_id: 'usr-456',
    title: 'Senior Engineer',
    target_role: 'Backend',
    is_preferred: true,
    is_active: true,
    filename: 'resume.pdf',
    original_filename: 'resume.pdf',
    file_size: 15000,
    mime_type: 'application/pdf',
    parsing_status: 'parsed',
    parsing_confidence: 0.92,
    extracted_skills: [{ name: 'Python', category: 'Backend', status: 'verified', source: 'text', confidence_score: 0.95 }],
    extracted_education: [],
    extracted_experience: [],
    extracted_projects: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z'
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ResumeService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });
    service = TestBed.inject(ResumeService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should unpack a direct JSON array of resumes', () => {
    service.getResumes().subscribe((resumes) => {
      expect(Array.isArray(resumes)).toBe(true);
      expect(resumes.length).toBe(1);
      expect(resumes[0].title).toBe('Senior Engineer');
    });

    const req = httpMock.expectOne(API_URL);
    expect(req.request.method).toBe('GET');
    req.flush([mockResume]); // Direct array response
  });

  it('should unpack resumes wrapped in a "resumes" field', () => {
    service.getResumes().subscribe((resumes) => {
      expect(Array.isArray(resumes)).toBe(true);
      expect(resumes.length).toBe(1);
      expect(resumes[0].id).toBe('res-123');
    });

    const req = httpMock.expectOne(API_URL);
    req.flush({ resumes: [mockResume] });
  });

  it('should unpack resumes wrapped in an "items" field', () => {
    service.getResumes().subscribe((resumes) => {
      expect(Array.isArray(resumes)).toBe(true);
      expect(resumes.length).toBe(1);
    });

    const req = httpMock.expectOne(API_URL);
    req.flush({ items: [mockResume] });
  });

  it('should fallback to empty array on unrecognized response body', () => {
    service.getResumes().subscribe((resumes) => {
      expect(Array.isArray(resumes)).toBe(true);
      expect(resumes.length).toBe(0);
    });

    const req = httpMock.expectOne(API_URL);
    req.flush(null);
  });
});

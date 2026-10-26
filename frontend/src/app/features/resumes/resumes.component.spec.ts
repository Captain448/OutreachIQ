import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ResumesComponent } from './resumes.component';
import { ResumeService } from '../../core/services/resume.service';
import { Resume } from '../../core/models/resume.model';

describe('ResumesComponent', () => {
  let component: ResumesComponent;
  let fixture: ComponentFixture<ResumesComponent>;
  let resumeServiceSpy: any;

  const mockResumes: Resume[] = [
    {
      id: 'res-1',
      user_id: 'usr-1',
      title: 'Senior AI Engineer Resume',
      target_role: 'AI Engineer',
      is_preferred: true,
      is_active: true,
      filename: 'resume1.pdf',
      original_filename: 'resume1.pdf',
      file_size: 24500,
      mime_type: 'application/pdf',
      parsing_status: 'parsed',
      parsing_confidence: 0.95,
      parsing_notes: 'Extracted cleanly',
      parsed_text: 'Jordan Doe AI Engineer...',
      extracted_skills: [
        {
          name: 'Python',
          category: 'Languages',
          status: 'verified',
          source: 'text',
          evidence: 'Built microservices',
          confidence_score: 0.95
        }
      ],
      extracted_education: [{ raw_entry: 'BS Computer Science', source: 'text' }],
      extracted_experience: [{ raw_entry: 'Senior AI Engineer at Tech Corp', source: 'text' }],
      extracted_projects: [{ raw_entry: 'Built LLM Agent', source: 'text' }],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z'
    },
    {
      id: 'res-2',
      user_id: 'usr-1',
      title: 'Full Stack Engineer',
      target_role: 'Full Stack Developer',
      is_preferred: false,
      is_active: true,
      filename: 'resume2.docx',
      original_filename: 'resume2.docx',
      file_size: 18200,
      mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      parsing_status: 'parsed',
      parsing_confidence: 0.88,
      parsing_notes: 'Parsed successfully',
      parsed_text: 'Full Stack Developer with Angular...',
      extracted_skills: [
        {
          name: 'TypeScript',
          category: 'Languages',
          status: 'verified',
          source: 'text',
          evidence: 'Angular apps',
          confidence_score: 0.9
        }
      ],
      extracted_education: [],
      extracted_experience: [],
      extracted_projects: [],
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z'
    }
  ];

  beforeEach(async () => {
    resumeServiceSpy = {
      getResumes: () => of(mockResumes),
      uploadResume: () => of({}),
      updateResume: () => of({}),
      deleteResume: () => of({})
    };

    await TestBed.configureTestingModule({
      imports: [ResumesComponent],
      providers: [
        { provide: ResumeService, useValue: resumeServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ResumesComponent);
    component = fixture.componentInstance;
  });

  it('should initialize and load direct array of resumes on init', () => {
    fixture.detectChanges(); // calls ngOnInit -> loadResumes()

    expect(component.resumes.length).toBe(2);
    expect(component.resumes[0].title).toBe('Senior AI Engineer Resume');
    expect(component.resumes[1].title).toBe('Full Stack Engineer');
    expect(component.loadingResumes).toBe(false);
    expect(component.loadError).toBeNull();
  });

  it('should reset loading state and set loadError when API request fails', () => {
    const errorResponse = {
      error: { detail: 'Internal server error while retrieving resumes' },
      message: 'Http failure response'
    };
    resumeServiceSpy.getResumes = () => throwError(() => errorResponse);

    component.loadResumes();

    expect(component.loadingResumes).toBe(false);
    expect(component.loadError).toBe('Internal server error while retrieving resumes');
    expect(component.resumes.length).toBe(0);
  });

  it('should handle retry when loadResumes is triggered again after failure', () => {
    // First trigger failure
    resumeServiceSpy.getResumes = () => throwError(() => new Error('Network error'));
    component.loadResumes();
    expect(component.loadingResumes).toBe(false);
    expect(component.loadError).toBe('Network error');

    // Then retry and succeed
    resumeServiceSpy.getResumes = () => of(mockResumes);
    component.loadResumes();

    expect(component.loadingResumes).toBe(false);
    expect(component.loadError).toBeNull();
    expect(component.resumes.length).toBe(2);
  });

  it('should normalize partial or malformed resume records safely', () => {
    const rawMalformed = [
      {
        id: 'res-sparse',
        title: null,
        original_filename: 'cv_sparse.pdf',
        file_size: null,
        parsing_confidence: null,
        extracted_skills: null,
        extracted_experience: null,
        extracted_education: null
      }
    ] as any;

    resumeServiceSpy.getResumes = () => of(rawMalformed);
    component.loadResumes();

    expect(component.loadingResumes).toBe(false);
    expect(component.resumes.length).toBe(1);
    const normalized = component.resumes[0];
    expect(normalized.title).toBe('cv_sparse.pdf');
    expect(normalized.file_size).toBe(0);
    expect(normalized.parsing_confidence).toBe(0);
    expect(normalized.extracted_skills).toEqual([]);
    expect(normalized.extracted_experience).toEqual([]);
    expect(normalized.extracted_education).toEqual([]);
  });
});

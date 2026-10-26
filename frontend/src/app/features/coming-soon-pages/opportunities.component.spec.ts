import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { provideRouter } from '@angular/router';
import { OpportunitiesComponent } from './opportunities.component';
import { OpportunityService } from '../../core/services/opportunity.service';
import { ProfileService } from '../../core/services/profile.service';
import { Opportunity } from '../../core/models/opportunity.model';
import { DiscoveryRun } from '../../core/models/discovery.model';

describe('OpportunitiesComponent', () => {
  let component: OpportunitiesComponent;
  let fixture: ComponentFixture<OpportunitiesComponent>;
  let oppServiceSpy: any;
  let profileServiceSpy: any;

  const mockOpportunities: Opportunity[] = [
    {
      id: 'opp-1',
      user_id: 'user-1',
      opportunity_type: 'ADVERTISED',
      status: 'ACTIVE',
      match_score: 0.88,
      evidence_confidence: 0.95,
      recommended_action: 'CONTACT_NOW',
      matched_skills: ['Python', 'PyTorch'],
      missing_skills: [],
      critical_failures: [],
      explanation: 'Strong match for AI/ML Engineer in Mohali.',
      job: {
        id: 'job-1',
        company_name: 'DeepInnovate',
        title: 'Senior AI/ML Engineer',
        normalized_title: 'Senior AI/ML Engineer',
        location: 'Mohali',
        is_remote: false,
        work_arrangement: 'hybrid',
        employment_type: 'full-time',
        description: 'Building deep learning systems with Python and PyTorch.',
        primary_url: 'https://deepinnovate.ai/job1',
        source_urls: ['https://deepinnovate.ai/job1'],
        date_discovered: '2026-01-01T00:00:00Z',
        source_name: 'Company Career Page',
        requirements: []
      },
      company: {
        id: 'comp-1',
        name: 'DeepInnovate',
        headquarters: 'Mohali',
        description: 'AI research startup specializing in deep learning.',
        growth_signal_score: 0.8,
        alignment_score: 0.85,
        signals_summary: 'Series A funding completed.',
        signals_data: [{ signal_type: 'funding_expansion', headline: 'Series A funding', confidence: 0.95, classification: 'startup' }],
        has_advertised_openings: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z'
      },
      evidence_items: [
        {
          id: 'ev-1',
          claim_type: 'OBSERVED_FACT',
          claim_text: 'Confirmed active job posting',
          source_url: 'https://deepinnovate.ai/job1',
          confidence: 0.95,
          retrieval_date: '2026-01-01T00:00:00Z'
        }
      ],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z'
    },
    {
      id: 'opp-2',
      user_id: 'user-1',
      opportunity_type: 'EMERGING',
      status: 'ACTIVE',
      match_score: 0.72,
      evidence_confidence: 0.90,
      recommended_action: 'CONTACT_NOW',
      matched_skills: ['Python'],
      missing_skills: ['FastAPI'],
      critical_failures: [],
      explanation: 'Unadvertised strategic opportunity with cloud startup.',
      company: {
        id: 'comp-2',
        name: 'CloudVector Systems',
        headquarters: 'Bengaluru',
        description: 'Venture-backed cloud startup developing distributed systems.',
        growth_signal_score: 0.75,
        alignment_score: 0.70,
        signals_summary: 'Hiring expansion detected.',
        signals_data: [{ signal_type: 'hiring_need', headline: 'Hiring expansion', confidence: 0.90, classification: 'startup' }],
        has_advertised_openings: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z'
      },
      evidence_items: [],
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z'
    }
  ];

  const mockRun: DiscoveryRun = {
    id: 'run-12345678',
    user_id: 'user-1',
    run_type: 'opportunity_discovery',
    status: 'completed',
    query_params: { target_roles: ['AI/ML Engineer'] },
    providers_queried: ['tavily', 'exa'],
    providers_succeeded: ['tavily', 'exa'],
    providers_failed: [],
    results_discovered_count: 10,
    results_deduplicated_count: 8,
    opportunities_created_count: 2,
    execution_time_seconds: 4.2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z'
  };

  beforeEach(async () => {
    oppServiceSpy = {
      getOpportunities: vi.fn().mockReturnValue(of(mockOpportunities)),
      getDiscoveryRuns: vi.fn().mockReturnValue(of([mockRun])),
      getDiscoveryRunStatus: vi.fn().mockReturnValue(of(mockRun)),
      startDiscovery: vi.fn().mockReturnValue(of(mockRun)),
      autoDiscover: vi.fn().mockReturnValue(of(null)),
      getProviderHealth: vi.fn().mockReturnValue(of([])),
      getFilterSuggestions: vi.fn().mockReturnValue(of({
        locations: ['Bengaluru', 'Mohali', 'Noida'],
        skills: ['Python', 'PyTorch', 'FastAPI']
      })),
      updateStatus: vi.fn().mockImplementation((id: string, status: string) => of({ id, status }))
    };

    profileServiceSpy = {
      getProfile: vi.fn().mockReturnValue(
        of({
          headline: 'AI Engineer',
          preferences: {
            desired_roles: ['AI/ML Engineer'],
            preferred_locations: ['Mohali'],
            remote_preference: 'flexible'
          }
        })
      )
    };

    await TestBed.configureTestingModule({
      imports: [OpportunitiesComponent],
      providers: [
        provideRouter([]),
        { provide: OpportunityService, useValue: oppServiceSpy },
        { provide: ProfileService, useValue: profileServiceSpy }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(OpportunitiesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should load persisted opportunities on page load and display results', () => {
    expect(oppServiceSpy.getOpportunities).toHaveBeenCalled();
    expect(component.opportunities.length).toBe(2);
    expect(component.filteredOpportunities.length).toBe(2);
    expect(component.loading).toBe(false);
  });

  it('should filter opportunities by work arrangement without triggering new discovery run', () => {
    component.filterWorkArrangement = 'hybrid';
    fixture.detectChanges();

    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-1');

    // Discovery API was not called again for local filter
    expect(oppServiceSpy.startDiscovery).not.toHaveBeenCalled();
  });

  it('should filter opportunities by minimum match score', () => {
    component.filterMinScore = 0.80;
    fixture.detectChanges();

    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].match_score).toBe(0.88);
  });

  it('should clear all filters and restore full list when clearAllFilters is called', () => {
    component.filterWorkArrangement = 'remote';
    component.filterMinScore = 0.90;
    component.filterLocation = 'Delhi';
    fixture.detectChanges();

    expect(component.filteredOpportunities.length).toBe(0);
    expect(component.activeFiltersCount).toBeGreaterThan(0);

    component.clearAllFilters();
    fixture.detectChanges();

    expect(component.activeFiltersCount).toBe(0);
    expect(component.filteredOpportunities.length).toBe(2);
  });

  it('should pass newly submitted discovery parameters when triggerDiscovery is invoked', () => {
    component.customRole = 'Robotics Engineer';
    component.customLocation = 'Mohali';
    component.customRemotePref = 'remote';
    component.customLimit = 30;

    component.triggerDiscovery();
    fixture.detectChanges();

    expect(oppServiceSpy.startDiscovery).toHaveBeenCalledWith({
      target_roles: ['Robotics Engineer'],
      locations: ['Mohali'],
      remote_preference: 'remote',
      opportunity_type: undefined,
      limit: 30
    });
  });

  it('should display profile completion notice when auto-discovery reports incomplete profile', () => {
    oppServiceSpy.getOpportunities = vi.fn().mockReturnValue(of([]));
    oppServiceSpy.autoDiscover = vi.fn().mockReturnValue(
      throwError(() => ({
        status: 400,
        error: { detail: 'Please specify desired role at /profile' }
      }))
    );

    component.loadOpportunitiesAndAutoDiscover();
    fixture.detectChanges();

    expect(component.profileMissingWarning).toBe('Please specify desired role at /profile');
  });

  it('should toggle opportunity saved status without errors', () => {
    const opp = component.opportunities[0];
    expect(opp.status).toBe('ACTIVE');

    component.toggleSave(opp);
    expect(oppServiceSpy.updateStatus).toHaveBeenCalledWith('opp-1', 'SAVED');
    expect(opp.status).toBe('SAVED');
    expect(component.savedCount).toBe(1);
  });

  it('should filter opportunities by company classification accurately and immediately', () => {
    // Add an enterprise opportunity
    const enterpriseOpp: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-3',
      company: {
        id: 'comp-3',
        name: 'Google LLC',
        classification: 'enterprise',
        size_range: '10,000+ employees',
        growth_signal_score: 0.9,
        alignment_score: 0.95,
        signals_data: [],
        has_advertised_openings: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z'
      }
    };
    component.opportunities = [...mockOpportunities, enterpriseOpp];
    fixture.detectChanges();

    // 1. Filter by startup
    component.filterClassification = 'startup';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(2);
    expect(component.filteredOpportunities.every((o) => component.getCompanyClassification(o) === 'startup')).toBe(true);

    // 2. Filter by enterprise
    component.filterClassification = 'enterprise';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-3');
    expect(component.filteredOpportunities[0].company?.name).toBe('Google LLC');

    // 3. Filter by smb (none present)
    component.filterClassification = 'smb';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(0);

    // 4. Clear classification filter
    component.filterClassification = '';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(3);
  });

  it('should correctly format company classifications with human-readable labels', () => {
    expect(component.formatClassification('enterprise')).toBe('🏢 MNC / Enterprise');
    expect(component.formatClassification('startup')).toBe('🚀 Startup');
    expect(component.formatClassification('mid_sized')).toBe('🏢 Mid-sized Company');
    expect(component.formatClassification('smb')).toBe('🏬 Small/Medium Business');
    expect(component.formatClassification('unknown')).toBe('🏛️ Unspecified');
    expect(component.formatClassification('')).toBe('🏛️ Unspecified');
  });

  it('should support switching between Mode A (Recommendations) and Mode B (Exploration)', () => {
    // Mode A on load
    expect(component.currentMode).toBe('RECOMMENDATIONS');

    // Trigger exploration run
    component.customRole = 'Data Engineer';
    component.submitDiscoveryRun();
    expect(component.currentMode).toBe('EXPLORATION');
    expect(component.showDiscoveryModal).toBe(false);

    // Switch back to Profile Recommendations
    component.switchToProfileMode();
    expect(component.currentMode).toBe('RECOMMENDATIONS');
    expect(oppServiceSpy.getOpportunities).toHaveBeenCalled();
  });

  it('should manage multi-location chips and custom location input with duplicate prevention', () => {
    component.selectedLocations = ['Bengaluru'];

    // Add city from dropdown
    component.addLocation('Noida');
    expect(component.selectedLocations).toEqual(['Bengaluru', 'Noida']);

    // Prevent duplicate addition (case-insensitive)
    component.addLocation('noida');
    expect(component.selectedLocations.length).toBe(2);

    // Add custom location with whitespace trimming
    component.customLocationInput = '  Greater Noida  ';
    component.addCustomLocation();
    expect(component.selectedLocations).toEqual(['Bengaluru', 'Noida', 'Greater Noida']);
    expect(component.customLocationInput).toBe('');

    // Remove location
    component.removeLocation(1); // remove Noida
    expect(component.selectedLocations).toEqual(['Bengaluru', 'Greater Noida']);

    // Clear all
    component.clearAllLocations();
    expect(component.selectedLocations.length).toBe(0);
  });

  it('should accurately resolve canonical location and disambiguate similar city names', () => {
    const oppNoida: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-noida',
      job: {
        ...mockOpportunities[0].job!,
        location: 'Noida'
      },
      company: {
        ...mockOpportunities[0].company!,
        headquarters: 'Mohali' // Job location overrides company headquarters
      }
    };

    const oppGreaterNoida: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-gn',
      job: {
        ...mockOpportunities[0].job!,
        location: 'Greater Noida'
      }
    };

    const oppDelhi: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-delhi',
      job: {
        ...mockOpportunities[0].job!,
        location: 'Delhi'
      }
    };

    const oppNewDelhi: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-nd',
      job: {
        ...mockOpportunities[0].job!,
        location: 'New Delhi'
      }
    };

    // Canonical location verification
    expect(component.getCanonicalLocation(oppNoida)).toBe('Noida');
    expect(component.getCanonicalLocation(oppGreaterNoida)).toBe('Greater Noida');
    expect(component.getCanonicalLocation(oppDelhi)).toBe('Delhi');
    expect(component.getCanonicalLocation(oppNewDelhi)).toBe('New Delhi');

    // In-memory filter disambiguation
    component.opportunities = [oppNoida, oppGreaterNoida, oppDelhi, oppNewDelhi];

    // Filter by 'Noida' -> must only include Noida, not Greater Noida
    component.filterLocation = 'Noida';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-noida');

    // Filter by 'Greater Noida' -> must only include Greater Noida
    component.filterLocation = 'Greater Noida';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-gn');

    // Filter by 'Delhi' -> must only include Delhi, not New Delhi
    component.filterLocation = 'Delhi';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-delhi');

    // Filter by 'New Delhi' -> must only include New Delhi
    component.filterLocation = 'New Delhi';
    fixture.detectChanges();
    expect(component.filteredOpportunities.length).toBe(1);
    expect(component.filteredOpportunities[0].id).toBe('opp-nd');
  });

  it('should load filter suggestions on init and provide autocomplete dropdowns', () => {
    expect(oppServiceSpy.getFilterSuggestions).toHaveBeenCalled();
    expect(component.locationSuggestions).toContain('Bengaluru');
    expect(component.skillSuggestions).toContain('Python');

    // Filtering location suggestions
    component.filterLocation = 'Moh';
    expect(component.filteredLocationSuggestions).toEqual(['Mohali']);

    // Selecting location suggestion
    component.selectLocationSuggestion('Mohali');
    expect(component.filterLocation).toBe('Mohali');
    expect(component.showLocationSuggestions).toBe(false);

    // Filtering skill suggestions
    component.filterSkill = 'Py';
    expect(component.filteredSkillSuggestions).toContain('Python');
    expect(component.filteredSkillSuggestions).toContain('PyTorch');

    // Selecting skill suggestion
    component.selectSkillSuggestion('PyTorch');
    expect(component.filterSkill).toBe('PyTorch');
    expect(component.showSkillSuggestions).toBe(false);
  });

  it('should handle keyboard navigation in autocomplete combobox', () => {
    component.filterLocation = '';
    component.showLocationSuggestions = true;
    component.selectedLocationIndex = 0;

    // Arrow down
    const arrowDownEvent = new KeyboardEvent('keydown', { key: 'ArrowDown' });
    component.onLocationKeydown(arrowDownEvent);
    expect(component.selectedLocationIndex).toBe(1);

    // Enter to select
    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
    component.onLocationKeydown(enterEvent);
    expect(component.filterLocation).toBe('Mohali');
    expect(component.showLocationSuggestions).toBe(false);

    // Escape closes
    component.showLocationSuggestions = true;
    const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
    component.onLocationKeydown(escEvent);
    expect(component.showLocationSuggestions).toBe(false);
  });

  it('should deduplicate duplicate opportunities client-side', () => {
    const duplicateOpp: Opportunity = {
      ...mockOpportunities[0],
      id: 'opp-duplicate-1',
      job: {
        ...mockOpportunities[0].job!,
        id: 'job-duplicate-1',
        primary_url: 'https://deepinnovate.ai/job1?utm_source=feed'
      }
    };

    const inputList = [mockOpportunities[0], duplicateOpp, mockOpportunities[1]];
    const deduped = component.deduplicateOpportunitiesClientSide(inputList);

    expect(deduped.length).toBe(2);
    expect(deduped[0].id).toBe('opp-1');
    expect(deduped[1].id).toBe('opp-2');
  });
});


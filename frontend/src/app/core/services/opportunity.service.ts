import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Opportunity, OpportunityStatus, OpportunityFilterParams } from '../models/opportunity.model';
import { Company } from '../models/company.model';
import { DiscoveryRun, DiscoveryRunRequest } from '../models/discovery.model';
import { ProviderHealth } from '../models/provider.model';

export interface FilterSuggestions {
  locations: string[];
  skills: string[];
}

@Injectable({
  providedIn: 'root'
})
export class OpportunityService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/opportunities';
  private readonly PROVIDERS_URL = 'http://localhost:8000/api/v1/providers';

  startDiscovery(request: DiscoveryRunRequest): Observable<DiscoveryRun> {
    return this.http.post<DiscoveryRun>(`${this.API_URL}/discovery`, request);
  }

  autoDiscover(): Observable<DiscoveryRun | null> {
    return this.http.post<DiscoveryRun | null>(`${this.API_URL}/auto-discover`, {});
  }

  getDiscoveryRunStatus(runId: string): Observable<DiscoveryRun> {
    return this.http.get<DiscoveryRun>(`${this.API_URL}/discovery/${runId}`);
  }

  getDiscoveryRuns(limit: number = 20, offset: number = 0): Observable<DiscoveryRun[]> {
    const params = new HttpParams().set('limit', limit).set('offset', offset);
    return this.http.get<DiscoveryRun[]>(`${this.API_URL}/runs`, { params });
  }

  getOpportunities(filters?: OpportunityFilterParams): Observable<Opportunity[]> {
    let params = new HttpParams();
    if (filters?.opportunity_type) params = params.set('opportunity_type', filters.opportunity_type);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.recommended_action) params = params.set('recommended_action', filters.recommended_action);
    if (filters?.search) params = params.set('search', filters.search);
    if (filters?.location) params = params.set('location', filters.location);
    if (filters?.work_arrangement) params = params.set('work_arrangement', filters.work_arrangement);
    if (filters?.employment_type) params = params.set('employment_type', filters.employment_type);
    if (filters?.company_classification) params = params.set('company_classification', filters.company_classification);
    if (filters?.min_score !== undefined && filters.min_score !== null) params = params.set('min_score', filters.min_score.toString());
    if (filters?.run_id) params = params.set('run_id', filters.run_id);
    if (filters?.sort_by) params = params.set('sort_by', filters.sort_by);
    if (filters?.limit) params = params.set('limit', filters.limit);
    if (filters?.offset) params = params.set('offset', filters.offset);

    return this.http.get<Opportunity[]>(this.API_URL, { params });
  }

  getOpportunity(id: string): Observable<Opportunity> {
    return this.http.get<Opportunity>(`${this.API_URL}/${id}`);
  }

  updateStatus(id: string, status: OpportunityStatus): Observable<Opportunity> {
    return this.http.patch<Opportunity>(`${this.API_URL}/${id}`, { status });
  }

  getCompanies(hasOpenings?: boolean): Observable<Company[]> {
    let params = new HttpParams();
    if (hasOpenings !== undefined) params = params.set('has_openings', hasOpenings);
    return this.http.get<Company[]>(`${this.API_URL}/companies/all`, { params });
  }

  getCompany(id: string): Observable<Company> {
    return this.http.get<Company>(`${this.API_URL}/companies/${id}`);
  }

  getProviderHealth(): Observable<ProviderHealth[]> {
    return this.http.get<ProviderHealth[]>(`${this.PROVIDERS_URL}/health`);
  }

  getFilterSuggestions(q?: string): Observable<FilterSuggestions> {
    let params = new HttpParams();
    if (q) params = params.set('q', q);
    return this.http.get<FilterSuggestions>(`${this.API_URL}/filter-suggestions`, { params });
  }
}

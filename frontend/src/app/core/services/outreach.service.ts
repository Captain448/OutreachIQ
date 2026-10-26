import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  OutreachDraft,
  OutreachDraftCreate,
  OutreachDraftUpdate,
  OutreachGenerateRequest,
  OutreachDraftListResponse,
  EligibleOpportunitySummary
} from '../models/outreach.model';

@Injectable({
  providedIn: 'root'
})
export class OutreachService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/outreach';

  getEligibleOpportunities(): Observable<EligibleOpportunitySummary[]> {
    return this.http.get<EligibleOpportunitySummary[]>(`${this.API_URL}/opportunities`);
  }

  getDrafts(): Observable<OutreachDraftListResponse> {
    return this.http.get<OutreachDraftListResponse>(`${this.API_URL}/drafts`);
  }

  getDraft(id: string): Observable<OutreachDraft> {
    return this.http.get<OutreachDraft>(`${this.API_URL}/drafts/${id}`);
  }

  createDraft(payload: OutreachDraftCreate): Observable<OutreachDraft> {
    return this.http.post<OutreachDraft>(`${this.API_URL}/drafts`, payload);
  }

  updateDraft(id: string, payload: OutreachDraftUpdate): Observable<OutreachDraft> {
    return this.http.put<OutreachDraft>(`${this.API_URL}/drafts/${id}`, payload);
  }

  regenerateDraft(id: string, payload?: OutreachGenerateRequest): Observable<OutreachDraft> {
    return this.http.post<OutreachDraft>(`${this.API_URL}/drafts/${id}/generate`, payload || {});
  }

  deleteDraft(id: string): Observable<{ status: string; id: string }> {
    return this.http.delete<{ status: string; id: string }>(`${this.API_URL}/drafts/${id}`);
  }
}

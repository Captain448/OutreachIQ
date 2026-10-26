import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CandidateIntelligenceRepresentation } from '../models/intelligence.model';

@Injectable({
  providedIn: 'root'
})
export class IntelligenceService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/profile/intelligence';

  getIntelligence(): Observable<CandidateIntelligenceRepresentation> {
    return this.http.get<CandidateIntelligenceRepresentation>(this.API_URL);
  }
}

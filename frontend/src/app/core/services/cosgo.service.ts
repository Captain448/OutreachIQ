import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  CosgoRun,
  CosgoAction,
  CosgoCoverageMatrixResponse,
  CosgoBenchmarkResponse,
  CosgoOptimizeRequest,
  CosgoBudgetUpdateRequest,
  CosgoActionUpdateProgressRequest
} from '../models/cosgo.model';

@Injectable({
  providedIn: 'root'
})
export class CosgoService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/cosgo';

  getLatestRun(): Observable<CosgoRun> {
    return this.http.get<CosgoRun>(`${this.API_URL}/latest`);
  }

  runOptimization(request?: CosgoOptimizeRequest): Observable<CosgoRun> {
    return this.http.post<CosgoRun>(`${this.API_URL}/optimize`, request || {});
  }

  getRunHistory(limit: number = 10): Observable<CosgoRun[]> {
    const params = new HttpParams().set('limit', limit);
    return this.http.get<CosgoRun[]>(`${this.API_URL}/runs`, { params });
  }

  getActionDetails(actionId: string): Observable<CosgoAction> {
    return this.http.get<CosgoAction>(`${this.API_URL}/actions/${actionId}`);
  }

  updateActionProgress(
    actionId: string,
    payload: CosgoActionUpdateProgressRequest
  ): Observable<CosgoAction> {
    return this.http.patch<CosgoAction>(`${this.API_URL}/actions/${actionId}/progress`, payload);
  }

  updateBudget(payload: CosgoBudgetUpdateRequest): Observable<CosgoRun> {
    return this.http.put<CosgoRun>(`${this.API_URL}/budget`, payload);
  }

  getCoverageMatrix(runId?: string): Observable<CosgoCoverageMatrixResponse> {
    let params = new HttpParams();
    if (runId) {
      params = params.set('run_id', runId);
    }
    return this.http.get<CosgoCoverageMatrixResponse>(`${this.API_URL}/coverage-matrix`, { params });
  }

  getBenchmark(budgetHours: number = 40.0, weeklyBudgetHours: number = 10.0): Observable<CosgoBenchmarkResponse> {
    const params = new HttpParams()
      .set('budget_hours', budgetHours)
      .set('weekly_budget_hours', weeklyBudgetHours);
    return this.http.get<CosgoBenchmarkResponse>(`${this.API_URL}/benchmark`, { params });
  }
}

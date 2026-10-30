import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  LearningOverview,
  BudgetUpdatePayload,
  BudgetUpdateResponse,
  DocResource,
  VideoSearchResponse,
  CourseItem,
  CertificationEntry,
  ProjectBlueprint,
  LearningProviderHealth,
  CosgoLearningDashboardResponse,
  LearningProgressPayload
} from '../models/learning.model';

@Injectable({
  providedIn: 'root'
})
export class LearningService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/learning';

  getCosgoLearningPlan(skill?: string): Observable<CosgoLearningDashboardResponse> {
    let params = new HttpParams();
    if (skill && skill.trim()) {
      params = params.set('skill', skill.trim());
    }
    return this.http.get<CosgoLearningDashboardResponse>(`${this.API_URL}/cosgo-plan`, { params });
  }

  updateLearningProgress(payload: LearningProgressPayload): Observable<{ status: string; skill_progress: any; cosgo_action_progress: any }> {
    return this.http.patch<{ status: string; skill_progress: any; cosgo_action_progress: any }>(`${this.API_URL}/progress`, payload);
  }

  getLearningOverview(): Observable<LearningOverview> {
    return this.http.get<LearningOverview>(`${this.API_URL}/overview`);
  }

  updateWeeklyBudget(weeklyHours: number): Observable<BudgetUpdateResponse> {
    const payload: BudgetUpdatePayload = { weekly_hours: weeklyHours };
    return this.http.put<BudgetUpdateResponse>(`${this.API_URL}/budget`, payload);
  }

  searchDocs(query?: string, limit: number = 20): Observable<DocResource[]> {
    let params = new HttpParams().set('limit', limit);
    if (query && query.trim()) {
      params = params.set('query', query.trim());
    }
    return this.http.get<DocResource[]>(`${this.API_URL}/docs`, { params });
  }

  searchVideos(skill: string, limit: number = 4): Observable<VideoSearchResponse> {
    const params = new HttpParams().set('skill', skill).set('limit', limit);
    return this.http.get<VideoSearchResponse>(`${this.API_URL}/videos`, { params });
  }

  searchCourses(skill?: string, accessType?: string, difficulty?: string): Observable<CourseItem[]> {
    let params = new HttpParams();
    if (skill && skill.trim()) {
      params = params.set('skill', skill.trim());
    }
    if (accessType && accessType.trim()) {
      params = params.set('access_type', accessType.trim());
    }
    if (difficulty && difficulty.trim()) {
      params = params.set('difficulty', difficulty.trim());
    }
    return this.http.get<CourseItem[]>(`${this.API_URL}/courses`, { params });
  }

  getCertifications(skill?: string, role?: string): Observable<CertificationEntry[]> {
    let params = new HttpParams();
    if (skill && skill.trim()) {
      params = params.set('skill', skill.trim());
    }
    if (role && role.trim()) {
      params = params.set('role', role.trim());
    }
    return this.http.get<CertificationEntry[]>(`${this.API_URL}/certifications`, { params });
  }

  getRecommendedProjects(): Observable<ProjectBlueprint[]> {
    return this.http.get<ProjectBlueprint[]>(`${this.API_URL}/projects`);
  }

  getHealth(): Observable<LearningProviderHealth> {
    return this.http.get<LearningProviderHealth>(`${this.API_URL}/health`);
  }
}

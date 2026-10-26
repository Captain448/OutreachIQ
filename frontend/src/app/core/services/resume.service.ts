import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { Resume, ResumeUpdatePayload } from '../models/resume.model';

@Injectable({
  providedIn: 'root'
})
export class ResumeService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/resumes';

  getResumes(): Observable<Resume[]> {
    return this.http.get<any>(this.API_URL).pipe(
      map((res: any) => {
        if (Array.isArray(res)) {
          return res;
        }
        if (res && typeof res === 'object') {
          if (Array.isArray(res.resumes)) return res.resumes;
          if (Array.isArray(res.items)) return res.items;
          if (Array.isArray(res.data)) return res.data;
        }
        return [];
      })
    );
  }

  getResume(id: string): Observable<Resume> {
    return this.http.get<Resume>(`${this.API_URL}/${id}`);
  }

  uploadResume(file: File, title?: string, targetRole?: string, isPreferred: boolean = false): Observable<Resume> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (targetRole) formData.append('target_role', targetRole);
    formData.append('is_preferred', String(isPreferred));

    return this.http.post<Resume>(this.API_URL, formData);
  }

  updateResume(id: string, payload: ResumeUpdatePayload): Observable<Resume> {
    return this.http.put<Resume>(`${this.API_URL}/${id}`, payload);
  }

  deleteResume(id: string): Observable<void> {
    return this.http.delete<void>(`${this.API_URL}/${id}`);
  }
}

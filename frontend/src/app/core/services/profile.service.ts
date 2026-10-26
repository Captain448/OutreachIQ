import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Profile, ProfileUpdatePayload } from '../models/profile.model';

@Injectable({
  providedIn: 'root'
})
export class ProfileService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/profile';

  getProfile(): Observable<Profile> {
    return this.http.get<Profile>(this.API_URL);
  }

  updateProfile(payload: ProfileUpdatePayload): Observable<Profile> {
    return this.http.put<Profile>(this.API_URL, payload);
  }
}

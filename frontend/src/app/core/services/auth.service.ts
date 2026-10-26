import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, of } from 'rxjs';
import { User, TokenResponse, LoginRequest, RegisterRequest } from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  private readonly API_URL = 'http://localhost:8000/api/v1/auth';
  private readonly TOKEN_KEY = 'outreachiq_jwt_token';

  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  private tokenSubject = new BehaviorSubject<string | null>(this.getStoredToken());
  public token$ = this.tokenSubject.asObservable();

  constructor() {
    const token = this.getStoredToken();
    if (token) {
      this.fetchCurrentUser().subscribe();
    }
  }

  get token(): string | null {
    return this.tokenSubject.value;
  }

  get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  get isAuthenticated(): boolean {
    return !!this.getStoredToken();
  }

  private getStoredToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private setStoredToken(token: string | null): void {
    if (token) {
      localStorage.setItem(this.TOKEN_KEY, token);
    } else {
      localStorage.removeItem(this.TOKEN_KEY);
    }
    this.tokenSubject.next(token);
  }

  register(req: RegisterRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.API_URL}/register`, req).pipe(
      tap((res) => {
        this.setStoredToken(res.access_token);
        this.fetchCurrentUser().subscribe();
      })
    );
  }

  login(req: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.API_URL}/login`, req).pipe(
      tap((res) => {
        this.setStoredToken(res.access_token);
        this.fetchCurrentUser().subscribe();
      })
    );
  }

  fetchCurrentUser(): Observable<User | null> {
    const token = this.getStoredToken();
    if (!token) {
      this.currentUserSubject.next(null);
      return of(null);
    }
    return this.http.get<User>(`${this.API_URL}/me`).pipe(
      tap((user) => this.currentUserSubject.next(user)),
      catchError(() => {
        this.logout();
        return of(null);
      })
    );
  }

  logout(): void {
    this.setStoredToken(null);
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }
}

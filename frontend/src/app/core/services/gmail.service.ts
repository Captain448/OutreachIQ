import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  GmailConnection,
  GmailOAuthUrlResponse,
  OutreachEmailPreviewRequest,
  OutreachEmailPreviewResponse,
  OutreachEmailSendRequest,
  OutreachEmailMessage,
  OutreachEmailReply,
  OutreachAutomationSettings,
  OutreachAutomationSettingsUpdate,
  ReplySyncResponse
} from '../models/gmail.model';

@Injectable({
  providedIn: 'root'
})
export class GmailService {
  private http = inject(HttpClient);
  private readonly API_URL = 'http://localhost:8000/api/v1/gmail';

  getConnection(): Observable<GmailConnection | null> {
    return this.http.get<GmailConnection | null>(`${this.API_URL}/connection`);
  }

  getOAuthUrl(): Observable<GmailOAuthUrlResponse> {
    return this.http.get<GmailOAuthUrlResponse>(`${this.API_URL}/oauth/url`);
  }

  exchangeCallback(code: string, state: string): Observable<GmailConnection> {
    return this.http.post<GmailConnection>(`${this.API_URL}/oauth/callback`, { code, state });
  }

  disconnect(): Observable<{ status: string; detail: string }> {
    return this.http.post<{ status: string; detail: string }>(`${this.API_URL}/disconnect`, {});
  }

  previewEmail(req: OutreachEmailPreviewRequest): Observable<OutreachEmailPreviewResponse> {
    return this.http.post<OutreachEmailPreviewResponse>(`${this.API_URL}/preview`, req);
  }

  sendEmail(req: OutreachEmailSendRequest): Observable<OutreachEmailMessage> {
    return this.http.post<OutreachEmailMessage>(`${this.API_URL}/send`, req);
  }

  getMessages(limit: number = 50, offset: number = 0): Observable<OutreachEmailMessage[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<OutreachEmailMessage[]>(`${this.API_URL}/messages`, { params });
  }

  getMessage(id: string): Observable<OutreachEmailMessage> {
    return this.http.get<OutreachEmailMessage>(`${this.API_URL}/messages/${id}`);
  }

  getReplies(messageId?: string): Observable<OutreachEmailReply[]> {
    let params = new HttpParams();
    if (messageId) {
      params = params.set('message_id', messageId);
    }
    return this.http.get<OutreachEmailReply[]>(`${this.API_URL}/replies`, { params });
  }

  syncReplies(): Observable<ReplySyncResponse> {
    return this.http.post<ReplySyncResponse>(`${this.API_URL}/replies/sync`, {});
  }

  getSettings(): Observable<OutreachAutomationSettings> {
    return this.http.get<OutreachAutomationSettings>(`${this.API_URL}/settings`);
  }

  updateSettings(settings: OutreachAutomationSettingsUpdate): Observable<OutreachAutomationSettings> {
    return this.http.put<OutreachAutomationSettings>(`${this.API_URL}/settings`, settings);
  }
}

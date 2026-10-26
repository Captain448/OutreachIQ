export type SendingMode = 'DRAFT_ONLY' | 'REVIEW_BEFORE_SEND' | 'AUTO_SEND_OPT_IN';

export type EmailMessageStatus = 'PENDING' | 'SENDING' | 'SENT' | 'FAILED' | 'OUTCOME_UNKNOWN';

export interface GmailConnection {
  id: string;
  user_id: string;
  email_address: string;
  is_active: boolean;
  scopes: string[];
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GmailOAuthUrlResponse {
  authorization_url: string;
  state: string;
}

export interface OutreachEmailPreviewRequest {
  draft_id: string;
  recipient_email: string;
  recipient_name?: string | null;
  subject?: string | null;
  body?: string | null;
}

export interface OutreachEmailPreviewResponse {
  draft_id: string;
  sender_email: string;
  recipient_email: string;
  recipient_name?: string | null;
  subject: string;
  body: string;
  content_hash: string;
  is_connected: boolean;
  can_send: boolean;
  warnings: string[];
}

export interface OutreachEmailSendRequest {
  draft_id: string;
  recipient_email: string;
  recipient_name?: string | null;
  subject: string;
  body: string;
  approved_content_hash: string;
  idempotency_key?: string | null;
  allow_recent_duplicate?: boolean;
}

export interface OutreachEmailMessage {
  id: string;
  user_id: string;
  draft_id?: string | null;
  sender_email: string;
  recipient_email: string;
  recipient_name?: string | null;
  subject: string;
  body: string;
  content_hash: string;
  idempotency_key: string;
  status: EmailMessageStatus;
  gmail_message_id?: string | null;
  gmail_thread_id?: string | null;
  error_message?: string | null;
  attempt_count: number;
  sent_at?: string | null;
  has_reply: boolean;
  reply_count: number;
  last_reply_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachEmailReply {
  id: string;
  message_id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  from_email: string;
  from_name?: string | null;
  subject: string;
  snippet?: string | null;
  body_preview?: string | null;
  received_at: string;
  is_read: boolean;
  created_at: string;
}

export interface OutreachAutomationSettings {
  id: string;
  user_id: string;
  sending_mode: SendingMode;
  daily_limit: number;
  emails_sent_today: number;
  cooldown_minutes: number;
  last_sent_at?: string | null;
  duplicate_suppression_days: number;
  is_paused: boolean;
  auto_followup_enabled: boolean;
  followup_delay_days: number;
  created_at: string;
  updated_at: string;
}

export interface OutreachAutomationSettingsUpdate {
  sending_mode?: SendingMode;
  daily_limit?: number;
  cooldown_minutes?: number;
  duplicate_suppression_days?: number;
  is_paused?: boolean;
  auto_followup_enabled?: boolean;
  followup_delay_days?: number;
}

export interface ReplySyncResponse {
  synced_threads_count: number;
  new_replies_count: number;
  status: string;
  last_synced_at: string;
}

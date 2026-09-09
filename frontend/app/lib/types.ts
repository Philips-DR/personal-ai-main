// Frontend types — mirrors backend Pydantic models
// Keep in sync with backend/app/models/

export type Intent =
  | "email.read" | "email.triage" | "email.draft" | "email.summarize" | "email.send"
  | "meeting.transcribe" | "meeting.summarize" | "meeting.actions"
  | "task.create" | "task.list" | "task.update" | "task.remind"
  | "brief.generate" | "brief.configure"
  | "github.document"
  | "drive.search" | "drive.read" | "doc.create" | "doc.append" | "sheet.append_row"
  | "learning.plan" | "learning.review" | "learning.prompt" | "life.suggest"
  | "memory.recall" | "general.chat";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface PendingAction {
  action_type: string;
  description: string;
  payload: Record<string, unknown>;
}

export interface ChatRequest {
  message: string;
  conversation_history: Message[];
}

export interface ChatResponse {
  content: string;
  structured: Record<string, unknown> | null;
  pending_actions: PendingAction[];
}

export type TaskStatus = "todo" | "in_progress" | "blocked" | "done" | "snoozed";
export type TaskPriority = "urgent" | "high" | "medium" | "low";

export interface Task {
  id: string;
  title: string;
  description?: string;
  owner: string;
  assignee?: string;
  due_date?: string;
  priority: TaskPriority;
  status: TaskStatus;
  project_name?: string;
  source_type?: string;
  source_quote?: string;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  module: string;
  intent: string | null;
  input_summary: string | null;
  output_summary: string | null;
  metadata: Record<string, unknown>;
  error: string | null;
  duration_ms: number | null;
  created_at: string;
}

export interface AuditPage {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface ModuleMetric {
  module: string;
  total_calls: number;
  error_calls: number;
  avg_duration_ms: number;
  total_input_tokens: number;
  total_output_tokens: number;
}

export interface IntentCount {
  intent: string;
  count: number;
}

export interface Metrics {
  by_module: ModuleMetric[];
  by_intent: IntentCount[];
  total_calls: number;
  total_errors: number;
  total_input_tokens: number;
  total_output_tokens: number;
  avg_duration_ms: number;
}

export interface UserPreferences {
  id: string;
  user_id: string;
  brief_cron: string;
  brief_timezone: string;
  brief_include_learning: boolean;
  brief_include_life: boolean;
  brief_tone: string;
  learning_focus_areas: string[];
  life_focus_areas: string[];
  transcription_provider: string;
  drive_enabled: boolean;
  extra: Record<string, unknown>;
  updated_at: string;
}

export type TriageCategory = "action_needed" | "follow_up" | "fyi" | "newsletter" | "spam";

export interface EmailThread {
  id: string;
  gmail_thread_id: string;
  subject?: string;
  from_name?: string;
  from_address?: string;
  snippet?: string;
  category?: TriageCategory;
  urgency_score?: number;
  summary?: string;
  needs_reply: boolean;
  draft_content?: string;
  draft_status: "none" | "pending_review" | "approved" | "sent";
}

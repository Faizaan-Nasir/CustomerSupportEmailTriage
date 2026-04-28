export type TicketStatus = "open" | "escalated" | "resolved" | string;

export interface TicketListItem {
  id: string;
  customer_email: string;
  subject: string | null;
  status: TicketStatus;
  urgency_score: number;
  priority_label: "uncertain" | "high" | "medium" | "low";
  priority_rank: number;
  created_at: string;
}

export interface InterpretationDetail {
  id: string;
  intent: string | null;
  category: string | null;
  sentiment: string | null;
  urgency: number | null;
  confidence: number | null;
  reasoning: string | null;
  created_at: string;
}

export interface EntityDetail {
  id: string;
  key: string;
  value: string;
  source: string | null;
  confidence: number | null;
  created_at: string;
}

export interface AttachmentDetail {
  id: string;
  file_url: string | null;
  preview_url: string | null;
  parsed_text: string | null;
  created_at: string;
}

export interface MessageDetail {
  id: string;
  sender: string;
  content: string;
  timestamp: string;
}

export interface AgentActionDetail {
  id: string;
  summary: string | null;
  action_plan: string[];
  escalation_target: string | null;
  generated_at: string;
}

export interface TicketDetail {
  id: string;
  customer_email: string;
  subject: string | null;
  body: string | null;
  status: TicketStatus;
  urgency_score: number;
  interaction_count: number;
  created_at: string;
  updated_at: string;
  interpretation: InterpretationDetail | null;
  entities: EntityDetail[];
  required_fields: string[];
  attachments: AttachmentDetail[];
  messages: MessageDetail[];
  agent_action: AgentActionDetail | null;
}

export type AgentActionType = "reply" | "escalate" | "resolve";

export interface AgentActionPayload {
  ticket_id: string;
  action: AgentActionType;
  data: Record<string, unknown>;
}

export interface AgentActionResponse {
  ticket_id: string;
  action: AgentActionType;
  status: TicketStatus;
  message_id: string | null;
}

export interface EntityUpdatePayload {
  key: string;
  value: string;
  source?: string | null;
  confidence?: number | null;
}

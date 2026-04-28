import type {
  AgentActionPayload,
  AgentActionResponse,
  EntityDetail,
  EntityUpdatePayload,
  TicketDetail,
  TicketListItem,
} from "../types/ticket";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

function buildUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    // Fall through to generic message.
  }

  return `Request failed with status ${response.status}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as T;
}

export async function fetchTickets(): Promise<TicketListItem[]> {
  return requestJson<TicketListItem[]>("/tickets");
}

export async function fetchTicketById(ticketId: string): Promise<TicketDetail> {
  return requestJson<TicketDetail>(`/tickets/${ticketId}`);
}

export async function sendAgentAction(
  payload: AgentActionPayload,
): Promise<AgentActionResponse> {
  return requestJson<AgentActionResponse>("/agent/action", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface SimulatedEmailPayload {
  customer_email: string;
  subject: string;
  body: string;
  attachments?: File[];
  thread_id?: string;
}

export interface SimulatedEmailResponse {
  ticket_id: string;
  status: string;
  email_body?: string;
  escalated?: boolean;
  escalation_target?: string;
}

export async function submitSimulatedEmail(
  payload: SimulatedEmailPayload,
): Promise<SimulatedEmailResponse> {
  const formData = new FormData();
  formData.append("customer_email", payload.customer_email);
  formData.append("subject", payload.subject);
  formData.append("email", payload.body);
  formData.append("sender", "customer");
  if (payload.thread_id) {
    formData.append("thread_id", payload.thread_id);
  }

  for (const attachment of payload.attachments ?? []) {
    formData.append("attachments", attachment);
  }

  const response = await fetch(buildUrl("/ingest/upload"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as SimulatedEmailResponse;
}

export async function updateEntity(
  ticketId: string,
  entityId: string,
  payload: EntityUpdatePayload,
): Promise<EntityDetail> {
  return requestJson<EntityDetail>(`/tickets/${ticketId}/entities/${entityId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resolveAttachmentPreviewUrl(previewUrl: string | null): string | null {
  if (!previewUrl) {
    return null;
  }
  return buildUrl(previewUrl);
}

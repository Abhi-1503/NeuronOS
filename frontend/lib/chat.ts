import { apiFetch } from "@/lib/api-client";

export type Citation = {
  type: "document" | "customer" | "project";
  id: string;
  excerpt: string;
};

export type ConversationSummary = {
  id: string;
  title: string | null;
  updated_at: string;
};

export type ChatMessageHistory = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
};

export type ConversationDetail = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessageHistory[];
};

export type SendMessageResponse = {
  conversation_id: string;
  message: {
    role: "assistant";
    content: string;
    citations: Citation[];
  };
};

export function sendMessage(
  input: { conversation_id?: string; message: string },
  token: string,
): Promise<SendMessageResponse> {
  return apiFetch<SendMessageResponse>("/chat/messages", { method: "POST", body: input, token });
}

export function listConversations(token: string): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>("/chat/conversations", { token });
}

export function getConversation(conversationId: string, token: string): Promise<ConversationDetail> {
  return apiFetch<ConversationDetail>(`/chat/conversations/${conversationId}`, { token });
}

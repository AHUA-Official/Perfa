const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  temperature?: number;
}

export interface ServerInfo {
  server_id: string;
  ip: string;
  alias?: string;
  status: 'online' | 'offline';
  tags?: string[];
  hardware?: Record<string, any>;
}

export interface WorkflowStatus {
  scenario: string;
  node_statuses: Record<string, string>;
  completed_nodes: string[];
  current_node?: string;
}

export interface ReportInfo {
  id: string;
  type: string;
  server_id: string;
  created_at: string;
  status: string;
  summary?: string;
}

/** 非流式对话 */
export async function chatCompletion(
  messages: ChatMessage[],
  options?: { model?: string; temperature?: number }
): Promise<string> {
  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: options?.model || 'perfa-agent',
      messages,
      stream: false,
      temperature: options?.temperature,
    }),
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

/** 流式对话 — 返回 ReadableStream */
export async function chatCompletionStream(
  messages: ChatMessage[],
  options?: { model?: string; temperature?: number }
): Promise<ReadableStream<Uint8Array>> {
  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: options?.model || 'perfa-agent',
      messages,
      stream: true,
      temperature: options?.temperature,
    }),
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  if (!res.body) throw new Error('No response body');
  return res.body;
}

/** 获取服务器列表 */
export async function listServers(): Promise<ServerInfo[]> {
  const res = await fetch(`${API_BASE}/v1/servers`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.servers || [];
}

/** 获取报告列表 */
export async function listReports(): Promise<ReportInfo[]> {
  const res = await fetch(`${API_BASE}/v1/reports`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.reports || [];
}

/** 获取报告详情 */
export async function getReport(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/reports/${id}`);
  if (!res.ok) throw new Error(`Report not found: ${id}`);
  return res.json();
}

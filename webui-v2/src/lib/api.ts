const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

async function parseApiResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const data = await res.json();
    if (!res.ok) {
      const errorMessage = data?.error || data?.detail || `HTTP ${res.status}`;
      throw new Error(errorMessage);
    }
    return data as T;
  }

  const text = (await res.text()).trim();
  const fallbackMessage = text || `HTTP ${res.status}`;
  throw new Error(fallbackMessage);
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream?: boolean;
  temperature?: number;
  server_id?: string | null;
}

export interface ServerInfo {
  server_id: string;
  ip: string;
  alias?: string;
  status: 'online' | 'offline' | 'unknown';
  tags?: string[];
  hardware?: Record<string, any>;
  agent_id?: string | null;
  agent_port?: number | null;
  agent_status?: string | null;
  agent_version?: string | null;
  current_task?: Record<string, any> | null;
}

export interface AgentActionResult {
  success: boolean;
  error?: string;
  data?: {
    success?: boolean;
    error?: string;
    message?: string;
    agent_id?: string;
    reinstalled?: boolean;
    services?: Record<string, string>;
  };
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
  title?: string;
  scenario?: string;
  scenario_label?: string;
  server_id: string;
  server_alias?: string;
  server_ip?: string;
  created_at: string;
  status: string;
  summary?: string;
  source?: string;
  test_count?: number;
}

export interface ReportDetail {
  id: string;
  type: string;
  title?: string;
  scenario?: string;
  scenario_label?: string;
  server_id: string;
  server_alias?: string;
  server_ip?: string;
  created_at: string;
  status: string;
  summary?: string;
  ai_report?: string;
  content?: any;
  raw_results?: Record<string, any>;
  raw_errors?: Array<Record<string, any>>;
  knowledge_matches?: Array<Record<string, any>>;
  task_ids?: Record<string, string>;
  tool_calls?: Array<Record<string, any>>;
  trace_id?: string;
  query?: string;
  source?: string;
  charts?: any;
}

export interface TraceSummary {
  trace_id: string;
  span_count: number;
  error_count: number;
  spans: Array<{
    id: string;
    operation: string;
    service?: string;
    duration_ms: number;
    status: 'ok' | 'error';
    tags: Record<string, any>;
  }>;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  message_count: number;
  created_at?: string;
  last_active?: string;
  last_user_message?: string;
}

export interface SessionDetail {
  session_id: string;
  title: string;
  message_count: number;
  created_at?: string;
  last_active?: string;
  last_user_message?: string;
  messages: Array<{
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    timestamp?: string;
    metadata?: Record<string, any>;
  }>;
}

/** 非流式对话 */
export async function chatCompletion(
  messages: ChatMessage[],
  options?: { model?: string; temperature?: number; serverId?: string | null }
): Promise<string> {
  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: options?.model || 'perfa-agent',
        messages,
        stream: false,
        temperature: options?.temperature,
        server_id: options?.serverId || undefined,
      }),
    });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

/** 流式对话 — 返回 ReadableStream */
export async function chatCompletionStream(
  messages: ChatMessage[],
  options?: { model?: string; temperature?: number; serverId?: string | null }
): Promise<ReadableStream<Uint8Array>> {
  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: options?.model || 'perfa-agent',
        messages,
        stream: true,
        temperature: options?.temperature,
        server_id: options?.serverId || undefined,
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

export async function deployServerAgent(
  serverId: string,
  options?: { forceReinstall?: boolean; agentOnly?: boolean }
): Promise<AgentActionResult> {
  const res = await fetch(`${API_BASE}/v1/servers/${serverId}/agent/deploy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      force_reinstall: options?.forceReinstall ?? false,
      agent_only: options?.agentOnly ?? true,
    }),
  });
  return parseApiResponse<AgentActionResult>(res);
}

export async function uninstallServerAgent(
  serverId: string,
  options?: { keepData?: boolean }
): Promise<AgentActionResult> {
  const res = await fetch(`${API_BASE}/v1/servers/${serverId}/agent/uninstall`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      keep_data: options?.keepData ?? true,
    }),
  });
  return parseApiResponse<AgentActionResult>(res);
}

export async function getServerAgentStatus(serverId: string): Promise<AgentActionResult> {
  const res = await fetch(`${API_BASE}/v1/servers/${serverId}/agent/status`);
  return parseApiResponse<AgentActionResult>(res);
}

/** 获取报告列表 */
export async function listReports(): Promise<ReportInfo[]> {
  const res = await fetch(`${API_BASE}/v1/reports`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.reports || [];
}

/** 获取报告详情 */
export async function getReport(id: string): Promise<ReportDetail> {
  const res = await fetch(`${API_BASE}/v1/reports/${id}`);
  if (!res.ok) throw new Error(`Report not found: ${id}`);
  return res.json();
}

export async function getLatestReport(serverId?: string): Promise<ReportDetail | null> {
  const reports = await listReports();
  const filtered = serverId ? reports.filter((report) => report.server_id === serverId) : reports;
  const latest = filtered
    .slice()
    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime())[0];
  if (!latest) return null;
  return getReport(latest.id);
}

export async function getTraceSummary(traceId: string): Promise<TraceSummary> {
  const res = await fetch(`/api/monitor/jaeger/api/traces/${traceId}`);
  if (!res.ok) throw new Error(`Trace not found: ${traceId}`);
  const data = await res.json();
  const trace = data.data?.[0];
  const spans = (trace?.spans || []).map((span: any) => {
    const tags = Object.fromEntries((span.tags || []).map((tag: any) => [tag.key, tag.value]));
    return {
      id: span.spanID,
      operation: span.operationName,
      service: span.process?.serviceName,
      duration_ms: Math.round((span.duration || 0) / 1000),
      status: tags.error ? 'error' : 'ok',
      tags,
    };
  });

  return {
    trace_id: traceId,
    span_count: spans.length,
    error_count: spans.filter((span: any) => span.status === 'error').length,
    spans,
  };
}

/** 获取真实会话列表 */
export async function listSessions(): Promise<SessionSummary[]> {
  const res = await fetch(`${API_BASE}/v1/sessions`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.sessions || [];
}

/** 获取单个会话完整历史 */
export async function getSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`${API_BASE}/v1/sessions/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${sessionId}`);
  return res.json();
}

/** 删除单个会话 */
export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/v1/sessions/${sessionId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete session: ${sessionId}`);
}

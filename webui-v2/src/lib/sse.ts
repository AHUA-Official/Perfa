/**
 * SSE 流式解析器 — 双通道架构
 *
 * delta.content: 只承载最终答案文本
 * metadata: 承载过程事件（thinking/tool/workflow/summary 等）
 */

export interface ProcessEvent {
  type: 'thinking_start' | 'thinking_result' | 'tool_result' | 'workflow_progress' | 'answer_start' | 'answer_done' | 'summary';
  iteration?: number;
  reasoning_preview?: string;
  is_final?: boolean;
  tool_name?: string;
  tool_args?: Record<string, any>;
  success?: boolean;
  summary?: string;
  execution_time?: number;
  current_node?: string;
  status?: string;
  scenario?: string;
  mode?: string;
  tool_calls_count?: number;
  is_success?: boolean;
}

export interface SSEChunk {
  /** 正文增量（只来自 answer_delta） */
  content: string;
  done: boolean;
  /** 过程事件（metadata 通道） */
  event?: ProcessEvent;
  session_id?: string;
  conversation_id?: string;
  trace_id?: string;
  jaeger_url?: string;
  workflow?: {
    scenario: string;
    node_statuses: Record<string, string>;
    completed_nodes: string[];
    current_node?: string;
  };
}

export function parseSSEEventBlock(block: string): SSEChunk | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).replace(/^ /, ''))
    .join('\n');

  if (!data) return null;
  if (data === '[DONE]') return { content: '', done: true };

  try {
    const parsed = JSON.parse(data);
    const delta = parsed.choices?.[0]?.delta;
    const content = delta?.content || '';

    const session_id = parsed.session_id || undefined;
    const conversation_id = parsed.conversation_id || undefined;
    const trace_id = parsed.trace_id || undefined;
    const jaeger_url = parsed.jaeger_url || undefined;
    const workflow = parsed.workflow || undefined;

    // 解析 metadata 事件
    let event: ProcessEvent | undefined;
    if (parsed.metadata && parsed.metadata.type) {
      const m = parsed.metadata;
      event = {
        type: m.type,
        iteration: m.iteration,
        reasoning_preview: m.reasoning_preview,
        is_final: m.is_final,
        tool_name: m.tool_name,
        tool_args: m.tool_args,
        success: m.success,
        summary: m.summary,
        execution_time: m.execution_time,
        current_node: m.current_node,
        status: m.status,
        scenario: m.scenario,
        mode: m.mode,
        tool_calls_count: m.tool_calls_count,
        is_success: m.is_success,
      };
    }

    return {
      content,
      done: false,
      event,
      session_id,
      conversation_id,
      trace_id,
      jaeger_url,
      workflow,
    };
  } catch {
    return null;
  }
}

/**
 * 从 ReadableStream 中逐块读取 SSE 事件
 */
export async function consumeSSEStream(
  stream: ReadableStream<Uint8Array>,
  onChunk: (chunk: SSEChunk) => void,
  onDone?: () => void
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        const chunk = parseSSEEventBlock(block);
        if (!chunk) continue;

        onChunk(chunk);
        if (chunk.done) {
          onDone?.();
          return;
        }
      }
    }

    if (buffer.trim()) {
      const chunk = parseSSEEventBlock(buffer);
      if (chunk) {
        onChunk(chunk);
      }
    }

    onDone?.();
  } finally {
    reader.releaseLock();
  }
}

/**
 * SSE 流式解析器 — 解析 OpenAI 兼容格式的 SSE chunks
 *
 * 格式:
 *   data: {"choices":[{"delta":{"content":"xxx"}}]}
 *   data: {"choices":[...], "trace_id":"xxx", "jaeger_url":"xxx", "workflow":{...}}
 *   data: [DONE]
 */

export interface SSEChunk {
  content: string;
  done: boolean;
  metadata?: Record<string, any>;
  trace_id?: string;
  jaeger_url?: string;
  workflow?: {
    scenario: string;
    node_statuses: Record<string, string>;
    completed_nodes: string[];
    current_node?: string;
  };
}

export function parseSSELine(line: string): SSEChunk | null {
  if (!line.startsWith('data: ')) return null;
  const data = line.slice(6).trim();
  if (data === '[DONE]') return { content: '', done: true };

  try {
    const parsed = JSON.parse(data);
    const delta = parsed.choices?.[0]?.delta;
    const content = delta?.content || '';

    // 提取 trace_id 和 jaeger_url
    const trace_id = parsed.trace_id || undefined;
    const jaeger_url = parsed.jaeger_url || undefined;

    // 提取工作流元信息
    const workflow = parsed.workflow || undefined;

    // 提取其他元信息
    const metadata = parsed.metadata || undefined;

    return {
      content,
      done: false,
      metadata,
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
 * @param stream fetch Response.body
 * @param onChunk 每个解析出的 chunk 回调
 * @param onDone 流结束回调
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
      const lines = buffer.split('\n');
      // 保留最后一行（可能不完整）
      buffer = lines.pop() || '';

      for (const line of lines) {
        const chunk = parseSSELine(line.trim());
        if (chunk) {
          onChunk(chunk);
          if (chunk.done) {
            onDone?.();
            return;
          }
        }
      }
    }
    onDone?.();
  } finally {
    reader.releaseLock();
  }
}

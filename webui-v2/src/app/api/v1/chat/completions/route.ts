/**
 * SSE 流式代理 — 绕过 Next.js rewrite 的缓冲问题
 *
 * Next.js 的 rewrite 代理会缓冲 SSE 响应，导致前端无法实时收到流式数据。
 * 此 API Route 直接将请求转发到后端，并以 ReadableStream 方式实时回传。
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:10000';

export async function POST(request: Request) {
  const body = await request.json();

  const isStream = body.stream === true;

  const res = await fetch(`${BACKEND_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    return new Response(JSON.stringify({ error: `Backend error: ${res.status}` }), {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  if (!isStream) {
    // 非流式：直接返回 JSON
    const data = await res.json();
    return Response.json(data);
  }

  // 流式：透传 SSE，逐块推送到客户端
  const stream = new ReadableStream({
    async start(controller) {
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      const encoder = new TextEncoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // 立即将每个 chunk 推送给客户端（不做缓冲）
          const chunk = decoder.decode(value, { stream: true });
          controller.enqueue(encoder.encode(chunk));
        }
      } catch (err) {
        console.error('SSE proxy error:', err);
      } finally {
        controller.close();
        reader.releaseLock();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // 防止 nginx 缓冲
    },
  });
}

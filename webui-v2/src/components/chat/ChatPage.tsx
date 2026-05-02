'use client';

import { useCallback, useRef, useEffect, useState } from 'react';
import { Tag, Button, Typography } from 'antd';
import {
  ReloadOutlined,
  DesktopOutlined
} from '@ant-design/icons';
import { useChatStore } from '@/store/useChatStore';
import { getLatestReport, getTraceSummary, listServers, listSessions, ServerInfo } from '@/lib/api';
import { consumeSSEStream } from '@/lib/sse';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import WorkflowProgress from './WorkflowProgress';

const { Text } = Typography;

const SCENARIOS = [
  { label: '🚀 快速测试', prompt: '快速测试服务器性能' },
  { label: '📊 全面评估', prompt: '全面评估服务器性能' },
  { label: '💻 CPU 测试', prompt: '测试CPU性能' },
  { label: '💾 存储测试', prompt: '测试磁盘IO性能' },
  { label: '🌐 网络测试', prompt: '测试网络性能' },
];

export default function ChatPage() {
  const {
    messages, sessionId, conversationId, isLoading,
    addMessage, updateMessage, addEvent, setLoading,
    setSessions, setSessionsLoading, activeSessionId,
  } =
    useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 服务器列表
  const [servers, setServers] = useState<ServerInfo[]>([]);
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [serversLoading, setServersLoading] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadServers = useCallback(async () => {
    setServersLoading(true);
    try {
      const data = await listServers();
      setServers(data);
    } catch {
      setServers([]);
    } finally {
      setServersLoading(false);
    }
  }, []);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const sessions = await listSessions();
      const mappedSessions = sessions.map((session) => ({
          id: session.session_id,
          title: session.title || '新对话',
          createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
          updatedAt: session.last_active ? new Date(session.last_active).getTime() : Date.now(),
          lastUserMessage: session.last_user_message,
        }));
      setSessions(mappedSessions);
    } finally {
      setSessionsLoading(false);
    }
  }, [setSessions, setSessionsLoading]);

  useEffect(() => {
    if (!activeSessionId) {
      void loadSessions();
    }
  }, [activeSessionId, loadSessions]);

  // 停止生成
  const handleStop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    // 标记最后一条正在流式的消息为完成
    const lastStreaming = [...useChatStore.getState().messages].reverse().find((message) => message.isStreaming);
    if (lastStreaming) {
      updateMessage(lastStreaming.id, {
        isStreaming: false,
        content: lastStreaming.content || '（已停止生成）',
      });
    }
  }, [updateMessage, setLoading]);

  const sendMessage = useCallback(
    async (content: string) => {
      // 如果正在加载，忽略
      if (isLoading) return;

      addMessage({ role: 'user', content });

      const assistantId = addMessage({
        role: 'assistant',
        content: '',
        isStreaming: true,
      });

      setLoading(true);

      // 创建 AbortController
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const currentState = useChatStore.getState();
        const history = currentState.messages
          .filter((m) => !m.isStreaming)
          .map((m) => ({ role: m.role, content: m.content }));
        const currentServer =
          servers.find((server) => server.server_id === selectedServer) ||
          servers.find((server) => server.status === 'online');

        const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';
        const res = await fetch(`${API_BASE}/v1/chat/completions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: 'perfa-agent',
            messages: history,
            stream: true,
            session_id: currentState.sessionId || sessionId,
            conversation_id: currentState.conversationId || conversationId || currentState.sessionId || sessionId,
          }),
          signal: controller.signal,
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);
        if (!res.body) throw new Error('No response body');

        const stream = res.body;
        let fullContent = '';
        let workflowStatus: any = null;
        let traceId: string | undefined;
        let jaegerUrl: string | undefined;
        let streamingStarted = false;

        await consumeSSEStream(
          stream,
          (chunk) => {
            if (chunk.session_id) {
              useChatStore.getState().setSessionId(chunk.session_id);
            }
            if (chunk.conversation_id) {
              useChatStore.getState().setConversationId(chunk.conversation_id);
            }
            if (chunk.session_id || chunk.conversation_id) {
              loadSessions();
            }
            // ---- 正文通道：只有 delta.content 才进入主消息 ----
            if (chunk.content) {
              streamingStarted = true;
              fullContent += chunk.content;
              updateMessage(assistantId, {
                content: fullContent,
                isStreaming: true,
                serverId: currentServer?.server_id,
              });
            }
            // ---- 过程事件通道：metadata 事件进入 events 列表 ----
            if (chunk.event) {
              const evt = chunk.event;
              // summary 事件特殊处理 → 存到 message.summary
              if (evt.type === 'summary') {
                updateMessage(assistantId, {
                  summary: {
                    mode: evt.mode || 'react',
                    execution_time: evt.execution_time || 0,
                    tool_calls_count: evt.tool_calls_count || 0,
                    is_success: evt.is_success ?? true,
                  },
                });
              } else {
                addEvent(assistantId, evt);
              }
            }
            if (chunk.workflow) {
              workflowStatus = chunk.workflow;
              updateMessage(assistantId, { workflowStatus, serverId: currentServer?.server_id });
            }
            if (chunk.trace_id) {
              traceId = chunk.trace_id;
              updateMessage(assistantId, { traceId });
            }
            if (chunk.jaeger_url) {
              jaegerUrl = chunk.jaeger_url;
              updateMessage(assistantId, { jaegerUrl });
            }
          },
          () => {
            updateMessage(assistantId, {
              isStreaming: false,
              content: fullContent || (streamingStarted ? fullContent : '（本次响应没有返回正文）'),
              workflowStatus: workflowStatus || undefined,
              traceId,
              jaegerUrl,
              serverId: currentServer?.server_id,
            });
          }
        );

        const enrichTasks: Promise<void>[] = [];
        if (traceId) {
          enrichTasks.push(
            getTraceSummary(traceId)
              .then((traceSummary) => {
                updateMessage(assistantId, { traceSummary });
              })
              .catch(() => undefined)
          );
        }
        if (currentServer?.server_id) {
          enrichTasks.push(
            getLatestReport(currentServer.server_id)
              .then((report) => {
                if (report) {
                  updateMessage(assistantId, { report });
                }
              })
              .catch(() => undefined)
          );
        }
        await Promise.all(enrichTasks);
      } catch (err: any) {
        if (err.name === 'AbortError') {
          // 用户主动停止
          const currentMessages = useChatStore.getState().messages;
          const existingContent = currentMessages.find((message) => message.id === assistantId)?.content || '';
          updateMessage(assistantId, {
            isStreaming: false,
            content: existingContent ? `${existingContent}\n\n*⏹ 已停止生成*` : '⏹ 已停止生成',
          });
        } else {
          updateMessage(assistantId, {
            content: `❌ 请求失败: ${err.message}`,
            isStreaming: false,
          });
        }
      } finally {
        setLoading(false);
        abortControllerRef.current = null;
        loadSessions();
      }
    },
    [addMessage, updateMessage, setLoading, isLoading, sessionId, conversationId, loadSessions]
  );

  // 点击服务器 IP → 在对话中插入 "测试 <ip> 服务器"
  const handleServerClick = useCallback((server: ServerInfo) => {
    setSelectedServer(server.server_id);
    const prompt = server.alias
      ? `对服务器 ${server.alias} (${server.ip}) 执行性能测试`
      : `对服务器 ${server.ip} 执行性能测试`;
    sendMessage(prompt);
  }, [sendMessage]);

  const lastAssistantMsg = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant');
  const workflowStatus = lastAssistantMsg?.workflowStatus;

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* 左侧：服务器列表 */}
      <div className="w-[240px] bg-bg-card border-r border-white/5 flex flex-col shrink-0">
        <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
          <Text className="!text-text-secondary text-xs font-medium uppercase tracking-wide">
            服务器
          </Text>
          <Button
            type="text"
            icon={<ReloadOutlined />}
            size="small"
            className="!text-text-muted"
            onClick={loadServers}
            loading={serversLoading}
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          {servers.length === 0 ? (
            <div className="px-4 py-8 text-center">
              <DesktopOutlined className="text-2xl text-text-muted mb-2" />
              <p className="text-xs text-text-muted">暂无服务器</p>
              <p className="text-xs text-text-muted">
                去<em className="text-primary not-italic">服务器管理</em>注册
              </p>
            </div>
          ) : (
            <div className="py-1">
              {servers.map((server) => {
                const isSelected = selectedServer === server.server_id;
                const statusColor = server.status === 'online' ? '#34A853' : '#EA4335';
                const isOffline = server.status !== 'online';
                return (
                  <div
                    key={server.server_id}
                    className={`px-4 py-2.5 cursor-pointer transition-colors group
                      ${isSelected ? 'bg-primary/10 border-l-2 border-l-primary' : 'border-l-2 border-l-transparent'}
                      ${isOffline ? 'opacity-60 cursor-not-allowed' : 'hover:bg-bg-hover'}`}
                    onClick={() => !isLoading && !isOffline && handleServerClick(server)}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: statusColor }}
                      />
                      <Text
                        code
                        className={`!text-xs ${isSelected ? '!text-primary' : '!text-text-primary'}`}
                      >
                        {server.ip}
                      </Text>
                    </div>
                    {server.alias && (
                      <div className="ml-4 mt-0.5">
                        <Text className="!text-text-secondary text-xs">{server.alias}</Text>
                      </div>
                    )}
                    {server.tags && server.tags.length > 0 && (
                      <div className="ml-4 mt-1 flex flex-wrap gap-1">
                        {server.tags.slice(0, 2).map((t) => (
                          <Tag key={t} color="cyan" className="!text-[10px] !px-1 !py-0 !m-0">
                            {t}
                          </Tag>
                        ))}
                      </div>
                    )}
                    {isOffline && (
                      <div className="ml-4 mt-1">
                        <Text className="!text-[11px] !text-text-muted">离线服务器暂不支持直接发起测试</Text>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-white/5">
          <Text className="!text-text-muted text-xs">
            {servers.length} 台服务器 · {servers.filter(s => s.status === 'online').length} 在线
          </Text>
        </div>
      </div>

      {/* 右侧：对话区 */}
      <div className="chat-container flex-1">
        {workflowStatus && <WorkflowProgress status={workflowStatus} />}

        <div className="messages-area">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-text-muted">
              <div className="text-6xl mb-4 animate-fade-in">🖥️</div>
              <h2 className="text-xl font-medium text-text-secondary mb-2 animate-fade-in-delay-1">
                Perfa 性能测试平台
              </h2>
              <p className="text-sm text-text-muted mb-2 animate-fade-in-delay-2">
                输入指令或选择快捷场景开始测试
              </p>
              <p className="text-xs text-text-muted mb-6 animate-fade-in-delay-3">
                点击左侧服务器 IP 可直接对该服务器发起测试
              </p>
              <div className="flex flex-wrap gap-2 justify-center animate-fade-in-delay-4">
                {SCENARIOS.map((s) => (
                  <button
                    key={s.label}
                    className="scenario-btn"
                    onClick={() => sendMessage(s.prompt)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        <ChatInput
          onSend={sendMessage}
          onStop={handleStop}
          isLoading={isLoading}
          scenarios={SCENARIOS}
        />
      </div>
    </div>
  );
}

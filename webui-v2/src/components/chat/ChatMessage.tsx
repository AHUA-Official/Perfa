'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message, ProcessEvent } from '@/store/useChatStore';
import { UserOutlined, RobotOutlined, LinkOutlined, ClockCircleOutlined, ToolOutlined, ThunderboltOutlined, DownOutlined, RightOutlined, FileSearchOutlined, NodeIndexOutlined } from '@ant-design/icons';
import { Button, Tag, Tooltip } from 'antd';
import { useState } from 'react';
import ResultCard from './ResultCard';

interface Props {
  message: Message;
}

/** 过程事件时间线条目 */
function EventItem({ event }: { event: ProcessEvent }) {
  const icon = (() => {
    switch (event.type) {
      case 'thinking_start':
        return <span className="text-blue-400">🔄</span>;
      case 'thinking_result':
        return event.is_final ? <span className="text-green-400">✅</span> : <span className="text-yellow-400">💭</span>;
      case 'tool_result':
        return event.success ? <span className="text-green-400">🔧</span> : <span className="text-red-400">❌</span>;
      case 'workflow_progress':
        return <span className="text-purple-400">📋</span>;
      default:
        return <span>•</span>;
    }
  })();

  const text = (() => {
    switch (event.type) {
      case 'thinking_start':
        return `第${event.iteration}轮思考中...`;
      case 'thinking_result':
        if (event.is_final) return '得到最终答案';
        if (event.tool_name) return `调用工具: ${event.tool_name}`;
        return '思考完成';
      case 'tool_result':
        return `${event.tool_name} — ${event.summary || ''} (${event.execution_time}s)`;
      case 'workflow_progress':
        return `[${event.scenario}] ${event.current_node}: ${event.status}`;
      default:
        return '';
    }
  })();

  return (
    <div className="flex items-center gap-2 py-1 text-xs text-text-secondary">
      <span className="shrink-0">{icon}</span>
      <span className="truncate">{text}</span>
    </div>
  );
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';
  const [processExpanded, setProcessExpanded] = useState(false);
  const [insightExpanded, setInsightExpanded] = useState(false);

  // 过程事件（不含 answer_start/answer_done）
  const processEvents = message.events.filter(
    (e) => !e.type.startsWith('answer')
  );

  // 是否有可展示的过程
  const hasProcess = processEvents.length > 0;
  const hasInsights = !!(message.workflowStatus || message.traceSummary || message.report);

  return (
    <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="flex items-start gap-2">
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 ${
            isUser
              ? 'bg-primary/20 text-primary'
              : 'bg-info/20 text-info'
          }`}
        >
          {isUser ? <UserOutlined /> : <RobotOutlined />}
        </div>
        <div className="flex-1 min-w-0">
          {isUser ? (
            <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</div>
          ) : (
            <>
              {/* 执行过程（可折叠） */}
              {hasProcess && (
                <div className="mb-2">
                  <button
                    className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
                    onClick={() => setProcessExpanded(!processExpanded)}
                  >
                    {processExpanded ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
                    <ThunderboltOutlined style={{ fontSize: 10 }} />
                    <span>执行过程 ({processEvents.length})</span>
                  </button>
                  {processExpanded && (
                    <div className="mt-1.5 pl-3 border-l-2 border-white/10 space-y-0.5">
                      {processEvents.map((evt, i) => (
                        <EventItem key={i} event={evt} />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 答案正文 */}
              <div className="markdown-body">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ node, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      const inline = !match;
                      return !inline ? (
                        <SyntaxHighlighter
                          style={oneDark as any}
                          language={match[1]}
                          PreTag="div"
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code
                          className="bg-bg-hover px-1.5 py-0.5 rounded text-primary text-[13px]"
                          {...props}
                        >
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
                {message.isStreaming && (
                  <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />
                )}
              </div>

              {hasInsights && (
                <div className="mt-3 rounded-2xl border border-white/8 bg-black/10 px-3 py-3">
                  <button
                    className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
                    onClick={() => setInsightExpanded(!insightExpanded)}
                  >
                    {insightExpanded ? <DownOutlined style={{ fontSize: 10 }} /> : <RightOutlined style={{ fontSize: 10 }} />}
                    <NodeIndexOutlined style={{ fontSize: 10 }} />
                    <span>会话联动视图</span>
                  </button>

                  {insightExpanded && (
                    <div className="mt-3 grid grid-cols-1 xl:grid-cols-3 gap-3">
                      {message.workflowStatus && (
                        <ResultCard
                          title="Workflow"
                          data={{
                            scenario: message.workflowStatus.scenario,
                            current_node: message.workflowStatus.current_node || '—',
                            completed_nodes: message.workflowStatus.completed_nodes.length,
                          }}
                        >
                          <div className="space-y-2 text-xs">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Tag color="blue">{message.workflowStatus.scenario}</Tag>
                              <Tag color="gold">当前节点: {message.workflowStatus.current_node || '—'}</Tag>
                            </div>
                            <div className="space-y-1">
                              {Object.entries(message.workflowStatus.node_statuses).map(([node, status]) => (
                                <div key={node} className="flex items-center justify-between rounded-lg bg-white/5 px-2 py-1">
                                  <span className="text-text-secondary">{node}</span>
                                  <Tag color={status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'blue'} className="!m-0">
                                    {status}
                                  </Tag>
                                </div>
                              ))}
                            </div>
                          </div>
                        </ResultCard>
                      )}

                      {message.traceSummary && (
                        <ResultCard
                          title="Trace"
                          data={{
                            trace_id: message.traceSummary.trace_id,
                            span_count: message.traceSummary.span_count,
                            error_count: message.traceSummary.error_count,
                          }}
                        >
                          <div className="space-y-2 text-xs">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Tag color="cyan">{message.traceSummary.span_count} spans</Tag>
                              <Tag color={message.traceSummary.error_count > 0 ? 'red' : 'green'}>
                                {message.traceSummary.error_count > 0 ? `${message.traceSummary.error_count} error` : 'clean'}
                              </Tag>
                            </div>
                            <div className="space-y-1">
                              {message.traceSummary.spans.slice(0, 4).map((span) => (
                                <div key={span.id} className="rounded-lg bg-white/5 px-2 py-1">
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="text-text-primary truncate">{span.operation}</span>
                                    <span className="text-text-muted">{span.duration_ms}ms</span>
                                  </div>
                                  {span.service && (
                                    <div className="text-text-muted mt-0.5 truncate">{span.service}</div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </ResultCard>
                      )}

                      {message.report && (
                        <ResultCard
                          title="Report"
                          data={{
                            type: message.report.type,
                            status: message.report.status,
                            created_at: message.report.created_at,
                          }}
                        >
                          <div className="space-y-2 text-xs">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Tag color="purple">{message.report.type}</Tag>
                              <Tag color={message.report.status === 'completed' ? 'green' : 'blue'}>
                                {message.report.status}
                              </Tag>
                            </div>
                            <div className="text-text-secondary line-clamp-4">
                              {message.report.summary || '这次响应关联的最新报告暂无摘要。'}
                            </div>
                          </div>
                        </ResultCard>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* 底部元信息 */}
              {!message.isStreaming && (message.jaegerUrl || message.summary) && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5 flex-wrap">
                  {message.summary && (
                    <>
                      <Tag color={message.summary.mode === 'workflow' ? 'blue' : 'green'} className="!text-[10px] !px-1.5 !py-0 !m-0">
                        {message.summary.mode === 'workflow' ? '工作流' : 'ReAct'}
                      </Tag>
                      <span className="text-text-muted text-[11px] flex items-center gap-1">
                        <ClockCircleOutlined style={{ fontSize: 10 }} />
                        {message.summary.execution_time}s
                      </span>
                      {message.summary.tool_calls_count > 0 && (
                        <span className="text-text-muted text-[11px] flex items-center gap-1">
                          <ToolOutlined style={{ fontSize: 10 }} />
                          {message.summary.tool_calls_count}次调用
                        </span>
                      )}
                    </>
                  )}
                  {message.jaegerUrl && (
                    <Tooltip title={`Trace: ${message.traceId}`}>
                      <Button
                        type="link"
                        size="small"
                        icon={<LinkOutlined />}
                        className="!text-primary !p-0 !h-auto !text-[11px]"
                        onClick={() => window.open(message.jaegerUrl, '_blank', 'noopener,noreferrer')}
                      >
                        Trace
                      </Button>
                    </Tooltip>
                  )}
                  {message.report && (
                    <Tag color="purple" className="!text-[10px] !px-1 !py-0 !m-0">
                      <FileSearchOutlined /> 报告已联动
                    </Tag>
                  )}
                  {message.workflowStatus && (
                    <Tag color="blue" className="!text-[10px] !px-1 !py-0 !m-0">
                      {message.workflowStatus.scenario}
                    </Tag>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

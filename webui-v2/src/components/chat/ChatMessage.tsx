'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message } from '@/store/useChatStore';
import { UserOutlined, RobotOutlined, LinkOutlined } from '@ant-design/icons';
import { Button, Tag, Tooltip } from 'antd';

interface Props {
  message: Message;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user';

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
          )}

          {/* AI 回复底部：Trace 链接 + 执行模式 */}
          {!isUser && !message.isStreaming && message.jaegerUrl && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5">
              <Tooltip title={`Trace ID: ${message.traceId}`}>
                <Button
                  type="link"
                  size="small"
                  icon={<LinkOutlined />}
                  className="!text-primary !p-0 !h-auto !text-xs"
                  onClick={() => window.open(`http://localhost:16686/trace/${message.traceId}`, '_blank')}
                >
                  查看 Trace 链路
                </Button>
              </Tooltip>
              {message.workflowStatus && (
                <Tag color="blue" className="!text-[10px] !px-1 !py-0 !m-0">
                  工作流: {message.workflowStatus.scenario}
                </Tag>
              )}
              {!message.workflowStatus && (
                <Tag color="green" className="!text-[10px] !px-1 !py-0 !m-0">
                  ReAct 模式
                </Tag>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

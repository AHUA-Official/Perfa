'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Input, Button, Tooltip } from 'antd';
import { SendOutlined, StopOutlined } from '@ant-design/icons';

interface Scenario {
  label: string;
  prompt: string;
}

interface Props {
  onSend: (content: string) => void;
  onStop: () => void;
  isLoading: boolean;
  scenarios: Scenario[];
}

export default function ChatInput({ onSend, onStop, isLoading, scenarios }: Props) {
  const [input, setInput] = useState('');
  const inputRef = useRef<any>(null);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput('');
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && input.trim()) {
        handleSend();
      }
    }
  };

  return (
    <div className="chat-input-area">
      <div className="scenario-buttons">
        {scenarios.slice(0, 5).map((s) => (
          <button
            key={s.label}
            className={`scenario-btn ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={() => !isLoading && onSend(s.prompt)}
            disabled={isLoading}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="flex gap-2 items-end">
        <Input.TextArea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isLoading ? 'AI 正在思考中...' : '输入指令，如：测试 CPU 性能...'}
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={isLoading}
          className="!bg-bg-main !border-white/10 !text-text-primary !resize-none transition-all duration-200"
        />
        {isLoading ? (
          <Tooltip title="停止生成">
            <Button
              danger
              icon={<StopOutlined />}
              onClick={onStop}
              className="!h-auto stop-button"
            />
          </Tooltip>
        ) : (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!input.trim()}
            className="!h-auto send-button"
          />
        )}
      </div>
    </div>
  );
}

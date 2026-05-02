import { create } from 'zustand';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  /** 工作流进度信息 */
  workflowStatus?: {
    scenario: string;
    node_statuses: Record<string, string>;
    completed_nodes: string[];
    current_node?: string;
  };
  /** 是否正在流式接收 */
  isStreaming?: boolean;
  /** OTel trace ID */
  traceId?: string;
  /** Jaeger trace URL */
  jaegerUrl?: string;
}

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;

  addMessage: (msg: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  clearMessages: () => void;
  setSessionId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  sessionId: null,
  isLoading: false,

  addMessage: (msg) => {
    const id = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const timestamp = Date.now();
    set((state) => ({
      messages: [...state.messages, { ...msg, id, timestamp }],
    }));
    return id;
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    }));
  },

  clearMessages: () => set({ messages: [], sessionId: null }),

  setSessionId: (id) => set({ sessionId: id }),
  setLoading: (loading) => set({ isLoading: loading }),
}));

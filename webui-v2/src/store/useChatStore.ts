import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/** 过程事件（与 SSE ProcessEvent 对应） */
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
  timestamp?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  events: ProcessEvent[];
  summary?: {
    mode: string;
    execution_time: number;
    tool_calls_count: number;
    is_success: boolean;
  };
  workflowStatus?: {
    scenario: string;
    node_statuses: Record<string, string>;
    completed_nodes: string[];
    current_node?: string;
  };
  isStreaming?: boolean;
  traceId?: string;
  jaegerUrl?: string;
  serverId?: string;
  report?: {
    id: string;
    type: string;
    status: string;
    created_at: string;
    summary?: string;
    content?: any;
  } | null;
  traceSummary?: {
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
  } | null;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  lastUserMessage?: string;
}

interface ChatState {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: Message[];
  sessionId: string | null;
  conversationId: string | null;
  isLoading: boolean;
  sessionsLoading: boolean;

  setSessions: (sessions: ChatSession[]) => void;
  replaceMessages: (messages: Message[]) => void;
  removeSession: (id: string) => void;
  createSession: () => string;
  switchSession: (id: string, messages?: Message[]) => void;
  addMessage: (msg: Omit<Message, 'id' | 'timestamp' | 'events'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  addEvent: (id: string, event: ProcessEvent) => void;
  clearMessages: () => void;
  setSessionId: (id: string | null) => void;
  setConversationId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setSessionsLoading: (loading: boolean) => void;
}

function makeId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

const memoryStorage = {
  length: 0,
  clear: () => undefined,
  getItem: () => null,
  key: () => null,
  setItem: () => undefined,
  removeItem: () => undefined,
};

function upsertSession(
  sessions: ChatSession[],
  sessionId: string,
  updates: Partial<ChatSession>
) {
  const existing = sessions.find((session) => session.id === sessionId);
  if (!existing) {
    return [{ id: sessionId, title: '新对话', createdAt: Date.now(), updatedAt: Date.now(), ...updates }, ...sessions]
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }

  return sessions
    .map((session) => (session.id === sessionId ? { ...session, ...updates } : session))
    .sort((a, b) => b.updatedAt - a.updatedAt);
}

export const useChatStore = create<ChatState>()(persist((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  sessionId: null,
  conversationId: null,
  isLoading: false,
  sessionsLoading: false,

  setSessions: (sessions) => set({ sessions }),

  replaceMessages: (messages) => set({ messages }),

  removeSession: (id) => set((state) => {
    const nextSessions = state.sessions.filter((session) => session.id !== id);
    const isCurrent = state.activeSessionId === id;
    return {
      sessions: nextSessions,
      activeSessionId: isCurrent ? null : state.activeSessionId,
      sessionId: isCurrent ? null : state.sessionId,
      conversationId: isCurrent ? null : state.conversationId,
      messages: isCurrent ? [] : state.messages,
    };
  }),

  createSession: () => {
    const id = makeId('pending_session');
    set((state) => ({
      activeSessionId: id,
      sessionId: null,
      conversationId: id,
      messages: [],
      sessions: upsertSession(state.sessions, id, {
        title: '新对话',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        lastUserMessage: undefined,
      }),
    }));
    return id;
  },

  switchSession: (id, messages) => {
    set({
      activeSessionId: id,
      sessionId: id.startsWith('pending_session') ? null : id,
      conversationId: id,
      messages: messages ?? get().messages,
    });
  },

  addMessage: (msg) => {
    const id = makeId('msg');
    const timestamp = Date.now();
    const nextMessage: Message = { ...msg, id, timestamp, events: [] };
    set((state) => {
      const activeId = state.activeSessionId || state.sessionId || makeId('pending_session');
      const firstUser = state.messages.find((message) => message.role === 'user');
      const titleSource = firstUser?.content || (msg.role === 'user' ? msg.content : '新对话');
      const normalizedTitle = titleSource.replace(/\s+/g, ' ').trim();
      return {
        activeSessionId: activeId,
        messages: [...state.messages, nextMessage],
        sessions: upsertSession(state.sessions, activeId, {
          title: normalizedTitle.slice(0, 24) + (normalizedTitle.length > 24 ? '...' : ''),
          updatedAt: timestamp,
          lastUserMessage: msg.role === 'user' ? msg.content : state.sessions.find((session) => session.id === activeId)?.lastUserMessage,
        }),
      };
    });
    return id;
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((message) => (message.id === id ? { ...message, ...updates } : message)),
    }));
  },

  addEvent: (id, event) => {
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id
          ? { ...message, events: [...message.events, { ...event, timestamp: Date.now() }] }
          : message
      ),
    }));
  },

  clearMessages: () => {
    const id = makeId('pending_session');
    set((state) => ({
      activeSessionId: id,
      sessionId: null,
      conversationId: id,
      messages: [],
      sessions: upsertSession(state.sessions, id, {
        title: '新对话',
        createdAt: Date.now(),
        updatedAt: Date.now(),
        lastUserMessage: undefined,
      }),
    }));
  },

  setSessionId: (id) => {
    if (!id) {
      set({ sessionId: null });
      return;
    }
    set((state) => {
      const currentActiveId = state.activeSessionId;
      const currentSession = state.sessions.find((session) => session.id === currentActiveId);
      const nextTitle = currentSession?.title || '新对话';
      const nextLastUser = currentSession?.lastUserMessage;
      const filteredSessions = state.sessions.filter((session) => session.id !== currentActiveId);
      return {
        sessionId: id,
        activeSessionId: id,
        conversationId: id,
        sessions: upsertSession(filteredSessions, id, {
          title: nextTitle,
          updatedAt: Date.now(),
          lastUserMessage: nextLastUser,
        }),
      };
    });
  },

  setConversationId: (id) => set({ conversationId: id }),

  setLoading: (loading) => set({ isLoading: loading }),
  setSessionsLoading: (loading) => set({ sessionsLoading: loading }),
}), {
  name: 'perfa-chat-store',
  storage: createJSONStorage(() =>
    typeof window !== 'undefined' ? localStorage : memoryStorage
  ),
  partialize: (state) => ({
    sessions: state.sessions,
    activeSessionId: state.activeSessionId,
    messages: state.messages,
    sessionId: state.sessionId,
    conversationId: state.conversationId,
  }),
}));

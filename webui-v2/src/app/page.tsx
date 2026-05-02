'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { Layout, Menu, Button, Typography, Popconfirm, Tooltip, Skeleton, Input, Tag } from 'antd';
import {
  MessageOutlined,
  DesktopOutlined,
  FileTextOutlined,
  PlusOutlined,
  HistoryOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ChatPage from '@/components/chat/ChatPage';
import ServersPage from '@/components/servers/ServersPage';
import ReportsPage from '@/components/reports/ReportsPage';
import MonitorPage from '@/components/monitor/MonitorPage';
import { useChatStore } from '@/store/useChatStore';
import { deleteSession, getSession, listSessions } from '@/lib/api';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

type PageKey = 'chat' | 'servers' | 'reports' | 'monitor';

const menuItems = [
  { key: 'chat', icon: <MessageOutlined />, label: '对话' },
  { key: 'servers', icon: <DesktopOutlined />, label: '服务器' },
  { key: 'reports', icon: <FileTextOutlined />, label: '报告' },
  { key: 'monitor', icon: <EyeOutlined />, label: '监控' },
];

export default function HomePage() {
  const [currentPage, setCurrentPage] = useState<PageKey>('chat');
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [sessionQuery, setSessionQuery] = useState('');
  const {
    createSession, clearMessages, sessions, activeSessionId,
    switchSession, replaceMessages, setSessions, removeSession,
    sessionsLoading, setSessionsLoading
  } = useChatStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleNewChat = useCallback(() => {
    createSession();
    setCurrentPage('chat');
  }, [createSession]);

  const renderPage = () => {
    switch (currentPage) {
      case 'chat':
        return <ChatPage />;
      case 'servers':
        return <ServersPage />;
      case 'reports':
        return <ReportsPage />;
      case 'monitor':
        return <MonitorPage />;
    }
  };

  const recentChats = useMemo(() => {
    const query = sessionQuery.trim().toLowerCase();
    const base = query
      ? sessions.filter((session) =>
          `${session.title} ${session.lastUserMessage || ''}`.toLowerCase().includes(query)
        )
      : sessions;
    return base.slice(0, 8);
  }, [sessionQuery, sessions]);

  const loadSessionList = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const sessionList = await listSessions();
      setSessions(
        sessionList.map((session) => ({
          id: session.session_id,
          title: session.title || '新对话',
          createdAt: session.created_at ? new Date(session.created_at).getTime() : Date.now(),
          updatedAt: session.last_active ? new Date(session.last_active).getTime() : Date.now(),
          lastUserMessage: session.last_user_message,
        }))
      );
    } finally {
      setSessionsLoading(false);
    }
  }, [setSessions, setSessionsLoading]);

  const handleSelectSession = useCallback(async (sessionId: string) => {
    try {
      const session = await getSession(sessionId);
      switchSession(
        sessionId,
        session.messages
          .filter((message) => message.role === 'user' || message.role === 'assistant')
          .map((message, index) => ({
            id: `history_${session.session_id}_${index}`,
            role: message.role as 'user' | 'assistant',
            content: message.content,
            timestamp: message.timestamp ? new Date(message.timestamp).getTime() : Date.now(),
            events: [],
          }))
      );
    } catch {
      replaceMessages([]);
      switchSession(sessionId, []);
    }
    setCurrentPage('chat');
  }, [replaceMessages, switchSession]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    await deleteSession(sessionId);
    removeSession(sessionId);
    if (activeSessionId === sessionId) {
      clearMessages();
    }
    await loadSessionList();
  }, [activeSessionId, clearMessages, loadSessionList, removeSession]);

  return (
    <Layout hasSider className="min-h-screen app-shell">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        className="!bg-bg-card"
        trigger={null}
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center gap-2 px-4 py-4 border-b border-white/5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-bg-main font-bold text-sm">
              P
            </div>
            {!collapsed && (
              <Text className="!text-text-primary font-semibold text-lg">
                Perfa
              </Text>
            )}
          </div>

          <Menu
            mode="inline"
            selectedKeys={[currentPage]}
            items={menuItems}
            onClick={({ key }) => setCurrentPage(key as PageKey)}
            className="!bg-transparent !border-r-0 mt-2"
            theme="dark"
          />

          {!collapsed && (
            <div className="mt-auto px-4 py-3 border-t border-white/5">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-text-muted">对话历史</div>
                <Tag color="gold" className="!m-0 !text-[10px]">{sessions.length}</Tag>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <Input
                  size="small"
                  allowClear
                  value={sessionQuery}
                  onChange={(e) => setSessionQuery(e.target.value)}
                  placeholder="搜索会话"
                  className="!bg-bg-main !border-white/10 !text-text-primary"
                />
                <Tooltip title="刷新会话列表">
                  <Button
                    type="text"
                    size="small"
                    icon={<ReloadOutlined />}
                    className="!text-text-muted"
                    loading={sessionsLoading}
                    onClick={() => void loadSessionList()}
                  />
                </Tooltip>
              </div>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {recentChats.length === 0 ? (
                  <div className="text-xs text-text-secondary px-2 py-1 truncate">
                    {sessionQuery ? '没有匹配会话' : '暂无消息'}
                  </div>
                ) : (
                  recentChats.map((chat) => (
                    <div
                      key={chat.id}
                      className={`text-xs px-2 py-1 rounded transition-colors ${
                        chat.id === activeSessionId
                          ? 'bg-primary/10 text-primary'
                          : 'text-text-secondary hover:bg-bg-hover'
                      }`}
                      title={chat.title}
                    >
                      <div className="flex items-center gap-2">
                        <button
                          className="flex-1 text-left truncate"
                          onClick={() => void handleSelectSession(chat.id)}
                        >
                          {chat.title}
                        </button>
                        {!chat.id.startsWith('pending_session') && (
                          <Popconfirm
                            title="删除这个会话？"
                            okText="删除"
                            cancelText="取消"
                            onConfirm={() => void handleDeleteSession(chat.id)}
                          >
                            <Button
                              type="text"
                              size="small"
                              icon={<DeleteOutlined />}
                              className="!text-text-muted hover:!text-red-400"
                            />
                          </Popconfirm>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </Sider>

      <Layout>
        <Header className="!bg-bg-card !px-6 flex items-center justify-between border-b border-white/5">
          <div className="flex items-center gap-3">
            <Button
              type="text"
              icon={<HistoryOutlined />}
              className="!text-text-secondary"
              onClick={() => setCollapsed(!collapsed)}
            />
            <Text className="!text-text-primary font-medium">
              {menuItems.find((i) => i.key === currentPage)?.label}
            </Text>
          </div>
          {currentPage === 'chat' && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size="small"
              onClick={handleNewChat}
            >
              新对话
            </Button>
          )}
        </Header>

        <Content className="!bg-bg-main !m-0 overflow-hidden">
          {mounted ? (
            renderPage()
          ) : (
            <div className="p-6">
              <Skeleton active paragraph={{ rows: 8 }} />
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
}

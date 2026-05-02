'use client';

import { useState, useCallback, useRef } from 'react';
import { Layout, Menu, Button, Typography } from 'antd';
import {
  MessageOutlined,
  DesktopOutlined,
  FileTextOutlined,
  PlusOutlined,
  HistoryOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import ChatPage from '@/components/chat/ChatPage';
import ServersPage from '@/components/servers/ServersPage';
import ReportsPage from '@/components/reports/ReportsPage';
import MonitorPage from '@/components/monitor/MonitorPage';

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

  return (
    <Layout className="min-h-screen">
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={240}
        className="!bg-bg-card"
        trigger={null}
      >
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
          <div className="absolute bottom-4 left-4 right-4">
            <div className="text-xs text-text-muted mb-2">会话历史</div>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              <div className="text-xs text-text-secondary px-2 py-1 rounded hover:bg-bg-hover cursor-pointer truncate">
                暂无历史会话
              </div>
            </div>
          </div>
        )}
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
            >
              新对话
            </Button>
          )}
        </Header>

        <Content className="!bg-bg-main !m-0 overflow-hidden">
          {renderPage()}
        </Content>
      </Layout>
    </Layout>
  );
}

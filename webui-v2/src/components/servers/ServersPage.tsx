'use client';

import { useEffect, useState } from 'react';
import {
  Table, Tag, Badge, Drawer, Typography, Button, Modal, Form, Input,
  InputNumber, Select, message, Space, Popconfirm, Card
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined,
  DesktopOutlined, KeyOutlined, UserOutlined, CloudServerOutlined, RocketOutlined
} from '@ant-design/icons';
import { deployServerAgent, listServers, ServerInfo, uninstallServerAgent } from '@/lib/api';

const { Text, Paragraph } = Typography;

const statusMap: Record<string, { color: string; text: string }> = {
  online: { color: 'green', text: '在线' },
  offline: { color: 'red', text: '离线' },
  unknown: { color: 'gray', text: '未知' },
};

interface RegisterFormValues {
  ip: string;
  port?: number;
  ssh_user: string;
  ssh_password?: string;
  ssh_key_path?: string;
  privilege_mode?: 'root' | 'sudo_nopasswd' | 'sudo_password' | 'none';
  sudo_password?: string;
  alias?: string;
  tags?: string[];
}

export default function ServersPage() {
  const [servers, setServers] = useState<ServerInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [agentActionLoading, setAgentActionLoading] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<ServerInfo | null>(null);
  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [form] = Form.useForm<RegisterFormValues>();

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    setLoading(true);
    try {
      const data = await listServers();
      setServers(data);
      setSelected((prev) => {
        if (!prev) return prev;
        return data.find((server) => server.server_id === prev.server_id) || null;
      });
    } catch {
      setServers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: RegisterFormValues) => {
    setRegisterLoading(true);
    try {
      const res = await fetch('/api/v1/servers/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      let data: any;
      try {
        data = await res.json();
      } catch {
        // 非 JSON 响应（如 500 错误页面）
        message.error(`注册失败: 服务器错误 (HTTP ${res.status})`);
        return;
      }
      if (data.success) {
        message.success(`服务器 ${values.ip} 注册成功！`);
        setRegisterModalOpen(false);
        form.resetFields();
        loadServers();
      } else {
        const errMsg = data.error || data.detail || '注册失败';
        message.error(errMsg);
      }
    } catch (err: any) {
      message.error(`注册失败: ${err.message}`);
    } finally {
      setRegisterLoading(false);
    }
  };

  const handleRemove = async (serverId: string) => {
    try {
      const res = await fetch(`/api/v1/servers/${serverId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        message.success('服务器已移除');
        loadServers();
        setSelected(null);
      } else {
        message.error(data.error || '移除失败');
      }
    } catch (err: any) {
      message.error(`移除失败: ${err.message}`);
    }
  };

  const setServerActionLoading = (serverId: string, value: boolean) => {
    setAgentActionLoading((prev) => ({ ...prev, [serverId]: value }));
  };

  const handleDeployAgent = async (server: ServerInfo, forceReinstall = false) => {
    setServerActionLoading(server.server_id, true);
    try {
      const data = await deployServerAgent(server.server_id, {
        forceReinstall,
        agentOnly: true,
      });
      if (data.success) {
        message.success(forceReinstall ? 'Agent 重装任务已提交' : 'Agent 安装任务已提交');
        await loadServers();
      } else {
        message.error(data.error || 'Agent 部署失败');
      }
    } catch (err: any) {
      message.error(`Agent 部署失败: ${err.message}`);
    } finally {
      setServerActionLoading(server.server_id, false);
    }
  };

  const handleUninstallAgent = async (server: ServerInfo) => {
    setServerActionLoading(server.server_id, true);
    try {
      const data = await uninstallServerAgent(server.server_id, { keepData: true });
      if (data.success) {
        message.success('Agent 已卸载');
        await loadServers();
        if (selected?.server_id === server.server_id) {
          setSelected({ ...server, agent_id: null, agent_status: 'not_deployed', agent_port: null });
        }
      } else {
        message.error(data.error || 'Agent 卸载失败');
      }
    } catch (err: any) {
      message.error(`Agent 卸载失败: ${err.message}`);
    } finally {
      setServerActionLoading(server.server_id, false);
    }
  };

  const renderAgentStatus = (server: ServerInfo) => {
    if (!server.agent_id || server.agent_status === 'not_deployed') {
      return <Tag>未安装</Tag>;
    }
    if (server.agent_status === 'online' || server.agent_status === 'running') {
      return <Tag color="green">运行中</Tag>;
    }
    if (server.agent_status === 'offline' || server.agent_status === 'stopped') {
      return <Tag color="orange">已部署但离线</Tag>;
    }
    if (server.agent_status === 'error') {
      return <Tag color="red">异常</Tag>;
    }
    return <Tag color="blue">{server.agent_status || '已部署'}</Tag>;
  };

  const columns = [
    {
      title: 'IP',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip: string) => <Text code className="!text-primary">{ip}</Text>,
    },
    {
      title: '别名',
      dataIndex: 'alias',
      key: 'alias',
      render: (alias: string) => alias || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = statusMap[status] || { color: 'default', text: status };
        return <Badge color={s.color} text={<span className="text-text-secondary">{s.text}</span>} />;
      },
    },
    {
      title: 'Agent',
      key: 'agent_status',
      render: (_: any, record: ServerInfo) => renderAgentStatus(record),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) =>
        tags?.map((t) => <Tag key={t} color="cyan">{t}</Tag>) || '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ServerInfo) => (
        <Space size="small" onClick={(e) => e.stopPropagation()}>
          {!record.agent_id || record.agent_status === 'not_deployed' ? (
            <Button
              size="small"
              icon={<RocketOutlined />}
              loading={agentActionLoading[record.server_id]}
              onClick={() => handleDeployAgent(record, false)}
            >
              安装 Agent
            </Button>
          ) : (
            <>
              <Button
                size="small"
                loading={agentActionLoading[record.server_id]}
                onClick={() => handleDeployAgent(record, true)}
              >
                重装 Agent
              </Button>
              <Popconfirm
                title="确认卸载该服务器上的 Agent？"
                onConfirm={() => handleUninstallAgent(record)}
                okText="确认"
                cancelText="取消"
              >
                <Button size="small" danger loading={agentActionLoading[record.server_id]}>
                  卸载 Agent
                </Button>
              </Popconfirm>
            </>
          )}
          <Popconfirm
            title="确认移除该服务器？"
            onConfirm={() => handleRemove(record.server_id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-text-primary flex items-center gap-2">
          <CloudServerOutlined /> 服务器管理
        </h2>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadServers} size="small">
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setRegisterModalOpen(true)}
          >
            注册服务器
          </Button>
        </Space>
      </div>

      {servers.length === 0 && !loading ? (
        <Card className="!bg-bg-card !border-white/5 text-center py-12">
          <DesktopOutlined className="text-4xl text-text-muted mb-4" />
          <p className="text-text-secondary mb-4">暂无注册服务器</p>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setRegisterModalOpen(true)}
          >
            注册第一台服务器
          </Button>
        </Card>
      ) : (
        <Table
          dataSource={servers}
          columns={columns}
          rowKey="server_id"
          loading={loading}
          onRow={(record) => ({
            onClick: () => setSelected(record),
            className: 'cursor-pointer',
          })}
          pagination={false}
          className="!bg-bg-card [&_.ant-table]:!bg-transparent [&_.ant-table-thead>tr>th]:!bg-bg-hover [&_.ant-table-thead>tr>th]:!text-text-secondary"
        />
      )}

      {/* 服务器详情 Drawer */}
      <Drawer
        title={selected?.alias || selected?.ip}
        open={!!selected}
        onClose={() => setSelected(null)}
        width={480}
        className="!bg-bg-card"
      >
        {selected && (
          <div className="space-y-4">
            <div>
              <Text className="!text-text-muted">IP 地址</Text>
              <div><Text code className="!text-primary">{selected.ip}</Text></div>
            </div>
            <div>
              <Text className="!text-text-muted">状态</Text>
              <div>
                <Badge
                  color={statusMap[selected.status]?.color || 'default'}
                  text={statusMap[selected.status]?.text || selected.status}
                />
              </div>
            </div>
            <div>
              <Text className="!text-text-muted">Agent 部署</Text>
              <div className="mt-1">{renderAgentStatus(selected)}</div>
              {selected.agent_id && (
                <div className="mt-2">
                  <Text code className="!text-xs !text-primary">{selected.agent_id}</Text>
                </div>
              )}
              {selected.agent_version && (
                <div className="mt-1">
                  <Text className="!text-text-secondary text-xs">版本 {selected.agent_version}</Text>
                </div>
              )}
            </div>
            {selected.current_task && (
              <div>
                <Text className="!text-text-muted">当前任务</Text>
                <pre className="mt-1 text-xs bg-bg-main p-3 rounded-lg overflow-auto max-h-40">
                  {JSON.stringify(selected.current_task, null, 2)}
                </pre>
              </div>
            )}
            {selected.hardware && (
              <div>
                <Text className="!text-text-muted">硬件信息</Text>
                <pre className="mt-1 text-xs bg-bg-main p-3 rounded-lg overflow-auto max-h-80">
                  {JSON.stringify(selected.hardware, null, 2)}
                </pre>
              </div>
            )}
            <div className="pt-4 border-t border-white/10">
              <Space wrap>
                {!selected.agent_id || selected.agent_status === 'not_deployed' ? (
                  <Button
                    type="primary"
                    icon={<RocketOutlined />}
                    loading={agentActionLoading[selected.server_id]}
                    onClick={() => handleDeployAgent(selected, false)}
                  >
                    安装 Agent
                  </Button>
                ) : (
                  <>
                    <Button
                      loading={agentActionLoading[selected.server_id]}
                      onClick={() => handleDeployAgent(selected, true)}
                    >
                      重装 Agent
                    </Button>
                    <Popconfirm
                      title="确认卸载该服务器上的 Agent？"
                      onConfirm={() => handleUninstallAgent(selected)}
                    >
                      <Button danger loading={agentActionLoading[selected.server_id]}>
                        卸载 Agent
                      </Button>
                    </Popconfirm>
                  </>
                )}
                <Popconfirm
                  title="确认移除该服务器？"
                  onConfirm={() => handleRemove(selected.server_id)}
                >
                  <Button danger icon={<DeleteOutlined />}>移除服务器</Button>
                </Popconfirm>
              </Space>
            </div>
          </div>
        )}
      </Drawer>

      {/* 注册服务器 Modal */}
      <Modal
        title={
          <span className="flex items-center gap-2">
            <CloudServerOutlined /> 注册新服务器
          </span>
        }
        open={registerModalOpen}
        onCancel={() => { setRegisterModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        confirmLoading={registerLoading}
        okText="注册"
        cancelText="取消"
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRegister}
          initialValues={{ port: 22, privilege_mode: 'root' }}
          className="mt-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Form.Item
              name="ip"
              label="IP 地址"
              rules={[{ required: true, message: '请输入服务器 IP' }]}
            >
              <Input placeholder="192.168.1.100" prefix={<DesktopOutlined />} />
            </Form.Item>
            <Form.Item name="port" label="SSH 端口">
              <InputNumber className="w-full" min={1} max={65535} />
            </Form.Item>
          </div>

          <Form.Item
            name="ssh_user"
            label="SSH 用户名"
            rules={[{ required: true, message: '请输入 SSH 用户名' }]}
          >
            <Input placeholder="root" prefix={<UserOutlined />} />
          </Form.Item>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item name="ssh_password" label="SSH 密码" extra="密码和密钥二选一">
              <Input.Password placeholder="可选" prefix={<KeyOutlined />} />
            </Form.Item>
            <Form.Item name="ssh_key_path" label="SSH 密钥路径" extra="如 ~/.ssh/id_rsa">
              <Input placeholder="可选" />
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item name="privilege_mode" label="提权模式">
              <Select
                options={[
                  { label: 'root', value: 'root' },
                  { label: 'sudo 免密', value: 'sudo_nopasswd' },
                  { label: 'sudo 密码', value: 'sudo_password' },
                  { label: '无提权', value: 'none' },
                ]}
              />
            </Form.Item>
            <Form.Item shouldUpdate noStyle>
              {({ getFieldValue }) =>
                getFieldValue('privilege_mode') === 'sudo_password' ? (
                  <Form.Item name="sudo_password" label="sudo 密码">
                    <Input.Password placeholder="用于 sudo 提权" />
                  </Form.Item>
                ) : (
                  <div />
                )
              }
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Form.Item name="alias" label="别名">
              <Input placeholder="如：web-server-01" />
            </Form.Item>
            <Form.Item name="tags" label="标签">
              <Select mode="tags" placeholder="输入后回车" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  );
}

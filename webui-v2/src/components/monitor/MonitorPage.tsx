'use client';

import { useState, useCallback, useEffect } from 'react';
import { Tabs, Typography, Card, Tag, Space, Badge, Button, List, Empty, Tooltip, Descriptions, message } from 'antd';
import {
  EyeOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  SearchOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  CloudServerOutlined,
  RobotOutlined,
  DatabaseOutlined,
  DashboardOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

/** 所有服务统一配置 — 有代理走代理，没有的只显示端口信息 */
const ALL_SERVICES = [
  { name: 'Perfa Agent API', category: '核心服务', icon: <RobotOutlined />, proxyUrl: '/api/v1/models', port: 10000, desc: 'LangChain Agent + OpenAI 兼容 API', color: '#00D9A6' },
  { name: 'MCP Server', category: '核心服务', icon: <ApiOutlined />, proxyUrl: null, port: 18080, desc: 'MCP 工具服务（SSH 管理）', color: '#4285F4' },
  { name: 'Node Agent', category: '核心服务', icon: <CloudServerOutlined />, proxyUrl: null, port: 5000, desc: '节点 Agent（压测执行）', color: '#FBBC04' },
  { name: 'WebUI V2', category: '核心服务', icon: <DashboardOutlined />, proxyUrl: null, port: 3002, desc: '前端界面（Next.js）', color: '#34A853' },
  { name: 'OTel Collector', category: '可观测性', icon: <EyeOutlined />, proxyUrl: null, port: 4317, desc: 'OpenTelemetry 数据采集', color: '#FF6D00' },
  { name: 'Jaeger UI', category: '可观测性', icon: <SearchOutlined />, proxyUrl: '/api/jaeger', port: 16686, desc: '分布式链路追踪', color: '#66BCFF' },
  { name: 'Grafana', category: '可观测性', icon: <DashboardOutlined />, proxyUrl: '/api/grafana', port: 3000, desc: '监控看板', color: '#F46800' },
  { name: 'VictoriaMetrics', category: '可观测性', icon: <DatabaseOutlined />, proxyUrl: '/api/vm', port: 8428, desc: '时序数据库', color: '#6C3FC5' },
];

interface TraceSpan {
  operation: string;
  duration_ms: number;
  tags: Record<string, any>;
  events: Array<{
    fields: Record<string, string>;
  }>;
  has_error: boolean;
}

interface TraceDetail {
  trace_id: string;
  span_count: number;
  spans: TraceSpan[];
}

export default function MonitorPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [traceSearchLoading, setTraceSearchLoading] = useState(false);
  const [traces, setTraces] = useState<TraceDetail[]>([]);
  const [searchError, setSearchError] = useState('');
  const [serviceStatus, setServiceStatus] = useState<Record<string, 'checking' | 'online' | 'offline'>>({});

  // 检测服务状态
  const checkServices = useCallback(async () => {
    const statusMap: Record<string, 'checking' | 'online' | 'offline'> = {};
    
    const checkPromises = ALL_SERVICES.filter(s => s.proxyUrl).map(async (svc) => {
      statusMap[svc.name] = 'checking';
      try {
        const res = await fetch(svc.proxyUrl!, { signal: AbortSignal.timeout(3000) });
        statusMap[svc.name] = res.ok ? 'online' : 'offline';
      } catch {
        statusMap[svc.name] = 'offline';
      }
    });

    await Promise.all(checkPromises);
    setServiceStatus(statusMap);
  }, []);

  useEffect(() => {
    checkServices();
  }, [checkServices]);

  const searchTraces = useCallback(async (query?: string) => {
    setTraceSearchLoading(true);
    setSearchError('');
    try {
      const params = new URLSearchParams({
        service: 'perfa-agent',
        lookback: '1800000000',
        limit: '10',
      });
      if (query) {
        if (/^[a-f0-9]{16,32}$/i.test(query.trim())) {
          window.open(`/api/jaeger/trace/${query.trim()}`, '_blank');
          setTraceSearchLoading(false);
          return;
        }
      }

      const res = await fetch(`/api/jaeger/api/traces?${params}`);
      if (!res.ok) throw new Error(`Jaeger API 返回 ${res.status}`);
      const data = await res.json();

      const rawTraces = data.data || [];
      if (rawTraces.length === 0) {
        setTraces([]);
        setSearchError('未找到 trace 记录');
      } else {
        const parsed: TraceDetail[] = rawTraces.map((t: any) => ({
          trace_id: t.traceID,
          span_count: t.spans?.length || 0,
          spans: (t.spans || []).map((s: any) => {
            const tags: Record<string, any> = {};
            for (const tag of s.tags || []) {
              if (['error', 'success', 'tool_name', 'node', 'is_final', 'node_status', 'is_success'].includes(tag.key)) {
                tags[tag.key] = tag.value;
              }
            }
            const events: TraceSpan['events'] = [];
            for (const log of s.logs || []) {
              const fields: Record<string, string> = {};
              for (const f of log.fields || []) {
                if (['reasoning_content', 'decision_type', 'tool_name', 'tool_args',
                     'result_preview', 'answer_preview', 'error_message', 'reason',
                     'routed_scenario', 'test_name', 'task_id', 'tool_chain',
                     'final_result_preview', 'error_detail', 'last_status',
                     'server_ip', 'agent_status'].includes(f.key)) {
                  fields[f.key] = String(f.value).slice(0, 200);
                }
              }
              if (Object.keys(fields).length > 0) events.push({ fields });
            }
            return {
              operation: s.operationName,
              duration_ms: s.duration / 1000,
              tags,
              events,
              has_error: tags.error === true || tags.success === false,
            };
          }),
        }));
        setTraces(parsed);
      }
    } catch (e: any) {
      setSearchError(e.message || '查询失败');
      setTraces([]);
    } finally {
      setTraceSearchLoading(false);
    }
  }, []);

  const openService = (svc: typeof ALL_SERVICES[0]) => {
    if (svc.proxyUrl) {
      window.open(svc.proxyUrl, '_blank');
    }
    // 没有代理的服务不自动跳转，只显示端口信息
  };

  const tabs = [
    {
      key: 'overview',
      label: (
        <span className="flex items-center gap-2">
          <DashboardOutlined />
          服务总览
        </span>
      ),
      children: (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-2">
            <Text className="!text-text-secondary">所有服务的运行状态和入口</Text>
            <Button size="small" icon={<ReloadOutlined />} onClick={checkServices} className="!text-text-muted">
              刷新状态
            </Button>
          </div>
          {['核心服务', '可观测性'].map((category) => (
            <div key={category}>
              <div className="text-xs text-text-muted mb-2 uppercase tracking-wide">{category}</div>
              <div className="grid grid-cols-2 gap-3">
                {ALL_SERVICES.filter(s => s.category === category).map((svc) => {
                  const status = serviceStatus[svc.name];
                  const hasProxy = !!svc.proxyUrl;
                  return (
                    <Card
                      key={svc.name}
                      size="small"
                      className={`!bg-bg-card !border-white/5 transition-colors ${hasProxy ? 'hover:!border-primary/30 cursor-pointer' : ''}`}
                      onClick={() => hasProxy && openService(svc)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-sm"
                            style={{ backgroundColor: `${svc.color}20`, color: svc.color }}
                          >
                            {svc.icon}
                          </div>
                          <div>
                            <Text className="!text-text-primary text-sm font-medium block">{svc.name}</Text>
                            <Text className="!text-text-muted text-[11px] block">{svc.desc}</Text>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge
                            status={status === 'online' ? 'success' : status === 'checking' ? 'processing' : 'default'}
                            text={
                              <span className="text-[11px] text-text-muted">
                                {status === 'online' ? '在线' : status === 'checking' ? '检测中' : status === 'offline' ? '离线' : '—'}
                              </span>
                            }
                          />
                          <div className="mt-1 flex items-center gap-1">
                            <Text code className="!text-[10px] !text-primary">:{svc.port}</Text>
                            {hasProxy && (
                              <Tag color="cyan" className="!text-[9px] !px-1 !py-0 !m-0 !leading-none">代理</Tag>
                            )}
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ),
    },
    {
      key: 'jaeger',
      label: (
        <span className="flex items-center gap-2">
          <EyeOutlined />
          Jaeger 链路追踪
        </span>
      ),
      children: (
        <div className="flex flex-col items-center justify-center h-[calc(100vh-240px)]">
          <div className="text-center space-y-4">
            <div className="text-5xl mb-4">🔍</div>
            <Title level={4} className="!text-text-primary !mb-2">
              Jaeger 分布式链路追踪
            </Title>
            <Text className="!text-text-secondary block mb-4">
              查看完整的请求链路、AI 思考过程、工具调用详情
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<LinkOutlined />}
              onClick={() => window.open('/api/jaeger', '_blank')}
              className="!px-8 !h-12 !text-base"
            >
              打开 Jaeger UI
            </Button>
            <div className="text-text-muted text-xs mt-2">
              通过 Next.js 代理访问，无需直接连 localhost
            </div>
          </div>
        </div>
      ),
    },
    {
      key: 'trace-search',
      label: (
        <span className="flex items-center gap-2">
          <SearchOutlined />
          Trace 搜索
        </span>
      ),
      children: (
        <div className="space-y-4">
          <div className="flex gap-3 items-center">
            <Space>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={() => searchTraces()}
                loading={traceSearchLoading}
                type="primary"
              >
                查看最近 Traces
              </Button>
            </Space>
          </div>

          {searchError && (
            <div className="text-text-muted text-sm">
              <WarningOutlined className="mr-1 text-yellow-500" />
              {searchError}
            </div>
          )}

          {traces.length > 0 ? (
            <List
              dataSource={traces}
              renderItem={(trace) => (
                <Card
                  size="small"
                  className="!bg-bg-card !border-white/5 mb-3"
                  title={
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ApiOutlined className="text-primary" />
                        <Text code className="!text-primary text-xs">
                          {trace.trace_id.slice(0, 16)}...
                        </Text>
                        <Tag className="!text-[10px]">{trace.span_count} spans</Tag>
                      </div>
                      <Button
                        type="link"
                        size="small"
                        icon={<LinkOutlined />}
                        className="!text-primary !p-0"
                        onClick={() => window.open(`/api/jaeger/trace/${trace.trace_id}`, '_blank')}
                      >
                        在 Jaeger 中查看
                      </Button>
                    </div>
                  }
                >
                  <div className="space-y-2">
                    {trace.spans
                      .filter((s) => s.events.length > 0 || s.has_error)
                      .map((span, idx) => (
                        <div key={idx} className="pl-2 border-l-2 border-primary/30 py-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Text className="!text-text-primary text-xs font-medium">
                              {span.operation}
                            </Text>
                            <Text className="!text-text-muted text-[10px]">
                              {span.duration_ms.toFixed(0)}ms
                            </Text>
                            {span.has_error && (
                              <Tag color="error" className="!text-[10px] !px-1 !py-0 !m-0">ERROR</Tag>
                            )}
                          </div>
                          {span.events.map((evt, eidx) => (
                            <div key={eidx} className="ml-2 text-[11px]">
                              {evt.fields.reasoning_content && (
                                <div className="text-text-muted mb-0.5">
                                  💭 AI推理: {evt.fields.reasoning_content.slice(0, 150)}
                                </div>
                              )}
                              {evt.fields.decision_type && (
                                <div className="text-info mb-0.5">
                                  🎯 决策: {evt.fields.decision_type}
                                  {evt.fields.tool_name && ` → ${evt.fields.tool_name}`}
                                </div>
                              )}
                              {evt.fields.result_preview && (
                                <div className="text-text-secondary mb-0.5">
                                  📋 结果: {evt.fields.result_preview.slice(0, 100)}
                                </div>
                              )}
                              {evt.fields.error_message && (
                                <div className="text-red-400 mb-0.5">
                                  ❌ 错误: {evt.fields.error_message.slice(0, 100)}
                                </div>
                              )}
                              {evt.fields.routed_scenario && (
                                <div className="text-primary mb-0.5">
                                  🔀 路由: → {evt.fields.routed_scenario} ({evt.fields.reason || ''})
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ))}
                  </div>
                </Card>
              )}
            />
          ) : (
            !searchError && (
              <Empty description="点击「查看最近 Traces」搜索" className="mt-8" />
            )
          )}
        </div>
      ),
    },
    {
      key: 'grafana',
      label: (
        <span className="flex items-center gap-2">
          <EyeOutlined />
          Grafana
        </span>
      ),
      children: (
        <div className="flex flex-col items-center justify-center h-[calc(100vh-240px)]">
          <div className="text-center space-y-4">
            <div className="text-5xl mb-4">📊</div>
            <Title level={4} className="!text-text-primary !mb-2">
              Grafana 性能监控看板
            </Title>
            <Text className="!text-text-secondary block mb-4">
              可视化展示性能指标、趋势图和告警
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<LinkOutlined />}
              onClick={() => window.open('/api/grafana', '_blank')}
              className="!px-8 !h-12 !text-base"
            >
              打开 Grafana
            </Button>
          </div>
        </div>
      ),
    },
    {
      key: 'vm',
      label: (
        <span className="flex items-center gap-2">
          <EyeOutlined />
          VictoriaMetrics
        </span>
      ),
      children: (
        <div className="flex flex-col items-center justify-center h-[calc(100vh-240px)]">
          <div className="text-center space-y-4">
            <div className="text-5xl mb-4">📈</div>
            <Title level={4} className="!text-text-primary !mb-2">
              VictoriaMetrics 时序数据库
            </Title>
            <Text className="!text-text-secondary block mb-4">
              高性能指标存储和查询引擎
            </Text>
            <Button
              type="primary"
              size="large"
              icon={<LinkOutlined />}
              onClick={() => window.open('/api/vm/vmui', '_blank')}
              className="!px-8 !h-12 !text-base"
            >
              打开 VictoriaMetrics
            </Button>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-text-primary flex items-center gap-2">
          <EyeOutlined /> 可观测性监控
        </h2>
        <Space>
          <Tag icon={<CheckCircleOutlined />} color="success">
            OTel
          </Tag>
          <Tag icon={<CheckCircleOutlined />} color="success">
            Jaeger
          </Tag>
          <Tag color="processing">Grafana</Tag>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabs}
        className="[&_.ant-tabs-nav]:!mb-3"
      />
    </div>
  );
}

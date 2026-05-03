'use client';

import { useState, useCallback, useEffect, useMemo } from 'react';
import { Tabs, Typography, Card, Tag, Space, Badge, Button, List, Empty, Input } from 'antd';
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
  ExpandOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;
const MONITOR_ROOT = '/api/monitor';

/** 所有服务统一配置 — 有代理走代理，没有的只显示端口信息 */
const ALL_SERVICES = [
  { name: 'Perfa Agent API', category: '核心服务', icon: <RobotOutlined />, proxyUrl: `/api/v1/models`, port: 10000, desc: 'LangChain Agent + OpenAI 兼容 API', color: '#00D9A6' },
  { name: 'MCP Server', category: '核心服务', icon: <ApiOutlined />, proxyUrl: null, port: 9000, desc: 'MCP 工具服务（SSE + SSH 管理）', color: '#4285F4' },
  { name: 'Node Agent', category: '核心服务', icon: <CloudServerOutlined />, proxyUrl: null, port: 8080, desc: '节点 Agent（压测执行）', color: '#FBBC04' },
  { name: 'WebUI V2', category: '核心服务', icon: <DashboardOutlined />, proxyUrl: null, port: 3002, desc: '前端界面（Next.js）', color: '#34A853' },
  { name: 'OTel Collector', category: '可观测性', icon: <EyeOutlined />, proxyUrl: null, port: 4317, desc: 'OpenTelemetry 数据采集', color: '#FF6D00' },
  { name: 'Jaeger UI', category: '可观测性', icon: <SearchOutlined />, proxyUrl: `${MONITOR_ROOT}/jaeger`, port: 16686, desc: '分布式链路追踪', color: '#66BCFF' },
  { name: 'Grafana', category: '可观测性', icon: <DashboardOutlined />, proxyUrl: `${MONITOR_ROOT}/grafana`, port: 3000, desc: '监控看板', color: '#F46800' },
  { name: 'VictoriaMetrics', category: '可观测性', icon: <DatabaseOutlined />, proxyUrl: `${MONITOR_ROOT}/vm`, port: 8428, desc: '时序数据库', color: '#6C3FC5' },
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

function EmbeddedConsole({
  title,
  description,
  src,
  externalHref,
}: {
  title: string;
  description: string;
  src: string;
  externalHref?: string;
}) {
  const [frameKey, setFrameKey] = useState(0);
  const href = externalHref || src;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-text-primary">{title}</div>
          <div className="text-xs text-text-muted">{description}</div>
        </div>
        <Space>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => setFrameKey((value) => value + 1)}
          >
            刷新面板
          </Button>
          <Button
            size="small"
            icon={<ExpandOutlined />}
            onClick={() => window.open(href, '_blank', 'noopener,noreferrer')}
          >
            新标签打开
          </Button>
        </Space>
      </div>

      <div className="rounded-2xl overflow-hidden border border-white/8 bg-black/20 shadow-[0_20px_60px_rgba(0,0,0,0.28)]">
        <iframe
          key={frameKey}
          src={src}
          title={title}
          className="w-full h-[calc(100vh-290px)] min-h-[640px] bg-white"
        />
      </div>
    </div>
  );
}

export default function MonitorPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [traceSearchLoading, setTraceSearchLoading] = useState(false);
  const [traces, setTraces] = useState<TraceDetail[]>([]);
  const [searchError, setSearchError] = useState('');
  const [serviceStatus, setServiceStatus] = useState<Record<string, 'checking' | 'online' | 'offline'>>({});
  const [traceQuery, setTraceQuery] = useState('');

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
          window.open(`${MONITOR_ROOT}/jaeger/trace/${query.trim()}`, '_blank');
          setTraceSearchLoading(false);
          return;
        }
      }

      const res = await fetch(`${MONITOR_ROOT}/jaeger/api/traces?${params}`);
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

  const serviceCounts = useMemo(() => {
    const values = Object.values(serviceStatus);
    return {
      online: values.filter((value) => value === 'online').length,
      offline: values.filter((value) => value === 'offline').length,
    };
  }, [serviceStatus]);

  const openService = (svc: typeof ALL_SERVICES[0]) => {
    if (svc.proxyUrl) {
      window.open(svc.proxyUrl, '_blank');
    }
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
            <div>
              <Text className="!text-text-secondary block">所有服务的运行状态和入口</Text>
              <div className="mt-1 flex items-center gap-2">
                <Tag color="green">{serviceCounts.online} 在线</Tag>
                <Tag color={serviceCounts.offline > 0 ? 'red' : 'default'}>{serviceCounts.offline} 离线</Tag>
              </div>
            </div>
            <Button size="small" icon={<ReloadOutlined />} onClick={checkServices} className="!text-text-muted">刷新状态</Button>
          </div>
          {['核心服务', '可观测性'].map((category) => (
            <div key={category}>
              <div className="text-xs text-text-muted mb-2 uppercase tracking-wide">{category}</div>
              <div className="grid grid-cols-2 gap-3">
                {ALL_SERVICES.filter(s => s.category === category).map((svc) => {
                  const status = serviceStatus[svc.name];
                  const hasProxy = !!svc.proxyUrl;
                  const canOpen = hasProxy;
                  return (
                    <Card
                      key={svc.name}
                      size="small"
                      className={`!bg-bg-card !border-white/5 transition-colors ${canOpen ? 'hover:!border-primary/30 cursor-pointer' : ''}`}
                      onClick={() => canOpen && openService(svc)}
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
                            <Tag color={svc.proxyUrl ? 'cyan' : 'default'} className="!text-[9px] !px-1 !py-0 !m-0 !leading-none">
                              {svc.proxyUrl ? '入口' : '本地端口'}
                            </Tag>
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
        <EmbeddedConsole
          title="Jaeger 分布式链路追踪"
          description="直接在页面内查看 trace、span、工具调用和 AI 推理链路。"
          src={`${MONITOR_ROOT}/jaeger`}
        />
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
              <Input
                allowClear
                placeholder="输入 trace id 可直接打开"
                value={traceQuery}
                onChange={(event) => setTraceQuery(event.target.value)}
                className="!w-[280px]"
              />
              <Button
                icon={<ThunderboltOutlined />}
                onClick={() => searchTraces(traceQuery)}
                loading={traceSearchLoading}
                type="primary"
              >
                查询 Trace
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
                        onClick={() => window.open(`${MONITOR_ROOT}/jaeger/trace/${trace.trace_id}`, '_blank')}
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
        <EmbeddedConsole
          title="Grafana 性能监控看板"
          description="在工作台里直接查看 dashboard、节点趋势、运行指标和告警上下文。"
          src={`${MONITOR_ROOT}/grafana`}
        />
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
        <EmbeddedConsole
          title="VictoriaMetrics 指标查询"
          description="直接在嵌入面板里做指标查询、验证抓取结果和对比时间序列。"
          src={`${MONITOR_ROOT}/vm/vmui`}
        />
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

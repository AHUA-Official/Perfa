'use client';

import { useState, useCallback } from 'react';
import { Tabs, Typography, Card, Tag, Space, Badge, Input, Button, List, Empty, Spin, Tooltip, Descriptions } from 'antd';
import {
  EyeOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  SearchOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;
const { Search } = Input;

const IFRAME_URLS = {
  jaeger: '/api/jaeger',
  grafana: '/api/grafana',
  victoriaMetrics: '/api/vm/vmui',
};

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
  const [activeTab, setActiveTab] = useState('jaeger');
  const [traceSearchLoading, setTraceSearchLoading] = useState(false);
  const [traces, setTraces] = useState<TraceDetail[]>([]);
  const [searchError, setSearchError] = useState('');

  const searchTraces = useCallback(async (query?: string) => {
    setTraceSearchLoading(true);
    setSearchError('');
    try {
      const params = new URLSearchParams({
        service: 'perfa-agent',
        lookback: '1800000000', // 30 min
        limit: '10',
      });
      if (query) {
        // 如果输入的是 trace ID，直接跳转
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

  const tabs = [
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
              onClick={() => window.open('http://localhost:16686', '_blank')}
              className="!px-8 !h-12 !text-base"
            >
              打开 Jaeger UI
            </Button>
            <div className="text-text-muted text-xs mt-2">
              在新标签页中打开，可查看完整交互式追踪界面
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
            <Search
              placeholder="输入 Trace ID 或搜索..."
              allowClear
              enterButton="搜索"
              size="middle"
              className="max-w-md"
              onSearch={(v) => searchTraces(v)}
              loading={traceSearchLoading}
            />
            <Button
              icon={<ThunderboltOutlined />}
              onClick={() => searchTraces()}
              loading={traceSearchLoading}
            >
              查看最近 Traces
            </Button>
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
                        onClick={() => window.open(`http://localhost:16686/trace/${trace.trace_id}`, '_blank')}
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
                                  {evt.fields.reasoning_content.length > 150 ? '...' : ''}
                                </div>
                              )}
                              {evt.fields.decision_type && (
                                <div className="text-info mb-0.5">
                                  🎯 决策: {evt.fields.decision_type}
                                  {evt.fields.tool_name && ` → ${evt.fields.tool_name}`}
                                  {evt.fields.answer_preview && `: ${evt.fields.answer_preview.slice(0, 80)}`}
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
                              {evt.fields.tool_chain && (
                                <div className="text-text-secondary mb-0.5">
                                  🔗 调用链: {evt.fields.tool_chain}
                                </div>
                              )}
                              {evt.fields.test_name && evt.fields.task_id && (
                                <div className="text-text-secondary mb-0.5">
                                  ⚡ 压测: {evt.fields.test_name} task={evt.fields.task_id.slice(0, 12)}...
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
              <Empty
                description="点击「查看最近 Traces」搜索"
                className="mt-8"
              />
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
          Grafana 监控看板
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
              onClick={() => window.open('http://localhost:3000', '_blank')}
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
              onClick={() => window.open('http://localhost:8428/vmui', '_blank')}
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
            OTel Collector
          </Tag>
          <Tag icon={<CheckCircleOutlined />} color="success">
            Jaeger
          </Tag>
          <Tag color="processing">Grafana</Tag>
        </Space>
      </div>

      {/* 服务状态卡片 */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[
          { name: 'OTel Collector', url: 'localhost:4317', status: 'running' },
          { name: 'Jaeger UI', url: 'localhost:16686', status: 'running' },
          { name: 'Grafana', url: 'localhost:3000', status: 'running' },
          { name: 'VictoriaMetrics', url: 'localhost:8428', status: 'running' },
        ].map((svc) => (
          <Card
            key={svc.name}
            size="small"
            className="!bg-bg-card !border-white/5"
          >
            <div className="flex items-center justify-between">
              <div>
                <Text className="!text-text-secondary text-xs">{svc.name}</Text>
                <div className="flex items-center gap-1 mt-1">
                  <LinkOutlined className="text-text-muted text-xs" />
                  <Text code className="!text-primary text-xs">
                    {svc.url}
                  </Text>
                </div>
              </div>
              <Badge
                status={svc.status === 'running' ? 'success' : 'default'}
                text={
                  <span className="text-xs text-text-secondary">
                    {svc.status === 'running' ? '运行中' : '未启动'}
                  </span>
                }
              />
            </div>
          </Card>
        ))}
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

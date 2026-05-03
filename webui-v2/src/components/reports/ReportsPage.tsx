'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Descriptions,
  Drawer,
  Empty,
  Skeleton,
  Space,
  Tag,
  Tabs,
  Typography,
} from 'antd';
import { FileSearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { getReport, listReports, ReportDetail, ReportInfo } from '@/lib/api';

const { Paragraph, Text, Title } = Typography;

const STATUS_LABELS: Record<string, string> = {
  completed: '已完成',
  failed: '失败',
  collecting: '收集中',
};

const STATUS_COLORS: Record<string, string> = {
  completed: 'green',
  failed: 'red',
  collecting: 'gold',
};

const SCENARIO_COLORS: Record<string, string> = {
  quick_test: 'blue',
  full_assessment: 'purple',
  cpu_focus: 'green',
  storage_focus: 'orange',
  network_focus: 'cyan',
  legacy_benchmark: 'default',
};

function safeDate(value?: string) {
  if (!value) return '时间未知';
  const ts = new Date(value).getTime();
  if (Number.isNaN(ts)) return '时间未知';
  return new Date(ts).toLocaleString('zh-CN');
}

function displayServer(report: Pick<ReportInfo, 'server_alias' | 'server_ip' | 'server_id'>) {
  return report.server_alias || report.server_ip || report.server_id || '未识别服务器';
}

function formatJsonBlock(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ReportInfo | null>(null);
  const [reportDetail, setReportDetail] = useState<ReportDetail | null>(null);

  useEffect(() => {
    void loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      setReports(await listReports());
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  const openReport = async (report: ReportInfo) => {
    setSelectedReport(report);
    setDetailLoading(true);
    try {
      setReportDetail(await getReport(report.id));
    } catch {
      setReportDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const stats = useMemo(() => {
    return {
      total: reports.length,
      workflow: reports.filter((report) => report.source !== 'legacy').length,
      legacy: reports.filter((report) => report.source === 'legacy').length,
    };
  }, [reports]);

  if (!reports.length && !loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <Title level={4} className="!mb-1 !text-text-primary">测试报告</Title>
            <Text className="!text-text-secondary">这里会展示完整的工作流评估报告，以及必要的原始测试证据。</Text>
          </div>
          <Button icon={<ReloadOutlined />} onClick={() => void loadReports()}>刷新</Button>
        </div>
        <Card className="!bg-bg-card !border-white/5">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span className="!text-text-muted">暂无报告，先跑一次完整测试工作流</span>}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <Title level={4} className="!mb-1 !text-text-primary">测试报告</Title>
          <Text className="!text-text-secondary">综合结论、原始结果、任务 ID 和错误证据都放在同一份报告里。</Text>
        </div>
        <Space>
          <Tag color="gold">{stats.total} 份报告</Tag>
          <Tag color="blue">{stats.workflow} 综合报告</Tag>
          <Tag>{stats.legacy} 历史结果</Tag>
          <Button icon={<ReloadOutlined />} onClick={() => void loadReports()} loading={loading}>刷新</Button>
        </Space>
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {reports.map((report) => (
            <Card
              key={report.id}
              className="!bg-bg-card !border-white/5 hover:!border-primary/30 transition-all duration-200 cursor-pointer"
              onClick={() => void openReport(report)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Tag color={SCENARIO_COLORS[report.scenario || report.type] || 'default'}>
                      {report.scenario_label || report.title || report.type}
                    </Tag>
                    <Tag color={STATUS_COLORS[report.status] || 'default'}>
                      {STATUS_LABELS[report.status] || report.status}
                    </Tag>
                    {report.test_count ? <Tag>{report.test_count} 项测试</Tag> : null}
                  </div>
                  <Title level={5} className="!mb-1 !text-text-primary">
                    {report.title || `${report.type} 报告`}
                  </Title>
                  <Text className="!text-text-secondary block">
                    {displayServer(report)}
                  </Text>
                  <div className="mt-2 text-xs text-text-muted">{safeDate(report.created_at)}</div>
                </div>
              </div>
              <Paragraph className="!text-text-secondary !text-sm !mt-3 !mb-0" ellipsis={{ rows: 4 }}>
                {report.summary || '暂无摘要，点击查看完整详情。'}
              </Paragraph>
            </Card>
          ))}
        </div>
      )}

      <Drawer
        width={900}
        open={!!selectedReport}
        onClose={() => {
          setSelectedReport(null);
          setReportDetail(null);
        }}
        title={
          <div className="flex items-center gap-2">
            <FileSearchOutlined />
            <span>{reportDetail?.title || selectedReport?.title || '报告详情'}</span>
          </div>
        }
      >
        {detailLoading ? (
          <Skeleton active paragraph={{ rows: 14 }} />
        ) : reportDetail ? (
          <div className="space-y-4">
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                { key: 'server', label: '服务器', children: displayServer(reportDetail) },
                { key: 'scenario', label: '场景', children: reportDetail.scenario_label || reportDetail.scenario || reportDetail.type },
                { key: 'status', label: '状态', children: STATUS_LABELS[reportDetail.status] || reportDetail.status },
                { key: 'created_at', label: '创建时间', children: safeDate(reportDetail.created_at) },
                { key: 'trace_id', label: 'Trace ID', children: reportDetail.trace_id || '无' },
                { key: 'source', label: '来源', children: reportDetail.source === 'legacy' ? '历史单项结果' : '工作流综合报告' },
              ]}
            />

            {reportDetail.summary ? (
              <Alert
                type={reportDetail.status === 'failed' ? 'warning' : 'info'}
                message="摘要"
                description={<div className="whitespace-pre-wrap">{reportDetail.summary}</div>}
                showIcon
              />
            ) : null}

            <Tabs
              defaultActiveKey="ai"
              items={[
                {
                  key: 'ai',
                  label: 'AI 结论',
                  children: (
                    <Card className="!bg-bg-card !border-white/5">
                      <div className="whitespace-pre-wrap leading-7 text-text-primary text-sm">
                        {reportDetail.ai_report || String(reportDetail.content || '暂无 AI 结论')}
                      </div>
                    </Card>
                  ),
                },
                {
                  key: 'results',
                  label: '原始结果',
                  children: (
                    <Collapse
                      items={Object.entries(reportDetail.raw_results || {}).map(([key, value]) => ({
                        key,
                        label: key,
                        children: (
                          <pre className="p-4 rounded-xl bg-black/20 text-[12px] text-text-primary overflow-auto whitespace-pre-wrap break-words">
                            {formatJsonBlock(value)}
                          </pre>
                        ),
                      }))}
                    />
                  ),
                },
                {
                  key: 'knowledge',
                  label: '知识依据',
                  children: (
                    <div className="space-y-3">
                      {(reportDetail.knowledge_matches || []).length ? (
                        (reportDetail.knowledge_matches || []).map((item, index) => (
                          <Card key={`${item.path || index}`} size="small" className="!bg-bg-card !border-white/5">
                            <div className="flex items-center gap-2 mb-2 flex-wrap">
                              <Tag color={SCENARIO_COLORS[item.category] || 'default'}>{item.category || 'general'}</Tag>
                              {item.test_name ? <Tag>{item.test_name}</Tag> : null}
                              {item.score ? <Tag>score {item.score}</Tag> : null}
                            </div>
                            <Text strong className="!text-text-primary">{item.title || item.path || '知识片段'}</Text>
                            <Text className="!text-text-muted block text-xs mt-1">{item.path}</Text>
                            <Paragraph className="!text-text-secondary !text-sm !mt-3 !mb-0 whitespace-pre-wrap">
                              {item.snippet || '无片段内容'}
                            </Paragraph>
                          </Card>
                        ))
                      ) : (
                        <Empty description="本报告暂无知识库检索片段" />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'evidence',
                  label: '任务与错误',
                  children: (
                    <div className="space-y-4">
                      <Card size="small" className="!bg-bg-card !border-white/5">
                        <Text className="!text-text-muted text-xs">任务 ID 映射</Text>
                        <pre className="mt-3 p-4 rounded-xl bg-black/20 text-[12px] text-text-primary overflow-auto whitespace-pre-wrap break-words">
                          {formatJsonBlock(reportDetail.task_ids || {})}
                        </pre>
                      </Card>
                      <Card size="small" className="!bg-bg-card !border-white/5">
                        <Text className="!text-text-muted text-xs">错误记录</Text>
                        <pre className="mt-3 p-4 rounded-xl bg-black/20 text-[12px] text-text-primary overflow-auto whitespace-pre-wrap break-words">
                          {formatJsonBlock(reportDetail.raw_errors || [])}
                        </pre>
                      </Card>
                      <Card size="small" className="!bg-bg-card !border-white/5">
                        <Text className="!text-text-muted text-xs">原始工具调用</Text>
                        <pre className="mt-3 p-4 rounded-xl bg-black/20 text-[12px] text-text-primary overflow-auto whitespace-pre-wrap break-words">
                          {formatJsonBlock(reportDetail.tool_calls || [])}
                        </pre>
                      </Card>
                    </div>
                  ),
                },
              ]}
            />
          </div>
        ) : (
          <Empty description="报告详情加载失败" />
        )}
      </Drawer>
    </div>
  );
}

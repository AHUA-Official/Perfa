'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, Tag, Empty, Typography, Drawer, Button, Skeleton, Space } from 'antd';
import { BarChartOutlined, ReloadOutlined, FileSearchOutlined } from '@ant-design/icons';
import { getReport, listReports, ReportDetail, ReportInfo } from '@/lib/api';

const { Text, Paragraph, Title } = Typography;

const typeColors: Record<string, string> = {
  quick_test: 'blue',
  full_assessment: 'purple',
  cpu_focus: 'green',
  storage_focus: 'orange',
  network_focus: 'cyan',
};

const typeLabels: Record<string, string> = {
  quick_test: '快速测试',
  full_assessment: '全面评估',
  cpu_focus: 'CPU 专项',
  storage_focus: '存储专项',
  network_focus: '网络专项',
};

function formatContent(content: unknown) {
  if (!content) return '暂无详细内容';
  if (typeof content === 'string') return content;
  try {
    return JSON.stringify(content, null, 2);
  } catch {
    return String(content);
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
      const data = await listReports();
      setReports(data);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  const groupedReports = useMemo(() => reports.slice().sort((a, b) => {
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
  }), [reports]);

  const reportStats = useMemo(() => ({
    total: reports.length,
    completed: reports.filter((report) => report.status === 'completed').length,
    cpu: reports.filter((report) => report.type === 'cpu_focus').length,
  }), [reports]);

  const openReport = async (report: ReportInfo) => {
    setSelectedReport(report);
    setDetailLoading(true);
    try {
      const detail = await getReport(report.id);
      setReportDetail(detail);
    } catch {
      setReportDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  if (reports.length === 0 && !loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <Title level={4} className="!text-text-primary !mb-1">测试报告</Title>
            <Text className="!text-text-secondary">运行完成后的结果会在这里沉淀和回看。</Text>
          </div>
          <Button icon={<ReloadOutlined />} onClick={() => void loadReports()}>刷新</Button>
        </div>
        <Card className="!bg-bg-card !border-white/5">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<span className="!text-text-muted">暂无测试报告，先跑一次压测工作流</span>}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <Title level={4} className="!text-text-primary !mb-1">测试报告</Title>
          <Text className="!text-text-secondary">按时间浏览历史结果，并查看详细输出与结构化内容。</Text>
        </div>
        <Space>
          <Tag color="gold">{reportStats.total} 份报告</Tag>
          <Tag color="green">{reportStats.completed} 已完成</Tag>
          <Tag color="blue">{reportStats.cpu} CPU</Tag>
          <Button icon={<ReloadOutlined />} onClick={() => void loadReports()} loading={loading}>
            刷新
          </Button>
        </Space>
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {groupedReports.map((report) => (
            <Card
              key={report.id}
              className="!bg-bg-card !border-white/5 hover:!border-primary/30 transition-all duration-200 cursor-pointer"
              onClick={() => void openReport(report)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Tag color={typeColors[report.type] || 'default'}>
                      {typeLabels[report.type] || report.type}
                    </Tag>
                    <Tag color={report.status === 'completed' ? 'green' : 'orange'}>
                      {report.status === 'completed' ? '已完成' : report.status}
                    </Tag>
                  </div>
                  <Text code className="!text-[11px] !text-primary">{report.server_id || 'unknown-server'}</Text>
                  <div className="mt-2 text-xs text-text-muted">
                    {new Date(report.created_at).toLocaleString('zh-CN')}
                  </div>
                </div>
                <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <BarChartOutlined />
                </div>
              </div>
              <Paragraph className="!text-text-secondary !text-sm !mt-3 !mb-0" ellipsis={{ rows: 3 }}>
                {report.summary || '这份报告没有摘要，点击查看详细内容。'}
              </Paragraph>
            </Card>
          ))}
        </div>
      )}

      <Drawer
        width={720}
        open={!!selectedReport}
        onClose={() => {
          setSelectedReport(null);
          setReportDetail(null);
        }}
        title={
          <div className="flex items-center gap-2">
            <FileSearchOutlined />
            <span>{selectedReport ? (typeLabels[selectedReport.type] || selectedReport.type) : '报告详情'}</span>
          </div>
        }
      >
        {detailLoading ? (
          <Skeleton active paragraph={{ rows: 12 }} />
        ) : reportDetail ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Card size="small" className="!bg-bg-card !border-white/5">
                <Text className="!text-text-muted text-xs">服务器</Text>
                <div className="mt-1"><Text code className="!text-primary">{reportDetail.server_id}</Text></div>
              </Card>
              <Card size="small" className="!bg-bg-card !border-white/5">
                <Text className="!text-text-muted text-xs">创建时间</Text>
                <div className="mt-1"><Text className="!text-text-primary">{new Date(reportDetail.created_at).toLocaleString('zh-CN')}</Text></div>
              </Card>
            </div>

            {reportDetail.summary && (
              <Card size="small" className="!bg-bg-card !border-white/5">
                <Text className="!text-text-muted text-xs">摘要</Text>
                <Paragraph className="!text-text-primary !mt-2 !mb-0 whitespace-pre-wrap">
                  {reportDetail.summary}
                </Paragraph>
              </Card>
            )}

            <Card size="small" className="!bg-bg-card !border-white/5">
              <Text className="!text-text-muted text-xs">详细内容</Text>
              <pre className="mt-3 p-4 rounded-xl bg-black/20 text-[12px] text-text-primary overflow-auto whitespace-pre-wrap break-words max-h-[60vh]">
                {formatContent(reportDetail.content)}
              </pre>
            </Card>
          </div>
        ) : (
          <Empty description="报告详情加载失败" />
        )}
      </Drawer>
    </div>
  );
}

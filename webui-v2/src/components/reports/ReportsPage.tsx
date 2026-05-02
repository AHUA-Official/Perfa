'use client';

import { useEffect, useState } from 'react';
import { Card, Tag, Empty, Typography } from 'antd';
import { listReports, ReportInfo } from '@/lib/api';

const { Text, Paragraph } = Typography;

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

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadReports();
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

  if (reports.length === 0) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-medium text-text-primary mb-4">测试报告</h2>
        <Empty
          description={
            <span className="!text-text-muted">暂无测试报告，先跑一次压测吧</span>
          }
        />
      </div>
    );
  }

  return (
    <div className="p-6">
      <h2 className="text-lg font-medium text-text-primary mb-4">测试报告</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((report) => (
          <Card
            key={report.id}
            className="!bg-bg-card !border-white/5 hover:!border-primary/30 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-2 mb-2">
              <Tag color={typeColors[report.type] || 'default'}>
                {typeLabels[report.type] || report.type}
              </Tag>
              <Tag color={report.status === 'completed' ? 'green' : 'red'}>
                {report.status === 'completed' ? '已完成' : report.status}
              </Tag>
            </div>
            <div className="text-xs text-text-muted mb-1">
              服务器: {report.server_id}
            </div>
            <div className="text-xs text-text-muted">
              {new Date(report.created_at).toLocaleString('zh-CN')}
            </div>
            {report.summary && (
              <Paragraph
                className="!text-text-secondary !text-xs !mt-2 !mb-0"
                ellipsis={{ rows: 2 }}
              >
                {report.summary}
              </Paragraph>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

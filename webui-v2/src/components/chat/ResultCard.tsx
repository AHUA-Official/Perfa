'use client';

import { BarChartOutlined, TableOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  data: Record<string, any>;
  children?: React.ReactNode;
}

export default function ResultCard({ title, data, children }: Props) {
  return (
    <div className="result-card">
      <div className="result-card-header">
        <BarChartOutlined />
        <span>{title}</span>
      </div>
      {children || (
        <div className="text-sm">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex justify-between py-1 border-b border-white/5 last:border-0">
              <span className="text-text-secondary">{key}</span>
              <span className="text-text-primary font-mono">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

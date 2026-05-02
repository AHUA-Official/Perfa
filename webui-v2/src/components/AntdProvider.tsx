'use client';

import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';

export default function AntdProvider({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#00D9A6',
          colorBgContainer: '#1A1D26',
          colorBgElevated: '#242830',
          colorBorder: 'rgba(255,255,255,0.06)',
          colorText: '#E8EAED',
          colorTextSecondary: '#9AA0A6',
          borderRadius: 8,
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      // Agent API 代理（chat/completions 由 API Route 单独处理，绕过 SSE 缓冲问题）
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:10000/v1/:path*',
      },
      {
        source: '/monitor/grafana',
        destination: 'http://localhost:3000/monitor/grafana/',
      },
      {
        source: '/monitor/grafana/:path*',
        destination: 'http://localhost:3000/monitor/grafana/:path*',
      },
      {
        source: '/api/monitor/jaeger',
        destination: 'http://localhost:16686/api/monitor/jaeger/',
      },
      {
        source: '/api/monitor/jaeger/:path*',
        destination: 'http://localhost:16686/api/monitor/jaeger/:path*',
      },
      {
        source: '/monitor/vm',
        destination: 'http://localhost:8428/vmui/',
      },
      {
        source: '/monitor/vm/:path*',
        destination: 'http://localhost:8428/vmui/:path*',
      },
      {
        source: '/api/jaeger/:path*',
        destination: 'http://localhost:16686/api/monitor/jaeger/:path*',
      },
    ];
  },
};

module.exports = nextConfig;

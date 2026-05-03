/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // Agent API 代理（chat/completions 由 API Route 单独处理，绕过 SSE 缓冲问题）
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:10000/v1/:path*',
      },
      {
        source: '/api/monitor/grafana',
        destination: 'http://localhost:3000/api/monitor/grafana/',
      },
      {
        source: '/api/monitor/grafana/:path*',
        destination: 'http://localhost:3000/api/monitor/grafana/:path*',
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
        source: '/api/monitor/vm',
        destination: 'http://localhost:8428/',
      },
      {
        source: '/api/monitor/vm/:path*',
        destination: 'http://localhost:8428/:path*',
      },
      {
        source: '/api/jaeger/:path*',
        destination: 'http://localhost:16686/api/monitor/jaeger/:path*',
      },
    ];
  },
};

module.exports = nextConfig;

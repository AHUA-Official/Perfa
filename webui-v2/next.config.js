/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // Agent API 代理
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:10000/v1/:path*',
      },
      // Jaeger 全站代理（解决浏览器 Private Network Access 阻止）
      {
        source: '/api/jaeger/:path*',
        destination: 'http://localhost:16686/:path*',
      },
      // Grafana 代理
      {
        source: '/api/grafana/:path*',
        destination: 'http://localhost:3000/:path*',
      },
      // VictoriaMetrics 代理
      {
        source: '/api/vm/:path*',
        destination: 'http://localhost:8428/:path*',
      },
    ];
  },
};

module.exports = nextConfig;

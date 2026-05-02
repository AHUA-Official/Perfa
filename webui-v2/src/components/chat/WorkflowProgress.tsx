'use client';

import { CheckCircleFilled, SyncOutlined, CloseCircleFilled, ClockCircleOutlined } from '@ant-design/icons';

interface WorkflowStatus {
  scenario: string;
  node_statuses: Record<string, string>;
  completed_nodes: string[];
  current_node?: string;
}

interface Props {
  status: WorkflowStatus;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; className: string }> = {
  completed: {
    icon: <CheckCircleFilled />,
    className: 'completed',
  },
  running: {
    icon: <SyncOutlined spin />,
    className: 'running',
  },
  failed: {
    icon: <CloseCircleFilled />,
    className: 'failed',
  },
  pending: {
    icon: <ClockCircleOutlined />,
    className: 'pending',
  },
};

const NODE_DISPLAY_NAMES: Record<string, string> = {
  check_environment: '环境检查',
  select_server: '选择服务器',
  check_tools: '工具检查',
  install_tools: '安装工具',
  run_benchmark: '执行测试',
  run_unixbench: 'UnixBench',
  run_superpi: 'SuperPI',
  run_fio: 'FIO',
  run_stream: 'Stream',
  run_mlc: 'MLC',
  run_hping3: 'hping3',
  run_sysbench_cpu: 'sysbench CPU',
  run_sysbench_memory: 'sysbench Memory',
  run_sysbench_threads: 'sysbench Threads',
  run_openssl_speed: 'OpenSSL Speed',
  run_stress_ng: 'stress-ng',
  run_iperf3: 'iperf3',
  run_7z_b: '7z Benchmark',
  cpu_test: 'CPU测试',
  memory_test: '内存测试',
  disk_test: '磁盘测试',
  network_test: '网络测试',
  sysbench_cpu_test: 'sysbench CPU',
  sysbench_threads_test: 'sysbench Threads',
  openssl_speed_test: 'OpenSSL Speed',
  sysbench_memory_test: 'sysbench Memory',
  iperf3_throughput: 'iperf3 吞吐',
  hping3_latency: 'hping3 延迟',
  collect_results: '收集结果',
  generate_report: '生成报告',
  handle_error: '错误处理',
};

export default function WorkflowProgress({ status }: Props) {
  const entries = Object.entries(status.node_statuses);
  if (entries.length === 0) return null;

  return (
    <div className="px-6 py-3">
      <div className="text-xs text-text-secondary mb-2">
        工作流: <span className="text-primary font-medium">{status.scenario}</span>
      </div>
      <div className="workflow-progress">
        {entries.map(([node, state], idx) => {
          const config = STATUS_CONFIG[state] || STATUS_CONFIG.pending;
          const displayName =
            NODE_DISPLAY_NAMES[node] || node.replace(/_/g, ' ');

          return (
            <div key={node} className="flex items-center">
              <div className={`workflow-node ${config.className}`}>
                {config.icon}
                <span>{displayName}</span>
              </div>
              {idx < entries.length - 1 && (
                <span className="workflow-arrow">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

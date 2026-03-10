"""
DaemonSet Agent 主入口
负责启动所有Agent组件
"""

import argparse
import logging
import signal
import sys
from pathlib import Path

import yaml

from core.agent import Agent
from utils.logger import setup_logging

# 设置日志
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，准备退出...")
    sys.exit(0)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Perfa DaemonSet Agent')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='日志级别'
    )
    args = parser.parse_args()
    
    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # 设置日志
    setup_logging(
        level=args.log_level,
        log_file=config.get('logging', {}).get('path', '/var/log/perfa-agent.log')
    )
    
    logger.info("=" * 60)
    logger.info("启动 Perfa DaemonSet Agent")
    logger.info(f"配置文件: {config_path}")
    logger.info(f"Agent ID: {config['agent']['id']}")
    logger.info("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动Agent
    agent = Agent(config)
    
    try:
        # 启动Agent（会阻塞）
        agent.start()
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，准备退出...")
    except Exception as e:
        logger.error(f"Agent启动失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 停止Agent
        agent.stop()
        logger.info("Agent已停止")


if __name__ == "__main__":
    main()

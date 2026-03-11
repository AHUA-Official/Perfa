# 守护进程 agent 的设计

## 守护进程 agent 的功能

1. monitor - 采集cpu、内存、磁盘等系统资源使用情况
2. tool - 管理对应的压力测试工具
3. benchmark - 管理对应的压力测试任务
4. api - 提供和mcp交互的接口

## 守护进程 agent 的架构


## monitor 的实现

在monitor文件夹下，实现cpu、内存、磁盘等系统资源的采集，当前阶段只需要打log
启动main.py, 就可以把monitor的功能注册进去 然后起来
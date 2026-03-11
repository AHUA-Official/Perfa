# Tool 模块使用指南

## 目录结构

```
tool/
├── sources/          # 源代码目录（需手动上传）
│   ├── cpu/
│   │   ├── unixbench/    # UnixBench 源码
│   │   └── superpi/      # SuperPi 源码
│   ├── mem/
│   │   ├── stream.c      # STREAM 源码（单个文件）
│   │   └── mlc/          # MLC 二进制
│   ├── disk/
│   └── net/
└── binaries/         # 编译产物目录（自动生成）
    ├── cpu/
    ├── mem/
    ├── disk/
    └── net/
```

## 文件上传位置

### CPU 测试工具

**UnixBench**:
```bash
# 解压 UnixBench 源码到:
/home/ubuntu/Perfa/src/node_agent/tool/sources/cpu/unixbench/

# 目录结构应为:
sources/cpu/unixbench/UnixBench/Run  (或 sources/cpu/unixbench/Run)
```

**SuperPi**:
```bash
# 解压 SuperPi 源码到:
/home/ubuntu/Perfa/src/node_agent/tool/sources/cpu/superpi/

# 目录结构应为:
sources/cpu/superpi/super_pi  (或 sources/cpu/superpi/SuperPi)
```

### 内存测试工具

**STREAM**:
```bash
# 直接上传 stream.c 文件:
/home/ubuntu/Perfa/src/node_agent/tool/sources/mem/stream.c
```

**MLC**:
```bash
# 上传 MLC 二进制文件:
/home/ubuntu/Perfa/src/node_agent/tool/sources/mem/mlc

# 或解压 MLC 包到:
/home/ubuntu/Perfa/src/node_agent/tool/sources/mem/mlc/Linux/mlc
```

### 磁盘测试工具

**FIO**:
- 通过 apt 自动安装，无需手动上传

### 网络测试工具

**hping3**:
- 通过 apt 自动安装，无需手动上传

## 使用方法

### 1. 上传源码后安装

```python
from node_agent.tool import ToolManager

manager = ToolManager()

# 检查工具状态
status = manager.check_tool("stream")
print(status)
# {'status': 'not_installed', 'message': 'STREAM source available, ready to compile'}

# 安装（编译）
result = manager.install_tool("stream")
print(result)
# {'success': True, 'message': 'Successfully installed stream'}
```

### 2. 批量检查

```bash
# 命令行
python3 src/node_agent/tool/test_tool_manager.py check
```

### 3. 批量安装

```bash
python3 src/node_agent/tool/test_tool_manager.py install
```

## 安装说明

| 工具 | 安装方式 | 需要上传 |
|------|---------|---------|
| unixbench | 本地编译 | UnixBench 源码 |
| superpi | 本地编译 | SuperPi 源码 |
| stream | 本地编译 | stream.c |
| mlc | 复制二进制 | mlc 二进制 |
| fio | apt 安装 | 无需 |
| hping3 | apt 安装 | 无需 |

## 编译依赖

```bash
# 安装编译工具
sudo apt-get install build-essential gcc g++ make

# UnixBench 可能需要
sudo apt-get install libx11-dev libgl1-mesa-dev
```

## 注意事项

1. `sources/` 目录存放源代码，不会被删除
2. `binaries/` 目录存放编译产物，卸载时会被清理
3. 修改源码后需要重新安装才会生效
4. 卸载操作只清理编译产物，不删除源码

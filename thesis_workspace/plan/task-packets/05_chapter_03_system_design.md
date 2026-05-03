# Task Packet

- Scope: 写作第三章系统总体设计，覆盖架构、流程、模块、接口、数据存储和部署拓扑。
- Files to read: `codeknowledge/01-architecture-overview.md`, `codeknowledge/03-operations/environments-and-topology.md`, `codeknowledge/03-operations/runtime-and-ports.md`, `codeknowledge/06-deep-dives/*.md`, `ops/scripts/start-all.sh`, `src/mcp_server/storage/database.py`, `src/mcp_server/config.py`
- Files allowed to edit: `thesis_workspace/chapters/03_system_design.md`, `thesis_workspace/figures/data-manifest.md`, `thesis_workspace/tables/table-schema.md`, `thesis_workspace/plan/progress.md`
- Required skills: writing-chapters, writing-core, figures-diagram
- Evidence/data inputs: Perfa architecture docs, startup scripts, database schema, module deep dives
- Required artifacts: 第三章初稿、架构/流程/拓扑图占位、模块职责表、接口表、数据存储表
- Rejection checks: 不写成 README；不深入到第四章实现细节；部署模式必须区分已验证本地链路和代码支持的混合链路；不夸大远端多节点一键部署成熟度
- Validation commands: `wc -m thesis_workspace/chapters/03_system_design.md`; `rg '首先|其次|最后|此外|另外|接下来|总之|值得注意的是|需要指出的是|显而易见|我认为|我觉得' thesis_workspace/chapters/03_system_design.md`

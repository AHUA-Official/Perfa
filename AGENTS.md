# Perfa Agent Harness Rules

This repository is a vertical agent harness for server performance testing. It is not a general coding-agent scheduler. Agents working in this repo must preserve the boundary between natural-language orchestration and real benchmark execution.

## System Scope

Perfa orchestrates this chain:

1. User request in WebUI V2.
2. LangChain Agent routes the request to a workflow or ReAct mode.
3. MCP Server exposes bounded tools for server, agent, tool, benchmark, report, and knowledge operations.
4. Node Agent runs the real benchmark and monitor tasks on the target node.
5. ReportStore and ReportsPage preserve the final explanation plus raw evidence.

Do not bypass MCP Server or Node Agent for benchmark work unless a test explicitly owns that lower-level module.

## Required Benchmark Lifecycle

Every performance-test workflow must follow this lifecycle:

1. Select the target server.
2. Check Node Agent health/status.
3. Check required benchmark tools.
4. Install missing tools only when the workflow owns that action.
5. Run exactly the intended benchmark task.
6. Poll status until completed, failed, or timed out.
7. Fetch raw result and log references.
8. Generate a report.
9. Persist evidence for later review.

The workflow must not claim success before the result has a task id and retrievable raw output.

## Evidence Checklist

A report is complete only when the available fields are preserved. Required fields depend on the workflow, but agents should keep as many as the system can produce:

- `task_id` or `task_ids`
- `raw_results`
- `raw_errors`
- `tool_calls`
- `trace_id` when tracing is enabled
- `log_path` or log reference when Node Agent returns one
- `knowledge_matches` when benchmark knowledge retrieval runs
- server identity: `server_id`, alias or IP

If evidence is missing, say which part is missing. Do not replace missing evidence with an LLM-only conclusion.

## MCP Tool Boundary

Use MCP for capabilities that reflect real project state or changing external state:

- server registration and status
- Node Agent lifecycle
- benchmark tool installation and verification
- benchmark execution and result retrieval
- report generation
- FurinaBench benchmark knowledge retrieval

Do not add MCP tools for static facts that can live in normal repo docs. Avoid broad shell-style MCP tools that allow arbitrary actions.

## Knowledge Boundary

`benchmarkknowledge/FurinaBench-main` is the runtime benchmark knowledge base. The implemented capability is local Markdown retrieval through `search_benchmark_knowledge`.

This is not a full vector-database RAG system. ChromaDB, embedding search, and historical report similarity remain future extensions unless code and tests prove otherwise.

## Verification Rules

Before saying a change is complete, run focused verification that matches the edited area:

- MCP tools: `python3 test/mcp_server/test_tools.py`
- workflow nodes: `python3 test/langchain_agent/test_workflow_nodes.py`
- Node Agent runtime: `python3 test/node_agent/test_executor_runtime.py`
- ops scripts: `python3 test/ops/test_scripts.py`
- WebUI helpers/pages: corresponding scripts under `test/webui_v2/`

If a command cannot run or enters an interactive setup flow, report that exactly. Do not mark it as passed.

## Harness Design Boundary

Perfa may borrow harness-engineering practices from coding-agent systems: short instructions, explicit lifecycle, progress tracking, verification gates, and evidence capture.

Perfa should not copy coding-agent product assumptions such as issue-daemon scheduling, concurrent code-edit workers, automatic PR loops, or low-friction merge policies. Server performance testing values isolation, repeatability, and evidence preservation more than task throughput.

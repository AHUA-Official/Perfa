"""Benchmark knowledge base retrieval tools."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool


_TEST_ALIASES = {
    "cpu_test": ["sysbench", "cpu", "unixbench", "superpi", "处理器"],
    "memory_test": ["stream", "mlc", "memory", "内存", "带宽"],
    "disk_test": ["fio", "storage", "磁盘", "存储", "iops", "延迟"],
    "storage_test": ["fio", "storage", "磁盘", "存储", "iops", "延迟"],
    "network_test": ["iperf", "iperf3", "hping", "network", "网络"],
    "unixbench": ["unixbench", "unix bench", "cpu", "综合性能", "跑分"],
    "superpi": ["superpi", "super pi", "pi", "单核", "cpu"],
    "sysbench_cpu": ["sysbench", "cpu", "events_per_sec"],
    "sysbench_memory": ["sysbench", "memory", "内存"],
    "sysbench_threads": ["sysbench", "threads", "线程"],
    "stream": ["stream", "内存", "bandwidth", "带宽"],
    "mlc": ["mlc", "内存", "latency", "bandwidth"],
    "fio": ["fio", "磁盘", "存储", "iops", "latency", "延时"],
    "iperf3": ["iperf", "iperf3", "网络", "吞吐"],
    "hping3": ["hping", "hping3", "网络", "rtt", "延迟"],
    "openssl_speed": ["openssl", "crypto", "加密", "cpu"],
    "stress_ng": ["stress-ng", "stress", "压力"],
    "7z_b": ["7z", "7zip", "压缩", "mips"],
}

_CATEGORY_ALIASES = {
    "cpu": ["cpu", "04-cpu", "处理器", "单核", "调度"],
    "memory": ["memory", "内存", "05-内存", "stream", "mlc"],
    "storage": ["storage", "存储", "磁盘", "06-存储", "fio", "aio"],
    "network": ["network", "网络", "07-网络", "iperf", "hping", "ping"],
    "database": ["database", "数据库", "08-数据库", "mysql", "sysbench"],
    "web": ["web", "http", "09-http", "wrk", "ab"],
}


def _default_knowledge_root() -> Path:
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "benchmarkknowledge" / "FurinaBench-main"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _terms(*values: Optional[str]) -> List[str]:
    terms: List[str] = []
    for value in values:
        if not value:
            continue
        normalized = _normalize(value)
        terms.extend(part for part in re.split(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]+", normalized) if part)
    return list(dict.fromkeys(terms))


def _infer_category(path: Path) -> str:
    text = _normalize(str(path))
    for category, aliases in _CATEGORY_ALIASES.items():
        if any(alias.lower() in text for alias in aliases):
            return category
    return "general"


def _clean_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", text)
    text = re.sub(r"`{1,3}", " ", text)
    text = re.sub(r"[#>*_\-|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class BenchmarkKnowledgeSearchTool(BaseTool):
    """Search the local FurinaBench Markdown knowledge base."""

    name = "search_benchmark_knowledge"
    description = """检索本地 FurinaBench 性能 Benchmark 知识库，返回与测试工具、指标解释、参数选择和诊断建议相关的 Markdown 片段。

适用场景：
- 生成压测报告时补充方法依据和注意事项
- 用户询问 fio、UnixBench、stream、iperf3 等工具如何理解结果
- 根据测试类型检索 CPU、内存、存储、网络相关知识"""
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "检索问题或关键词，例如：fio 随机读写延迟、UnixBench 单核分数",
            },
            "test_name": {
                "type": "string",
                "description": "可选的测试名称，用于补充检索词",
            },
            "category": {
                "type": "string",
                "description": "可选分类",
                "enum": ["cpu", "memory", "storage", "network", "database", "web", "general"],
            },
            "limit": {
                "type": "integer",
                "description": "返回片段数量",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, knowledge_root: Optional[str] = None):
        root = knowledge_root or os.getenv("PERFA_BENCHMARK_KNOWLEDGE_PATH")
        self.knowledge_root = Path(root) if root else _default_knowledge_root()
        self._index: Optional[List[Dict[str, Any]]] = None

    def execute(
        self,
        query: str,
        test_name: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        if not self.knowledge_root.exists():
            return {
                "success": False,
                "error": f"Benchmark knowledge path not found: {self.knowledge_root}",
                "matches": [],
            }

        index = self._load_index()
        search_terms = _terms(query, test_name, " ".join(_TEST_ALIASES.get(test_name or "", [])))
        if not search_terms:
            return {"success": True, "query": query, "matches": []}

        scored = []
        wanted_category = (category or "").lower()
        for doc in index:
            if wanted_category and wanted_category != "general" and doc["category"] != wanted_category:
                continue
            score = self._score_doc(doc, search_terms, test_name)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        matches = [self._format_match(doc, score, search_terms) for score, doc in scored[: max(1, min(limit, 10))]]
        return {
            "success": True,
            "query": query,
            "test_name": test_name,
            "category": category,
            "knowledge_root": str(self.knowledge_root),
            "matches": matches,
        }

    def _load_index(self) -> List[Dict[str, Any]]:
        if self._index is not None:
            return self._index

        docs: List[Dict[str, Any]] = []
        for path in sorted(self.knowledge_root.rglob("*.md")):
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel_path = path.relative_to(self.knowledge_root)
            title = path.stem
            heading = next((line.lstrip("# ").strip() for line in raw.splitlines() if line.strip().startswith("#")), "")
            clean = _clean_markdown(raw)
            docs.append({
                "title": heading or title,
                "path": str(rel_path),
                "category": _infer_category(rel_path),
                "content": clean[:30000],
            })

        self._index = docs
        return docs

    def _score_doc(self, doc: Dict[str, Any], terms: List[str], test_name: Optional[str]) -> int:
        title = _normalize(doc["title"])
        path = _normalize(doc["path"])
        content = _normalize(doc["content"])
        score = 0

        for term in terms:
            if not term:
                continue
            if term in title:
                score += 12
            if term in path:
                score += 8
            occurrences = content.count(term)
            if occurrences:
                score += min(occurrences, 8)

        for alias in _TEST_ALIASES.get(test_name or "", []):
            alias_norm = _normalize(alias)
            if alias_norm and (alias_norm in title or alias_norm in path):
                score += 10

        return score

    def _format_match(self, doc: Dict[str, Any], score: int, terms: List[str]) -> Dict[str, Any]:
        content = doc["content"]
        content_lower = _normalize(content)
        start = 0
        for term in terms:
            idx = content_lower.find(term.lower())
            if idx >= 0:
                start = max(0, idx - 90)
                break
        snippet = content[start:start + 420].strip()
        if start > 0:
            snippet = "..." + snippet
        if len(content) > start + 420:
            snippet += "..."

        return {
            "title": doc["title"],
            "path": doc["path"],
            "category": doc["category"],
            "score": score,
            "snippet": snippet,
        }

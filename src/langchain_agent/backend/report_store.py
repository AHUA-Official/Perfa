"""Lightweight persistent store for workflow reports."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReportStore:
    """Persist workflow reports as a JSON array on disk."""

    def __init__(self, path: Optional[str] = None):
        default_path = "/home/ubuntu/Perfa/data/langchain/reports.json"
        self.path = Path(path or os.getenv("LANGCHAIN_REPORT_STORE_PATH", default_path))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read_all(self) -> List[Dict[str, Any]]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            if not raw:
                return []
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_all(self, reports: List[Dict[str, Any]]) -> None:
        self.path.write_text(
            json.dumps(reports, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def save_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            reports = self._read_all()
            reports = [item for item in reports if item.get("id") != report.get("id")]
            reports.append(report)
            reports.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            self._write_all(reports)
        return report

    def list_reports(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            reports = self._read_all()
        reports.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return reports[:limit]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            reports = self._read_all()
        for report in reports:
            if report.get("id") == report_id:
                return report
        return None

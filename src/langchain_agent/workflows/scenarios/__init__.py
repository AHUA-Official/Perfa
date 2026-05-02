"""
Perfa - LangChain Agent Module

@file: workflows/scenarios/__init__.py
@desc: 场景模板包
@author: Perfa Team
@date: 2026-04-27
"""

from langchain_agent.workflows.scenarios.quick_test import build_quick_test_graph
from langchain_agent.workflows.scenarios.full_assessment import build_full_assessment_graph
from langchain_agent.workflows.scenarios.cpu_focus import build_cpu_focus_graph
from langchain_agent.workflows.scenarios.storage_focus import build_storage_focus_graph
from langchain_agent.workflows.scenarios.network_focus import build_network_focus_graph

__all__ = [
    "build_quick_test_graph",
    "build_full_assessment_graph",
    "build_cpu_focus_graph",
    "build_storage_focus_graph",
    "build_network_focus_graph",
]

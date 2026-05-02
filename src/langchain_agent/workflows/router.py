"""
Perfa - LangChain Agent Module

@file: workflows/router.py
@desc: 场景路由器 - LLM 意图识别 → 场景选择
@author: Perfa Team
@date: 2026-04-27
"""

import json
import re
from dataclasses import dataclass
from typing import Optional

from langchain_agent.core.logger import get_logger
logger = get_logger()


@dataclass
class Scenario:
    """场景定义"""
    name: str           # 场景标识
    display_name: str   # 显示名称
    description: str    # 场景描述
    keywords: list      # 触发关键词


# 预定义场景
SCENARIOS = {
    "quick_test": Scenario(
        name="quick_test",
        display_name="快速测试",
        description="单项快速测试，如测一下CPU、跑个fio",
        keywords=["快速", "测一下", "跑个", "单项", "简单测试", "quick"]
    ),
    "full_assessment": Scenario(
        name="full_assessment",
        display_name="全面性能评估",
        description="全面性能评估，包含CPU/内存/磁盘/网络全项测试",
        keywords=["全面", "完整", "综合", "评估", "全量", "full", "all"]
    ),
    "cpu_focus": Scenario(
        name="cpu_focus",
        display_name="CPU 专项评估",
        description="CPU 深度测试，包含 UnixBench + SuperPI",
        keywords=["cpu", "处理器", "算力", "计算性能", "unixbench", "superpi"]
    ),
    "storage_focus": Scenario(
        name="storage_focus",
        display_name="存储专项评估",
        description="存储/内存测试，包含 FIO + MLC + Stream",
        keywords=["磁盘", "硬盘", "存储", "io", "内存带宽", "fio", "mlc", "stream", "disk"]
    ),
    "network_focus": Scenario(
        name="network_focus",
        display_name="网络专项评估",
        description="网络测试，包含 hping3 延迟和丢包",
        keywords=["网络", "延迟", "带宽", "丢包", "hping3", "network", "ping"]
    ),
    "free_chat": Scenario(
        name="free_chat",
        display_name="自由对话",
        description="闲聊或非测试请求，走原 ReAct 循环",
        keywords=[]
    ),
}

# 路由 Prompt
ROUTER_PROMPT = """你是一个场景分类器。根据用户查询，判断属于哪个测试场景。

## 可选场景

- quick_test: 单项快速测试，如"测一下CPU"、"跑个fio"、"帮我跑个superpi"
- full_assessment: 全面性能评估，如"全面评估服务器性能"、"完整测试"、"综合评估"
- cpu_focus: CPU 深度测试，如"详细CPU测试"、"CPU性能分析"、"测试处理器"
- storage_focus: 存储/内存测试，如"测试磁盘性能"、"内存带宽测试"、"IO性能"
- network_focus: 网络测试，如"测试网络延迟"、"网络质量"、"ping测试"
- free_chat: 闲聊、问候或非性能测试请求

## 用户查询

{query}

## 输出格式

请以 JSON 格式返回：
{{"scenario": "场景名", "confidence": 0.0-1.0, "reason": "选择原因"}}

只返回 JSON，不要其他内容。"""


class ScenarioRouter:
    """
    场景路由器
    
    使用 LLM 进行意图识别，将用户查询路由到对应的测试场景。
    置信度低于阈值时走 free_chat（原 ReAct 循环）。
    """
    
    def __init__(self, llm, confidence_threshold: float = 0.7):
        """
        初始化场景路由器
        
        Args:
            llm: LangChain LLM 实例
            confidence_threshold: 置信度阈值，低于此值走 free_chat
        """
        self.llm = llm
        self.confidence_threshold = confidence_threshold
        logger.info(f"场景路由器初始化完成，置信度阈值: {confidence_threshold}")
    
    async def route(self, query: str) -> Scenario:
        """
        路由用户查询到对应场景
        
        Args:
            query: 用户查询
            
        Returns:
            Scenario: 匹配的场景
        """
        # 1. 先尝试关键词快速匹配
        quick_match = self._quick_match(query)
        if quick_match:
            logger.info(f"关键词快速匹配场景: {quick_match.name}")
            return quick_match
        
        # 2. 使用 LLM 进行意图识别
        try:
            scenario = await self._llm_route(query)
            logger.info(f"LLM 路由场景: {scenario.name}")
            return scenario
        except Exception as e:
            logger.warning(f"LLM 路由失败: {e}，降级到 free_chat")
            return SCENARIOS["free_chat"]
    
    def _quick_match(self, query: str) -> Optional[Scenario]:
        """
        基于关键词的快速匹配
        
        Args:
            query: 用户查询（小写化）
            
        Returns:
            Optional[Scenario]: 匹配的场景，无匹配返回 None
        """
        query_lower = query.lower()
        
        # 优先匹配更具体的场景
        for scenario_name in ["full_assessment", "cpu_focus", "storage_focus", "network_focus", "quick_test"]:
            scenario = SCENARIOS[scenario_name]
            for keyword in scenario.keywords:
                if keyword in query_lower:
                    return scenario
        
        return None
    
    async def _llm_route(self, query: str) -> Scenario:
        """
        使用 LLM 进行场景路由
        
        Args:
            query: 用户查询
            
        Returns:
            Scenario: 匹配的场景
        """
        prompt = ROUTER_PROMPT.format(query=query)
        
        # 调用 LLM
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        # 解析 JSON
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if not json_match:
            logger.warning(f"无法解析路由结果: {content}")
            return SCENARIOS["free_chat"]
        
        try:
            result = json.loads(json_match.group())
            scenario_name = result.get("scenario", "free_chat")
            confidence = result.get("confidence", 0.0)
            reason = result.get("reason", "")
            
            logger.info(f"路由结果: scenario={scenario_name}, confidence={confidence}, reason={reason}")
            
            # 置信度检查
            if confidence < self.confidence_threshold:
                logger.info(f"置信度 {confidence} 低于阈值 {self.confidence_threshold}，走 free_chat")
                return SCENARIOS["free_chat"]
            
            # 场景名验证
            if scenario_name not in SCENARIOS:
                logger.warning(f"未知场景名: {scenario_name}，走 free_chat")
                return SCENARIOS["free_chat"]
            
            return SCENARIOS[scenario_name]
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return SCENARIOS["free_chat"]

"""
Perfa - LangChain Agent Module

@file: tools/mcp_adapter.py
@desc: MCP工具适配器
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
from typing import List, Dict, Any, Optional, Callable, Type

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model

# MCP SDK导入
from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPToolAdapter:
    """
    MCP工具适配器
    
    将MCP工具封装为LangChain兼容的工具格式
    """
    
    def __init__(self, sse_url: str, api_key: Optional[str] = None):
        """
        初始化MCP工具适配器
        
        Args:
            sse_url: MCP Server的SSE URL (e.g., http://localhost:8000/sse)
            api_key: API密钥（如果需要认证）
        """
        self.sse_url = sse_url
        self.api_key = api_key
        self.tools: Dict[str, BaseTool] = {}
        self.session: Optional[ClientSession] = None
        self._connection_lock = asyncio.Lock()
        
        logger.info(f"MCP工具适配器初始化完成，Server地址: {sse_url}")
    
    async def connect(self) -> bool:
        """
        连接到MCP Server并加载工具列表
        
        注意：此方法只加载工具列表，不保持持久连接
        实际的工具调用会在每次调用时建立新连接
        
        Returns:
            bool: 是否连接成功
        """
        async with self._connection_lock:
            try:
                logger.info(f"正在连接MCP Server: {self.sse_url}")
                
                # 建立临时SSE连接以加载工具列表
                async with sse_client(self.sse_url) as streams:
                    async with ClientSession(*streams) as session:
                        # 初始化会话
                        await session.initialize()
                        
                        # 加载工具（使用临时session）
                        await self._load_tools_with_session(session)
                        
                        logger.info(f"MCP Server连接成功，加载 {len(self.tools)} 个工具")
                        return True
                        
            except Exception as e:
                logger.error(f"MCP Server连接失败: {str(e)}")
                return False
    
    async def _load_tools_with_session(self, session: ClientSession):
        """使用指定session加载工具"""
        try:
            # 获取工具列表
            result = await session.list_tools()
            
            # MCP返回的是ListToolsResult对象，需要访问tools属性
            if hasattr(result, 'tools'):
                tools_list = result.tools
            else:
                tools_list = result if isinstance(result, list) else []
            
            logger.debug(f"MCP返回 {len(tools_list)} 个工具")
            
            for tool_info in tools_list:
                # 获取工具名称和描述
                if hasattr(tool_info, 'name'):
                    tool_name = tool_info.name
                    tool_desc = getattr(tool_info, 'description', '无描述')
                else:
                    logger.warning(f"工具格式异常: {type(tool_info)}")
                    continue
                
                # 将MCP工具包装为LangChain工具
                wrapped_tool = self._wrap_tool(tool_info)
                self.tools[tool_name] = wrapped_tool
                
                logger.debug(f"加载MCP工具: {tool_name}")
            
            logger.info(f"成功加载 {len(self.tools)} 个MCP工具")
            
        except Exception as e:
            logger.error(f"加载MCP工具失败: {str(e)}")
            raise
    
    async def _load_tools(self):
        """从MCP Server加载工具（已废弃，使用_load_tools_with_session）"""
        # 此方法已废弃，保留向后兼容
        pass
    
    def _wrap_tool(self, tool_info) -> BaseTool:
        """
        包装MCP工具为LangChain工具
        
        Args:
            tool_info: MCP工具信息
        
        Returns:
            BaseTool: LangChain兼容的工具
        """
        # 获取工具描述
        description = tool_info.description if hasattr(tool_info, 'description') else f"MCP工具: {tool_info.name}"
        
        # 根据inputSchema创建参数模型
        args_schema = self._create_args_schema(tool_info)
        
        # 创建异步工具函数
        async def async_tool_function(**kwargs):
            """异步工具函数 - 每次调用建立临时连接"""
            try:
                # 过滤 None 值，MCP Server 不接受 null 参数
                filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
                logger.info(f"调用MCP工具: {tool_info.name}，参数: {filtered_kwargs}")
                
                # 建立临时SSE连接
                async with sse_client(self.sse_url) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        
                        # 调用MCP工具
                        result = await session.call_tool(tool_info.name, filtered_kwargs)
                        
                        logger.info(f"MCP工具调用成功: {tool_info.name}")
                        logger.debug(f"MCP返回结果类型: {type(result)}")
                        logger.debug(f"MCP返回结果属性: {dir(result)}")
                        logger.debug(f"MCP返回结果: {result}")
                        
                        # 解析结果
                        # MCP SDK 的 CallToolResult 对象结构：
                        # - content: List[TextContent | ImageContent | ...]
                        # - isError: bool (optional)
                        if hasattr(result, 'structuredContent') and result.structuredContent:
                            return result.structuredContent
                        elif hasattr(result, 'content'):
                            # content 是一个列表，包含 TextContent/ImageContent 等
                            content = result.content
                            if isinstance(content, list) and len(content) > 0:
                                first_item = content[0]
                                # 尝试获取 text 属性（TextContent 类型）
                                if hasattr(first_item, 'text'):
                                    text_content = first_item.text
                                    # 尝试解析为 JSON（MCP 工具返回的通常是 JSON 字符串）
                                    try:
                                        import json
                                        parsed = json.loads(text_content)
                                        logger.debug(f"成功解析JSON响应: {parsed}")
                                        return parsed
                                    except (json.JSONDecodeError, TypeError):
                                        # 如果不是 JSON，返回原始文本
                                        logger.debug(f"返回原始文本: {text_content}")
                                        return text_content
                                else:
                                    return str(first_item)
                            return str(content)
                        else:
                            logger.warning(f"未知的结果格式: {result}")
                            return result
                
            except Exception as e:
                error_msg = f"MCP工具调用失败 {tool_info.name}: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
        
        # 创建LangChain StructuredTool
        tool = StructuredTool(
            name=tool_info.name,
            description=description,
            func=lambda **kwargs: kwargs,  # 占位符
            coroutine=async_tool_function,
            args_schema=args_schema
        )
        
        return tool
    
    def _map_json_type_to_python(self, json_type: str, json_schema: dict) -> tuple:
        """
        将JSON Schema类型映射到Python类型
        
        Args:
            json_type: JSON Schema类型字符串
            json_schema: 完整的属性定义（用于处理enum等）
        
        Returns:
            tuple: (Python类型, 默认值)
        """
        type_mapping = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        # 获取基础类型
        base_type = type_mapping.get(json_type, str)
        
        # 处理特殊类型
        if json_type == 'string' and 'enum' in json_schema:
            # 枚举类型保持为字符串
            pass
        
        return base_type, None
    
    def _create_args_schema(self, tool_info) -> Optional[Type[BaseModel]]:
        """
        根据MCP工具的inputSchema创建Pydantic模型
        
        Args:
            tool_info: MCP工具信息
        
        Returns:
            Optional[Type[BaseModel]]: 参数模型或None
        """
        try:
            # 获取inputSchema
            if not hasattr(tool_info, 'inputSchema'):
                return None
            
            schema = tool_info.inputSchema
            if not isinstance(schema, dict):
                return None
            
            # 如果没有properties，返回None（无参数工具）
            properties = schema.get('properties', {})
            if not properties:
                return None
            
            required_fields = set(schema.get('required', []))
            
            # 动态创建Pydantic模型
            fields = {}
            for prop_name, prop_def in properties.items():
                # 获取类型
                prop_type_str = prop_def.get('type', 'string')
                description = prop_def.get('description', '')
                default_value = prop_def.get('default')
                
                # 将JSON Schema类型映射到Python类型
                python_type, _ = self._map_json_type_to_python(prop_type_str, prop_def)
                
                # 如果是required字段，不设默认值
                if prop_name in required_fields:
                    # Required字段
                    fields[prop_name] = (python_type, Field(..., description=description))
                else:
                    # Optional字段 - 使用Optional包装
                    if default_value is not None:
                        # 如果schema定义了默认值，使用它
                        fields[prop_name] = (Optional[python_type], Field(default=default_value, description=description))
                    else:
                        # 否则使用None作为默认值
                        fields[prop_name] = (Optional[python_type], Field(default=None, description=description))
            
            # 创建动态模型
            model_name = f"{tool_info.name}_args"
            model = create_model(model_name, **fields)
            
            return model
            
        except Exception as e:
            logger.warning(f"创建参数模型失败 {tool_info.name}: {e}")
            return None
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取指定工具
        
        Args:
            name: 工具名称
        
        Returns:
            Optional[BaseTool]: 工具或None
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """
        获取所有工具
        
        Returns:
            List[BaseTool]: 工具列表
        """
        return list(self.tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        获取所有工具名称
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        测试MCP Server连接
        
        Returns:
            Dict: 测试结果
        """
        try:
            success = await self.connect()
            
            if success:
                return {
                    "success": True,
                    "message": f"MCP Server连接成功，可用工具数: {len(self.tools)}",
                    "tool_count": len(self.tools),
                    "tool_names": self.get_tool_names()
                }
            else:
                return {
                    "success": False,
                    "error": "MCP Server连接失败",
                    "tool_count": 0,
                    "tool_names": []
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"测试连接时发生异常: {str(e)}",
                "tool_count": 0,
                "tool_names": []
            }
    
    async def close(self):
        """关闭连接"""
        if self.session:
            # MCP会话通常不需要显式关闭
            logger.info("MCP会话已关闭")

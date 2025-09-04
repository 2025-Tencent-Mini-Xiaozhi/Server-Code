"""服务端MCP工具执行器"""

from typing import Dict, Any, Optional, List
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse
from .mcp_manager import ServerMCPManager
from config.logger import setup_logging


class ServerMCPExecutor(ToolExecutor):
    """服务端MCP工具执行器"""

    def __init__(self, conn, device_id: str = None, secret_id: str = None, secret_key: str = None):
        """初始化MCP执行器
        
        Args:
            conn: 连接对象
            device_id: 设备ID，用于标识设备相关的工具调用
            secret_id: SECRET ID，用于腾讯云API认证
            secret_key: SECRET Key，用于腾讯云API认证
        """
        self.conn = conn
        self.device_id = device_id
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.mcp_manager: Optional[ServerMCPManager] = None
        self._initialized = False
        self.logger = setup_logging()

    async def initialize(self):
        """初始化MCP管理器"""
        if not self._initialized:
            self.mcp_manager = ServerMCPManager(self.conn, self.device_id, self.secret_id, self.secret_key)
            await self.mcp_manager.initialize_servers()
            self._initialized = True

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端MCP工具"""
        if not self._initialized or not self.mcp_manager:
            return ActionResponse(
                action=Action.ERROR,
                response="MCP管理器未初始化",
            )

        try:
            # 移除mcp_前缀（如果有）
            actual_tool_name = tool_name
            if tool_name.startswith("mcp_"):
                actual_tool_name = tool_name[4:]

            result = await self.mcp_manager.execute_tool(actual_tool_name, arguments)

            return ActionResponse(action=Action.REQLLM, result=str(result))

        except ValueError as e:
            return ActionResponse(
                action=Action.NOTFOUND,
                response=str(e),
            )
        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有服务端MCP工具"""
        self.logger.info(f"ServerMCPExecutor.get_tools 被调用，初始化状态: {self._initialized}")
        
        if not self._initialized or not self.mcp_manager:
            self.logger.warning("MCP执行器未初始化或MCP管理器为空")
            return {}

        tools = {}
        mcp_tools = self.mcp_manager.get_all_tools()
        self.logger.info(f"从MCP管理器获取到 {len(mcp_tools)} 个工具")

        for tool in mcp_tools:
            func_def = tool.get("function", {})
            tool_name = func_def.get("name", "")
            if tool_name == "":
                continue
            tools[tool_name] = ToolDefinition(
                name=tool_name, description=tool, tool_type=ToolType.SERVER_MCP
            )
            self.logger.debug(f"注册MCP工具: {tool_name}")

        self.logger.info(f"ServerMCPExecutor返回 {len(tools)} 个工具: {list(tools.keys())}")
        return tools

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的服务端MCP工具"""
        if not self._initialized or not self.mcp_manager:
            return False

        # 移除mcp_前缀（如果有）
        actual_tool_name = tool_name
        if tool_name.startswith("mcp_"):
            actual_tool_name = tool_name[4:]

        return self.mcp_manager.is_mcp_tool(actual_tool_name)

    async def cleanup(self):
        """清理MCP连接"""
        if self.mcp_manager:
            await self.mcp_manager.cleanup_all()

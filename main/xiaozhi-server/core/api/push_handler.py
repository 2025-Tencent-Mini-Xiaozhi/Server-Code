"""
主动推送消息处理器
用于服务器主动向设备发送文字语音消息
"""
import json
import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.handle.receiveAudioHandle import startToChat
from core.utils.push_message_utils import send_direct_tts_message, send_notification_message, broadcast_message_to_all_devices

TAG = __name__


class PushHandler:
    def __init__(self, config: dict, ws_server=None):
        """
        初始化推送处理器
        
        Args:
            config: 系统配置
            ws_server: WebSocket服务器实例，用于访问活动连接
        """
        self.config = config
        self.ws_server = ws_server
        self.logger = setup_logging()

    def set_websocket_server(self, ws_server):
        """设置WebSocket服务器引用"""
        self.ws_server = ws_server

    async def handle_options(self, request):
        """处理OPTIONS请求（CORS预检）"""
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
        return web.Response(headers=headers)

    async def handle_post(self, request):
        """
        处理POST请求 - 主动推送消息
        
        请求格式:
        {
            "device_id": "设备ID", (单个设备推送时必需)
            "message": "要发送的文字消息", (必需)
            "voice": "语音类型(可选)",
            "bypass_llm": true/false, (可选，默认false，是否绕过LLM直接TTS)
            "notification_type": "info/warning/error/success/system/urgent", (可选，通知类型)
            "broadcast": true/false, (可选，默认false，是否广播到所有设备)
            "exclude_devices": ["device1", "device2"] (可选，广播时要排除的设备列表)
        }
        """
        try:
            # 设置CORS头
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            }

            # 验证WebSocket服务器是否可用
            if not self.ws_server:
                self.logger.bind(tag=TAG).error("WebSocket服务器未初始化")
                return web.json_response(
                    {"success": False, "message": "WebSocket服务器未初始化"},
                    status=500,
                    headers=headers
                )

            # 解析请求数据
            try:
                data = await request.json()
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"解析请求数据失败: {e}")
                return web.json_response(
                    {"success": False, "message": "请求数据格式错误"},
                    status=400,
                    headers=headers
                )

            # 验证必需参数
            device_id = data.get("device_id")
            message = data.get("message")
            bypass_llm = data.get("bypass_llm", False)
            notification_type = data.get("notification_type", "info")
            is_broadcast = data.get("broadcast", False)
            exclude_devices = data.get("exclude_devices", [])

            if not message:
                self.logger.bind(tag=TAG).error("缺少必需参数: message")
                return web.json_response(
                    {"success": False, "message": "缺少必需参数: message"},
                    status=400,
                    headers=headers
                )

            # 如果不是广播模式，则需要device_id
            if not is_broadcast and not device_id:
                self.logger.bind(tag=TAG).error("单设备推送模式下缺少必需参数: device_id")
                return web.json_response(
                    {"success": False, "message": "单设备推送模式下缺少必需参数: device_id"},
                    status=400,
                    headers=headers
                )

            # 处理广播模式
            if is_broadcast:
                self.logger.bind(tag=TAG).info(f"开始广播消息到所有设备: {message}")
                try:
                    await broadcast_message_to_all_devices(
                        self.ws_server, 
                        message, 
                        notification_type, 
                        exclude_devices
                    )
                    return web.json_response(
                        {
                            "success": True, 
                            "message": "广播消息发送完成",
                            "broadcast_message": message,
                            "notification_type": notification_type,
                            "excluded_devices": exclude_devices
                        },
                        headers=headers
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"广播消息失败: {e}")
                    return web.json_response(
                        {"success": False, "message": f"广播消息失败: {str(e)}"},
                        status=500,
                        headers=headers
                    )

            # 单设备推送模式
            # 查找目标设备连接
            target_connection = self._find_connection_by_device_id(device_id)
            if not target_connection:
                self.logger.bind(tag=TAG).error(f"未找到设备连接: {device_id}")
                return web.json_response(
                    {"success": False, "message": f"设备 {device_id} 未连接"},
                    status=404,
                    headers=headers
                )

            # 检查连接状态
            if not target_connection.websocket or target_connection.websocket.close_code is not None:
                self.logger.bind(tag=TAG).error(f"设备连接已关闭: {device_id}")
                return web.json_response(
                    {"success": False, "message": f"设备 {device_id} 连接已关闭"},
                    status=410,
                    headers=headers
                )

            # 发送消息到设备
            await self._send_message_to_device(
                target_connection, 
                message, 
                data.get("voice"), 
                bypass_llm, 
                notification_type
            )

            self.logger.bind(tag=TAG).info(f"成功向设备 {device_id} 发送消息: {message}")
            return web.json_response(
                {
                    "success": True, 
                    "message": "消息发送成功",
                    "device_id": device_id,
                    "sent_message": message,
                    "bypass_llm": bypass_llm,
                    "notification_type": notification_type
                },
                headers=headers
            )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"推送消息处理异常: {e}")
            return web.json_response(
                {"success": False, "message": f"服务器内部错误: {str(e)}"},
                status=500,
                headers=headers
            )

    def _find_connection_by_device_id(self, device_id: str):
        """
        根据设备ID查找对应的连接
        
        Args:
            device_id: 设备ID
            
        Returns:
            ConnectionHandler: 找到的连接处理器，未找到返回None
        """
        if not self.ws_server or not hasattr(self.ws_server, 'active_connections'):
            self.logger.bind(tag=TAG).error("WebSocket服务器或活动连接集合不可用")
            return None

        for connection in self.ws_server.active_connections:
            if hasattr(connection, 'device_id') and connection.device_id == device_id:
                self.logger.bind(tag=TAG).debug(f"找到设备连接: {device_id}")
                return connection

        self.logger.bind(tag=TAG).debug(f"未找到设备连接: {device_id}")
        return None

    async def _send_message_to_device(self, connection, message: str, voice: str = None, bypass_llm: bool = False, notification_type: str = "info"):
        """
        向指定设备发送消息
        
        Args:
            connection: 设备连接处理器
            message: 要发送的文字消息
            voice: 语音类型（可选）
            bypass_llm: 是否绕过LLM直接TTS
            notification_type: 通知类型
        """
        try:
            # 检查连接是否正在说话，如果是则中断
            if connection.client_is_speaking:
                self.logger.bind(tag=TAG).info(f"设备正在说话，先中断当前输出")
                # 这里可以调用中断逻辑，类似handleAbortMessage
                connection.client_abort = True
                # 等待一小段时间让中断生效
                await asyncio.sleep(0.1)

            # 设置语音类型（如果指定）
            if voice and hasattr(connection, 'tts') and connection.tts:
                original_voice = getattr(connection.tts, 'voice', None)
                if hasattr(connection.tts, 'set_voice'):
                    connection.tts.set_voice(voice)
                    self.logger.bind(tag=TAG).info(f"临时设置语音类型为: {voice}")

            # 根据模式选择发送方式
            if bypass_llm:
                # 直接TTS模式
                if notification_type in ["info", "warning", "error", "success", "system", "urgent"]:
                    await send_notification_message(connection, message, notification_type)
                else:
                    await send_direct_tts_message(connection, message, bypass_llm=True)
                self.logger.bind(tag=TAG).info(f"使用直接TTS模式发送消息到设备: {connection.device_id}")
            else:
                # 通过LLM模式 - 调用现有的startToChat函数处理消息
                await startToChat(connection, message)
                self.logger.bind(tag=TAG).info(f"使用LLM模式发送消息到设备: {connection.device_id}")

            self.logger.bind(tag=TAG).info(f"消息已发送到设备: {connection.device_id}")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"发送消息到设备失败: {e}")
            raise

    async def handle_get(self, request):
        """处理GET请求 - 获取连接状态"""
        try:
            headers = {
                "Access-Control-Allow-Origin": "*",
            }

            if not self.ws_server:
                return web.json_response(
                    {"success": False, "message": "WebSocket服务器未初始化"},
                    headers=headers
                )

            # 获取所有活动连接信息
            connections_info = []
            for connection in self.ws_server.active_connections:
                if hasattr(connection, 'device_id') and connection.device_id:
                    connection_info = {
                        "device_id": connection.device_id,
                        "client_ip": getattr(connection, 'client_ip', 'unknown'),
                        "session_id": getattr(connection, 'session_id', 'unknown'),
                        "is_speaking": getattr(connection, 'client_is_speaking', False),
                        "connected": connection.websocket and connection.websocket.close_code is None
                    }
                    connections_info.append(connection_info)

            return web.json_response(
                {
                    "success": True,
                    "total_connections": len(connections_info),
                    "connections": connections_info
                },
                headers=headers
            )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取连接状态失败: {e}")
            return web.json_response(
                {"success": False, "message": f"获取连接状态失败: {str(e)}"},
                status=500,
                headers=headers
            )

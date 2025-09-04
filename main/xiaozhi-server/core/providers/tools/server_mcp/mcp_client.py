"""服务端MCP客户端"""

import os
import json
import shutil
import asyncio
import threading
import requests
import concurrent.futures
import time
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any
from datetime import timedelta
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from config.logger import setup_logging
from core.utils.util import sanitize_tool_name

# 引入告警队列管理器
from core.services.cluster_alert_queue import alert_queue_manager

# 引入腾讯云SDK
try:
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.tke.v20180525 import tke_client, models as models_2018
    TENCENT_SDK_AVAILABLE = True
except ImportError:
    TENCENT_SDK_AVAILABLE = False

TAG = __name__

load_dotenv()

class ServerMCPClient:
    """服务端MCP客户端，用于连接和管理MCP服务"""

    def __init__(self, config: Dict[str, Any], device_id: str = None, secret_id: str = None, secret_key: str = None):
        """初始化服务端MCP客户端

        Args:
            config: MCP服务配置字典
            device_id: 设备ID，用于标识设备相关的工具调用
            secret_id: SECRET ID，用于腾讯云API认证
            secret_key: SECRET Key，用于腾讯云API认证
        """
        self.logger = setup_logging()
        self.config = config
        self.device_id = device_id
        self.secret_id = secret_id
        self.secret_key = secret_key
        
        # 从.env文件读取智能体配置
        self.agent_model = os.getenv("AGENT_MODEL", "")
        self.agent_api_key = os.getenv("AGENT_API_KEY", "")

        self._worker_task: Optional[asyncio.Task] = None
        self._alert_polling_task: Optional[asyncio.Task] = None  # 告警轮询任务
        self._ready_evt = asyncio.Event()
        self._shutdown_evt = asyncio.Event()

        self.session: Optional[ClientSession] = None
        self.tools: List = []  # 原始工具对象
        self.tools_dict: Dict[str, Any] = {}
        self.name_mapping: Dict[str, str] = {}
        
        # 集群列表缓存
        self.cluster_list: Optional[List[Dict[str, Any]]] = None
        self.cluster_list_raw: Optional[str] = None  # 原始JSON响应
        
        # 简化的集群映射：只保存ID和地域（用于后续快速查询）
        self.cluster_map: Dict[str, str] = {}  # {cluster_id: region}
        
        print(f"[MCPClient初始化] config={config}, device_id={device_id}, secret_id={secret_id}, secret_key={secret_key}")
        print(f"[MCPClient初始化] agent_model={self.agent_model}, agent_api_key={'*' * len(self.agent_api_key) if self.agent_api_key else '未设置'}")
        
    async def _logging_callback(self, params: types.LoggingMessageNotificationParams) -> None:
        """处理服务端的日志消息通知"""
        # 根据日志级别使用不同的输出方式
        level = params.level.lower() if params.level else "info"
        logger_name = params.logger or "unknown"
        message = params.data or ""
        
        # 格式化通知消息
        formatted_message = f"[MCP通知] {logger_name} | {message}"
        
        # 根据级别选择对应的日志方法
        if level == "error":
            self.logger.bind(tag=TAG).error(formatted_message)
            # 同时打印到控制台以确保重要消息可见
            print(f"ERROR [{logger_name}]: {message}", flush=True)
        elif level == "warning" or level == "warn":
            self.logger.bind(tag=TAG).warning(formatted_message)
            print(f"WARNING [{logger_name}]: {message}", flush=True)
        elif level == "debug":
            self.logger.bind(tag=TAG).debug(formatted_message)
            print(f"DEBUG [{logger_name}]: {message}", flush=True)
        else:  # info 或其他级别
            self.logger.bind(tag=TAG).info(formatted_message)
            print(f"INFO [{logger_name}]: {message}", flush=True)

    async def _message_handler(self, message) -> None:
        """处理来自服务端的其他消息"""
        if isinstance(message, Exception):
            self.logger.bind(tag=TAG).error(f"MCP客户端收到错误消息: {message}")
            print(f"MCP客户端错误: {message}", flush=True)
            return
        
        # 处理服务端通知
        try:
            if hasattr(message, 'method'):  # 通知消息
                self.logger.bind(tag=TAG).info(f"收到MCP服务端通知: {message}")
                print(f"MCP服务端通知: {message}", flush=True)
            else:
                self.logger.bind(tag=TAG).info(f"MCP客户端收到其他消息: {type(message).__name__}")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理MCP消息时发生错误: {e}")
            print(f"处理MCP消息错误: {e}", flush=True)
            self.logger.bind(tag=TAG).debug(f"消息详情: {message}")
            print(f"MCP消息 [{type(message).__name__}]: {message}", flush=True)

    async def initialize(self):
        """初始化MCP客户端连接"""
        if self._worker_task:
            return

        print("正在初始化MCP客户端连接...", flush=True)
        self.logger.bind(tag=TAG).info("开始初始化MCP客户端")
        
        # 重新从.env文件读取智能体配置，确保获取最新值
        self.agent_model = os.getenv("AGENT_MODEL", "")
        self.agent_api_key = os.getenv("AGENT_API_KEY", "")
        
        print(f"[MCPClient初始化] 重新读取配置 - agent_model={self.agent_model}, agent_api_key={'*' * len(self.agent_api_key) if self.agent_api_key else '未设置'}")
        self.logger.bind(tag=TAG).info(f"初始化时读取智能体配置 - model: {self.agent_model}, api_key: {'*' * len(self.agent_api_key) if self.agent_api_key else '未设置'}")

        self._worker_task = asyncio.create_task(
            self._worker(), name="ServerMCPClientWorker"
        )
        await self._ready_evt.wait()

        self.logger.bind(tag=TAG).info(
            f"服务端MCP客户端已连接，可用工具: {[name for name in self.name_mapping.values()]}"
        )
        
        # 在初始化完成后打印所有参数信息
        print(f"[MCP客户端初始化完成] 参数信息：", flush=True)
        print(f"   - device_id: {self.device_id}", flush=True)
        print(f"   - secret_id: {self.secret_id}", flush=True)
        print(f"   - secret_key: {self.secret_key[:8] + '...' if self.secret_key else None}", flush=True)
        print(f"   - agent_model: {self.agent_model}", flush=True)
        print(f"   - agent_api_key: {'*' * len(self.agent_api_key) if self.agent_api_key else '未设置'}", flush=True)
        
        self.logger.bind(tag=TAG).info(f"MCP客户端参数 - device_id: {self.device_id}, secret_id: {self.secret_id}, secret_key: {self.secret_key[:8] + '...' if self.secret_key else None}, agent_model: {self.agent_model}, agent_api_key: {'*' * len(self.agent_api_key) if self.agent_api_key else '未设置'}")
        
        # 延迟启动告警轮询消费任务，避免与主连接初始化产生资源竞争
        asyncio.create_task(self._delayed_start_alert_polling(), name=f"DelayedAlertPollingStarter-{id(self)}")

    async def _execute_alert_analysis_async(self, cluster_id: str, raw_alert: dict) -> None:
        """异步执行告警分析任务"""
        try:
            print(f"开始异步执行告警分析，集群: {cluster_id}, 设备ID: {self.device_id}")
            
            # 第二阶段：进行智能分析
            print(f"开始自动智能分析告警...", flush=True)
            try:
                # 调用智能分析（但不自动发送通知，我们要自己控制通知流程）
                analysis_result = await self.analyze_alert_with_agent(
                    cluster_id=cluster_id,
                    alert_data=raw_alert,
                    send_notification=False  # 关闭自动通知，我们手动处理
                )
                
                # 第三阶段：处理分析结果
                if analysis_result and not analysis_result.startswith("ERROR") and not analysis_result.startswith("缺少"):
                    print(f"智能分析完成，准备发送分析结果...", flush=True)
                    
                    if self.device_id:
                        try:
                            # 提取并缓存关键参数供后续回滚使用
                            print(f"正在缓存告警上下文信息，集群: {cluster_id}, 设备: {self.device_id}", flush=True)
                            await self._cache_alert_context(cluster_id, raw_alert, analysis_result)
                            
                            # 验证缓存是否成功
                            cached_context = self.get_cached_alert_context()
                            if cached_context:
                                print(f"缓存验证成功: {cached_context}", flush=True)
                            else:
                                print(f"警告: 缓存验证失败，未找到缓存的上下文", flush=True)
                            
                            # 直接发送分析结果到设备，保持原有的直接通知方式
                            await self._send_direct_notification(
                                self.device_id,
                                analysis_result,
                                "alert_analysis_result"
                            )
                            print(f"告警分析结果已发送到设备，关键参数已缓存", flush=True)
                                
                        except Exception as notify_error:
                            print(f"发送分析结果失败: {notify_error}", flush=True)
                            self.logger.bind(tag=TAG).warning(f"发送分析结果失败: {notify_error}")
                    else:
                        print(f"无法发送分析结果：设备ID未设置", flush=True)
                else:
                    print(f"智能分析未成功: {analysis_result}", flush=True)
                    
                    # 分析失败时也要通知用户
                    if self.device_id:
                        try:
                            error_message = f"集群 {cluster_id} 告警分析失败: {analysis_result}"
                            await self._send_direct_notification(
                                self.device_id,
                                error_message,
                                "error"
                            )
                        except Exception as error_notify_error:
                            print(f"发送错误通知失败: {error_notify_error}", flush=True)
                    
            except Exception as analysis_error:
                print(f"自动智能分析失败: {analysis_error}", flush=True)
                self.logger.bind(tag=TAG).warning(f"自动智能分析失败: {analysis_error}")
                
                # 分析失败时也要通知用户
                if self.device_id:
                    try:
                        error_message = f"集群 {cluster_id} 告警分析执行失败: {str(analysis_error)}"
                        await self._send_direct_notification(
                            self.device_id,
                            error_message,
                            "error"
                        )
                    except Exception as error_notify_error:
                        print(f"发送错误通知失败: {error_notify_error}", flush=True)

        except Exception as e:
            error_message = f"异步告警分析执行失败: {str(e)}"
            print(f"异步告警分析错误: {error_message}")
            
            # 即使出错也尝试发送错误通知
            if self.device_id:
                try:
                    await self._send_direct_notification(
                        self.device_id,
                        error_message,
                        "error"
                    )
                except Exception as final_error:
                    print(f"发送最终错误通知失败: {final_error}", flush=True)

    def _run_async_alert_analysis_in_thread(self, cluster_id: str, raw_alert: dict) -> None:
        """在新线程中运行异步告警分析任务"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行异步告警分析任务
            loop.run_until_complete(
                self._execute_alert_analysis_async(cluster_id, raw_alert)
            )
        except Exception as e:
            print(f"线程中执行异步告警分析失败: {str(e)}")
        finally:
            # 清理事件循环
            try:
                loop.close()
            except:
                pass

    async def _handle_cluster_alert(self, cluster_id: str, raw_alert: dict):
        """处理集群告警（在MCP客户端中处理）
        
        Args:
            cluster_id: 集群ID
            raw_alert: 原始告警数据
        """
        try:
            # 简单打印集群ID和原始数据报文
            print(f"集群: {cluster_id}", flush=True)
            print(f"原始数据报文: {raw_alert}", flush=True)
            
            # 记录到日志
            self.logger.bind(tag=TAG).info(f"[MCP客户端] 处理集群告警 - 集群: {cluster_id}")
            
            # 立即发送"正在分析"通知
            if self.device_id:
                try:
                    # 提取告警基本信息用于通知
                    alert_info = ""
                    request_body = raw_alert.get("request_body", {})
                    if request_body:
                        alert_id = request_body.get("alertId", "未知")
                        policy_name = request_body.get("alarmPolicyInfo", {}).get("policyName", "未知策略")
                        alert_info = f"告警ID: {alert_id}, 策略: {policy_name}"
                    
                    immediate_message = f"您的集群收到一条新的告警\n"
                    
                    await self._send_direct_notification(
                        self.device_id,
                        immediate_message,
                        "info"
                    )
                    print(f"已发送立即通知到设备", flush=True)
                        
                except Exception as notify_error:
                    print(f"发送立即通知失败: {notify_error}", flush=True)
                    self.logger.bind(tag=TAG).warning(f"发送立即通知失败: {notify_error}")
            
            # 在后台线程中异步执行告警分析任务
            alert_analysis_thread = threading.Thread(
                target=self._run_async_alert_analysis_in_thread,
                args=(cluster_id, raw_alert),
                daemon=True,  # 设置为守护线程，主程序退出时自动结束
                name=f"AlertAnalysis-{cluster_id}-{id(self)}"
            )
            
            # 启动后台告警分析线程
            alert_analysis_thread.start()
            
            print(f"告警分析任务已启动，集群: {cluster_id}，设备ID: {self.device_id}，线程: {alert_analysis_thread.name}")
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"[MCP客户端] 处理集群告警时发生错误: {e}")
            print(f"ERROR: [MCP客户端] 处理告警失败: {e}", flush=True)

    async def _cache_alert_context(self, cluster_id: str, raw_alert: dict, analysis_result: str):
        """缓存告警上下文信息供后续回滚使用"""
        try:
            # 从原始告警数据中提取关键信息
            context_info = {
                "cluster_id": cluster_id,
                "timestamp": time.time(),
                "analysis_result": analysis_result
            }
            
            # 尝试从告警数据中提取应用名称
            request_body = raw_alert.get("request_body", {})
            if request_body:
                alert_id = request_body.get("alertId", "")
                policy_name = request_body.get("alarmPolicyInfo", {}).get("policyName", "")
                context_info["alert_id"] = alert_id
                context_info["policy_name"] = policy_name
            
            # 尝试从分析结果中提取应用名称（通过正则表达式）
            import re
            
            # 匹配分析结果中的应用名称（包含多种可能的格式）
            app_name_patterns = [
                r'应用名称[：:]\s*([a-zA-Z0-9\-_.]+)',
                r'应用\s*[：:]?\s*([a-zA-Z0-9\-_.]+)',
                r'([a-zA-Z0-9\-_.]+)\s*应用',
                r'服务名称[：:]\s*([a-zA-Z0-9\-_.]+)',
                r'服务\s*[：:]?\s*([a-zA-Z0-9\-_.]+)',
                r'([a-zA-Z0-9\-_.]+)\s*服务',
                r'name[：:]\s*([a-zA-Z0-9\-_.]+)',
                r'pod\s*([a-zA-Z0-9\-_.]+)',
                r'deployment\s*([a-zA-Z0-9\-_.]+)',
                r'容器\s*([a-zA-Z0-9\-_.]+)',
                r'问题应用[：:]\s*([a-zA-Z0-9\-_.]+)',
                r'故障应用[：:]\s*([a-zA-Z0-9\-_.]+)',
            ]
            
            extracted_app_name = None
            for pattern in app_name_patterns:
                match = re.search(pattern, analysis_result, re.IGNORECASE)
                if match:
                    extracted_app_name = match.group(1).strip()
                    if extracted_app_name and len(extracted_app_name) > 2:  # 过滤掉太短的匹配
                        break
            
            # 同时缓存为 app_name 和 name 两个键，以兼容不同的参数名
            if extracted_app_name:
                context_info["app_name"] = extracted_app_name
                context_info["name"] = extracted_app_name  # 添加name字段
                print(f"从分析结果中提取到应用名称: {extracted_app_name}")
            else:
                print("未能从分析结果中提取到应用名称，将使用默认值或手动输入")
            
            # 使用设备ID作为缓存键，保存最近的告警上下文
            cache_key = f"alert_context_{self.device_id}"
            
            # 这里使用简单的内存缓存，实际项目中可以使用Redis等
            if not hasattr(self, '_alert_context_cache'):
                self._alert_context_cache = {}
            
            self._alert_context_cache[cache_key] = context_info
            print(f"已缓存告警上下文信息: {context_info}")
            
        except Exception as e:
            print(f"缓存告警上下文失败: {e}")
            self.logger.bind(tag=TAG).warning(f"缓存告警上下文失败: {e}")

    def get_cached_alert_context(self) -> dict:
        """获取缓存的告警上下文信息"""
        try:
            cache_key = f"alert_context_{self.device_id}"
            if hasattr(self, '_alert_context_cache') and cache_key in self._alert_context_cache:
                context = self._alert_context_cache[cache_key]
                # 检查缓存是否过期（30分钟）
                if time.time() - context.get("timestamp", 0) < 1800:
                    return context
                else:
                    # 清理过期缓存
                    del self._alert_context_cache[cache_key]
                    return {}
            return {}
        except Exception as e:
            print(f"获取缓存的告警上下文失败: {e}")
            return {}

    async def process_alert_with_intelligence(self, cluster_id: str, alert_data: dict, send_notification: bool = True) -> str:
        """对告警进行智能处理（包括分析和可选的通知发送）
        
        这是一个用户可以主动调用的方法，用于对消费到的告警进行智能分析。
        该方法不依赖MCP服务，直接在客户端中执行。
        
        Args:
            cluster_id: 集群ID
            alert_data: 告警数据（完整的webhook数据）
            send_notification: 是否发送分析结果到设备，默认为True
            
        Returns:
            str: 分析结果
        """
        try:
            print(f"[智能分析] 开始智能处理集群 {cluster_id} 的告警...", flush=True)
            self.logger.bind(tag=TAG).info(f"开始智能告警处理 - 集群: {cluster_id}")
            
            # 调用智能分析
            analysis_result = await self.analyze_alert_with_agent(cluster_id, alert_data, send_notification)
            
            if analysis_result and not analysis_result.startswith("错误") and not analysis_result.startswith("缺少"):
                print(f"智能分析结果:", flush=True)
                print(f"{analysis_result}", flush=True)
                print(f"{'='*60}", flush=True)
                
                # 如果分析成功且需要发送通知
                if send_notification and self.device_id:
                    try:
                        # 构建通知消息
                        notification_msg = f"集群告警智能分析结果\n\n集群: {cluster_id}\n\n{analysis_result}"
                        
                        # 发送智能分析结果到设备（可以调用MCP工具或直接发送）
                        if self.is_connected() and "send_ai_request" in self.tools_dict:
                            # 使用AI请求工具发送（通过LLM进一步处理）
                            send_result = await self.call_tool(
                                "send_ai_request", 
                                {
                                    "device_id": self.device_id,
                                    "request": notification_msg,
                                    "notification_type": "alert"
                                }
                            )
                            print(f"设备通知: 智能分析结果已发送到设备: {send_result}", flush=True)
                        elif self.is_connected() and "send_device_notification" in self.tools_dict:
                            # 使用直接通知工具发送（绕过LLM）
                            send_result = await self.call_tool(
                                "send_device_notification", 
                                {
                                    "device_id": self.device_id,
                                    "message": notification_msg,
                                    "notification_type": "alert"
                                }
                            )
                            print(f"设备通知: 智能分析结果已发送到设备: {send_result}", flush=True)
                        else:
                            print(f"无法发送通知：MCP连接不可用或通知工具不存在", flush=True)
                            
                    except Exception as notify_error:
                        print(f"发送通知失败: {notify_error}", flush=True)
                        self.logger.bind(tag=TAG).warning(f"发送智能分析通知失败: {notify_error}")
                
            else:
                print(f"智能分析未成功: {analysis_result}", flush=True)
            
            return analysis_result
            
        except Exception as e:
            error_msg = f"智能告警处理失败: {str(e)}"
            print(f"错误: {error_msg}", flush=True)
            self.logger.bind(tag=TAG).error(f"智能告警处理失败 - 集群: {cluster_id}, 错误: {e}")
            return error_msg

    async def _send_direct_notification(self, device_id: str, message: str, notification_type: str = "info") -> str:
        """直接向指定设备发送通知消息，绕过LLM处理
        
        Args:
            device_id: 设备ID
            message: 通知消息
            notification_type: 通知类型
            
        Returns:
            str: 发送结果
        """
        try:
            url = "http://localhost:8003/xiaozhi/push/message"
            headers = {"Content-Type": "application/json"}
            data = {
                "device_id": device_id,
                "message": message,
                "auth_key": "3b039beb-90fa-4170-bed2-e0e146126877",
                "bypass_llm": True,  # 强制绕过LLM
                "notification_type": notification_type,
            }

            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = f"直接通知发送成功到设备 {device_id}: [{notification_type}] {message[:50]}..."
                print(f"设备通知: {result}", flush=True)
                self.logger.bind(tag=TAG).info(result)
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                result = f"直接通知发送失败: {error_msg}"
                print(f"错误: {result}", flush=True)
                self.logger.bind(tag=TAG).error(result)
                return result

        except requests.exceptions.Timeout:
            result = "直接通知发送超时"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result
        except requests.exceptions.ConnectionError:
            result = "直接通知发送连接失败"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result
        except Exception as e:
            result = f"直接通知发送异常: {str(e)}"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result

    async def _send_ai_request(self, device_id: str, request: str, notification_type: str = "info") -> str:
        """向AI发送需要智能处理的请求，通过LLM进行分析和回复
        
        Args:
            device_id: 设备ID
            request: 请求内容
            notification_type: 通知类型
            
        Returns:
            str: 发送结果
        """
        try:
            url = "http://localhost:8003/xiaozhi/push/message"
            headers = {"Content-Type": "application/json"}
            data = {
                "device_id": device_id,
                "message": request,
                "auth_key": "3b039beb-90fa-4170-bed2-e0e146126877",
                "bypass_llm": False,  # 强制使用LLM
                "notification_type": notification_type,
            }

            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                result = f"AI请求发送成功到设备 {device_id}: {request[:50]}..."
                print(f"{result}", flush=True)
                self.logger.bind(tag=TAG).info(result)
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                result = f"AI请求发送失败: {error_msg}"
                print(f"错误: {result}", flush=True)
                self.logger.bind(tag=TAG).error(result)
                return result

        except requests.exceptions.Timeout:
            result = "AI请求发送超时（LLM处理时间较长）"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result
        except requests.exceptions.ConnectionError:
            result = "AI请求发送连接失败"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result
        except Exception as e:
            result = f"AI请求发送异常: {str(e)}"
            print(f"错误: {result}", flush=True)
            self.logger.bind(tag=TAG).error(result)
            return result

    async def analyze_alert_with_agent(self, cluster_id: str, alert_data: dict, send_notification: bool = True) -> str:
        """使用智能体分析具体的告警数据
        
        Args:
            cluster_id: 集群ID
            alert_data: 告警数据（完整的webhook数据）
            send_notification: 是否发送通知到设备，默认为True
            
        Returns:
            str: 分析结果
        """
        try:
            print(f"开始使用智能体分析集群 {cluster_id} 的告警...", flush=True)
            self.logger.bind(tag=TAG).info(f"开始智能体告警分析 - 集群: {cluster_id}")
            
            # 检查必要的配置
            if not self.secret_id or not self.secret_key:
                error_msg = "缺少腾讯云API凭据，无法进行智能分析"
                print(f"错误: {error_msg}", flush=True)
                return error_msg
            
            if not self.agent_model or not self.agent_api_key:
                error_msg = "缺少智能体LLM配置，无法进行智能分析"
                print(f"错误: {error_msg}", flush=True)
                return error_msg
            
            # 导入告警分析智能体（动态导入避免循环依赖）
            try:
                from .cluster_alarm_analysis_agent import ClusterAlarmAnalysisAgent
            except ImportError:
                error_msg = "无法导入告警分析智能体模块"
                print(f"错误: {error_msg}", flush=True)
                return error_msg
            
            # 构建LLM配置
            llm_config = {
                "model": self.agent_model,
                "model_server": "dashscope",
                "api_key": self.agent_api_key,
                "generate_cfg": {
                    "top_p": 0.8,
                    "temperature": 0.7,
                },
            }
            
            # 获取集群所在的地域
            region = self.cluster_map.get(cluster_id, "ap-guangzhou")
            
            # 创建告警分析智能体
            agent = ClusterAlarmAnalysisAgent(
                llm_config=llm_config,
                secret_id=self.secret_id,
                secret_key=self.secret_key,
                region=region,
                device_id=self.device_id if send_notification else "",
            )
            
            # 调用智能体进行告警分析（传入具体的告警数据）
            result = await agent.analyze_specific_alert(cluster_id, alert_data)
            
            print(f"智能体告警分析完成", flush=True)
            self.logger.bind(tag=TAG).info(f"智能体告警分析完成 - 集群: {cluster_id}")
            
            return result
            
        except Exception as e:
            error_msg = f"智能体告警分析失败: {str(e)}"
            print(f"错误: {error_msg}", flush=True)
            self.logger.bind(tag=TAG).error(f"智能体告警分析失败 - 集群: {cluster_id}, 错误: {e}")
            return error_msg

    async def _delayed_start_alert_polling(self):
        """延迟启动告警轮询消费者，避免与主连接初始化产生资源竞争"""
        try:
            # 等待5秒，让主连接先稳定建立
            await asyncio.sleep(5.0)
            
            # 检查是否已经关闭
            if self._shutdown_evt.is_set():
                return
            
            # 启动告警轮询任务
            self._alert_polling_task = asyncio.create_task(
                self._alert_polling_worker(), name=f"AlertPollingWorker-{id(self)}"
            )
            
            self.logger.bind(tag=TAG).info("延迟启动告警轮询消费者成功")
            print("延迟启动告警轮询消费者成功", flush=True)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"延迟启动告警轮询失败: {e}")
            print(f"延迟启动告警轮询失败: {e}", flush=True)

    async def cleanup(self):
        """清理MCP客户端资源"""
        if not self._worker_task:
            return

        # 告警轮询已改为自动模式，无需手动取消注册
        self.logger.bind(tag=TAG).info("准备清理MCP客户端资源")
        print("准备清理MCP客户端资源", flush=True)

        # 告警轮询任务将在关闭时自动停止 - 临时注释掉，排查连接断开问题
        # self.logger.bind(tag=TAG).info("准备停止告警轮询")
        # print("准备停止告警轮询", flush=True)

        self._shutdown_evt.set()
        try:
            await asyncio.wait_for(self._worker_task, timeout=20)
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.bind(tag=TAG).error(f"服务端MCP客户端关闭错误: {e}")
        finally:
            self._worker_task = None
            
        # 停止告警轮询任务
        if self._alert_polling_task and not self._alert_polling_task.done():
            self._alert_polling_task.cancel()
            try:
                await self._alert_polling_task
            except asyncio.CancelledError:
                pass
            self._alert_polling_task = None
            self.logger.bind(tag=TAG).info("告警轮询任务已停止")
            print("告警轮询任务已停止", flush=True)

    async def _alert_polling_worker(self):
        """告警轮询消费工作协程
        
        每个MCP客户端都会轮询自己负责集群的告警队列，实现自动消费
        """
        self.logger.bind(tag=TAG).info("告警轮询消费者已启动")
        print(f"DEBUG: 启动告警轮询消费者，MCP客户端实例ID: {id(self)}", flush=True)
        
        try:
            while not self._shutdown_evt.is_set():
                try:
                    # 获取当前客户端负责的集群列表
                    cluster_ids = list(self.cluster_map.keys()) if self.cluster_map else []
                    
                    if cluster_ids:
                        # 轮询每个集群的队列
                        for cluster_id in cluster_ids:
                            alert = await alert_queue_manager.consume_alerts(cluster_id)
                            if alert:
                                # 消费到告警，立即处理
                                print(f"DEBUG: 客户端 {id(self)} 消费到集群 {cluster_id} 的告警", flush=True)
                                await self._handle_cluster_alert(cluster_id, alert)
                    else:
                        # 如果还没有集群列表，等待一段时间
                        await asyncio.sleep(3)
                        continue
                    
                    # 短暂休眠，避免过于频繁的轮询
                    await asyncio.sleep(1)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"告警轮询消费过程中发生错误: {e}")
                    await asyncio.sleep(3)  # 发生错误时等待更长时间
                    
        except asyncio.CancelledError:
            pass
        finally:
            self.logger.bind(tag=TAG).info("告警轮询消费者已停止")
            print(f"DEBUG: 停止告警轮询消费者，MCP客户端实例ID: {id(self)}", flush=True)

    def has_tool(self, name: str) -> bool:
        """检查是否包含指定工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否包含该工具
        """
        return name in self.tools_dict

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的定义

        Returns:
            List[Dict[str, Any]]: 工具定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for name, tool in self.tools_dict.items()
        ]

    async def call_tool(self, name: str, args: dict) -> Any:
        """调用指定工具

        Args:
            name: 工具名称
            args: 工具参数

        Returns:
            Any: 工具执行结果

        Raises:
            RuntimeError: 客户端未初始化时抛出
        """
        if not self.session:
            raise RuntimeError("服务端MCP客户端未初始化")

        real_name = self.name_mapping.get(name, name)
        
        # 通用参数自动注入功能
        # 检查工具是否需要我们拥有的参数，如果需要则自动注入
        if name in self.tools_dict:
            tool = self.tools_dict[name]
            tool_schema = tool.inputSchema
            
            # 检查工具参数schema中是否包含我们可以注入的参数
            if tool_schema and isinstance(tool_schema, dict) and "properties" in tool_schema:
                properties = tool_schema["properties"]
                self.logger.bind(tag=TAG).debug(f"工具 {name} 的参数schema: {properties.keys()}")
                
                # 自动注入device_id参数
                if "device_id" in properties and self.device_id:
                    if "device_id" in args:
                        # 如果传入了device_id参数，检查是否为占位符或错误值
                        original_device_id = args["device_id"]
                        if original_device_id in ["<your_device_id>", "your_device_id", "", None] or original_device_id != self.device_id:
                            args["device_id"] = self.device_id
                            self.logger.bind(tag=TAG).info(f"修正device_id参数: {original_device_id} -> {self.device_id}")
                            print(f"修正device_id参数: {original_device_id} -> {self.device_id}", flush=True)
                        else:
                            self.logger.bind(tag=TAG).debug(f"device_id参数值正确，无需修正: {self.device_id}")
                    else:
                        # 如果没有传入device_id参数，自动添加
                        args["device_id"] = self.device_id
                        self.logger.bind(tag=TAG).info(f"自动添加device_id参数: {self.device_id}")
                        print(f"自动添加device_id参数: {self.device_id}", flush=True)
                
                # 自动注入或替换secret_id参数
                if "secret_id" in properties and self.secret_id:
                    # 检查是否存在占位符值或空值，如果是则替换
                    if "secret_id" not in args or args["secret_id"] in ["your_secret_id", "<your_secret_id>", "", None]:
                        original_value = args.get("secret_id", "未设置")
                        args["secret_id"] = self.secret_id
                        self.logger.bind(tag=TAG).info(f"注入secret_id参数: {original_value} -> {self.secret_id}")
                        print(f"注入secret_id参数: {original_value} -> {self.secret_id}", flush=True)
                
                # 自动注入或替换secret_key参数
                if "secret_key" in properties and self.secret_key:
                    # 检查是否存在占位符值或空值，如果是则替换
                    if "secret_key" not in args or args["secret_key"] in ["your_secret_key", "<your_secret_key>", "", None]:
                        original_value = args.get("secret_key", "未设置")
                        args["secret_key"] = self.secret_key
                        self.logger.bind(tag=TAG).info(f"注入secret_key参数: {original_value} -> {self.secret_key[:8]}...")
                        print(f"注入secret_key参数: {original_value} -> {self.secret_key[:8]}...", flush=True)
                
                # 自动注入或替换region参数（如果没有提供有效值）
                if "region" in properties and "region" in args and args["region"] in ["your_region", "<your_region>", "", None]:
                    # 使用默认的广州区域
                    original_value = args["region"]
                    args["region"] = "ap-guangzhou"
                    self.logger.bind(tag=TAG).info(f"注入region参数: {original_value} -> ap-guangzhou")
                    print(f"注入region参数: {original_value} -> ap-guangzhou", flush=True)
                
                # 自动注入或替换agent_model参数
                if "agent_model" in properties and self.agent_model:
                    # 检查是否存在占位符值或空值，如果是则替换
                    if "agent_model" not in args or args["agent_model"] in ["your_agent_model", "<your_agent_model>", "", None]:
                        original_value = args.get("agent_model", "未设置")
                        args["agent_model"] = self.agent_model
                        self.logger.bind(tag=TAG).info(f"注入agent_model参数: {original_value} -> {self.agent_model}")
                        print(f"注入agent_model参数: {original_value} -> {self.agent_model}", flush=True)
                
                # 自动注入或替换agent_api_key参数
                if "agent_api_key" in properties and self.agent_api_key:
                    # 检查是否存在占位符值或空值，如果是则替换
                    if "agent_api_key" not in args or args["agent_api_key"] in ["your_agent_api_key", "<your_agent_api_key>", "", None]:
                        original_value = args.get("agent_api_key", "未设置")
                        args["agent_api_key"] = self.agent_api_key
                        self.logger.bind(tag=TAG).info(f"注入agent_api_key参数: {original_value} -> {self.agent_api_key[:8]}...")
                        print(f"注入agent_api_key参数: {original_value} -> {self.agent_api_key[:8]}...", flush=True)
        
        print(f"调用MCP工具: {name} -> {real_name}, 参数: {args}", flush=True)
        self.logger.bind(tag=TAG).info(f"调用MCP工具: {name} -> {real_name}, 参数: {args}")
        
        loop = self._worker_task.get_loop()
        coro = self.session.call_tool(real_name, args)

        try:
            # 对于智能体工具，需要更长的超时时间
            timeout_seconds = 300.0 if 'inspection' in name.lower() or 'agent' in name.lower() else 120.0
            
            if loop is asyncio.get_running_loop():
                # 为长时间运行的智能体工具设置300秒超时，其他工具120秒
                result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            else:
                fut: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(coro, loop)
                # 为长时间运行的智能体工具设置300秒超时，其他工具120秒
                result = await asyncio.wait_for(asyncio.wrap_future(fut), timeout=timeout_seconds)
            
            print(f"MCP工具 {name} 调用成功", flush=True)
            self.logger.bind(tag=TAG).info(f"MCP工具 {name} 调用成功")
            
            # 详细输出调用结果
            if result:
                if hasattr(result, 'content') and result.content:
                    # 如果结果有content属性，输出其内容
                    result_content = ""
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            result_content += content_item.text + "\n"
                        elif hasattr(content_item, 'type') and content_item.type == 'text':
                            result_content += str(content_item) + "\n"
                        else:
                            result_content += str(content_item) + "\n"
                    
                    print(f"MCP工具 {name} 返回结果:\n{result_content.strip()}", flush=True)
                    self.logger.bind(tag=TAG).info(f"MCP工具 {name} 返回结果: {result_content.strip()}")
                else:
                    # 如果没有content属性，直接输出结果对象
                    print(f"MCP工具 {name} 返回结果: {result}", flush=True)
                    self.logger.bind(tag=TAG).info(f"MCP工具 {name} 返回结果: {result}")
            else:
                print(f"MCP工具 {name} 返回结果为空", flush=True)
                self.logger.bind(tag=TAG).info(f"MCP工具 {name} 返回结果为空")
            
            self.logger.bind(tag=TAG).debug(f"MCP工具 {name} 详细返回结果: {result}")
            return result
        except asyncio.TimeoutError:
            timeout_seconds = 300.0 if 'inspection' in name.lower() or 'agent' in name.lower() else 120.0
            error_msg = f"MCP工具 {name} 执行超时（{timeout_seconds}秒）"
            print(error_msg, flush=True)
            self.logger.bind(tag=TAG).error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            print(f"MCP工具 {name} 调用失败: {e}", flush=True)
            self.logger.bind(tag=TAG).error(f"MCP工具 {name} 调用失败: {e}")
            raise

    def is_connected(self) -> bool:
        """检查MCP客户端是否连接正常

        Returns:
            bool: 如果客户端已连接并正常工作，返回True，否则返回False
        """
        # 检查工作任务是否存在
        if self._worker_task is None:
            return False

        # 检查工作任务是否已经完成或取消
        if self._worker_task.done():
            return False

        # 检查会话是否存在
        if self.session is None:
            return False

        # 所有检查都通过，连接正常
        return True

    async def _worker(self):
        """MCP客户端工作协程"""
        async with AsyncExitStack() as stack:
            try:
                # 建立 StdioClient
                if "command" in self.config:
                    cmd = (
                        shutil.which("npx")
                        if self.config["command"] == "npx"
                        else self.config["command"]
                    )
                    env = {**os.environ, **self.config.get("env", {})}
                    params = StdioServerParameters(
                        command=cmd,
                        args=self.config.get("args", []),
                        env=env,
                    )
                    stdio_r, stdio_w = await stack.enter_async_context(
                        stdio_client(params)
                    )
                    read_stream, write_stream = stdio_r, stdio_w

                # 建立SSEClient
                elif "url" in self.config:
                    if "API_ACCESS_TOKEN" in self.config:
                        headers = {
                            "Authorization": f"Bearer {self.config['API_ACCESS_TOKEN']}"
                        }
                    else:
                        headers = {}
                    sse_r, sse_w = await stack.enter_async_context(
                        sse_client(self.config["url"], headers=headers)
                    )
                    read_stream, write_stream = sse_r, sse_w

                else:
                    raise ValueError("MCP客户端配置必须包含'command'或'url'")

                self.session = await stack.enter_async_context(
                    ClientSession(
                        read_stream=read_stream,
                        write_stream=write_stream,
                        read_timeout_seconds=timedelta(seconds=300),  # 增加到300秒以支持智能体长时间运行
                        message_handler=self._message_handler,  # 添加消息处理器
                        logging_callback=self._logging_callback,  # 添加日志回调
                    )
                )
                self.logger.bind(tag=TAG).info("MCP客户端会话创建成功，开始初始化...")
                await self.session.initialize()
                self.logger.bind(tag=TAG).info("MCP客户端会话初始化完成")

                # 获取工具
                self.tools = (await self.session.list_tools()).tools
                self.logger.bind(tag=TAG).info(f"获取到 {len(self.tools)} 个工具")
                for t in self.tools:
                    sanitized = sanitize_tool_name(t.name)
                    self.tools_dict[sanitized] = t
                    self.name_mapping[sanitized] = t.name
                    self.logger.bind(tag=TAG).debug(f"注册工具: {t.name} -> {sanitized}")

                self._ready_evt.set()
                self.logger.bind(tag=TAG).info("MCP客户端准备就绪，开始等待关闭信号...")

                # 自动获取集群列表（如果提供了腾讯云凭据）
                await self._auto_fetch_cluster_list()

                # 挂起等待关闭
                await self._shutdown_evt.wait()
                self.logger.bind(tag=TAG).info("收到关闭信号，MCP客户端开始清理...")

            except Exception as e:
                self.logger.bind(tag=TAG).error(f"服务端MCP客户端工作协程错误: {e}")
                self._ready_evt.set()
                raise

    async def _auto_fetch_cluster_list(self):
        """自动获取集群列表（直接调用腾讯云API）"""
        if not self.secret_id or not self.secret_key:
            self.logger.bind(tag=TAG).info("未提供腾讯云凭据，跳过自动获取集群列表")
            return
        
        if not TENCENT_SDK_AVAILABLE:
            self.logger.bind(tag=TAG).warning("腾讯云SDK不可用，无法自动获取集群列表")
            print("腾讯云SDK不可用，请安装tencentcloud-sdk-python", flush=True)
            return
            
        try:
            self.logger.bind(tag=TAG).info("开始自动获取集群列表...")
            print("正在自动获取腾讯云TKE集群列表...", flush=True)
            
            # 直接调用腾讯云API获取集群列表
            # 这里我们尝试几个常见的地域
            regions_to_try = ["ap-guangzhou", "ap-shanghai", "ap-beijing", "ap-shenzhen"]
            all_clusters = []
            
            for region in regions_to_try:
                try:
                    clusters = await self._fetch_clusters_from_region(region)
                    if clusters:
                        # 为每个集群添加地域信息
                        for cluster in clusters:
                            cluster["Region"] = region
                        all_clusters.extend(clusters)
                        
                        self.logger.bind(tag=TAG).info(f"从地域 {region} 获取到 {len(clusters)} 个集群")
                        print(f"从地域 {region} 获取到 {len(clusters)} 个集群", flush=True)
                        
                except Exception as e:
                    self.logger.bind(tag=TAG).debug(f"获取地域 {region} 集群列表失败: {e}")
                    continue
            
            # 存储集群列表
            self.cluster_list = all_clusters
            self.cluster_list_raw = json.dumps({"Clusters": all_clusters}, ensure_ascii=False)
            
            # 构建简化的集群映射（只保存ID和地域）
            self.cluster_map = {}
            for cluster in all_clusters:
                cluster_id = cluster.get("ClusterId")
                region = cluster.get("Region")
                if cluster_id and region:
                    self.cluster_map[cluster_id] = region
            
            self.logger.bind(tag=TAG).info(f"构建集群映射完成: {self.cluster_map}")
            print(f"集群映射: {self.cluster_map}", flush=True)
            
            if all_clusters:
                self.logger.bind(tag=TAG).info(f"自动获取集群列表成功，共找到 {len(all_clusters)} 个集群")
                print(f"自动获取集群列表成功，共找到 {len(all_clusters)} 个集群", flush=True)
                
                # 打印集群概要信息
                for cluster in all_clusters:
                    cluster_id = cluster.get("ClusterId", "Unknown")
                    cluster_name = cluster.get("ClusterName", "Unknown")
                    cluster_status = cluster.get("ClusterStatus", "Unknown")
                    cluster_region = cluster.get("Region", "Unknown")
                    cluster_version = cluster.get("ClusterVersion", "Unknown")
                    cluster_type = cluster.get("ClusterType", "Unknown")
                    node_num = cluster.get("ClusterNodeNum", 0)
                    cluster_os = cluster.get("ClusterOs", "Unknown")
                    container_runtime = cluster.get("ContainerRuntime", "Unknown")
                    
                    print(f"  集群: {cluster_name} ({cluster_id})", flush=True)
                    print(f"     状态: {cluster_status} | 地域: {cluster_region} | 版本: {cluster_version}", flush=True)
                    print(f"     类型: {cluster_type} | 节点数: {node_num} | 系统: {cluster_os}", flush=True)
                    print(f"     容器运行时: {container_runtime}", flush=True)
                    
                    # 记录详细日志
                    self.logger.bind(tag=TAG).info(f"集群详情 - 名称: {cluster_name}, ID: {cluster_id}, 状态: {cluster_status}, 地域: {cluster_region}, 版本: {cluster_version}, 节点数: {node_num}")
                    
                    # 如果有网络配置信息，也显示一下
                    if "ClusterNetworkSettings" in cluster:
                        network = cluster["ClusterNetworkSettings"]
                        service_cidr = network.get("ServiceCIDR", "Unknown")
                        vpc_id = network.get("VpcId", "Unknown")
                        print(f"     网络: VPC({vpc_id}) | 服务CIDR: {service_cidr}", flush=True)
                
                # 告警轮询已在初始化时自动启动，无需注册处理器
                self.logger.bind(tag=TAG).info(f"集群列表已获取，告警轮询将自动监听 {len(self.cluster_map)} 个集群")
                print(f"集群列表已获取，告警轮询将自动监听 {len(self.cluster_map)} 个集群", flush=True)
                print(f"集群列表已获取，告警轮询将自动监听 {len(self.cluster_map)} 个集群", flush=True)
            else:
                self.logger.bind(tag=TAG).info("未找到任何TKE集群")
                print("信息: 未找到任何TKE集群", flush=True)
                
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"自动获取集群列表失败: {e}")
            print(f"错误: 自动获取集群列表失败: {e}", flush=True)

    async def _fetch_clusters_from_region(self, region: str) -> List[Dict[str, Any]]:
        """从指定地域获取集群列表
        
        Args:
            region: 地域代码
            
        Returns:
            List[Dict[str, Any]]: 集群列表
        """
        try:
            # 创建腾讯云凭据
            cred = credential.Credential(self.secret_id, self.secret_key)

            # 配置HTTP配置
            httpProfile = HttpProfile()
            httpProfile.endpoint = "tke.tencentcloudapi.com"

            # 创建客户端配置
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile

            # 创建TKE客户端
            client = tke_client.TkeClient(cred, region, clientProfile)

            # 创建请求
            req = models_2018.DescribeClustersRequest()
            params = {}
            req.from_json_string(json.dumps(params))

            # 执行请求
            resp = client.DescribeClusters(req)
            
            # 解析响应
            response_data = json.loads(resp.to_json_string())
            
            # 处理响应结构: Response.Clusters
            if "Response" in response_data and "Clusters" in response_data["Response"]:
                return response_data["Response"]["Clusters"]
            elif "Clusters" in response_data:
                return response_data["Clusters"]
            else:
                return []

        except TencentCloudSDKException as e:
            self.logger.bind(tag=TAG).debug(f"腾讯云API调用失败 - 地域 {region}: {str(e)}")
            return []
        except Exception as e:
            self.logger.bind(tag=TAG).debug(f"获取地域 {region} 集群列表时发生错误: {str(e)}")
            return []

    def get_cluster_list(self) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的集群列表
        
        Returns:
            Optional[List[Dict[str, Any]]]: 集群列表，如果未获取则返回None
        """
        return self.cluster_list
    
    def get_cluster_list_raw(self) -> Optional[str]:
        """获取原始的集群列表JSON响应
        
        Returns:
            Optional[str]: 原始JSON字符串，如果未获取则返回None
        """
        return self.cluster_list_raw
    
    def get_cluster_count(self) -> int:
        """获取集群数量
        
        Returns:
            int: 集群数量
        """
        return len(self.cluster_list) if self.cluster_list else 0
    
    def get_cluster_by_id(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """根据集群ID获取集群信息
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            Optional[Dict[str, Any]]: 集群信息，如果未找到则返回None
        """
        if not self.cluster_list:
            return None
            
        for cluster in self.cluster_list:
            if cluster.get("ClusterId") == cluster_id:
                return cluster
        return None
    
    def get_clusters_by_region(self, region: str) -> List[Dict[str, Any]]:
        """根据地域获取集群列表
        
        Args:
            region: 地域代码
            
        Returns:
            List[Dict[str, Any]]: 该地域的集群列表
        """
        if not self.cluster_list:
            return []
            
        return [cluster for cluster in self.cluster_list if cluster.get("Region") == region]

    async def refresh_cluster_list(self) -> bool:
        """手动刷新集群列表
        
        Returns:
            bool: 刷新是否成功
        """
        try:
            await self._auto_fetch_cluster_list()
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"手动刷新集群列表失败: {e}")
            return False

    def get_running_clusters(self) -> List[Dict[str, Any]]:
        """获取运行中的集群列表
        
        Returns:
            List[Dict[str, Any]]: 运行中的集群列表
        """
        if not self.cluster_list:
            return []
            
        return [cluster for cluster in self.cluster_list if cluster.get("ClusterStatus") == "Running"]

    def get_cluster_summary(self) -> Dict[str, Any]:
        """获取集群概要统计信息
        
        Returns:
            Dict[str, Any]: 包含各种统计信息的字典
        """
        if not self.cluster_list:
            return {
                "total_count": 0,
                "running_count": 0,
                "regions": [],
                "cluster_types": {},
                "k8s_versions": {},
                "total_nodes": 0
            }
        
        # 统计信息
        running_clusters = [c for c in self.cluster_list if c.get("ClusterStatus") == "Running"]
        regions = list(set(c.get("Region", "Unknown") for c in self.cluster_list))
        
        # 统计集群类型
        cluster_types = {}
        for cluster in self.cluster_list:
            cluster_type = cluster.get("ClusterType", "Unknown")
            cluster_types[cluster_type] = cluster_types.get(cluster_type, 0) + 1
        
        # 统计K8s版本
        k8s_versions = {}
        for cluster in self.cluster_list:
            version = cluster.get("ClusterVersion", "Unknown")
            k8s_versions[version] = k8s_versions.get(version, 0) + 1
        
        # 统计总节点数
        total_nodes = sum(cluster.get("ClusterNodeNum", 0) for cluster in self.cluster_list)
        
        return {
            "total_count": len(self.cluster_list),
            "running_count": len(running_clusters),
            "regions": sorted(regions),
            "cluster_types": cluster_types,
            "k8s_versions": k8s_versions,
            "total_nodes": total_nodes
        }

    def get_cluster_by_name(self, cluster_name: str) -> Optional[Dict[str, Any]]:
        """根据集群名称获取集群信息
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Optional[Dict[str, Any]]: 集群信息，如果未找到则返回None
        """
        if not self.cluster_list:
            return None
            
        for cluster in self.cluster_list:
            if cluster.get("ClusterName") == cluster_name:
                return cluster
        return None

    def search_clusters(self, keyword: str) -> List[Dict[str, Any]]:
        """根据关键词搜索集群（搜索名称和ID）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Dict[str, Any]]: 匹配的集群列表
        """
        if not self.cluster_list or not keyword:
            return []
        
        keyword_lower = keyword.lower()
        matched_clusters = []
        
        for cluster in self.cluster_list:
            cluster_name = cluster.get("ClusterName", "").lower()
            cluster_id = cluster.get("ClusterId", "").lower()
            
            if keyword_lower in cluster_name or keyword_lower in cluster_id:
                matched_clusters.append(cluster)
        
        return matched_clusters

    def print_cluster_summary(self):
        """打印集群概要信息到控制台"""
        if not self.cluster_list:
            print("暂无集群信息", flush=True)
            return
        
        summary = self.get_cluster_summary()
        
        print(f"\n集群概要统计:", flush=True)
        print(f"  总集群数: {summary['total_count']}", flush=True)
        print(f"  运行中: {summary['running_count']}", flush=True)
        print(f"  总节点数: {summary['total_nodes']}", flush=True)
        print(f"  覆盖地域: {', '.join(summary['regions'])}", flush=True)
        
        if summary['cluster_types']:
            print(f"  集群类型分布:", flush=True)
            for cluster_type, count in summary['cluster_types'].items():
                print(f"    - {cluster_type}: {count}个", flush=True)
        
        if summary['k8s_versions']:
            print(f"  K8s版本分布:", flush=True)
            for version, count in summary['k8s_versions'].items():
                print(f"    - {version}: {count}个", flush=True)

    # ==========================================
    # 简化集群映射访问方法
    # ==========================================

    def get_cluster_map(self) -> Dict[str, str]:
        """获取集群ID到地域的映射
        
        Returns:
            Dict[str, str]: {cluster_id: region} 映射字典
        """
        return self.cluster_map.copy() if self.cluster_map else {}

    def get_cluster_region(self, cluster_id: str) -> Optional[str]:
        """根据集群ID获取地域
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            Optional[str]: 地域代码，如果未找到则返回None
        """
        return self.cluster_map.get(cluster_id)

    def get_cluster_ids(self) -> List[str]:
        """获取所有集群ID列表
        
        Returns:
            List[str]: 集群ID列表
        """
        return list(self.cluster_map.keys()) if self.cluster_map else []

    def get_regions(self) -> List[str]:
        """获取所有地域列表（去重）
        
        Returns:
            List[str]: 地域列表
        """
        if not self.cluster_map:
            return []
        return list(set(self.cluster_map.values()))

    def get_clusters_in_region(self, region: str) -> List[str]:
        """获取指定地域的所有集群ID
        
        Args:
            region: 地域代码
            
        Returns:
            List[str]: 该地域的集群ID列表
        """
        if not self.cluster_map:
            return []
        return [cluster_id for cluster_id, cluster_region in self.cluster_map.items() if cluster_region == region]

    def has_cluster(self, cluster_id: str) -> bool:
        """检查是否存在指定的集群
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            bool: 集群是否存在
        """
        return cluster_id in self.cluster_map if self.cluster_map else False

    def print_cluster_map(self):
        """打印简化的集群映射信息"""
        if not self.cluster_map:
            print("暂无集群映射信息", flush=True)
            return
        
        print(f"\n集群映射 (共{len(self.cluster_map)}个):", flush=True)
        for cluster_id, region in self.cluster_map.items():
            print(f"  - {cluster_id} → {region}", flush=True)
        
        # 按地域分组显示
        regions = self.get_regions()
        if len(regions) > 1:
            print(f"\n按地域分组:", flush=True)
            for region in sorted(regions):
                cluster_ids = self.get_clusters_in_region(region)
                print(f"  {region}: {len(cluster_ids)}个集群 {cluster_ids}", flush=True)

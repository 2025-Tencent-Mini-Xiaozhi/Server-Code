"""告警推送接收处理器"""

import json
from datetime import datetime
from aiohttp import web
from config.logger import setup_logging
from core.api.base_handler import BaseHandler

# 引入告警队列管理器
from core.services.cluster_alert_queue import alert_queue_manager

TAG = __name__


class AlertHandler(BaseHandler):
    """告警推送接收处理器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = setup_logging()

    async def receive_alert(self, request):
        """
        接收告警推送的HTTP接口
        
        支持GET和POST方法，用于接收各种告警信息
        """
        try:
            # 记录请求基本信息
            method = request.method
            path = request.path_qs
            headers = dict(request.headers)
            remote_addr = request.remote
            
            # 获取查询参数
            query_params = dict(request.query)
            
            # 获取请求体内容
            content_type = request.headers.get('Content-Type', '').lower()
            request_body = None
            
            if method in ['POST', 'PUT', 'PATCH']:
                try:
                    if 'application/json' in content_type:
                        # JSON格式
                        request_body = await request.json()
                        
                    elif 'application/x-www-form-urlencoded' in content_type:
                        # 表单格式
                        form_data = await request.post()
                        request_body = dict(form_data)
                        
                    elif 'multipart/form-data' in content_type:
                        # 多部分表单格式
                        form_data = await request.post()
                        request_body = {}
                        for key, value in form_data.items():
                            if hasattr(value, 'filename'):  # 文件上传
                                request_body[key] = f"<文件: {value.filename}>"
                            else:
                                request_body[key] = value
                        
                    else:
                        # 其他格式，获取原始文本
                        text_body = await request.text()
                        request_body = text_body
                        
                except Exception as parse_error:
                    # 如果解析失败，获取原始字节
                    raw_body = await request.read()
                    request_body = f"<解析失败，原始字节长度: {len(raw_body)}>"
                    print(f"[告警推送] 请求体解析失败: {parse_error}", flush=True)
            
            # 记录完整的告警推送信息
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "path": path,
                "remote_addr": remote_addr,
                "headers": headers,
                "query_params": query_params,
                "content_type": content_type,
                "request_body": request_body
            }
            
            # 将告警加入生产者队列
            queue_result = False
            try:
                if request_body and isinstance(request_body, dict):
                    queue_result = alert_queue_manager.produce_alert(alert_data)
                    if queue_result:
                        print(f"[告警推送] ✅ 告警已加入队列 (来源: {remote_addr})", flush=True)
                        self.logger.bind(tag=TAG).info(f"告警已加入队列 - 来源: {remote_addr}")
                    else:
                        print(f"[告警推送] ⚠️  告警跳过队列处理 (非集群告警)", flush=True)
                        self.logger.bind(tag=TAG).info("告警跳过队列处理 - 非集群告警")
                else:
                    print(f"[告警推送] ℹ️  非JSON格式告警，跳过队列处理", flush=True)
                    self.logger.bind(tag=TAG).info("非JSON格式告警，跳过队列处理")
            except Exception as queue_error:
                print(f"[告警推送] ❌ 告警队列处理错误: {queue_error}", flush=True)
                self.logger.bind(tag=TAG).error(f"告警队列处理错误: {queue_error}")
            
            # 返回成功响应
            response_data = {
                "status": "success",
                "message": "告警推送已接收",
                "timestamp": datetime.now().isoformat(),
                "received_data": {
                    "method": method,
                    "content_type": content_type,
                    "has_query_params": bool(query_params),
                    "has_request_body": bool(request_body)
                },
                "queue_status": {
                    "added_to_queue": queue_result,
                    "queue_enabled": True
                }
            }
            
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理告警推送时发生错误: {e}")
            print(f"[告警推送] 错误: {e}", flush=True)
            
            error_response = {
                "status": "error",
                "message": f"处理告警推送时发生错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)

    async def get_alert_info(self, request):
        """
        获取告警接收接口信息
        """
        try:
            info = {
                "status": "active",
                "message": "告警推送接收接口正常运行",
                "timestamp": datetime.now().isoformat(),
                "endpoints": {
                    "alert_webhook": "/api/alert/webhook",
                    "alert_info": "/api/alert/info"
                },
                "supported_methods": ["GET", "POST", "PUT", "PATCH"],
                "supported_content_types": [
                    "application/json",
                    "application/x-www-form-urlencoded", 
                    "multipart/form-data",
                    "text/plain"
                ]
            }
            
            return web.json_response(info, status=200)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取告警接口信息时发生错误: {e}")
            
            error_response = {
                "status": "error",
                "message": f"获取告警接口信息时发生错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)

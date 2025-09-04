import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.api.image_handler import ImageHandler
from core.api.face_handler import FaceHandler
from core.api.push_handler import PushHandler
from core.api.alert_handler import AlertHandler
from core.api.file_cleanup_handler import FileCleanupHandler
import os

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.image_handler = ImageHandler(config)
        self.face_handler = FaceHandler(config)
        self.push_handler = PushHandler(config)
        self.alert_handler = AlertHandler(config)
        self.file_cleanup_handler = FileCleanupHandler(config)

    async def serve_static_file(self, request):
        """提供静态文件服务"""
        try:
            # 获取请求的文件路径
            file_path = request.match_info.get('file_path', '')
            
            # 安全检查：防止路径遍历攻击
            if '..' in file_path or file_path.startswith('/'):
                return web.Response(status=403, text="Forbidden")
            
            # 构建完整的文件路径
            full_path = os.path.join('test', file_path)
            
            # 检查文件是否存在
            if not os.path.exists(full_path) or not os.path.isfile(full_path):
                return web.Response(status=404, text="File not found")
            
            # 根据文件扩展名确定Content-Type
            if file_path.endswith('.html'):
                content_type = 'text/html; charset=utf-8'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            elif file_path.endswith('.css'):
                content_type = 'text/css'
            else:
                content_type = 'application/octet-stream'
            
            # 读取并返回文件内容
            with open(full_path, 'rb') as f:
                content = f.read()
            
            return web.Response(
                body=content,
                content_type=content_type,
                headers={'Access-Control-Allow-Origin': '*'}
            )
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"提供静态文件服务失败: {e}")
            return web.Response(status=500, text="Internal Server Error")

    def set_websocket_server(self, ws_server):
        """设置WebSocket服务器引用以支持推送功能"""
        self.push_handler.set_websocket_server(ws_server)
        self.logger.bind(tag=TAG).info("HTTP服务器已关联WebSocket服务器，推送功能已启用")

    def set_cleanup_service(self, cleanup_service):
        """设置文件清理服务引用"""
        self.file_cleanup_handler.set_cleanup_service(cleanup_service)
        self.logger.bind(tag=TAG).info("HTTP服务器已关联文件清理服务")

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def start(self):
        server_config = self.config["server"]
        read_config_from_api = self.config.get("read_config_from_api", False)
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application()
            
            # 添加中间件来处理TLS连接尝试
            @web.middleware
            async def ssl_redirect_middleware(request, handler):
                try:
                    return await handler(request)
                except Exception as e:
                    # 记录但不抛出错误，避免日志污染
                    if "Invalid method encountered" in str(e) or "BadStatusLine" in str(e):
                        self.logger.bind(tag=TAG).debug(f"TLS连接尝试被拒绝: {request.remote}")
                        return web.Response(status=400, text="HTTP服务器不支持HTTPS连接")
                    raise
            
            app.middlewares.append(ssl_redirect_middleware)

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                    # 添加图片上传路由
                    web.post("/upload", self.image_handler.handle_upload),
                    # 添加普通图片上传和人脸识别路由
                    web.post("/upload_image", self.image_handler.handle_upload_image),
                    # 添加人脸识别API路由
                    web.get("/face/images", self.face_handler.handle_get_images),
                    web.post("/face/check", self.face_handler.handle_check_face),
                    web.post("/face/register", self.face_handler.handle_register_face),
                    web.post("/face/recognize", self.face_handler.handle_recognize_face),
                    web.get("/face/user/{user_id}", self.face_handler.handle_get_user_face_info),
                    # 添加推送消息接口
                    web.get("/xiaozhi/push/message", self.push_handler.handle_get),
                    web.post("/xiaozhi/push/message", self.push_handler.handle_post),
                    web.options("/xiaozhi/push/message", self.push_handler.handle_options),
                    # 添加告警推送接收接口
                    web.get("/api/alert/webhook", self.alert_handler.receive_alert),
                    web.post("/api/alert/webhook", self.alert_handler.receive_alert),
                    web.put("/api/alert/webhook", self.alert_handler.receive_alert),
                    web.patch("/api/alert/webhook", self.alert_handler.receive_alert),
                    web.options("/api/alert/webhook", self.alert_handler.receive_alert),
                    web.get("/api/alert/info", self.alert_handler.get_alert_info),
                    # 添加文件清理管理接口
                    web.get("/api/cleanup/status", self.file_cleanup_handler.get_cleanup_status),
                    web.post("/api/cleanup/manual", self.file_cleanup_handler.manual_cleanup),
                    # 添加静态文件服务
                    web.get("/test/{file_path:.*}", self.serve_static_file),
                ]
            )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次

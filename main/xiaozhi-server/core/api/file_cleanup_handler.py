"""文件清理管理接口"""

import json
from datetime import datetime
from aiohttp import web
from config.logger import setup_logging
from core.api.base_handler import BaseHandler
from core.services.file_cleanup_service import FileCleanupService

TAG = __name__


class FileCleanupHandler(BaseHandler):
    """文件清理管理处理器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = setup_logging()
        self.cleanup_service = None

    def set_cleanup_service(self, cleanup_service: FileCleanupService):
        """设置文件清理服务引用"""
        self.cleanup_service = cleanup_service

    async def get_cleanup_status(self, request):
        """
        获取文件清理状态和统计信息
        """
        try:
            if not self.cleanup_service:
                return web.json_response({
                    "status": "error",
                    "message": "文件清理服务未初始化",
                    "timestamp": datetime.now().isoformat()
                }, status=500)

            # 获取清理统计信息
            stats = self.cleanup_service.get_cleanup_stats()
            
            response_data = {
                "status": "success",
                "message": "文件清理状态查询成功",
                "timestamp": datetime.now().isoformat(),
                "cleanup_stats": stats
            }
            
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取文件清理状态时发生错误: {e}")
            
            error_response = {
                "status": "error",
                "message": f"获取文件清理状态时发生错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)

    async def manual_cleanup(self, request):
        """
        手动触发一次文件清理
        """
        try:
            if not self.cleanup_service:
                return web.json_response({
                    "status": "error",
                    "message": "文件清理服务未初始化",
                    "timestamp": datetime.now().isoformat()
                }, status=500)

            # 获取清理前的统计信息
            stats_before = self.cleanup_service.get_cleanup_stats()
            camera_count_before = stats_before.get("camera_files", {}).get("count", 0)
            
            # 执行手动清理
            await self.cleanup_service.manual_cleanup()
            
            # 获取清理后的统计信息
            stats_after = self.cleanup_service.get_cleanup_stats()
            camera_count_after = stats_after.get("camera_files", {}).get("count", 0)
            
            deleted_count = camera_count_before - camera_count_after
            
            response_data = {
                "status": "success",
                "message": "手动清理执行完成",
                "timestamp": datetime.now().isoformat(),
                "cleanup_result": {
                    "deleted_files": deleted_count,
                    "remaining_camera_files": camera_count_after,
                    "stats_before": stats_before,
                    "stats_after": stats_after
                }
            }
            
            self.logger.bind(tag=TAG).info(f"手动清理完成 - 删除了 {deleted_count} 个文件")
            
            return web.json_response(response_data, status=200)
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"手动清理时发生错误: {e}")
            
            error_response = {
                "status": "error",
                "message": f"手动清理时发生错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)

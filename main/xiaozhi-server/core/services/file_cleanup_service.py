"""
文件清理服务

定期清理uploads目录下的临时文件，保留重要的用户数据
"""

import asyncio
import os
import glob
import time
from datetime import datetime
from config.logger import setup_logging

TAG = __name__


class FileCleanupService:
    """文件清理服务"""

    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.uploads_dir = os.path.join(os.getcwd(), "uploads")
        self.cleanup_interval = 300  # 5分钟 = 300秒
        self.is_running = False
        self.cleanup_task = None

    async def start(self):
        """启动文件清理服务"""
        if self.is_running:
            self.logger.bind(tag=TAG).warning("文件清理服务已经在运行中")
            return

        self.is_running = True
        self.logger.bind(tag=TAG).info(f"启动文件清理服务 - 清理间隔: {self.cleanup_interval}秒")
        print(f"[文件清理] 启动文件清理服务 - 每{self.cleanup_interval//60}分钟清理一次camera_开头的图片", flush=True)

        # 启动定期清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """停止文件清理服务"""
        if not self.is_running:
            return

        self.is_running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        self.logger.bind(tag=TAG).info("文件清理服务已停止")
        print("[文件清理] 文件清理服务已停止", flush=True)

    async def _cleanup_loop(self):
        """清理循环"""
        try:
            while self.is_running:
                await self._perform_cleanup()
                # 等待指定的时间间隔
                await asyncio.sleep(self.cleanup_interval)
        except asyncio.CancelledError:
            self.logger.bind(tag=TAG).info("文件清理循环被取消")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"文件清理循环发生错误: {e}")
            print(f"[文件清理] 错误: {e}", flush=True)

    async def _perform_cleanup(self):
        """执行文件清理"""
        try:
            # 确保uploads目录存在
            if not os.path.exists(self.uploads_dir):
                self.logger.bind(tag=TAG).warning(f"uploads目录不存在: {self.uploads_dir}")
                return

            # 查找所有camera_开头的图片文件
            camera_pattern = os.path.join(self.uploads_dir, "camera_*.jpg")
            camera_files = glob.glob(camera_pattern)

            # 同时检查其他可能的图片格式
            for ext in ['*.png', '*.jpeg', '*.bmp', '*.gif']:
                pattern = os.path.join(self.uploads_dir, f"camera_{ext}")
                camera_files.extend(glob.glob(pattern))

            if not camera_files:
                self.logger.bind(tag=TAG).debug("没有找到需要清理的camera_开头的文件")
                return

            # 删除找到的文件
            deleted_count = 0
            deleted_size = 0
            
            for file_path in camera_files:
                try:
                    # 获取文件大小（用于统计）
                    file_size = os.path.getsize(file_path)
                    
                    # 删除文件
                    os.remove(file_path)
                    deleted_count += 1
                    deleted_size += file_size
                    
                    self.logger.bind(tag=TAG).debug(f"已删除文件: {os.path.basename(file_path)}")
                    
                except OSError as e:
                    self.logger.bind(tag=TAG).error(f"删除文件失败 {file_path}: {e}")

            if deleted_count > 0:
                size_mb = deleted_size / (1024 * 1024)
                self.logger.bind(tag=TAG).info(
                    f"文件清理完成 - 删除了 {deleted_count} 个camera_开头的文件，释放空间: {size_mb:.2f} MB"
                )
                print(
                    f"[文件清理] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - "
                    f"删除了 {deleted_count} 个camera_开头的文件，释放空间: {size_mb:.2f} MB", 
                    flush=True
                )
            else:
                self.logger.bind(tag=TAG).debug("本次清理没有删除任何文件")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"执行文件清理时发生错误: {e}")
            print(f"[文件清理] 执行清理时发生错误: {e}", flush=True)

    async def manual_cleanup(self):
        """手动执行一次清理"""
        self.logger.bind(tag=TAG).info("执行手动文件清理")
        print("[文件清理] 执行手动清理...", flush=True)
        await self._perform_cleanup()

    def get_cleanup_stats(self):
        """获取清理统计信息"""
        try:
            if not os.path.exists(self.uploads_dir):
                return {
                    "uploads_dir_exists": False,
                    "error": "uploads目录不存在"
                }

            # 统计camera_开头的文件
            camera_pattern = os.path.join(self.uploads_dir, "camera_*")
            camera_files = glob.glob(camera_pattern)
            camera_count = len(camera_files)
            camera_size = sum(os.path.getsize(f) for f in camera_files if os.path.exists(f))

            # 统计face_开头的文件
            face_pattern = os.path.join(self.uploads_dir, "face_*")
            face_files = glob.glob(face_pattern)
            face_count = len(face_files)
            face_size = sum(os.path.getsize(f) for f in face_files if os.path.exists(f))

            # 统计所有文件
            all_files = glob.glob(os.path.join(self.uploads_dir, "*"))
            total_count = len(all_files)
            total_size = sum(os.path.getsize(f) for f in all_files if os.path.isfile(f))

            return {
                "uploads_dir_exists": True,
                "uploads_dir": self.uploads_dir,
                "camera_files": {
                    "count": camera_count,
                    "size_bytes": camera_size,
                    "size_mb": camera_size / (1024 * 1024)
                },
                "face_files": {
                    "count": face_count,
                    "size_bytes": face_size,
                    "size_mb": face_size / (1024 * 1024)
                },
                "total_files": {
                    "count": total_count,
                    "size_bytes": total_size,
                    "size_mb": total_size / (1024 * 1024)
                },
                "cleanup_interval_seconds": self.cleanup_interval,
                "is_running": self.is_running
            }

        except Exception as e:
            return {
                "error": f"获取统计信息失败: {e}"
            }

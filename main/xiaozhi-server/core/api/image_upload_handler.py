#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片上传和人脸验证模块
基于xiaozhi-camera-stream项目实现，适配当前MySQL数据库结构
"""

import os
import json
import time
import requests
from datetime import datetime
from aiohttp import web
import aiofiles
from PIL import Image
import numpy as np
import face_recognition
import cv2
import logging

logger = logging.getLogger(__name__)

class ImageUploadHandler:
    """图片上传和人脸验证处理器"""
    
    def __init__(self, face_db, upload_dir="uploads"):
        """
        初始化图片上传处理器
        
        Args:
            face_db: 人脸数据库实例
            upload_dir: 图片上传目录
        """
        self.face_db = face_db
        self.upload_dir = upload_dir
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        # 确保上传目录存在
        os.makedirs(upload_dir, exist_ok=True)
        
    def _allowed_file(self, filename):
        """检查文件扩展名是否允许"""
        return any(filename.lower().endswith(ext) for ext in self.allowed_extensions)
    
    def _generate_filename(self, original_filename, device_id=None):
        """生成唯一的文件名"""
        timestamp = int(time.time())
        
        if device_id:
            # 获取Device-Id后三段
            device_id_parts = device_id.split(':')
            if len(device_id_parts) >= 3:
                device_id_suffix = '_'.join(device_id_parts[-3:])
            else:
                device_id_suffix = device_id.replace(':', '_')
            filename = f"camera_{device_id_suffix}_{timestamp}.jpg"
        else:
            # 保留原始扩展名
            name, ext = os.path.splitext(original_filename)
            if not ext:
                ext = '.jpg'
            filename = f"upload_{timestamp}{ext}"
            
        return filename
    
    def _rgb565_to_rgb888(self, rgb565_data, width, height):
        """
        将RGB565格式数据转换为RGB888
        
        Args:
            rgb565_data: RGB565原始数据
            width: 图像宽度
            height: 图像高度
            
        Returns:
            numpy.ndarray: RGB888数组或None
        """
        try:
            # 检查数据长度
            expected_length = width * height * 2  # RGB565每像素2字节
            if len(rgb565_data) != expected_length:
                logger.warning(f"RGB565数据长度不匹配: 期望{expected_length}字节，实际{len(rgb565_data)}字节")
                # 尝试调整到最接近的大小
                if len(rgb565_data) < expected_length:
                    logger.error("RGB565数据长度不足")
                    return None
                # 截取到正确的长度
                rgb565_data = rgb565_data[:expected_length]
            
            # 转换为uint16数组
            rgb565_array = np.frombuffer(rgb565_data, dtype=np.uint16)
            
            # 如果字节序不对，尝试交换
            if rgb565_array.max() < 256:  # 可能是字节序问题
                rgb565_array = rgb565_array.byteswap()
            
            # 提取RGB分量
            r = ((rgb565_array & 0xF800) >> 11) << 3  # 5位红色
            g = ((rgb565_array & 0x07E0) >> 5) << 2   # 6位绿色  
            b = (rgb565_array & 0x001F) << 3          # 5位蓝色
            
            # 填充低位以获得完整的8位颜色
            r = r | (r >> 5)
            g = g | (g >> 6)
            b = b | (b >> 5)
            
            # 重塑为图像形状
            rgb_array = np.stack([r, g, b], axis=-1).astype(np.uint8)
            rgb_array = rgb_array.reshape(height, width, 3)
            
            return rgb_array
            
        except Exception as e:
            logging.error(f"验证人脸编码时出错: {e}")
            return None

def get_today_schedules(user_id):
    """获取今日日程"""
    try:
        # 导入配置加载器
        from config.config_loader import load_config
        config = load_config()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 获取manager-api配置
        manager_api_config = config.get("manager-api", {})
        if not manager_api_config.get("url") or not manager_api_config.get("secret"):
            logging.warning("manager-api配置缺失，无法获取日程数据")
            return []
        
        schedule_api_url = f"{manager_api_config['url']}/schedule/internal/user/{user_id}/date/{today}"
        
        headers = {
            'X-ServerSecret': manager_api_config['secret'],
            'Content-Type': 'application/json'
        }
        
        response = requests.get(schedule_api_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        schedule_data = response.json()
        logging.info(f"获取到的日程API响应：{schedule_data}")
        
        if isinstance(schedule_data, list):
            return schedule_data
        else:
            logging.warning(f"意外的日程API响应格式：{schedule_data}")
            return []
            
    except Exception as e:
        logging.error(f"获取今日日程时出错: {e}")
        return []
    
    async def handle_upload(self, request: web.Request) -> web.Response:
        """
        处理图片上传请求
        
        请求格式:
        - Method: POST
        - Path: /upload
        - Content-Type: multipart/form-data
        - Files: image
        - Form data: width, height, format (可选，用于RGB565格式)
        - Headers: Device-Id (可选)
        
        响应格式参考xiaozhi-camera-stream项目:
        成功时返回用户信息和识别结果
        失败时返回错误信息
        """
        logger.info("\n" + "="*50)
        logger.info("=== 接收图像数据 ===")
        logger.info("="*50)
        
        try:
            # 获取请求头中的设备ID
            device_id = request.headers.get('Device-Id', 'unknown')
            logger.info(f"设备ID: {device_id}")
            
            # 读取multipart表单数据
            reader = await request.multipart()
            
            image_data = None
            width = None
            height = None
            format_type = None
            filename = None
            
            # 解析表单字段
            async for field in reader:
                if field.name == 'image':
                    image_data = await field.read()
                    filename = field.filename or 'upload.jpg'
                elif field.name == 'width':
                    width = await field.text()
                elif field.name == 'height':
                    height = await field.text()
                elif field.name == 'format':
                    format_type = await field.text()
            
            if not image_data:
                logger.error("ERROR: No image data received")
                return web.json_response({
                    "status": -1,
                    "message": "没有接收到图像数据",
                    "action": "请检查图像数据是否正确发送",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }, status=400)
            
            logger.info(f"接收到图像数据: width={width}, height={height}, format={format_type}")
            logger.info(f"图像数据大小: {len(image_data)} 字节")
            
            # 生成保存文件名
            save_filename = self._generate_filename(filename, device_id)
            save_path = os.path.join(self.upload_dir, save_filename)
            
            # 处理不同格式的图像数据
            if width and height and format_type:
                # 处理原始格式数据（如RGB565）
                try:
                    width = int(width)
                    height = int(height)
                    format_type = int(format_type)
                    
                    if format_type == 0:  # RGB565格式
                        logger.info("处理RGB565格式数据")
                        rgb_array = self._rgb565_to_rgb888(image_data, width, height)
                        
                        if rgb_array is None:
                            logger.error("RGB565转换失败")
                            return web.json_response({
                                "status": -1,
                                "message": "图像格式转换失败",
                                "detail": "RGB565转换失败",
                                "action": "请检查图像数据格式",
                                "device_id": device_id,
                                "timestamp": datetime.now().isoformat()
                            }, status=400)
                        
                        # 创建PIL图像并保存
                        img = Image.fromarray(rgb_array, 'RGB')
                        img.save(save_path, 'JPEG', quality=85)
                        logger.info(f"RGB565图像已保存: {save_filename}")
                        
                    else:
                        logger.warning(f"不支持的原始格式: {format_type}")
                        return web.json_response({
                            "status": -1,
                            "message": "不支持的图像格式",
                            "detail": f"格式码: {format_type}",
                            "action": "请使用支持的图像格式",
                            "device_id": device_id,
                            "timestamp": datetime.now().isoformat()
                        }, status=400)
                        
                except ValueError as e:
                    logger.error(f"解析图像参数失败: {e}")
                    return web.json_response({
                        "status": -1,
                        "message": "图像参数错误",
                        "detail": str(e),
                        "action": "请检查width、height、format参数",
                        "device_id": device_id,
                        "timestamp": datetime.now().isoformat()
                    }, status=400)
                    
            else:
                # 处理普通图片文件
                if not self._allowed_file(filename):
                    logger.error(f"不支持的文件类型: {filename}")
                    return web.json_response({
                        "status": -1,
                        "message": "不支持的文件类型",
                        "detail": f"文件: {filename}",
                        "action": "请使用JPG、PNG等支持的图片格式",
                        "device_id": device_id,
                        "timestamp": datetime.now().isoformat()
                    }, status=400)
                
                # 直接保存图片文件
                async with aiofiles.open(save_path, 'wb') as f:
                    await f.write(image_data)
                logger.info(f"普通图片文件已保存: {save_filename}")
            
            # 自动进行人脸识别和信息查询
            logger.info(f"\n🔍 开始自动人脸识别...")
            
            # 步骤1: 人脸识别验证
            verify_result = await self._recognize_face_async(save_path)
            
            if not verify_result['success']:
                logger.error(f"❌ 人脸识别失败: {verify_result['message']}")
                
                error_response = {
                    "status": -1,
                    "message": "人脸识别失败",
                    "detail": verify_result['message'],
                    "action": "请确保图片中有清晰的人脸，或前往网页注册",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(self._format_response_log("错误报文", error_response))
                return web.json_response(error_response)
            
            # 检查是否找到匹配的用户
            if not verify_result.get('found', False):
                logger.error(f"❌ 未找到匹配的用户")
                logger.info(f"相似度: {verify_result.get('similarity', 0):.2f}")
                
                error_response = {
                    "status": -1,
                    "message": "未找到匹配的用户",
                    "detail": f"相似度: {verify_result.get('similarity', 0):.2f}",
                    "action": "请前往网页注册或联系管理员",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(self._format_response_log("错误报文", error_response))
                return web.json_response(error_response)
            
            # 获取识别到的用户信息
            user_id = verify_result['user_id']
            username = verify_result['username']
            real_name = verify_result['real_name']
            similarity = verify_result.get('similarity', 0)
            
            logger.info(f"✅ 识别成功，用户: {real_name} ({username})")
            logger.info(f"相似度: {similarity:.2f}")
            
            # 步骤2: 获取用户完整信息
            logger.info("📋 获取用户信息...")
            user_info = await self._get_user_info_async(user_id)
            
            if not user_info:
                logger.error(f"❌ 无法获取用户信息")
                error_response = {
                    "status": -1,
                    "message": "用户信息获取失败",
                    "action": "请联系管理员",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }
                return web.json_response(error_response)
            
            # 步骤3: 构建返回数据（适配我们的sys_user表结构）
            today_schedules = get_today_schedules(user_id)
            
            response_data = {
                "status": 1,
                "message": "身份验证成功",
                "timestamp": datetime.now().isoformat(),
                "device_id": device_id,
                "user_info": {
                    "name": user_info['real_name'],
                    "account": user_info['username'],
                    "password": user_info.get('secret_key', ''),  # 使用secret_key作为密码字段
                    "api_id": user_info.get('secret_id', ''),     # 使用secret_id作为API ID
                    "api_key": user_info.get('secret_key', ''),   # 使用secret_key作为API Key
                    "user_id": user_info['id']
                },
                "today_schedules": today_schedules,
                "recognition_info": {
                    "similarity": similarity,
                    "total_faces_detected": verify_result.get('total_faces_detected', 1),
                    "selected_largest_face": verify_result.get('selected_largest_face', False)
                }
            }
            
            logger.info(f"✅ 身份验证成功")
            logger.info(f"用户: {user_info['real_name']} ({user_info['username']})")
            logger.info(f"今日日程数量: {len(today_schedules)}")
            
            # 打印完整的返回报文
            logger.info(self._format_response_log("完整报文", response_data))
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"处理图像上传时出错: {str(e)}", exc_info=True)
            
            error_response = {
                "status": -1,
                "message": "服务器内部错误",
                "detail": f"Error: {str(e)}",
                "action": "请重试或联系管理员",
                "device_id": device_id if 'device_id' in locals() else 'unknown',
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)
    
    async def _recognize_face_async(self, image_path):
        """异步人脸识别（实际调用同步方法）"""
        try:
            # 调用现有的人脸识别方法
            result = self.face_db.recognize_face(image_path)
            return result
        except Exception as e:
            logger.error(f"人脸识别异常: {e}")
            return {"success": False, "message": f"人脸识别异常: {str(e)}"}
    
    async def _get_user_info_async(self, user_id):
        """异步获取用户信息（实际调用同步方法）"""
        try:
            # 调用现有的用户信息查询方法
            user_info = self.face_db.get_user_by_id(user_id)
            return user_info
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None
    
    def _format_response_log(self, title, response_data):
        """格式化响应日志"""
        import json
        formatted_json = json.dumps(response_data, ensure_ascii=False, indent=2)
        
        log_lines = [
            f"\n" + "="*60,
            f"📤 返回给设备的{title}:",
            f"="*60,
            formatted_json,
            f"="*60,
            f"📊 报文统计:",
            f"- 报文大小: {len(formatted_json)} 字符",
            f"- 状态: {'✅ 成功' if response_data.get('status') == 1 else '❌ 失败'}",
            f"="*60
        ]
        
        return '\n'.join(log_lines)

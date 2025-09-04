import os
import time
import logging
import requests
import numpy as np
from PIL import Image
from aiohttp import web
from datetime import datetime
from config.logger import setup_logging 
from core.api.face_database import get_face_database

TAG = __name__
logger = setup_logging()

# 添加调试开关，控制是否打印详细报文日志
DEBUG_PACKET_LOG = os.environ.get('DEBUG_PACKET_LOG', 'false').lower() == 'true'


class ImageHandler:
    def __init__(self, config: dict):
        self.config = config
        self.upload_dir = "uploads"
        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)
        # 获取人脸数据库实例
        self.face_db = get_face_database()
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}

    def rgb565_to_rgb888(self, rgb565_data, width, height):
        """将RGB565数据转换为RGB888格式"""
        expected_size = width * height * 2
        if len(rgb565_data) != expected_size:
            logger.warning(f"数据长度不匹配: 期望 {expected_size} 字节，实际 {len(rgb565_data)} 字节")
            return None

        logger.info(f"开始转换RGB565数据: {len(rgb565_data)} 字节 -> {width}x{height}")

        # 转换为numpy数组 (uint16)
        arr = np.frombuffer(rgb565_data, dtype=np.uint16)
        
        # 字节交换 - 使用NumPy 2.0兼容的方法
        # arr = arr.byteswap().newbyteorder('<')  # 旧方法
        arr = arr.byteswap().view(arr.dtype.newbyteorder('<'))  # NumPy 2.0兼容方法

        # 提取RGB分量，使用位移操作
        r = ((arr >> 11) & 0x1F) << 3  # 5位红色扩展到8位
        g = ((arr >> 5) & 0x3F) << 2   # 6位绿色扩展到8位
        b = (arr & 0x1F) << 3          # 5位蓝色扩展到8位

        # 组合RGB通道
        rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        rgb = rgb.reshape((height, width, 3))

        logger.info(f"转换完成: RGB数组形状 {rgb.shape}")

        return rgb

    def get_today_schedules(self, user_id):
        """获取用户今日日程"""
        try:
            # 获取今天的日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 构建API请求URL
            # 获取manager-api配置
            manager_api_config = self.config.get("manager-api", {})
            if not manager_api_config.get("url") or not manager_api_config.get("secret"):
                logger.warning("manager-api配置缺失，无法获取日程数据")
                return []
            
            api_url = f"{manager_api_config['url']}/schedule/internal/user/{user_id}/date/{today}"
            
            # 准备请求参数（内部API不需要额外参数）
            params = {}
            
            # 准备认证头
            headers = {
                'Authorization': f"Bearer {manager_api_config['secret']}",
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"📅 正在获取用户 {user_id} 的今日日程...")
            logger.debug(f"请求URL: {api_url}")
            logger.debug(f"请求参数: {params}")
            
            # 发送请求
            response = requests.get(api_url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    schedules_list = result.get('data', [])
                    
                    logger.info(f"✅ 成功获取到 {len(schedules_list)} 条今日日程")
                    
                    # 格式化日程数据
                    formatted_schedules = []
                    for schedule in schedules_list:
                        formatted_schedule = {
                            'id': schedule.get('id'),
                            'content': schedule.get('content'),
                            'schedule_date': schedule.get('scheduleDate'),
                            'status': schedule.get('status'),  # 0-未完成, 1-已完成
                            'status_text': '已完成' if schedule.get('status') == 1 else '未完成'
                        }
                        formatted_schedules.append(formatted_schedule)
                    
                    return formatted_schedules
                else:
                    logger.warning(f"API返回错误: {result.get('msg', '未知错误')}")
                    return []
            else:
                logger.error(f"日程API请求失败: HTTP {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("获取日程数据超时")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"获取日程数据网络错误: {e}")
            return []
        except Exception as e:
            logger.error(f"获取日程数据发生异常: {e}")
            return []

    async def handle_upload(self, request: web.Request) -> web.Response:
        """
        处理ESP32设备上传的图片
        
        请求格式:
        - Method: POST
        - Path: /upload
        - Headers: 
          - Device-Id: 设备MAC地址
          - Client-Id: 设备UUID
          - Content-Type: multipart/form-data
        - Form fields:
          - width: 图像宽度
          - height: 图像高度
          - format: 像素格式数值
          - image: 图片文件
        """
        try:
            # 获取设备信息
            device_id = request.headers.get('Device-Id')
            client_id = request.headers.get('Client-Id')
            
            logger.info(f"收到设备上传请求 - Device-ID: {device_id}, Client-ID: {client_id}")
            
            # 打印详细请求信息用于调试
            if DEBUG_PACKET_LOG:
                logger.debug(f"请求头信息: {dict(request.headers)}")
                logger.debug(f"请求URL: {request.url}")
                logger.debug(f"请求方法: {request.method}")
                logger.debug(f"Content-Type: {request.content_type}")
            
            # 检查是否为multipart/form-data请求
            if not request.content_type.startswith('multipart/form-data'):
                logger.error("请求Content-Type不是multipart/form-data")
                return web.json_response({
                    "code": 400,
                    "msg": "Content-Type必须是multipart/form-data"
                }, status=400)
            
            # 读取multipart数据
            reader = await request.multipart()
            
            # 初始化变量存储表单数据
            width = None
            height = None
            format_value = None
            image_data = None
            image_filename = None
            
            # 解析multipart数据
            while True:
                part = await reader.next()
                if part is None:
                    break
                    
                field_name = part.name
                
                if field_name == 'width':
                    width = (await part.read()).decode('utf-8')
                    if DEBUG_PACKET_LOG:
                        logger.debug(f"接收到width字段: {width}")
                elif field_name == 'height':
                    height = (await part.read()).decode('utf-8')
                    if DEBUG_PACKET_LOG:
                        logger.debug(f"接收到height字段: {height}")
                elif field_name == 'format':
                    format_value = (await part.read()).decode('utf-8')
                    if DEBUG_PACKET_LOG:
                        logger.debug(f"接收到format字段: {format_value}")
                elif field_name == 'image':
                    image_filename = part.filename
                    image_data = await part.read(decode=False)
                    if DEBUG_PACKET_LOG:
                        logger.debug(f"接收到image字段: {len(image_data)} 字节")
            
            # 验证必要字段
            if not all([width, height, format_value, image_data, image_filename]):
                logger.error("缺少必要字段")
                return web.json_response({
                    "code": 400,
                    "msg": "缺少必要字段: width, height, format, image"
                }, status=400)
            
            width = int(width)
            height = int(height)
            format_type = int(format_value)
            
            # 生成保存路径
            timestamp = int(time.time())
            # 获取Device-Id后三段作为文件名的一部分
            device_id_suffix = 'unknown'
            if device_id:
                device_id_parts = device_id.split(':')
                if len(device_id_parts) >= 3:
                    device_id_suffix = '_'.join(device_id_parts[-3:])
                else:
                    device_id_suffix = device_id.replace(':', '_')
            
            save_filename = f"camera_{device_id_suffix}_{timestamp}.jpg"
            save_path = os.path.join(self.upload_dir, save_filename)
            
            # 根据format类型处理图片数据
            if format_type == 1:  # JPEG格式
                logger.info("处理JPEG格式图片数据")
                with open(save_path, 'wb') as f:
                    f.write(image_data)
            elif format_type == 0:  # RGB565格式
                logger.info("处理RGB565格式数据")
                # 将RGB565数据转换为RGB888
                rgb_array = self.rgb565_to_rgb888(image_data, width, height)
                
                if rgb_array is None:
                    logger.error("RGB565转换失败")
                    return web.json_response({
                        "code": 500,
                        "msg": "RGB565转换失败"
                    }, status=500)
                
                # 创建PIL图像并保存为JPEG
                img = Image.fromarray(rgb_array, 'RGB')
                img.save(save_path, 'JPEG', quality=85)
                logger.info(f"RGB565图像已转换并保存: {save_path}")
            else:
                logger.warning(f"不支持的格式: {format_type}，按原始数据保存")
                with open(save_path, 'wb') as f:
                    f.write(image_data)
            
            file_size = os.path.getsize(save_path)
            logger.info(f"图片保存成功: {save_path}, 大小: {file_size} 字节")
            
            # 自动进行人脸识别和信息查询
            logger.info(f"\n🔍 开始自动人脸识别...")
            
            # 步骤1: 人脸识别验证
            verify_result = self.face_db.recognize_face(save_path)
            
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
            user_info = self.face_db.get_user_by_id(user_id)
            
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
            
            # 步骤3: 获取用户今日日程
            logger.info("📅 获取用户今日日程...")
            today_schedules = self.get_today_schedules(user_info['id'])
            
            # 步骤4: 构建返回数据（适配我们的sys_user表结构）
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
                "today_schedules": today_schedules,  # 返回实际的今日日程数据
                "recognition_info": {
                    "similarity": similarity,
                    "total_faces_detected": verify_result.get('total_faces_detected', 1),
                    "selected_largest_face": verify_result.get('selected_largest_face', False)
                }
            }
            
            logger.info(f"✅ 身份验证成功")
            logger.info(f"用户: {user_info['real_name']} ({user_info['username']})")
            
            # 打印完整的返回报文
            logger.info(self._format_response_log("完整报文", response_data))
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"处理图片上传时发生错误: {e}", exc_info=True)
            
            error_response = {
                "status": -1,
                "message": "服务器内部错误",
                "detail": f"Error: {str(e)}",
                "action": "请重试或联系管理员",
                "device_id": device_id if 'device_id' in locals() else 'unknown',
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(error_response, status=500)
    
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
    
    async def handle_upload_image(self, request: web.Request) -> web.Response:
        """
        处理普通图片上传和人脸识别
        
        请求格式:
        - Method: POST
        - Path: /upload_image
        - Content-Type: multipart/form-data
        - Files: image
        - Headers: Device-Id (可选)
        
        响应格式参考xiaozhi-camera-stream项目:
        成功时返回用户信息和识别结果
        失败时返回错误信息
        """
        logger.info("\n" + "="*50)
        logger.info("=== 接收普通图像上传 ===")
        logger.info("="*50)
        
        device_id = request.headers.get('Device-Id', 'unknown')
        logger.info(f"设备ID: {device_id}")
        
        try:
            # 读取multipart表单数据
            reader = await request.multipart()
            
            image_data = None
            filename = None
            
            # 解析表单字段
            async for field in reader:
                if field.name == 'image':
                    image_data = await field.read()
                    filename = field.filename or 'upload.jpg'
                    break
            
            if not image_data:
                logger.error("ERROR: No image data received")
                return web.json_response({
                    "status": -1,
                    "message": "没有接收到图像数据",
                    "action": "请检查图像数据是否正确发送",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }, status=400)
            
            logger.info(f"接收到图像文件: {filename}")
            logger.info(f"图像数据大小: {len(image_data)} 字节")
            
            # 检查文件类型
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
            
            # 生成保存文件名并保存
            save_filename = self._generate_filename(filename, device_id)
            save_path = os.path.join(self.upload_dir, save_filename)
            
            with open(save_path, 'wb') as f:
                f.write(image_data)
            logger.info(f"图片文件已保存: {save_filename}")
            
            # 自动进行人脸识别和信息查询
            logger.info(f"\n🔍 开始自动人脸识别...")
            
            # 步骤1: 人脸识别验证
            verify_result = self.face_db.recognize_face(save_path)
            
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
            user_info = self.face_db.get_user_by_id(user_id)
            
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
            
            # 步骤3: 获取用户今日日程
            logger.info("📅 获取用户今日日程...")
            today_schedules = self.get_today_schedules(user_info['id'])
            
            # 步骤4: 构建返回数据（适配我们的sys_user表结构）
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
                "today_schedules": today_schedules,  # 返回实际的今日日程数据
                "recognition_info": {
                    "similarity": similarity,
                    "total_faces_detected": verify_result.get('total_faces_detected', 1),
                    "selected_largest_face": verify_result.get('selected_largest_face', False)
                }
            }
            
            logger.info(f"✅ 身份验证成功")
            logger.info(f"用户: {user_info['real_name']} ({user_info['username']})")
            
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
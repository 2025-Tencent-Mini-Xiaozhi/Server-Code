import os
import time
import logging
import json
from aiohttp import web
from config.logger import setup_logging
from .face_database import get_face_database

TAG = __name__
logger = setup_logging()


class FaceHandler:
    def __init__(self, config: dict):
        self.config = config
        self.upload_dir = "uploads"
        self.face_db = get_face_database()
        
    async def handle_get_images(self, request: web.Request) -> web.Response:
        """
        获取上传的人脸图片列表
        
        请求格式:
        - Method: GET
        - Path: /face/images
        
        响应格式:
        {
            "code": 0,
            "msg": "success",
            "data": [
                {
                    "name": "图片文件名",
                    "size": 文件大小(字节),
                    "timestamp": 时间戳
                }
            ]
        }
        """
        try:
            logger.info("收到获取人脸图片列表请求")
            
            # 检查上传目录是否存在
            if not os.path.exists(self.upload_dir):
                logger.warning(f"上传目录不存在: {self.upload_dir}")
                return web.json_response({
                    "code": 0,
                    "msg": "success",
                    "data": []
                })
            
            # 获取上传目录中的所有文件
            files = []
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        "name": filename,
                        "size": stat.st_size,
                        "timestamp": int(stat.st_mtime)
                    })
            
            # 按时间戳倒序排列（最新的在前面）
            files.sort(key=lambda x: x["timestamp"], reverse=True)
            
            logger.info(f"成功获取到 {len(files)} 个图片文件")
            
            return web.json_response({
                "code": 0,
                "msg": "success",
                "data": files
            })
            
        except Exception as e:
            logger.error(f"获取人脸图片列表时发生错误: {e}", exc_info=True)
            return web.json_response({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": []
            }, status=500)
    
    async def handle_check_face(self, request: web.Request) -> web.Response:
        """
        检查人脸是否已存在（用于注册前验证）
        
        请求格式:
        - Method: POST
        - Path: /face/check
        - Body: {
            "image_name": "图片文件名"
        }
        
        响应格式:
        {
            "code": 0,
            "msg": "success",
            "data": {
                "success": true,
                "exists": false,
                "face_detected": true,
                "message": "检测到人脸，未发现重复注册",
                "total_faces_detected": 1
            }
        }
        """
        try:
            logger.info("收到人脸检查请求")
            
            # 解析请求数据
            data = await request.json()
            image_name = data.get('image_name')
            
            if not image_name:
                return web.json_response({
                    "code": 400,
                    "msg": "缺少图片文件名",
                    "data": None
                }, status=400)
            
            # 构建图片路径
            image_path = os.path.join(self.upload_dir, image_name)
            
            if not os.path.exists(image_path):
                return web.json_response({
                    "code": 404,
                    "msg": f"图片文件不存在: {image_name}",
                    "data": None
                }, status=404)
            
            # 调用人脸检查服务
            result = self.face_db.check_face_exists(image_path)
            
            logger.info(f"人脸检查结果: {result}")
            
            return web.json_response({
                "code": 0,
                "msg": "success",
                "data": result
            })
                
        except json.JSONDecodeError:
            logger.error("请求数据格式错误")
            return web.json_response({
                "code": 400,
                "msg": "请求数据格式错误",
                "data": None
            }, status=400)
        except Exception as e:
            logger.error(f"人脸检查时发生错误: {e}", exc_info=True)
            return web.json_response({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": None
            }, status=500)
    
    async def handle_register_face(self, request: web.Request) -> web.Response:
        """
        注册用户人脸
        
        请求格式:
        - Method: POST
        - Path: /face/register
        - Body: {
            "user_id": 用户ID,
            "real_name": "用户真实姓名",
            "image_name": "图片文件名"
        }
        
        响应格式:
        {
            "code": 0,
            "msg": "success",
            "data": {
                "success": true,
                "message": "注册成功消息",
                "user_id": 用户ID,
                "real_name": "用户姓名",
                "face_image_path": "人脸图片路径"
            }
        }
        """
        try:
            logger.info("收到人脸注册请求")
            
            # 解析请求数据
            data = await request.json()
            user_id = data.get('user_id')
            real_name = data.get('real_name')
            image_name = data.get('image_name')
            
            # 验证参数
            if not user_id:
                return web.json_response({
                    "code": 400,
                    "msg": "缺少用户ID",
                    "data": None
                }, status=400)
            
            if not real_name:
                return web.json_response({
                    "code": 400,
                    "msg": "缺少用户姓名",
                    "data": None
                }, status=400)
            
            if not image_name:
                return web.json_response({
                    "code": 400,
                    "msg": "缺少图片文件名",
                    "data": None
                }, status=400)
            
            # 构建图片路径
            image_path = os.path.join(self.upload_dir, image_name)
            
            if not os.path.exists(image_path):
                return web.json_response({
                    "code": 404,
                    "msg": f"图片文件不存在: {image_name}",
                    "data": None
                }, status=404)
            
            # 调用人脸注册服务
            result = self.face_db.register_face(image_path, user_id, real_name)
            
            if result["success"]:
                logger.info(f"人脸注册成功: 用户ID={user_id}, 姓名={real_name}")
                return web.json_response({
                    "code": 0,
                    "msg": "success",
                    "data": result
                })
            else:
                logger.warning(f"人脸注册失败: {result['message']}")
                return web.json_response({
                    "code": 400,
                    "msg": result["message"],
                    "data": result
                }, status=400)
                
        except json.JSONDecodeError:
            logger.error("请求数据格式错误")
            return web.json_response({
                "code": 400,
                "msg": "请求数据格式错误",
                "data": None
            }, status=400)
        except Exception as e:
            logger.error(f"人脸注册时发生错误: {e}", exc_info=True)
            return web.json_response({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": None
            }, status=500)
    
    async def handle_recognize_face(self, request: web.Request) -> web.Response:
        """
        识别人脸
        
        请求格式:
        - Method: POST
        - Path: /face/recognize
        - Body: {
            "image_name": "图片文件名"
        }
        
        响应格式:
        {
            "code": 0,
            "msg": "success",
            "data": {
                "success": true,
                "found": true,
                "user_id": 用户ID,
                "real_name": "用户姓名",
                "similarity": 0.95
            }
        }
        """
        try:
            logger.info("收到人脸识别请求")
            
            # 解析请求数据
            data = await request.json()
            image_name = data.get('image_name')
            
            if not image_name:
                return web.json_response({
                    "code": 400,
                    "msg": "缺少图片文件名",
                    "data": None
                }, status=400)
            
            # 构建图片路径
            image_path = os.path.join(self.upload_dir, image_name)
            
            if not os.path.exists(image_path):
                return web.json_response({
                    "code": 404,
                    "msg": f"图片文件不存在: {image_name}",
                    "data": None
                }, status=404)
            
            # 调用人脸识别服务
            result = self.face_db.recognize_face(image_path)
            
            logger.info(f"人脸识别结果: {result}")
            
            return web.json_response({
                "code": 0,
                "msg": "success",
                "data": result
            })
                
        except json.JSONDecodeError:
            logger.error("请求数据格式错误")
            return web.json_response({
                "code": 400,
                "msg": "请求数据格式错误",
                "data": None
            }, status=400)
        except Exception as e:
            logger.error(f"人脸识别时发生错误: {e}", exc_info=True)
            return web.json_response({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": None
            }, status=500)
    
    async def handle_get_user_face_info(self, request: web.Request) -> web.Response:
        """
        获取用户人脸信息
        
        请求格式:
        - Method: GET
        - Path: /face/user/{user_id}
        
        响应格式:
        {
            "code": 0,
            "msg": "success",
            "data": {
                "user_id": 用户ID,
                "username": "用户名",
                "real_name": "真实姓名",
                "face_enabled": true,
                "face_registered_at": "2023-01-01 12:00:00"
            }
        }
        """
        try:
            user_id = int(request.match_info['user_id'])
            logger.info(f"获取用户人脸信息: 用户ID={user_id}")
            
            result = self.face_db.get_user_face_info(user_id)
            
            if result:
                return web.json_response({
                    "code": 0,
                    "msg": "success",
                    "data": result
                })
            else:
                return web.json_response({
                    "code": 404,
                    "msg": "用户不存在或无人脸数据",
                    "data": None
                }, status=404)
                
        except ValueError:
            return web.json_response({
                "code": 400,
                "msg": "无效的用户ID",
                "data": None
            }, status=400)
        except Exception as e:
            logger.error(f"获取用户人脸信息时发生错误: {e}", exc_info=True)
            return web.json_response({
                "code": 500,
                "msg": f"服务器内部错误: {str(e)}",
                "data": None
            }, status=500)
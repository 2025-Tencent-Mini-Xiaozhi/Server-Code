#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于MySQL的人脸识别数据库模块
功能：人脸注册、人脸比对识别
集成到xiaozhi-server中
"""

import os
import json
import pymysql
import face_recognition
import cv2
import numpy as np
import hashlib
import secrets
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
from config.logger import setup_logging

logger = setup_logging()

class MySQLFaceDatabase:
    """基于MySQL的人脸识别数据库"""
    
    def __init__(self, host: str = "localhost", port: int = 3306, 
                 user: str = "root", password: str = "123456", 
                 database: str = "xiaozhi_esp32_server", tolerance: float = 0.5):
        """
        初始化人脸数据库

        Args:
            host: MySQL主机地址
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: 数据库名
            tolerance: 人脸匹配容忍度 (0-1，越小越严格)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.tolerance = tolerance
        self.upload_dir = "uploads"
        
        # 确保上传目录存在
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            logger.info(f"创建上传目录: {self.upload_dir}")
    
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def _load_and_detect_faces(self, image_path):
        """加载图片并检测人脸"""
        try:
            logger.info(f"正在加载图片: {image_path}")
            
            # 检查文件是否存在
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
                
            # 使用OpenCV加载图片
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"无法加载图片: {image_path}")
            
            logger.info(f"原始图片shape: {image.shape}, dtype: {image.dtype}")
            
            # 确保图片是8位格式
            if image.dtype != np.uint8:
                logger.info("转换图片到8位格式")
                image = image.astype(np.uint8)
            
            # 如果是灰度图，转换为3通道
            if len(image.shape) == 2:
                logger.info("转换灰度图为RGB")
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                # 如果是RGBA，转换为RGB
                logger.info("转换RGBA为RGB")
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            else:
                # 转换BGR为RGB格式 (face_recognition要求RGB格式)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            logger.info(f"处理后图片shape: {image.shape}, dtype: {image.dtype}")
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(image, model="hog")
            
            logger.info(f"检测到 {len(face_locations)} 张人脸")
            
            return image, face_locations
            
        except Exception as e:
            logger.error(f"加载和检测人脸时发生错误: {e}")
            raise
    
    def check_face_exists(self, image_path: str) -> Dict:
        """
        检查人脸是否已存在（用于注册前验证）
        
        Args:
            image_path: 要检查的图片路径
        
        Returns:
            检查结果字典
        """
        try:
            logger.info(f"检查人脸是否已存在: {image_path}")
            
            # 加载图片并检测人脸
            image, face_locations = self._load_and_detect_faces(image_path)
            
            if len(face_locations) == 0:
                return {
                    "success": False,
                    "exists": False,
                    "message": "图片中未检测到人脸",
                    "face_detected": False
                }
            
            # 选择最大的人脸
            selected_face_location = face_locations[0]
            if len(face_locations) > 1:
                max_area = 0
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    area = (bottom - top) * (right - left)
                    if area > max_area:
                        max_area = area
                        selected_face_location = face_locations[i]
                
                logger.info(f"检测到多张人脸({len(face_locations)}张)，选择最大的")
            
            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(image, [selected_face_location])
            
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "exists": False,
                    "message": "无法提取人脸特征",
                    "face_detected": True
                }
            
            face_encoding = face_encodings[0]
            
            # 检查数据库中是否已存在相似的人脸
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # 获取所有已注册的人脸数据
                    cursor.execute("""
                        SELECT id, username, real_name, face_encoding 
                        FROM sys_user 
                        WHERE face_encoding IS NOT NULL AND face_enabled = 1
                    """)
                    registered_faces = cursor.fetchall()
                    
                    if not registered_faces:
                        return {
                            "success": True,
                            "exists": False,
                            "message": "检测到人脸，未发现重复注册",
                            "face_detected": True,
                            "total_faces_detected": len(face_locations)
                        }
                    
                    # 准备已注册的人脸编码
                    known_encodings = []
                    person_data = []
                    
                    for face_data in registered_faces:
                        try:
                            encoding = np.array(json.loads(face_data['face_encoding']))
                            known_encodings.append(encoding)
                            person_data.append({
                                'user_id': face_data['id'],
                                'username': face_data['username'],
                                'real_name': face_data['real_name']
                            })
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"跳过无效的人脸编码数据: {e}")
                            continue
                    
                    if not known_encodings:
                        return {
                            "success": True,
                            "exists": False,
                            "message": "检测到人脸，未发现重复注册",
                            "face_detected": True,
                            "total_faces_detected": len(face_locations)
                        }
                    
                    # 计算人脸距离
                    face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                    min_distance = np.min(face_distances)
                    
                    # 检查是否在容忍度范围内
                    if min_distance <= self.tolerance:
                        best_match_index = np.argmin(face_distances)
                        matched_person = person_data[best_match_index]
                        similarity = 1 - min_distance
                        
                        logger.info(f"检测到重复人脸: {matched_person['real_name']}, 相似度: {similarity:.2f}")
                        
                        return {
                            "success": True,
                            "exists": True,
                            "message": f"该人脸已被用户 '{matched_person['real_name']}' 注册过",
                            "face_detected": True,
                            "total_faces_detected": len(face_locations),
                            "existing_user": {
                                "user_id": matched_person['user_id'],
                                "username": matched_person['username'],
                                "real_name": matched_person['real_name'],
                                "similarity": similarity
                            }
                        }
                    else:
                        logger.info(f"人脸检查通过，最小距离: {min_distance}")
                        return {
                            "success": True,
                            "exists": False,
                            "message": "检测到人脸，未发现重复注册",
                            "face_detected": True,
                            "total_faces_detected": len(face_locations)
                        }
                        
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"检查人脸是否存在时发生错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "exists": False,
                "message": f"检查过程出错: {str(e)}",
                "face_detected": False
            }
    
    def register_face(self, image_path: str, user_id: int, real_name: str) -> Dict:
        """
        注册用户人脸到数据库
        
        Args:
            image_path: 图片路径
            user_id: 用户ID
            real_name: 用户真实姓名
        
        Returns:
            注册结果字典
        """
        try:
            logger.info(f"开始注册人脸 - 用户ID: {user_id}, 姓名: {real_name}, 图片: {image_path}")
            
            # 验证参数
            if not os.path.exists(image_path):
                return {"success": False, "message": f"图片文件不存在: {image_path}"}
            
            # 加载图片并检测人脸
            image, face_locations = self._load_and_detect_faces(image_path)
            
            if len(face_locations) == 0:
                return {"success": False, "message": "图片中未检测到人脸"}
            
            # 如果检测到多张人脸，选择最大的
            selected_face_location = face_locations[0]
            detected_faces_count = len(face_locations)
            
            if detected_faces_count > 1:
                max_area = 0
                max_face_index = 0
                
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    area = (bottom - top) * (right - left)
                    if area > max_area:
                        max_area = area
                        max_face_index = i
                        selected_face_location = face_locations[i]
                
                logger.info(f"检测到多张人脸({detected_faces_count}张)，选择最大的")
            
            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(image, [selected_face_location])
            
            if len(face_encodings) == 0:
                return {"success": False, "message": "无法提取人脸特征"}
            
            face_encoding = face_encodings[0]
            
            # 检查数据库中是否已存在相似的人脸
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # 获取所有已注册的人脸数据
                    cursor.execute("""
                        SELECT id, username, real_name, face_encoding 
                        FROM sys_user 
                        WHERE face_encoding IS NOT NULL AND face_enabled = 1
                    """)
                    registered_faces = cursor.fetchall()
                    
                    # 如果数据库中有人脸，检查是否重复
                    if registered_faces:
                        known_encodings = []
                        person_data = []
                        
                        for face_data in registered_faces:
                            try:
                                encoding = np.array(json.loads(face_data['face_encoding']))
                                known_encodings.append(encoding)
                                person_data.append({
                                    'user_id': face_data['id'],
                                    'username': face_data['username'],
                                    'real_name': face_data['real_name']
                                })
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"跳过无效的人脸编码数据: {e}")
                                continue
                        
                        if known_encodings:
                            # 计算距离
                            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                            min_distance = np.min(face_distances)
                            
                            # 如果找到相似的人脸，提示用户
                            if min_distance <= self.tolerance:
                                best_match_index = np.argmin(face_distances)
                                best_person = person_data[best_match_index]
                                return {
                                    "success": False,
                                    "message": f"检测到相似人脸，可能与已注册用户 '{best_person['real_name']}' 重复 (相似度: {1-min_distance:.2f})"
                                }
                    
                    # 保存人脸图片
                    face_image_filename = f"face_{user_id}_{int(datetime.now().timestamp())}.jpg"
                    face_image_path = os.path.join(self.upload_dir, face_image_filename)
                    
                    # 复制图片到uploads目录
                    import shutil
                    shutil.copy2(image_path, face_image_path)
                    
                    # 更新用户表中的人脸信息
                    encoding_json = json.dumps(face_encoding.tolist())
                    current_time = datetime.now()
                    
                    cursor.execute("""
                        UPDATE sys_user 
                        SET face_encoding = %s, 
                            face_image_path = %s, 
                            face_registered_at = %s,
                            face_enabled = 1,
                            update_date = %s
                        WHERE id = %s
                    """, (encoding_json, face_image_path, current_time, current_time, user_id))
                    
                    if cursor.rowcount == 0:
                        return {"success": False, "message": "用户不存在"}
                    
                    conn.commit()
                    
                    logger.info(f"成功注册人脸 - 用户ID: {user_id}, 姓名: {real_name}")
                    
                    return {
                        "success": True,
                        "message": f"成功注册人脸: {real_name}",
                        "user_id": user_id,
                        "real_name": real_name,
                        "face_image_path": face_image_path,
                        "face_location": selected_face_location,
                        "total_faces_detected": detected_faces_count,
                        "selected_largest_face": detected_faces_count > 1
                    }
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"注册人脸过程出错: {str(e)}", exc_info=True)
            return {"success": False, "message": f"注册过程出错: {str(e)}"}
    
    def recognize_face(self, image_path: str, return_all_matches: bool = False) -> Dict:
        """
        识别人脸
        
        Args:
            image_path: 要识别的图片路径
            return_all_matches: 是否返回所有匹配结果
        
        Returns:
            识别结果字典
        """
        try:
            logger.info(f"开始识别人脸: {image_path}")
            
            # 加载图片并检测人脸
            image, face_locations = self._load_and_detect_faces(image_path)
            
            if len(face_locations) == 0:
                return {
                    "success": True,
                    "message": "图片中未检测到人脸",
                    "found": False,
                    "user_id": None,
                    "real_name": None,
                    "similarity": 0.0
                }
            
            # 选择最大的人脸
            selected_face_location = face_locations[0]
            if len(face_locations) > 1:
                max_area = 0
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    area = (bottom - top) * (right - left)
                    if area > max_area:
                        max_area = area
                        selected_face_location = face_locations[i]
            
            # 提取人脸特征
            face_encodings = face_recognition.face_encodings(image, [selected_face_location])
            
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "message": "无法提取人脸特征",
                    "found": False,
                    "user_id": None,
                    "real_name": None,
                    "similarity": 0.0
                }
            
            unknown_face_encoding = face_encodings[0]
            
            # 从数据库获取已注册的人脸
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, username, real_name, face_encoding 
                        FROM sys_user 
                        WHERE face_encoding IS NOT NULL AND face_enabled = 1
                    """)
                    registered_faces = cursor.fetchall()
                    
                    if not registered_faces:
                        return {
                            "success": True,
                            "message": "识别完成",
                            "found": False,
                            "user_id": None,
                            "real_name": None,
                            "similarity": 0.0
                        }
                    
                    # 准备已注册的人脸编码
                    known_encodings = []
                    person_data = []
                    
                    for face_data in registered_faces:
                        try:
                            encoding = np.array(json.loads(face_data['face_encoding']))
                            known_encodings.append(encoding)
                            person_data.append({
                                'user_id': face_data['id'],
                                'username': face_data['username'],
                                'real_name': face_data['real_name']
                            })
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"跳过无效的人脸编码数据: {e}")
                            continue
                    
                    if not known_encodings:
                        return {
                            "success": True,
                            "message": "没有有效的已注册人脸数据",
                            "found": False,
                            "user_id": None,
                            "real_name": None,
                            "similarity": 0.0
                        }
                    
                    # 计算人脸距离
                    face_distances = face_recognition.face_distance(known_encodings, unknown_face_encoding)
                    best_match_index = np.argmin(face_distances)
                    min_distance = face_distances[best_match_index]
                    
                    # 检查是否在容忍度范围内
                    if min_distance <= self.tolerance:
                        matched_person = person_data[best_match_index]
                        similarity = 1 - min_distance
                        
                        logger.info(f"识别成功: {matched_person['real_name']}, 相似度: {similarity:.2f}")
                        
                        result = {
                            "success": True,
                            "message": f"识别成功: {matched_person['real_name']}",
                            "found": True,
                            "user_id": matched_person['user_id'],
                            "username": matched_person['username'],
                            "real_name": matched_person['real_name'],
                            "similarity": similarity
                        }
                        
                        if return_all_matches:
                            # 返回所有匹配结果
                            all_matches = []
                            for i, distance in enumerate(face_distances):
                                if distance <= self.tolerance:
                                    similarity = 1 - distance
                                    all_matches.append({
                                        "user_id": person_data[i]['user_id'],
                                        "username": person_data[i]['username'],
                                        "real_name": person_data[i]['real_name'],
                                        "similarity": similarity
                                    })
                            
                            # 按相似度排序
                            all_matches.sort(key=lambda x: x['similarity'], reverse=True)
                            result["all_matches"] = all_matches
                        
                        return result
                    else:
                        logger.info(f"未找到匹配的人脸，最小距离: {min_distance}")
                        return {
                            "success": True,
                            "message": "未找到匹配的人脸",
                            "found": False,
                            "user_id": None,
                            "real_name": None,
                            "similarity": 0.0
                        }
                        
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"识别人脸过程出错: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"识别过程出错: {str(e)}",
                "found": False,
                "user_id": None,
                "real_name": None,
                "similarity": 0.0
            }
    
    def get_user_face_info(self, user_id: int) -> Optional[Dict]:
        """
        获取用户的人脸信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户人脸信息或None
        """
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, username, real_name, face_image_path, 
                               face_registered_at, face_enabled
                        FROM sys_user 
                        WHERE id = %s
                    """, (user_id,))
                    
                    user = cursor.fetchone()
                    if not user:
                        return None
                    
                    return {
                        "user_id": user['id'],
                        "username": user['username'],
                        "real_name": user['real_name'],
                        "face_image_path": user['face_image_path'],
                        "face_registered_at": user['face_registered_at'],
                        "face_enabled": bool(user['face_enabled'])
                    }
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"获取用户人脸信息时发生错误: {e}")
            return None
    
    def delete_user_face(self, user_id: int) -> Dict:
        """
        删除用户的人脸数据
        
        Args:
            user_id: 用户ID
        
        Returns:
            删除结果字典
        """
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # 先获取人脸图片路径
                    cursor.execute("""
                        SELECT face_image_path FROM sys_user WHERE id = %s
                    """, (user_id,))
                    
                    user = cursor.fetchone()
                    if not user:
                        return {"success": False, "message": "用户不存在"}
                    
                    face_image_path = user['face_image_path']
                    
                    # 清除人脸数据
                    cursor.execute("""
                        UPDATE sys_user 
                        SET face_encoding = NULL, 
                            face_image_path = NULL, 
                            face_registered_at = NULL,
                            face_enabled = 0,
                            update_date = %s
                        WHERE id = %s
                    """, (datetime.now(), user_id))
                    
                    conn.commit()
                    
                    # 删除人脸图片文件
                    if face_image_path and os.path.exists(face_image_path):
                        try:
                            os.remove(face_image_path)
                            logger.info(f"已删除人脸图片文件: {face_image_path}")
                        except Exception as e:
                            logger.warning(f"删除人脸图片文件失败: {e}")
                    
                    logger.info(f"成功删除用户 {user_id} 的人脸数据")
                    
                    return {
                        "success": True,
                        "message": "成功删除人脸数据"
                    }
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"删除人脸数据时发生错误: {e}")
            return {"success": False, "message": f"删除失败: {str(e)}"}
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根据用户ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息字典或None
        """
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # 查询用户信息
                    sql = """
                        SELECT id, username, real_name, secret_id, secret_key, 
                               create_date, face_enabled, face_registered_at
                        FROM sys_user 
                        WHERE id = %s AND face_enabled = 1
                    """
                    cursor.execute(sql, (user_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            "id": result['id'],
                            "username": result['username'],
                            "real_name": result['real_name'],
                            "secret_id": result['secret_id'],
                            "secret_key": result['secret_key'],
                            "create_date": result['create_date'],
                            "face_enabled": result['face_enabled'],
                            "face_registered_at": result['face_registered_at']
                        }
                    return None
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"获取用户信息时发生错误: {e}")
            return None


# 全局实例
face_db = None

def get_face_database():
    """获取人脸数据库实例"""
    global face_db
    if face_db is None:
        face_db = MySQLFaceDatabase()
    return face_db

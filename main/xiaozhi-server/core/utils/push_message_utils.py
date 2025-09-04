"""
TTS推送工具
"""
import json
import asyncio
import uuid
from core.handle.sendAudioHandle import send_tts_message, sendAudioMessage
from core.providers.tts.dto.dto import SentenceType
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


async def send_direct_tts_message(conn, message: str, bypass_llm: bool = True):
    """
    直接发送TTS消息到设备，可选择是否绕过LLM
    
    Args:
        conn: 连接处理器
        message: 要转换为语音的文字消息
        bypass_llm: 是否绕过LLM直接进行TTS（默认True）
    """
    try:
        logger.bind(tag=TAG).info(f"开始发送直接TTS消息到设备 {conn.device_id}: {message}")
        
        # 检查TTS是否可用
        if not conn.tts:
            logger.bind(tag=TAG).error(f"设备 {conn.device_id} TTS未初始化")
            raise Exception("TTS服务未初始化")
        
        # 检查连接状态
        if not conn.websocket or conn.websocket.close_code is not None:
            logger.bind(tag=TAG).error(f"设备 {conn.device_id} 连接已关闭")
            raise Exception("设备连接已关闭")
        
        # 设置说话状态
        conn.client_is_speaking = True
        conn.client_abort = False
        
        # 标记为第一句话，以便预缓冲
        conn.tts.tts_audio_first_sentence = True
        
        if bypass_llm:
            # 直接TTS模式 - 绕过LLM处理
            logger.bind(tag=TAG).info(f"使用直接TTS模式发送消息: {message}")
            
            # 导入必要的TTS类型
            from core.providers.tts.dto.dto import ContentType, TTSMessageDTO
            
            try:
                # 发送TTS开始状态消息
                logger.bind(tag=TAG).info(f"发送TTS开始状态消息")
                await send_tts_message(conn, "start", None)
                
                # 发送TTS开始信号
                logger.bind(tag=TAG).info(f"发送TTS开始信号")
                conn.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=conn.sentence_id or str(uuid.uuid4()),
                        sentence_type=SentenceType.FIRST,
                        content_type=ContentType.TEXT,
                        content_detail=""
                    )
                )
                
                # 发送TTS文本内容
                logger.bind(tag=TAG).info(f"开始TTS处理文本: {message}")
                conn.tts.tts_one_sentence(
                    conn, 
                    ContentType.TEXT, 
                    content_detail=message
                )
                
                # 发送TTS结束信号
                logger.bind(tag=TAG).info(f"发送TTS结束信号")
                conn.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=conn.sentence_id or str(uuid.uuid4()),
                        sentence_type=SentenceType.LAST,
                        content_type=ContentType.TEXT,
                        content_detail=""
                    )
                )
                
                logger.bind(tag=TAG).info(f"直接TTS消息发送成功: {conn.device_id}")
            except Exception as tts_error:
                logger.bind(tag=TAG).error(f"直接TTS处理失败: {tts_error}")
                # 如果直接TTS失败，回退到LLM模式
                logger.bind(tag=TAG).info(f"回退到LLM模式处理消息: {message}")
                from core.handle.receiveAudioHandle import startToChat
                await startToChat(conn, message)
        else:
            # 通过LLM模式 - 使用完整的对话流程
            logger.bind(tag=TAG).info(f"使用LLM模式发送消息: {message}")
            from core.handle.receiveAudioHandle import startToChat
            await startToChat(conn, message)
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送TTS消息失败: {e}")
        # 确保重置状态
        if hasattr(conn, 'client_is_speaking'):
            conn.client_is_speaking = False
        # 发送TTS停止消息
        try:
            await send_tts_message(conn, "stop", None)
        except:
            pass
        raise


async def send_notification_message(conn, message: str, notification_type: str = "info"):
    """
    发送通知类消息
    
    Args:
        conn: 连接处理器
        message: 通知消息内容
        notification_type: 通知类型 (info, warning, error, success)
    """
    try:
        # 根据通知类型添加前缀
        prefix_map = {
            "info": "提醒：",
            "warning": "注意：", 
            "error": "错误：",
            "success": "成功：",
            "system": "系统：",
            "urgent": "紧急：",
        }
        
        prefix = prefix_map.get(notification_type, "")
        full_message = f"{prefix}{message}"
        
        logger.bind(tag=TAG).info(f"发送{notification_type}类型通知到设备 {conn.device_id}: {full_message}")
        
        # 使用直接TTS模式发送通知
        await send_direct_tts_message(conn, full_message, bypass_llm=True)
        
    except Exception as e:
        logger.bind(tag=TAG).error(f"发送通知消息失败: {e}")
        raise


async def broadcast_message_to_all_devices(ws_server, message: str, notification_type: str = "info", exclude_device_ids: list = None):
    """
    向所有连接的设备广播消息
    
    Args:
        ws_server: WebSocket服务器实例
        message: 要广播的消息
        notification_type: 消息类型
        exclude_device_ids: 要排除的设备ID列表
    """
    if not ws_server or not hasattr(ws_server, 'active_connections'):
        logger.bind(tag=TAG).error("WebSocket服务器不可用")
        return
    
    exclude_device_ids = exclude_device_ids or []
    success_count = 0
    total_count = 0
    
    logger.bind(tag=TAG).info(f"开始向所有设备广播消息: {message}")
    
    # 创建所有发送任务
    send_tasks = []
    for connection in ws_server.active_connections:
        if (hasattr(connection, 'device_id') and 
            connection.device_id and 
            connection.device_id not in exclude_device_ids and
            connection.websocket and 
            connection.websocket.close_code is None):
            
            total_count += 1
            task = asyncio.create_task(
                _send_message_with_error_handling(connection, message, notification_type)
            )
            send_tasks.append((connection.device_id, task))
    
    # 等待所有任务完成
    if send_tasks:
        logger.bind(tag=TAG).info(f"正在向 {total_count} 个设备发送广播消息...")
        
        for device_id, task in send_tasks:
            try:
                await task
                success_count += 1
                logger.bind(tag=TAG).debug(f"成功向设备 {device_id} 发送广播消息")
            except Exception as e:
                logger.bind(tag=TAG).error(f"向设备 {device_id} 发送广播消息失败: {e}")
    
    logger.bind(tag=TAG).info(f"广播消息完成: 成功 {success_count}/{total_count} 个设备")


async def _send_message_with_error_handling(connection, message: str, notification_type: str):
    """
    带错误处理的消息发送
    """
    try:
        await send_notification_message(connection, message, notification_type)
    except Exception as e:
        # 错误已在上层函数中记录，这里只是确保不影响其他设备的发送
        pass

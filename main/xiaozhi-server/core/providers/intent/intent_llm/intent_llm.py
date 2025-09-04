from typing import List, Dict
from ..base import IntentProviderBase
from plugins_func.functions.play_music import initialize_music_handler
from config.logger import setup_logging
import re
import json
import hashlib
import time

TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.promot = ""
        # 导入全局缓存管理器
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType
        self.history_count = 4  # 默认使用最近4条对话记录

    def get_intent_system_prompt(self, functions_list: str) -> str:
        """
        根据配置的意图选项和可用函数动态生成系统提示词
        Args:
            functions: 可用的函数列表，JSON格式字符串
        Returns:
            格式化后的系统提示词
        """

        # 构建函数说明部分
        functions_desc = "可用的函数列表：\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\n函数名: {name}\n"
            functions_desc += f"描述: {desc}\n"

            if params:
                functions_desc += "参数:\n"
                for param_name, param_info in params.get("properties", {}).items():
                    param_desc = param_info.get("description", "")
                    param_type = param_info.get("type", "")
                    functions_desc += f"- {param_name} ({param_type}): {param_desc}\n"

            functions_desc += "---\n"

        prompt = (
            "你是一个意图识别助手。请分析用户的最后一句话，判断用户意图并调用相应的函数。\n\n"
            "**重要：你必须严格按照JSON格式返回，不允许返回任何其他内容！**\n\n"
            "- 如果用户询问数学计算、算式、运算等，使用 calculate_expression 函数\n"
            "- 如果用户使用疑问词（如'怎么'、'为什么'、'如何'）询问退出相关的问题（例如'怎么退出了？'），注意这不是让你退出，请返回 {'function_call': {'name': 'continue_chat'}\n"
            "- 仅当用户明确使用'退出系统'、'结束对话'、'我不想和你说话了'等指令时，才触发 handle_exit_intent\n\n"
            f"{functions_desc}\n"
            "处理步骤:\n"
            "1. 分析用户输入，确定用户意图\n"
            "2. 从可用函数列表中选择最匹配的函数\n"
            "3. 如果找到匹配的函数，生成对应的function_call 格式\n"
            '4. 如果没有找到匹配的函数，返回{"function_call": {"name": "continue_chat"}}\n\n'
            "**计算相关的特殊处理：**\n"
            "- 用户说'计算'、'算一下'、'求解'等，使用 calculate_expression 函数\n"
            "- 表达式参数直接使用用户提到的数学表达式\n"
            "- 例如：用户说'计算1+2-4'，返回 {\"function_call\": {\"name\": \"calculate_expression\", \"arguments\": {\"expression\": \"1+2-4\"}}}\n\n"
            "返回格式要求：\n"
            "1. **必须返回纯JSON格式，不允许有任何其他文字**\n"
            "2. 必须包含function_call字段\n"
            "3. function_call必须包含name字段\n"
            "4. 如果函数需要参数，必须包含arguments字段\n\n"
            "示例：\n"
            "```\n"
            "用户: 请计算1+2-4的结果\n"
            '返回: {"function_call": {"name": "calculate_expression", "arguments": {"expression": "1+2-4"}}}\n'
            "```\n"
            "```\n"
            "用户: 现在几点了？\n"
            '返回: {"function_call": {"name": "get_time"}}\n'
            "```\n"
            "```\n"
            "用户: 当前电池电量是多少？\n"
            '返回: {"function_call": {"name": "get_battery_level", "arguments": {"response_success": "当前电池电量为{value}%", "response_failure": "无法获取Battery的当前电量百分比"}}}\n'
            "```\n"
            "```\n"
            "用户: 当前屏幕亮度是多少？\n"
            '返回: {"function_call": {"name": "self_screen_get_brightness"}}\n'
            "```\n"
            "```\n"
            "用户: 设置屏幕亮度为50%\n"
            '返回: {"function_call": {"name": "self_screen_set_brightness", "arguments": {"brightness": 50}}}\n'
            "```\n"
            "```\n"
            "用户: 我想结束对话\n"
            '返回: {"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "goodbye"}}}\n'
            "```\n"
            "```\n"
            "用户: 你好啊\n"
            '返回: {"function_call": {"name": "continue_chat"}}\n'
            "```\n\n"
            "**严格要求：**\n"
            "1. **只返回JSON格式，绝对不要包含任何解释、说明或其他文字**\n"
            '2. 如果没有找到匹配的函数，返回{"function_call": {"name": "continue_chat"}}\n'
            "3. 确保返回的JSON格式正确，包含所有必要的字段\n"
            "4. **不要计算结果，只返回函数调用的JSON**\n"
            "特殊说明：\n"
            "- 当用户单次输入包含多个指令时（如'打开灯并且调高音量'）\n"
            "- 请返回多个function_call组成的JSON数组\n"
            "- 示例：{'function_calls': [{name:'light_on'}, {name:'volume_up'}]}"
        )
        return prompt

    def replyResult(self, text: str, original_text: str):
        llm_result = self.llm.response_no_stream(
            system_prompt=text,
            user_prompt="请根据以上内容，像人类一样说话的口吻回复用户，要求简洁，请直接返回结果。用户现在说："
            + original_text,
        )
        return llm_result

    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # 记录整体开始时间
        total_start_time = time.time()

        # 打印使用的模型信息
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"使用意图识别模型: {model_info}")

        # 计算缓存键
        cache_key = hashlib.md5((conn.device_id + text).encode()).hexdigest()

        # 检查缓存
        cached_intent = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached_intent is not None:
            cache_time = time.time() - total_start_time
            logger.bind(tag=TAG).debug(
                f"使用缓存的意图: {cache_key} -> {cached_intent}, 耗时: {cache_time:.4f}秒"
            )
            return cached_intent

        # 检查工具处理器是否已经初始化完成，如果未完成则重新获取工具列表
        need_refresh_prompt = False
        if self.promot == "":
            need_refresh_prompt = True
            logger.bind(tag=TAG).info("首次生成意图识别提示词")
        elif hasattr(conn.func_handler, 'finish_init') and conn.func_handler.finish_init:
            # 如果工具处理器已经初始化完成，但当前提示词是在初始化前生成的，则需要刷新
            current_tools = conn.func_handler.get_functions()
            current_tool_count = len(current_tools) if current_tools else 0
            logger.bind(tag=TAG).info(f"工具处理器已初始化，当前工具数量: {current_tool_count}")
            if current_tool_count > 9:  # 如果工具数量大于9（包含了MCP工具），说明需要刷新
                need_refresh_prompt = True
                # logger.bind(tag=TAG).info("检测到MCP工具已加载，强制刷新意图识别提示词")
                # 强制清空旧的提示词
                self.promot = ""
        
        if need_refresh_prompt:
            functions = conn.func_handler.get_functions()
            if hasattr(conn, "mcp_client"):
                mcp_tools = conn.mcp_client.get_available_tools()
                if mcp_tools is not None and len(mcp_tools) > 0:
                    if functions is None:
                        functions = []
                    functions.extend(mcp_tools)

            # logger.bind(tag=TAG).info(f"重新生成意图识别提示词，工具数量: {len(functions) if functions else 0}")
            if functions:
                tool_names = [f.get('function', {}).get('name', 'unknown') for f in functions]
                # logger.bind(tag=TAG).info(f"可用工具列表: {tool_names}")
            self.promot = self.get_intent_system_prompt(functions)

        music_config = initialize_music_handler(conn)
        music_file_names = music_config["music_file_names"]
        prompt_music = f"{self.promot}\n<musicNames>{music_file_names}\n</musicNames>"

        home_assistant_cfg = conn.config["plugins"].get("home_assistant")
        if home_assistant_cfg:
            devices = home_assistant_cfg.get("devices", [])
        else:
            devices = []
        if len(devices) > 0:
            hass_prompt = "\n下面是我家智能设备列表（位置，设备名，entity_id），可以通过homeassistant控制\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # 构建用户对话历史的提示
        msgStr = ""

        # 获取最近的对话历史
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            msgStr += f"{dialogue_history[i].role}: {dialogue_history[i].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # 记录预处理完成时间
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(f"意图识别预处理耗时: {preprocess_time:.4f}秒")

        # 使用LLM进行意图识别
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(f"开始LLM意图识别调用, 模型: {model_info}")

        intent = self.llm.response_no_stream(
            system_prompt=prompt_music, user_prompt=user_prompt
        )

        # 记录LLM调用完成时间
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"LLM意图识别完成, 模型: {model_info}, 调用耗时: {llm_time:.4f}秒"
        )

        # 记录后处理开始时间
        postprocess_start_time = time.time()

        # 清理和解析响应
        intent = intent.strip()
        
        # 首先检查是否是tool_call XML标签格式
        tool_call_matches = re.findall(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', intent, re.DOTALL)
        if tool_call_matches:
            # 提取所有tool_call标签内的JSON内容
            tool_calls = []
            for match in tool_call_matches:
                try:
                    # 解析每个工具调用JSON
                    tool_data = json.loads(match.strip())
                    # 包装为function_call格式
                    wrapped_tool = {
                        "function_call": {
                            "name": tool_data.get("name"),
                            "arguments": tool_data.get("arguments", {})
                        }
                    }
                    tool_calls.append(wrapped_tool)
                except json.JSONDecodeError as e:
                    logger.bind(tag=TAG).warning(f"解析tool_call JSON失败: {match}, 错误: {e}")
                    continue
            
            if tool_calls:
                # 转换为JSON字符串
                if len(tool_calls) == 1:
                    intent = json.dumps(tool_calls[0])
                else:
                    intent = json.dumps(tool_calls)
        else:
            # 尝试提取JSON部分，支持数组格式和对象格式
            # 首先尝试提取标准数组格式 [{...}, {...}]
            array_match = re.search(r"\[.*\]", intent, re.DOTALL)
            if array_match:
                intent = array_match.group(0)
            else:
                # 检查是否是逗号分隔的多个对象格式 {...}, {...}
                multi_object_match = re.search(r"\{.*\}\s*,\s*\{.*\}", intent, re.DOTALL)
                if multi_object_match:
                    # 为逗号分隔的对象添加数组括号
                    intent = "[" + multi_object_match.group(0) + "]"
                else:
                    # 如果不是数组，尝试提取单个对象格式 {...}
                    object_match = re.search(r"\{.*\}", intent, re.DOTALL)
                    if object_match:
                        intent = object_match.group(0)

        # 记录总处理时间
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"【意图识别性能】模型: {model_info}, 总耗时: {total_time:.4f}秒, LLM调用: {llm_time:.4f}秒, 查询: '{text[:20]}...'"
        )

        # 尝试解析为JSON
        try:
            intent_data = json.loads(intent)
            
            # 处理多工具调用数组格式
            if isinstance(intent_data, list):
                # 检查是否是直接的工具调用格式（不包含function_call字段）
                if len(intent_data) > 0 and "name" in intent_data[0] and "function_call" not in intent_data[0]:
                    # 直接工具调用格式，转换为function_call格式
                    converted_data = []
                    for tool_call in intent_data:
                        if "name" in tool_call:
                            converted_tool = {
                                "function_call": {
                                    "name": tool_call.get("name"),
                                    "arguments": tool_call.get("arguments", {})
                                }
                            }
                            converted_data.append(converted_tool)
                    
                    if converted_data:
                        function_data = converted_data[0]["function_call"]
                        function_name = function_data.get("name")
                        function_args = function_data.get("arguments", {})

                        # 记录识别到的多工具调用
                        logger.bind(tag=TAG).info(
                            f"llm 识别到多工具调用，主要意图: {function_name}, 参数: {function_args}, 总计: {len(converted_data)} 个工具"
                        )

                        # 如果是继续聊天，清理工具调用相关的历史消息
                        if function_name == "continue_chat":
                            # 保留非工具相关的消息
                            clean_history = [
                                msg
                                for msg in conn.dialogue.dialogue
                                if msg.role not in ["tool", "function"]
                            ]
                            conn.dialogue.dialogue = clean_history

                        # 添加到缓存
                        self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                        # 后处理时间
                        postprocess_time = time.time() - postprocess_start_time
                        logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                        # 返回转换后的function_call格式
                        return json.dumps(converted_data)
                
                # 多工具调用情况：处理第一个工具调用作为主要意图（标准function_call格式）
                elif len(intent_data) > 0 and "function_call" in intent_data[0]:
                    function_data = intent_data[0]["function_call"]
                    function_name = function_data.get("name")
                    function_args = function_data.get("arguments", {})

                    # 记录识别到的多工具调用
                    logger.bind(tag=TAG).info(
                        f"llm 识别到多工具调用，主要意图: {function_name}, 参数: {function_args}, 总计: {len(intent_data)} 个工具"
                    )

                    # 如果是继续聊天，清理工具调用相关的历史消息
                    if function_name == "continue_chat":
                        # 保留非工具相关的消息
                        clean_history = [
                            msg
                            for msg in conn.dialogue.dialogue
                            if msg.role not in ["tool", "function"]
                        ]
                        conn.dialogue.dialogue = clean_history

                    # 添加到缓存
                    self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                    # 后处理时间
                    postprocess_time = time.time() - postprocess_start_time
                    logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                    # 返回完整的多工具调用JSON
                    return intent
                else:
                    # 数组格式但没有有效的function_call
                    logger.bind(tag=TAG).warning(f"数组格式但缺少有效function_call: {intent}")
                    return '{"intent": "继续聊天"}'
            
            # 处理单工具调用对象格式
            elif isinstance(intent_data, dict):
                # 检查是否是直接的工具调用格式（不包含function_call字段）
                if "name" in intent_data and "function_call" not in intent_data:
                    # 直接工具调用格式，转换为function_call格式
                    converted_tool = {
                        "function_call": {
                            "name": intent_data.get("name"),
                            "arguments": intent_data.get("arguments", {})
                        }
                    }
                    
                    function_name = intent_data.get("name")
                    function_args = intent_data.get("arguments", {})

                    # 记录识别到的function call
                    logger.bind(tag=TAG).info(
                        f"llm 识别到意图: {function_name}, 参数: {function_args}"
                    )

                    # 如果是继续聊天，清理工具调用相关的历史消息
                    if function_name == "continue_chat":
                        # 保留非工具相关的消息
                        clean_history = [
                            msg
                            for msg in conn.dialogue.dialogue
                            if msg.role not in ["tool", "function"]
                        ]
                        conn.dialogue.dialogue = clean_history

                    # 添加到缓存
                    self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                    # 后处理时间
                    postprocess_time = time.time() - postprocess_start_time
                    logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                    # 返回转换后的function_call格式
                    return json.dumps(converted_tool)
                    
                # 标准function_call格式
                elif "function_call" in intent_data:
                    function_data = intent_data["function_call"]
                    function_name = function_data.get("name")
                    function_args = function_data.get("arguments", {})

                    # 记录识别到的function call
                    logger.bind(tag=TAG).info(
                        f"llm 识别到意图: {function_name}, 参数: {function_args}"
                    )

                    # 如果是继续聊天，清理工具调用相关的历史消息
                    if function_name == "continue_chat":
                        # 保留非工具相关的消息
                        clean_history = [
                            msg
                            for msg in conn.dialogue.dialogue
                            if msg.role not in ["tool", "function"]
                        ]
                        conn.dialogue.dialogue = clean_history

                    # 添加到缓存
                    self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                    # 后处理时间
                    postprocess_time = time.time() - postprocess_start_time
                    logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                    # 确保返回完全序列化的JSON字符串
                    return intent
                else:
                    # 其他字典格式，当作普通意图处理
                    # 添加到缓存
                    self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)

                    # 后处理时间
                    postprocess_time = time.time() - postprocess_start_time
                    logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")

                    # 返回普通意图
                    return intent
        except json.JSONDecodeError:
            # 后处理时间
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).error(
                f"无法解析意图JSON: {intent}, 后处理耗时: {postprocess_time:.4f}秒"
            )
            # 如果解析失败，默认返回继续聊天意图
            return '{"intent": "继续聊天"}'

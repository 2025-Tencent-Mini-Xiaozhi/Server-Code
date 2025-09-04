#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障恢复智能体
"""

import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

# 导入 qwen-agent 相关模块
from qwen_agent.agents import ReActChat

# 从当前工作目录加载 .env 文件（如果存在）
load_dotenv()


class ClusterApplicationRollbackAgent:
    """腾讯云集群故障恢复智能体"""

    def __init__(
        self,
        llm_config: Dict[str, Any],
        secret_id: str,
        secret_key: str,
        region: str,
        cluster_id: str = "",
        name: str = "",
        device_id: str = "",
    ):
        """
        初始化智能体

        Args:
            llm_config: LLM配置字典，包含model、api_key等配置
            secret_id: 腾讯云API密钥ID
            secret_key: 腾讯云API密钥
            cluster_id: 集群ID
            name: 应用名称
            region: 地域代码，默认ap-guangzhou
            device_id: 设备ID，用于发送通知
        """
        self.llm_config = llm_config
        self.tencent_secret_id = secret_id
        self.tencent_secret_key = secret_key
        self.tencent_region = region
        self.device_id = device_id
        self.cluster_id = cluster_id
        self.name = name
        self.bot = None

        # 验证参数
        self._validate_config()

        # 初始化智能助手
        self.bot = self._init_agent()

    def _validate_config(self):
        """验证配置参数"""
        # 验证腾讯云凭据
        if not self.tencent_secret_id or not self.tencent_secret_key:
            raise ValueError("腾讯云API凭据缺失：secret_id和secret_key都是必需参数")

        if len(
                self.tencent_secret_id) != 36 or not self.tencent_secret_id.startswith(
                ("AKID", "AKI")):
            raise ValueError("secret_id格式不正确，应以AKID开头且长度为36位")

        if len(self.tencent_secret_key) != 32:
            raise ValueError("secret_key应为32位长度")

        # 验证LLM配置
        if not self.llm_config:
            raise ValueError("LLM配置缺失：llm_config是必需参数")

        api_key = self.llm_config.get("api_key", "")
        if not api_key:
            raise ValueError("LLM API key 缺失，请在llm_config中设置api_key")

        # 验证 API key 是否包含不能被 latin-1 编码的字符
        if any(ord(ch) > 255 for ch in api_key):
            raise ValueError("API key 包含非 Latin-1 字符，无法在 HTTP 头部发送")

        # 检测是否仍为示例/占位符值
        lower_key = api_key.lower()
        if (
            "your" in lower_key
            or "replace" in lower_key
            or "test" in lower_key
            or "please" in lower_key
        ):
            raise ValueError("API key 似乎是占位符或测试值，请设置真实的API key")

    def _init_agent(self) -> ReActChat:
        """
        初始化智能助手

        Returns:
            ReActChat: 配置好的智能助手实例
        """
        # 工具配置
        tools = self._get_tool_configs()

        # 系统提示词：定义助手的专业能力
        system_message = f"""
你是一个专门负责腾讯云集群故障恢复（回滚）的智能助手，具备以下核心能力：
用户的secret_id是{self.tencent_secret_id}，secret_key是{self.tencent_secret_key}，region是{self.tencent_region}，device_id是{self.device_id}，cluster_id是{self.cluster_id}，需要回滚的应用name是{self.name}。
通用工作原则​​
- 所有结论必须源于工具调用返回的数据。
- 在巡检中发现风险时，应主动提示用户并进行深入分析。
- ​​闭环跟踪：​​ 实施修复后，需主动进行后续验证，并向用户汇报结果。
功能工作流详解
​执行回滚：​​ 调用 tencent-cloud-describe_cluster_release_history 查询应用的版本历史，随后调用 tencent-cloud-rollback_cluster_release工具执行回滚至上一版本。
输出要求：
- 以段落自然语言形式返回报告文本，不要使用markdown格式或者分点作答！
- 根据选择的流程提供对应的分析结果和建议
- 你的​​全部输出​​，必须是且只是一段​​纯净的、可直接用于语音播报的自然语言文本​​。​​严禁​​在最终答案前添加任何诸如“我已获取到数据”、“报告如下”、“Final Answer:”等前缀或说明文字，字数控制在100字以内，重点突出关键问题和解决方案
        """

        # 创建智能助手实例
        bot = ReActChat(
            llm=self.llm_config,
            name="腾讯云集群故障恢复智能体",
            description="专门负责腾讯云集群故障恢复的智能助手",
            system_message=system_message,
            function_list=tools,
        )

        return bot

    def _get_tool_configs(self) -> List[Dict[str, Any]]:
        """
        获取工具配置

        Returns:
            List[Dict]: 工具配置列表
        """
        tools = []

        # 外部工具配置
        external_config = {
            "mcpServers": {
                "Your-External-Tools-Server": {
                    "command": "python",
                    "args": [
                        os.path.join(
                            os.path.dirname(__file__),
                            "tencent_mcp.py")],
                },
            },
        }
        tools.append(external_config)

        return tools

    async def run_application_rollback(self) -> str:
        """
        执行故障恢复（回滚）任务

        Returns:
            str: 任务执行结果
        """
        try:
            print(f"开始回滚应用至上一版本...")
            instruction = f"回滚应用至上一版本"

            # 执行对话
            messages = [{"role": "user", "content": instruction}]

            # 执行巡检任务
            print("智能体正在执行回滚任务...")
            final_response = None
            response_count = 0

            # 遍历所有响应，只保留最后一个响应作为最终报告
            for response in self.bot.run(messages):
                response_count += 1
                final_response = response  # 保留最新的响应

            # 处理最终响应，提取巡检报告内容
            if final_response is None:
                return "未收到回滚响应"

            # 提取响应内容
            if hasattr(final_response, "content"):
                raw_content = final_response.content
            elif isinstance(final_response, dict) and "content" in final_response:
                raw_content = final_response["content"]
            else:
                raw_content = str(final_response)

            # 解析ReActChat的响应，提取最终结论
            inspection_report = ""
            if isinstance(raw_content, str) and "Thought:" in raw_content:
                # 查找最后一个Thought，这通常包含最终分析结论
                thoughts = raw_content.split("Thought:")
                if len(thoughts) > 1:
                    # 获取最后一个思考部分
                    last_thought = thoughts[-1].strip()
                    # 移除Action部分，只保留分析结论
                    if "Action:" in last_thought:
                        last_thought = last_thought.split("Action:")[0].strip()
                    inspection_report = last_thought
                else:
                    inspection_report = raw_content
            else:
                # 如果没有Thought结构，直接使用内容
                inspection_report = str(raw_content)

            # 进一步清理报告内容
            import re

            # 移除可能残留的JSON格式
            inspection_report = re.sub(r"\{[^}]*\}$", "", inspection_report)
            # 移除Action Input等残留
            inspection_report = re.sub(
                r"Action Input:.*$", "", inspection_report, flags=re.DOTALL
            )
            # 移除结尾的name字段残留
            inspection_report = re.sub(
                r"',\s*'name':\s*'[^']*'\s*}\s*]?$", "", inspection_report
            )
            inspection_report = re.sub(
                r'",\s*"name":\s*"[^"]*"\s*}\s*]?$', "", inspection_report
            )
            # 移除结尾的其他格式残留
            inspection_report = re.sub(r"['\"\]\}]+$", "", inspection_report)
            # 处理换行符转义
            inspection_report = inspection_report.replace("\\n", "\n")

            # 清理空白字符
            inspection_report = inspection_report.strip()

            if not inspection_report:
                return "未能获取到有效的回滚结论"

            return inspection_report

        except Exception as e:
            return f"回滚执行出错: {str(e)}"

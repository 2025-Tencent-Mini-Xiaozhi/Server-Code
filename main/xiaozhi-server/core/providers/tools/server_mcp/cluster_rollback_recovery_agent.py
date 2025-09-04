#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集群应用回滚恢复验证智能体
专门用于验证应用回滚后的恢复状态
"""

import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

# 导入 qwen-agent 相关模块
from qwen_agent.agents import ReActChat

# 从当前工作目录加载 .env 文件（如果存在）
load_dotenv()


class ClusterRollbackRecoveryAgent:
    """腾讯云集群应用回滚恢复验证智能体"""

    def __init__(
        self,
        llm_config: Dict[str, Any],
        secret_id: str,
        secret_key: str,
        region: str,
        cluster_id: str,
        app_name: str,
        device_id: str = "",
    ):
        """
        初始化智能体

        Args:
            llm_config: LLM配置字典，包含model、api_key等配置
            secret_id: 腾讯云API密钥ID
            secret_key: 腾讯云API密钥
            region: 地域代码，默认ap-guangzhou
            cluster_id: 集群ID
            app_name: 应用名称
            device_id: 设备ID，用于发送通知
        """
        self.llm_config = llm_config
        self.tencent_secret_id = secret_id
        self.tencent_secret_key = secret_key
        self.tencent_region = region
        self.cluster_id = cluster_id
        self.app_name = app_name
        self.device_id = device_id
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

        if not self.cluster_id or not self.app_name:
            raise ValueError("集群ID和应用名称都是必需参数")

        # 验证secret_id格式：应以AKID开头，长度通常在32-40位之间
        if not self.tencent_secret_id.startswith(("AKID", "AKI")) or len(self.tencent_secret_id) < 32:
            raise ValueError("secret_id格式不正确，应以AKID开头且长度至少32位")

        # 验证secret_key格式：长度通常在32-40位之间
        if len(self.tencent_secret_key) < 32:
            raise ValueError("secret_key长度不正确，应至少32位")

        # 验证LLM配置
        if not self.llm_config:
            raise ValueError("LLM配置缺失：llm_config是必需参数")

        api_key = self.llm_config.get("api_key", "")
        if not api_key:
            raise ValueError("LLM API key 缺失，请在llm_config中设置api_key")

        # 验证 API key 是否包含不能被 latin-1 编码的字符
        if any(ord(ch) > 255 for ch in api_key):
            raise ValueError("API key 包含非 Latin-1 字符，无法在 HTTP 头部发送")

        # 检测是否仍为示例/占位符值（排除测试场景）
        lower_key = api_key.lower()
        if (
            "your_api_key" in lower_key
            or "replace_this" in lower_key
            or "please_set" in lower_key
            or api_key in ["", "null", "undefined"]
        ):
            raise ValueError("API key 似乎是占位符值，请设置真实的API key")

    def _init_agent(self) -> ReActChat:
        """
        初始化智能助手

        Returns:
            ReActChat: 配置好的智能助手实例
        """
        # 工具配置：腾讯云MCP
        tools = self._get_tool_configs()

        # 系统提示词：定义助手的专业能力
        system_message = f"""
你是一个专门负责验证腾讯云TKE集群应用回滚恢复状态的智能助手，具备以下核心能力：
用户的secret_id是{self.tencent_secret_id}，secret_key是{self.tencent_secret_key}，region是{self.tencent_region}，device_id是{self.device_id}。

**检查目标**：集群{self.cluster_id}中的应用{self.app_name}

**主要任务**：验证应用回滚后是否已经恢复正常，问题是否得到解决

**工作流程**：
1. **应用状态检查**：
   - 调用 tencent-cloud-describe_cluster_releases 查看应用{self.app_name}的当前状态、版本信息
   - 确认应用是否处于正常运行状态

2. **Pod健康检查**：
   - 调用 tencent-cloud-describe_cluster_instances 查看集群节点状态
   - 调用 tencent-cloud-describe_resource_usage 检查应用相关的Pod资源使用情况
   - 关注Pod重启次数、内存使用率、CPU使用率等关键指标

3. **告警状态验证**：
   - 调用 tencent-cloud-describe_alarm_histories 查看最近10分钟的告警历史
   - 重点关注与应用{self.app_name}相关的告警是否已经停止
   - 检查是否还有未恢复的告警

4. **应用版本确认**：
   - 调用 tencent-cloud-describe_cluster_release_history 查看应用的部署历史
   - 确认当前版本是否为回滚后的目标版本

**输出要求**：
- 格式：必须是一个单一、连贯的自然语言段落，不能有列表符号或Markdown格式
- 风格：保持温柔、贴心、带点小机车的拟人化风格，使用"啦"、"吼"、"喔"等语气词
- 内容结构：
  1. 恢复状态：基于检查结果说明应用是否已恢复正常
  2. 关键指标：提及关键的恢复指标（如Pod状态、告警状态、资源使用等）
  3. 结论：明确说明回滚是否成功，问题是否解决
- 字数控制在200字以内

**判断标准**：
- 恢复成功：应用运行正常 + Pod稳定 + 相关告警已消除 + 资源使用正常
- 需要关注：部分指标改善但仍有问题
- 恢复失败：问题依然存在或出现新问题

你的​​全部输出​​，必须是且只是一段​​纯净的、可直接用于语音播报的自然语言文本​​。​​严禁​​在最终答案前添加任何诸如“我已获取到数据”、“报告如下”、“Final Answer:”等前缀或说明文字。
        """

        # 创建智能助手实例
        bot = ReActChat(
            llm=self.llm_config,
            name="集群应用回滚恢复验证智能体",
            description="专门负责验证集群应用回滚后恢复状态的智能助手",
            system_message=system_message,
            function_list=tools,
        )

        return bot

    def _get_tool_configs(self) -> List[Dict[str, Any]]:
        """
        获取腾讯云MCP工具配置

        Returns:
            List[Dict]: 工具配置列表
        """
        tools = []

        # 腾讯云 MCP 工具配置
        tencent_config = {
            "mcpServers": {
                "Tencent-Cloud-Mcp-Server": {
                    "command": "python",
                    "args": [
                        os.path.join(
                            os.path.dirname(__file__),
                            "tencent_mcp.py")],
                },
            },
        }
        tools.append(tencent_config)

        return tools

    async def run_recovery_verification(self) -> str:
        """
        执行回滚恢复验证

        Returns:
            str: 恢复验证报告字符串
        """
        try:
            print(f"开始执行应用回滚恢复验证 - 集群: {self.cluster_id}, 应用: {self.app_name}")
            
            instruction = f"请验证集群 {self.cluster_id} 中应用 {self.app_name} 的回滚恢复状态"

            # 构建消息格式
            messages = [{"role": "user", "content": [{"text": instruction}]}]

            # 执行验证任务
            print("智能体正在执行恢复验证任务...")
            final_response = None
            response_count = 0

            # 遍历所有响应，只保留最后一个响应作为最终报告
            for response in self.bot.run(messages):
                response_count += 1
                final_response = response  # 保留最新的响应

            # 处理最终响应，提取验证报告内容
            if final_response is None:
                return "未收到恢复验证响应"

            # 提取响应内容
            if hasattr(final_response, "content"):
                raw_content = final_response.content
            elif isinstance(final_response, dict) and "content" in final_response:
                raw_content = final_response["content"]
            else:
                raw_content = str(final_response)

            # 解析ReActChat的响应，提取最终结论
            verification_report = ""
            if isinstance(raw_content, str) and "Thought:" in raw_content:
                # 查找最后一个Thought，这通常包含最终分析结论
                thoughts = raw_content.split("Thought:")
                if len(thoughts) > 1:
                    # 获取最后一个思考部分
                    last_thought = thoughts[-1].strip()
                    # 移除Action部分，只保留分析结论
                    if "Action:" in last_thought:
                        last_thought = last_thought.split("Action:")[0].strip()
                    verification_report = last_thought
                else:
                    verification_report = raw_content
            else:
                # 如果没有Thought结构，直接使用内容
                verification_report = str(raw_content)

            # 进一步清理报告内容
            import re

            # 移除可能残留的JSON格式
            verification_report = re.sub(r"\{[^}]*\}$", "", verification_report)
            # 移除Action Input等残留
            verification_report = re.sub(
                r"Action Input:.*$", "", verification_report, flags=re.DOTALL
            )
            # 移除结尾的name字段残留
            verification_report = re.sub(
                r"',\s*'name':\s*'[^']*'\s*}\s*]?$", "", verification_report
            )
            verification_report = re.sub(
                r'",\s*"name":\s*"[^"]*"\s*}\s*]?$', "", verification_report
            )
            # 移除结尾的其他格式残留
            verification_report = re.sub(r"['\"\]\}]+$", "", verification_report)
            # 处理换行符转义
            verification_report = verification_report.replace("\\n", "\n")

            # 清理空白字符
            verification_report = verification_report.strip()

            if not verification_report:
                return "未能获取到有效的恢复验证结论"

            return verification_report

        except Exception as e:
            return f"恢复验证执行出错: {str(e)}"

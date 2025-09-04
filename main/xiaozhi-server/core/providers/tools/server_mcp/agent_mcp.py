import os
import signal
import sys
import threading
import asyncio
import requests
import time
from mcp.server.fastmcp import FastMCP
from cluster_inspection_agent import ClusterInspectionAgent
from cluster_alarm_analysis_agent import ClusterAlarmAnalysisAgent
from cluster_application_rollback import ClusterApplicationRollbackAgent
from dotenv import load_dotenv

load_dotenv()

# 初始化 MCP 服务器
mcp = FastMCP("Agent_MCP_Server")

def send_device_notification(
    device_id: str, message: str, notification_type: str = "info"
) -> str:
    """直接向指定设备发送通知消息，绕过LLM处理，适用于系统通知、警告等"""
    try:
        # 构建请求数据 - 强制绕过LLM
        url = "http://localhost:8003/xiaozhi/push/message"
        headers = {"Content-Type": "application/json"}
        data = {
            "device_id": device_id,
            "message": message,
            "auth_key": "3b039beb-90fa-4170-bed2-e0e146126877",
            "bypass_llm": True,  # 强制绕过LLM
            "notification_type": notification_type,
        }

        # 发送HTTP POST请求
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            return (
                f"直接通知发送成功到设备 {device_id}: [{notification_type}] {message}"
            )
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return f"直接通知发送失败: {error_msg}"

    except requests.exceptions.Timeout:
        return "直接通知发送超时"
    except requests.exceptions.ConnectionError:
        return "直接通知发送连接失败"
    except Exception as e:
        return f"直接通知发送异常: {str(e)}"


def send_ai_request(
    device_id: str, request: str, notification_type: str = "info"
) -> str:
    """向AI发送需要智能处理的请求，通过LLM进行分析和回复"""
    try:
        # 构建请求数据 - 强制使用LLM
        url = "http://localhost:8003/xiaozhi/push/message"
        headers = {"Content-Type": "application/json"}
        data = {
            "device_id": device_id,
            "message": request,
            "auth_key": "3b039beb-90fa-4170-bed2-e0e146126877",
            "bypass_llm": False,  # 强制使用LLM
            "notification_type": notification_type,
        }

        # 发送HTTP POST请求
        response = requests.post(
            url, headers=headers, json=data, timeout=15  # AI处理可能需要更长时间
        )

        if response.status_code == 200:
            return f"AI请求发送成功到设备 {device_id}: {request}"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return f"AI请求发送失败: {error_msg}"

    except requests.exceptions.Timeout:
        return "AI请求发送超时（LLM处理时间较长）"
    except requests.exceptions.ConnectionError:
        return "AI请求发送连接失败"
    except Exception as e:
        return f"AI请求发送异常: {str(e)}"


async def _execute_cluster_inspection_async(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str,
    top_p: float,
    temperature: float,
) -> None:
    """异步执行集群巡检任务"""
    max_retries = 2  # 最大重试次数
    retry_delay = 5  # 重试间隔（秒）
    
    for attempt in range(max_retries + 1):
        try:
            print(f"开始异步执行集群巡检，设备ID: {device_id}，尝试次数: {attempt + 1}/{max_retries + 1}")
            
            # 构建LLM配置
            llm_config = {
                "model": os.getenv("AGENT_MODEL", ""),
                "model_server": "dashscope",
                "api_key": os.getenv("AGENT_API_KEY", ""),
                "generate_cfg": {
                    "top_p": top_p,
                    "temperature": temperature,
                },
            }

            # 检查必要配置
            if not llm_config["model"] or not llm_config["api_key"]:
                error_msg = "智能体LLM配置缺失，无法进行巡检"
                print(f"配置错误: {error_msg}")
                if device_id:
                    send_device_notification(
                        device_id=device_id,
                        message=error_msg,
                        notification_type="error"
                    )
                return

            # 创建集群巡检智能体
            agent = ClusterInspectionAgent(
                llm_config=llm_config,
                secret_id=secret_id,
                secret_key=secret_key,
                region=region,
                device_id=device_id,
            )

            # 执行巡检（设置更长的超时时间）
            print(f"正在执行巡检，预计需要30-60秒...")
            report = await asyncio.wait_for(agent.run_inspection(), timeout=120.0)
            
            # 检查报告质量
            if not report or report.strip() == "" or "未能获取到有效的巡检结论" in report:
                raise Exception(f"巡检结果无效: {report}")
            
            # 发送详细巡检报告到设备
            if device_id:
                notification_result = send_device_notification(
                    device_id=device_id,
                    message=report,
                    notification_type="inspection_result"
                )
                print(f"巡检报告发送结果: {notification_result}")
                print(f"巡检任务完成，第 {attempt + 1} 次尝试成功")
            else:
                print(f"异步巡检完成，但未提供设备ID，无法发送通知")
                print(f"巡检报告: {report}")
            
            # 成功则跳出重试循环
            return

        except asyncio.TimeoutError:
            error_message = f"集群巡检执行超时（第 {attempt + 1} 次尝试）"
            print(f"超时错误: {error_message}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                print(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
                continue
            else:
                # 最后一次尝试失败，发送错误通知
                if device_id:
                    send_device_notification(
                        device_id=device_id,
                        message=f"集群巡检执行超时，已重试 {max_retries} 次，请稍后再试",
                        notification_type="error"
                    )
                
        except Exception as e:
            error_message = f"异步集群巡检执行失败（第 {attempt + 1} 次尝试）: {str(e)}"
            print(f"异步巡检错误: {error_message}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries:
                print(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)
                continue
            else:
                # 最后一次尝试失败，发送错误通知
                if device_id:
                    send_device_notification(
                        device_id=device_id,
                        message=f"集群巡检执行失败，已重试 {max_retries} 次: {str(e)}",
                        notification_type="error"
                    )


def _run_async_inspection_in_thread(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str,
    top_p: float,
    temperature: float,
) -> None:
    """在新线程中运行异步巡检任务"""
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        print(f"巡检线程已启动，设备ID: {device_id}")
        
        # 运行异步巡检任务
        loop.run_until_complete(
            _execute_cluster_inspection_async(
                secret_id, secret_key, region, device_id, top_p, temperature
            )
        )
        
        print(f"巡检线程执行完成，设备ID: {device_id}")
        
    except Exception as e:
        error_message = f"线程中执行异步巡检失败: {str(e)}"
        print(f"线程错误: {error_message}")
        
        # 尝试发送错误通知到设备
        try:
            if device_id:
                import requests
                url = "http://localhost:8003/xiaozhi/push/message"
                headers = {"Content-Type": "application/json"}
                data = {
                    "device_id": device_id,
                    "message": f"集群巡检线程执行失败: {str(e)}",
                    "auth_key": "3b039beb-90fa-4170-bed2-e0e146126877",
                    "bypass_llm": True,
                    "notification_type": "error",
                }
                response = requests.post(url, headers=headers, json=data, timeout=10)
                print(f"错误通知发送结果: HTTP {response.status_code}")
        except Exception as notify_error:
            print(f"发送错误通知失败: {notify_error}")
    
    finally:
        # 清理事件循环
        try:
            if 'loop' in locals():
                loop.close()
                print(f"事件循环已清理，设备ID: {device_id}")
        except Exception as cleanup_error:
            print(f"清理事件循环失败: {cleanup_error}")


async def _execute_cluster_alarm_analysis_async(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str,
    top_p: float,
    temperature: float,
) -> None:
    """异步执行集群告警分析任务"""
    try:
        print(f"开始异步执行集群告警分析，设备ID: {device_id}")
        
        # 构建LLM配置
        llm_config = {
            "model": os.getenv("AGENT_MODEL", ""),
            "model_server": "dashscope",
            "api_key": os.getenv("AGENT_API_KEY", ""),
            "generate_cfg": {
                "top_p": top_p,
                "temperature": temperature,
            },
        }

        # 创建集群告警分析智能体
        agent = ClusterAlarmAnalysisAgent(
            llm_config=llm_config,
            secret_id=secret_id,
            secret_key=secret_key,
            region=region,
            device_id=device_id,
        )

        # 执行告警分析
        report = await agent.run_alarm_analysis()
        
        # 发送详细告警分析报告到设备
        if device_id:
            notification_result = send_device_notification(
                device_id=device_id,
                message=report,
                notification_type="alarm_analysis_result"
            )
            print(f"告警分析报告发送结果: {notification_result}")
        else:
            print(f"异步告警分析完成，但未提供设备ID，无法发送通知")
            print(f"告警分析报告: {report}")

    except Exception as e:
        error_message = f"异步集群告警分析执行失败: {str(e)}"
        print(f"异步告警分析错误: {error_message}")
        
        # 即使出错也尝试发送错误通知
        if device_id:
            send_device_notification(
                device_id=device_id,
                message=f"集群告警分析执行失败: {str(e)}",
                notification_type="error"
            )


def _run_async_alarm_analysis_in_thread(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str
) -> None:
    """在新线程中运行异步告警分析任务"""
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行异步告警分析任务
        loop.run_until_complete(
            _execute_cluster_alarm_analysis_async(
                secret_id, secret_key, region, device_id, 0.8, 0.7
            )
        )
    except Exception as e:
        print(f"线程中执行异步告警分析失败: {str(e)}")
    finally:
        # 清理事件循环
        try:
            loop.close()
        except:
            pass


async def _execute_cluster_application_rollback_async(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str,
    cluster_id: str,
    name: str,
    top_p: float,
    temperature: float,
) -> None:
    """异步执行集群应用回滚任务（包含闭环反馈检查）"""
    try:
        print(f"开始异步执行集群应用回滚，设备ID: {device_id}, 集群: {cluster_id}, 应用: {name}")
        
        # 构建LLM配置
        llm_config = {
            "model": os.getenv("AGENT_MODEL", ""),
            "model_server": "dashscope",
            "api_key": os.getenv("AGENT_API_KEY", ""),
            "generate_cfg": {
                "top_p": top_p,
                "temperature": temperature,
            },
        }

        # 第一阶段：执行应用回滚
        print(f"第一阶段：执行应用回滚操作...")
        
        # 创建集群应用回滚智能体
        rollback_agent = ClusterApplicationRollbackAgent(
            llm_config=llm_config,
            secret_id=secret_id,
            secret_key=secret_key,
            region=region,
            device_id=device_id,
            cluster_id=cluster_id,
            name=name,
        )

        # 执行应用回滚
        rollback_report = await rollback_agent.run_application_rollback()
        
        # 发送回滚操作结果到设备
        if device_id:
            rollback_notification_result = send_device_notification(
                device_id=device_id,
                message=f"应用回滚操作已完成\n\n{rollback_report}\n\n将在5分钟后自动检查告警恢复情况...",
                notification_type="rollback_result"
            )
            print(f"回滚操作报告发送结果: {rollback_notification_result}")
        
        # 第二阶段：延时等待（5分钟）
        print(f"第二阶段：等待5分钟后进行告警恢复检查...")
        await asyncio.sleep(300)  # 等待2分钟 (120秒)
        
        # 第三阶段：执行告警检查
        print(f"第三阶段：执行应用恢复验证...")
        
        try:
            # 导入恢复验证智能体
            from cluster_rollback_recovery_agent import ClusterRollbackRecoveryAgent
            
            # 创建应用恢复验证智能体
            recovery_agent = ClusterRollbackRecoveryAgent(
                llm_config=llm_config,
                secret_id=secret_id,
                secret_key=secret_key,
                region=region,
                cluster_id=cluster_id,
                app_name=name,
                device_id=device_id,
            )
            
            # 执行应用恢复验证
            recovery_report = await recovery_agent.run_recovery_verification()
            
            # 发送恢复验证结果到设备
            if device_id:
                check_notification_result = send_device_notification(
                    device_id=device_id,
                    message=f"应用回滚恢复验证报告\n\n集群: {cluster_id}\n应用: {name}\n\n{recovery_report}",
                    notification_type="recovery_check_result"
                )
                print(f"恢复验证报告发送结果: {check_notification_result}")
            
        except Exception as check_error:
            error_message = f"应用恢复验证失败: {str(check_error)}"
            print(f"应用恢复验证错误: {error_message}")
            
            # 验证失败时也要通知用户
            if device_id:
                send_device_notification(
                    device_id=device_id,
                    message=f"应用 {name} 回滚后的恢复验证失败: {str(check_error)}",
                    notification_type="error"
                )
        
        print(f"应用回滚闭环反馈流程完成")

    except Exception as e:
        error_message = f"异步集群应用回滚执行失败: {str(e)}"
        print(f"异步应用回滚错误: {error_message}")
        
        # 即使出错也尝试发送错误通知
        if device_id:
            send_device_notification(
                device_id=device_id,
                message=f"集群应用回滚执行失败: {str(e)}",
                notification_type="error"
            )


def _run_async_application_rollback_in_thread(
    secret_id: str,
    secret_key: str,
    region: str,
    device_id: str,
    cluster_id: str,
    name: str,
    top_p: float,
    temperature: float,
) -> None:
    """在新线程中运行异步应用回滚任务"""
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行异步应用回滚任务
        loop.run_until_complete(
            _execute_cluster_application_rollback_async(
                secret_id, secret_key, region, device_id, cluster_id, name, top_p, temperature
            )
        )
    except Exception as e:
        print(f"线程中执行异步应用回滚失败: {str(e)}")
    finally:
        # 清理事件循环
        try:
            loop.close()
        except:
            pass


@mcp.tool(description="执行腾讯云TKE集群巡检")
async def run_cluster_inspection(
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    device_id: str = ""
) -> str:
    """
    执行腾讯云TKE集群巡检

    Args:
        secret_id: 腾讯云API密钥ID
        secret_key: 腾讯云API密钥
        region: 腾讯云区域代码，默认 'ap-guangzhou'
        device_id: 设备ID，用于发送通知

    Returns:
        str: 立即返回的响应字符串，实际巡检在后台异步执行

    Raises:
        Exception: 当参数验证失败时抛出异常

    """
    try:
        print(f"[巡检工具] 开始执行集群巡检 - 设备ID: {device_id}, 地域: {region}")
        
        # 基本参数验证
        if not secret_id or not secret_key:
            raise ValueError("腾讯云API凭据缺失：secret_id和secret_key都是必需参数")
        
        # 检查LLM配置
        agent_model = os.getenv("AGENT_MODEL", "")
        agent_api_key = os.getenv("AGENT_API_KEY", "")
        
        if not agent_model or not agent_api_key:
            error_msg = "智能体LLM配置缺失，请检查环境变量 AGENT_MODEL 和 AGENT_API_KEY"
            print(f"[巡检工具] 配置错误: {error_msg}")
            return f"启动集群巡检失败: {error_msg}"
        
        print(f"[巡检工具] 配置验证通过 - 模型: {agent_model}, API密钥: {'*' * min(8, len(agent_api_key))}...")
        
        # 在后台线程中异步执行巡检任务
        inspection_thread = threading.Thread(
            target=_run_async_inspection_in_thread,
            args=(secret_id, secret_key, region, device_id, 0.8, 0.7),
            daemon=True,  # 设置为守护线程，主程序退出时自动结束
            name=f"ClusterInspection-{device_id}-{int(time.time())}"
        )
        
        # 启动后台巡检线程
        inspection_thread.start()
        
        print(f"[巡检工具] 集群巡检任务已启动，设备ID: {device_id}，线程: {inspection_thread.name}")
        
        # 立即返回响应，告知用户正在巡检
        return "正在进行集群巡检，请稍后查看详细报告"

    except Exception as e:
        error_message = f"启动集群巡检失败: {str(e)}"
        print(f"[巡检工具] 启动错误: {error_message}")
        return error_message


@mcp.tool(description="执行腾讯云TKE告警分析")
async def run_cluster_alarm_analysis(
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    device_id: str = ""
) -> str:
    """
    执行腾讯云TKE告警分析

    Args:
        secret_id: 腾讯云API密钥ID
        secret_key: 腾讯云API密钥
        region: 腾讯云区域代码，默认 'ap-guangzhou'
        device_id: 设备ID，用于发送通知
        top_p: 模型参数，控制生成文本的多样性，默认 0.8
        temperature: 模型参数，控制生成文本的随机性，默认 0.7

    Returns:
        str: 立即返回的响应字符串，实际告警分析在后台异步执行

    Raises:
        Exception: 当参数验证失败时抛出异常

    """
    try:
        # 基本参数验证
        if not secret_id or not secret_key:
            raise ValueError("腾讯云API凭据缺失：secret_id和secret_key都是必需参数")
        
        # 在后台线程中异步执行告警分析任务
        alarm_analysis_thread = threading.Thread(
            target=_run_async_alarm_analysis_in_thread,
            args=(secret_id, secret_key, region, device_id),
            daemon=True,  # 设置为守护线程，主程序退出时自动结束
            name=f"ClusterAlarmAnalysis-{device_id}"
        )
        
        # 启动后台告警分析线程
        alarm_analysis_thread.start()
        
        print(f"集群告警分析任务已启动，设备ID: {device_id}，线程: {alarm_analysis_thread.name}")
        
        # 立即返回响应，告知用户正在分析
        return "正在进行集群告警分析，请稍后查看详细报告"

    except Exception as e:
        error_message = f"启动集群告警分析失败: {str(e)}"
        print(f"告警分析启动错误: {error_message}")
        return error_message


@mcp.tool(description="回滚TKE集群应用版本")
async def run_cluster_application_rollback(
    secret_id: str,
    secret_key: str,
    region: str = "ap-guangzhou",
    device_id: str = "",
    cluster_id: str = "",
    name: str = ""
) -> str:
    """
    执行腾讯云TKE集群应用回滚

    Args:
        secret_id: 腾讯云API密钥ID
        secret_key: 腾讯云API密钥
        region: 腾讯云区域代码，默认 'ap-guangzhou'
        device_id: 设备ID，用于发送通知
        cluster_id: 集群ID
        name: 应用名称

    Returns:
        str: 立即返回的响应字符串，实际应用回滚在后台异步执行

    Raises:
        Exception: 当参数验证失败时抛出异常

    """
    try:
        # 基本参数验证
        if not secret_id or not secret_key:
            raise ValueError("腾讯云API凭据缺失：secret_id和secret_key都是必需参数")
        
        if not cluster_id or not name:
            raise ValueError("集群ID和应用名称都是必需参数")
        
        # 在后台线程中异步执行应用回滚任务
        rollback_thread = threading.Thread(
            target=_run_async_application_rollback_in_thread,
            args=(secret_id, secret_key, region, device_id, cluster_id, name, 0.8, 0.7),
            daemon=True,  # 设置为守护线程，主程序退出时自动结束
            name=f"ApplicationRollback-{cluster_id}-{name}-{device_id}"
        )
        
        # 启动后台应用回滚线程
        rollback_thread.start()
        
        print(f"集群应用回滚任务已启动，集群: {cluster_id}, 应用: {name}, 设备ID: {device_id}，线程: {rollback_thread.name}")
        
        # 立即返回响应，告知用户正在回滚
        return f"正在进行应用的版本回滚，请稍后查看详细报告"

    except Exception as e:
        error_message = f"启动集群应用回滚失败: {str(e)}"
        print(f"应用回滚启动错误: {error_message}")
        return error_message


def signal_handler(signum, frame):
    """信号处理器，确保优雅退出"""
    sys.exit(0)


def main():
    """主函数"""

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    mcp.run()


if __name__ == "__main__":
    main()

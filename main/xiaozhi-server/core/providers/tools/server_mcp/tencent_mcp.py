#!/usr/bin/env python3
"""
FastMCP服务器
npx -y @modelcontextprotocol/inspector uv run server.py
"""

import json
import sys
import signal
import requests
from typing import List, Optional
from pydantic import Field

# 引入MCP相关
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

# 引入腾讯云SDK
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.tke.v20180525 import tke_client, models as models_2018
from tencentcloud.cls.v20201016 import cls_client, models as models_2020
from tencentcloud.monitor.v20180724 import monitor_client
from tencentcloud.monitor.v20180724 import models as models_20180724

# 创建FastMCP服务器实例
mcp = FastMCP("Tencent-Cloud-Mcp-Server")

# ==========================================
# 腾讯云TKE接口
# ==========================================


@mcp.tool(description="查询集群列表")
async def describe_clusters(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-guangzhou"),
) -> str:
    """
    查询集群列表。

    该工具调用腾讯云TKE接口，实现集群列表查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数

    Returns:
        JSON格式的集群列表响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClustersRequest()
        params = {}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusters(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(
    description="查询用户单个Region下的所有集群巡检结果概览信息",
)
async def describe_cluster_inspection_results_overview(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，详见腾讯云地域列表"),
) -> str:
    """
    查询用户单个Region下的所有集群巡检结果概览信息。
    该工具调用腾讯云TKE DescribeClusterInspectionResultsOverview接口，实现集群巡检结果查询功能。

    Args:
        secret_id: 腾讯云账户SecretId
        secret_key: 腾讯云账户SecretKey
        region: 腾讯云地域参数

    Returns:
        返回包含诊断结果统计、诊断结果概览和集群诊断结果概览的JSON字符串

    Raises:
        ToolError: API调用失败或执行时发生错误
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClusterInspectionResultsOverviewRequest()

        params = {}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusterInspectionResultsOverview(req)

        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="查询指定集群的巡检结果信息")
async def list_cluster_inspection_results(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-guangzhou"),
    cluster_ids: List[str] = Field(
        description="目标集群ID列表，为空查询用户所有集群", default=[]
    ),
) -> str:
    """
    查询指定集群的巡检结果信息。

    该工具调用腾讯云TKE接口，实现集群巡检结果查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_ids: 目标集群ID列表

    Returns:
        JSON格式的巡检结果响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.ListClusterInspectionResultsRequest()
        params = {}

        req.from_json_string(json.dumps(params))

        resp = client.ListClusterInspectionResults(req)
        
        # 解析API响应并过滤指定集群
        response_data = json.loads(resp.to_json_string())
        
        # 关键修改：根据cluster_ids过滤结果
        if cluster_ids:
            filtered_results = [
                result for result in response_data["InspectionResults"] 
                if result["ClusterId"] in cluster_ids
            ]
            response_data["InspectionResults"] = filtered_results
        
        return json.dumps(response_data, ensure_ascii=False)

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="查看集群状态列表")
async def describe_cluster_status(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
) -> str:
    """
    查看集群状态列表。

    该工具调用腾讯云TKE接口，实现集群状态查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数

    Returns:
        JSON格式的集群状态响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClusterStatusRequest()
        params = {}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusterStatus(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="获取集群资源使用量")
async def describe_resource_usage(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群ID"),
) -> str:
    """
    获取集群资源使用量。

    该工具调用腾讯云TKE接口，实现集群资源使用量查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群ID

    Returns:
        JSON格式的集群资源使用量响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeResourceUsageRequest()
        params = {"ClusterId": cluster_id}
        req.from_json_string(json.dumps(params))

        resp = client.DescribeResourceUsage(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="获取addon列表")
async def describe_addon(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群ID"),
    addon_name: Optional[str] = Field(
        description="addon名称，不传时会返回集群下全部的addon", default=None
    ),
) -> str:
    """
    获取addon列表。

    该工具调用腾讯云TKE接口，实现集群addon列表查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群ID
        addon_name: addon名称

    Returns:
        JSON格式的addon列表响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeAddonRequest()
        params = {"ClusterId": cluster_id}

        if addon_name:
            params["AddonName"] = addon_name

        req.from_json_string(json.dumps(params))

        resp = client.DescribeAddon(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="查询节点池列表")
async def describe_cluster_node_pools(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群id"),
    offset: int = Field(description="偏移量，默认0", default=0),
    limit: int = Field(description="返回数量，默认20，最大100", default=20),
) -> str:
    """
    查询节点池列表。

    该工具调用腾讯云TKE接口，实现节点池列表查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群id
        offset: 偏移量
        limit: 返回数量

    Returns:
        JSON格式的节点池列表响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        # 注意：这里需要使用正确版本的客户端
        # 确保导入的是 v20220501 版本
        from tencentcloud.tke.v20220501 import tke_client
        from tencentcloud.tke.v20220501 import models as models_2022

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2022.DescribeNodePoolsRequest()
        params = {"ClusterId": cluster_id, "Offset": offset, "Limit": limit}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeNodePools(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(description="查询集群下节点实例信息")
async def describe_cluster_instances(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群ID"),
    offset: Optional[int] = Field(description="偏移量，默认为0", default=None),
    limit: Optional[int] = Field(
        description="返回数量，默认为20，最大值为100", default=None
    ),
) -> str:
    """
    查询集群下节点实例信息。

    该工具调用腾讯云TKE接口，实现集群节点实例信息查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群ID
        offset: 偏移量
        limit: 返回数量

    Returns:
        JSON格式的集群节点实例信息响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClusterInstancesRequest()
        params = {"ClusterId": cluster_id}

        if offset is not None:
            params["Offset"] = offset
        if limit is not None:
            params["Limit"] = limit

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusterInstances(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(
    description="查询集群在应用市场中已安装应用列表"
)
async def describe_cluster_releases(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群id"),
    limit: Optional[int] = Field(description="每页数量限制", default=None),
    offset: Optional[int] = Field(description="页偏移量", default=None),
) -> str:
    """
    查询集群在应用市场中已安装应用列表。

    该工具调用腾讯云TKE接口，实现集群已安装应用列表查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群id
        limit: 每页数量限制
        offset: 页偏移量

    Returns:
        JSON格式的已安装应用列表响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClusterReleasesRequest()
        params = {"ClusterId": cluster_id}

        if limit is not None:
            params["Limit"] = limit
        if offset is not None:
            params["Offset"] = offset

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusterReleases(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(
    description="查询集群在应用市场中某个已安装应用的版本历史",
)
async def describe_cluster_release_history(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群ID"),
    name: str = Field(description="应用名称"),
    namespace: str = Field(description="应用所在命名空间"),
) -> str:
    """
    查询集群在应用市场中某个已安装应用的版本历史。

    该工具调用腾讯云TKE接口，实现集群已安装应用版本历史查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群ID
        name: 应用名称
        namespace: 应用所在命名空间

    Returns:
        JSON格式的应用版本历史响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.DescribeClusterReleaseHistoryRequest()
        params = {"ClusterId": cluster_id, "Name": name, "Namespace": namespace}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeClusterReleaseHistory(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(
    description="在应用市场中集群回滚应用至某个历史版本"
)
async def rollback_cluster_release(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    cluster_id: str = Field(description="集群ID"),
    name: str = Field(description="应用名称"),
    namespace: str = Field(description="应用命名空间"),
    revision: int = Field(description="回滚版本号"),
) -> str:
    """
    在应用市场中集群回滚应用至某个历史版本。

    该工具调用腾讯云TKE接口，实现集群应用版本回滚功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        cluster_id: 集群ID
        name: 应用名称
        namespace: 应用命名空间
        revision: 回滚版本号

    Returns:
        JSON格式的应用回滚响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "tke.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = tke_client.TkeClient(cred, region, clientProfile)

        req = models_2018.RollbackClusterReleaseRequest()
        params = {
            "ClusterId": cluster_id,
            "Name": name,
            "Namespace": namespace,
            "Revision": revision,
        }

        req.from_json_string(json.dumps(params))

        resp = client.RollbackClusterRelease(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


# ==========================================
# 腾讯云MONITOR接口
# ==========================================


@mcp.tool(description="查询腾讯云监控告警历史记录")
async def describe_alarm_histories(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数"),
    page_number: Optional[int] = Field(description="页数，从1开始计数", default=1),
    page_size: Optional[int] = Field(description="每页数量，取值1-100", default=10),
    order: Optional[str] = Field(
        description="排序方式，ASC=正序，DESC=逆序", default="DESC"
    ),
    start_time: int = Field(description="秒级起始时间戳", default=None),
    end_time: int = Field(description="秒级结束时间戳", default=None),
) -> str:
    """
    查询腾讯云监控告警历史记录。

    该工具调用腾讯云监控API的DescribeAlarmHistories接口，获取告警历史数据。

    Args:
        secret_id: 腾讯云访问密钥ID
        secret_key: 腾讯云访问密钥Key
        region: 腾讯云地域
        page_number: 分页页码
        page_size: 每页记录数
        order: 排序方式
        start_time: 查询起始时间戳
        end_time: 查询结束时间戳

    Returns:
        JSON格式的告警历史查询结果

    Raises:
        ToolError: API调用失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "monitor.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = monitor_client.MonitorClient(cred, region, clientProfile)

        req = models_20180724.DescribeAlarmHistoriesRequest()

        params = {"Module": "monitor"}

        if page_number is not None:
            params["PageNumber"] = page_number
        if page_size is not None:
            params["PageSize"] = page_size
        if order is not None:
            params["Order"] = order
        if start_time is not None:
            params["StartTime"] = start_time
        if end_time is not None:
            params["EndTime"] = end_time

        req.from_json_string(json.dumps(params))

        resp = client.DescribeAlarmHistories(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


# ==========================================
# 腾讯云CLS接口
# ==========================================


@mcp.tool(description="获取告警历史，例如今天未恢复的告警")
async def describe_alert_record_history(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-beijing"),
    from_time: int = Field(description="查询时间范围启始时间，毫秒级unix时间戳"),
    to_time: int = Field(description="查询时间范围结束时间，毫秒级unix时间戳"),
    offset: int = Field(description="分页的偏移量，默认值为0", default=0),
    limit: int = Field(description="分页单页限制数目，最大值100", default=10),
) -> str:
    """
    获取告警历史，例如今天未恢复的告警。

    该工具调用腾讯云CLS接口，实现告警历史查询功能。

    Args:
        secret_id: 腾讯云SecretId
        secret_key: 腾讯云SecretKey
        region: 地域参数
        from_time: 查询时间范围启始时间，毫秒级unix时间戳
        to_time: 查询时间范围结束时间，毫秒级unix时间戳
        offset: 分页的偏移量
        limit: 分页单页限制数目

    Returns:
        JSON格式的告警历史响应

    Raises:
        ToolError: 工具执行失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "cls.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = cls_client.ClsClient(cred, region, clientProfile)

        req = models_2020.DescribeAlertRecordHistoryRequest()
        params = {"From": from_time, "To": to_time, "Offset": offset, "Limit": limit}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeAlertRecordHistory(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"执行时发生错误: {str(e)}")


@mcp.tool(
    description="获取腾讯云日志服务的日志集信息列表"
)
async def describe_logsets(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-shanghai"),
    offset: Optional[int] = Field(default=0, description="分页偏移量，默认为0"),
    limit: Optional[int] = Field(
        default=20, description="分页限制数目，默认20，最大100"
    ),
) -> str:
    """
    腾讯云日志服务日志集列表查询工具。

    该工具调用腾讯云CLS DescribeLogsets接口，实现日志集信息的查询功能。

    Args:
        secret_id: 腾讯云访问密钥ID
        secret_key: 腾讯云访问密钥Key
        region: 腾讯云地域
        offset: 分页偏移量
        limit: 分页限制数目

    Returns:
        JSON格式的日志集列表查询结果

    Raises:
        ToolError: API调用失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "cls.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = cls_client.ClsClient(cred, region, clientProfile)

        req = models_2020.DescribeLogsetsRequest()
        params = {"Offset": offset, "Limit": limit}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeLogsets(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"日志集列表查询执行时发生错误: {str(e)}")


@mcp.tool(
    description="获取腾讯云日志服务的日志主题列表，支持分页和多种过滤条件",
)
async def describe_topics(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-shanghai"),
    offset: Optional[int] = Field(default=0, description="分页偏移量，默认为0"),
    limit: Optional[int] = Field(
        default=20, description="分页限制数目，默认20，最大100"
    ),
) -> str:
    """
    腾讯云日志服务日志主题列表查询工具。

    该工具调用腾讯云CLS DescribeTopics接口，实现日志主题信息的查询功能。

    Args:
        secret_id: 腾讯云访问密钥ID
        secret_key: 腾讯云访问密钥Key
        region: 腾讯云地域
        offset: 分页偏移量
        limit: 分页限制数目

    Returns:
        JSON格式的日志主题列表查询结果

    Raises:
        ToolError: API调用失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "cls.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = cls_client.ClsClient(cred, region, clientProfile)

        req = models_2020.DescribeTopicsRequest()
        params = {"Offset": offset, "Limit": limit}

        req.from_json_string(json.dumps(params))

        resp = client.DescribeTopics(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"日志主题列表查询执行时发生错误: {str(e)}")


@mcp.tool(
    description="检索分析日志数据，支持CQL和Lucene语法"
)
async def search_log(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-shanghai"),
    from_time: int = Field(description="检索起始时间，Unix时间戳（毫秒）"),
    to_time: int = Field(description="检索结束时间，Unix时间戳（毫秒）"),
    query: str = Field(description="检索分析语句，支持CQL或Lucene语法"),
    syntax_rule: Optional[int] = Field(
        default=1, description="检索语法规则，0=Lucene，1=CQL（推荐）"
    ),
    topic_id: Optional[str] = Field(default=None, description="单个日志主题ID"),
    sort: Optional[str] = Field(default="desc", description="排序方式，asc或desc"),
    limit: Optional[int] = Field(default=100, description="返回日志条数，最大1000"),
    offset: Optional[int] = Field(default=0, description="偏移量，从第几行开始返回"),
    context: Optional[str] = Field(
        default=None, description="透传上次返回的Context值获取更多日志"
    ),
    sampling_rate: Optional[float] = Field(
        default=1.0, description="采样率，0-1之间，1为不采样"
    ),
    use_new_analysis: Optional[bool] = Field(
        default=True, description="是否使用新的检索结果返回方式"
    ),
    highlight: Optional[bool] = Field(default=False, description="是否高亮显示关键词"),
) -> str:
    """
    腾讯云日志服务检索分析工具。

    该工具调用腾讯云CLS SearchLog接口，实现日志检索和分析功能。

    Args:
        secret_id: 腾讯云访问密钥ID
        secret_key: 腾讯云访问密钥Key
        region: 腾讯云地域
        from_time: 检索起始时间（毫秒级Unix时间戳）
        to_time: 检索结束时间（毫秒级Unix时间戳）
        query: 检索分析语句
        syntax_rule: 检索语法规则（推荐使用1=CQL）
        topic_id: 日志主题ID（单主题检索时使用）
        sort: 排序方式
        limit: 返回条数限制
        offset: 偏移量
        context: 分页上下文
        sampling_rate: 统计分析采样率
        use_new_analysis: 是否使用新的分析结果格式
        highlight: 是否高亮关键词

    Returns:
        JSON格式的日志检索分析结果

    Raises:
        ToolError: API调用失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "cls.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = cls_client.ClsClient(cred, region, clientProfile)

        req = models_2020.SearchLogRequest()
        params = {
            "From": from_time,
            "To": to_time,
            "Query": query,
            "SyntaxRule": syntax_rule,
            "Sort": sort,
            "Limit": limit,
            "Offset": offset,
            "SamplingRate": sampling_rate,
            "UseNewAnalysis": use_new_analysis,
            "HighLight": highlight,
        }

        if topic_id is not None:
            params["TopicId"] = topic_id
        if context is not None:
            params["Context"] = context

        req.from_json_string(json.dumps(params))

        resp = client.SearchLog(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"日志检索分析执行时发生错误: {str(e)}")


@mcp.tool(description="搜索指定日志附近的上下文内容")
async def describe_log_context(
    secret_id: str = Field(description="腾讯云SecretId"),
    secret_key: str = Field(description="腾讯云SecretKey"),
    region: str = Field(description="地域参数，如ap-shanghai"),
    topic_id: str = Field(description="日志主题ID"),
    b_time: str = Field(description="日志时间，格式：YYYY-mm-dd HH:MM:SS.FFF"),
    pkg_id: str = Field(description="日志包序号"),
    pkg_log_id: int = Field(description="日志包内一条日志的序号"),
    prev_logs: Optional[int] = Field(default=10, description="前N条日志，默认10"),
    next_logs: Optional[int] = Field(default=10, description="后N条日志，默认10"),
    query: Optional[str] = Field(
        default=None, description="检索语句，对日志上下文进行过滤"
    ),
    from_time: Optional[int] = Field(
        default=None, description="上下文检索开始时间，毫秒级时间戳"
    ),
    to_time: Optional[int] = Field(
        default=None, description="上下文检索结束时间，毫秒级时间戳"
    ),
) -> str:
    """
    腾讯云日志服务上下文检索工具。

    该工具调用腾讯云CLS DescribeLogContext接口，实现日志上下文检索功能。

    Args:
        secret_id: 腾讯云访问密钥ID
        secret_key: 腾讯云访问密钥Key
        region: 腾讯云地域
        topic_id: 要查询的日志主题ID
        b_time: 日志时间，UTC+8时区格式
        pkg_id: 日志包序号
        pkg_log_id: 日志包内日志序号
        prev_logs: 前N条日志数量
        next_logs: 后N条日志数量
        query: 可选的检索过滤语句
        from_time: 可选的检索开始时间
        to_time: 可选的检索结束时间

    Returns:
        JSON格式的日志上下文检索结果

    Raises:
        ToolError: API调用失败时抛出的异常
    """
    try:
        cred = credential.Credential(secret_id, secret_key)

        httpProfile = HttpProfile()
        httpProfile.endpoint = "cls.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = cls_client.ClsClient(cred, region, clientProfile)

        req = models_2020.DescribeLogContextRequest()
        params = {
            "TopicId": topic_id,
            "BTime": b_time,
            "PkgId": pkg_id,
            "PkgLogId": pkg_log_id,
            "PrevLogs": prev_logs,
            "NextLogs": next_logs,
        }

        if query is not None:
            params["Query"] = query
        if from_time is not None:
            params["From"] = from_time
        if to_time is not None:
            params["To"] = to_time

        req.from_json_string(json.dumps(params))

        resp = client.DescribeLogContext(req)
        return resp.to_json_string()

    except TencentCloudSDKException as e:
        raise ToolError(f"腾讯云API调用失败: {str(e)}")
    except Exception as e:
        raise ToolError(f"日志上下文检索执行时发生错误: {str(e)}")

# ==========================================
# 时间戳工具
# ==========================================


@mcp.tool(description="获取当前时间的Unix时间戳，精确到秒")
async def get_unix_timestamp_seconds() -> str:
    """
    获取当前时间的Unix时间戳（秒级）。

    返回当前时间对应的Unix时间戳，单位为秒。
    示例返回值：1611650000

    Returns:
        str: Unix时间戳（秒），如：1611650000
    """
    import time

    try:
        # 获取当前时间的Unix时间戳（秒）
        timestamp_seconds = int(time.time())

        return json.dumps(
            {
                "timestamp": timestamp_seconds,
                "unit": "seconds",
                "description": "Unix时间戳（秒级）",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        raise ToolError(f"获取Unix时间戳（秒）时发生错误: {str(e)}")


@mcp.tool(description="获取当前时间的Unix时间戳，精确到毫秒")
async def get_unix_timestamp_milliseconds() -> str:
    """
    获取当前时间的Unix时间戳（毫秒级）。

    返回当前时间对应的Unix时间戳，单位为毫秒。
    示例返回值：1619581700000

    Returns:
        str: Unix时间戳（毫秒），如：1619581700000
    """
    import time

    try:
        # 获取当前时间的Unix时间戳（毫秒）
        timestamp_milliseconds = int(time.time() * 1000)

        return json.dumps(
            {
                "timestamp": timestamp_milliseconds,
                "unit": "milliseconds",
                "description": "Unix时间戳（毫秒级）",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        raise ToolError(f"获取Unix时间戳（毫秒）时发生错误: {str(e)}")


# ==========================================
# 系统启动
# ==========================================


def signal_handler(signum, frame):
    """信号处理器，确保优雅退出"""
    sys.exit(0)


def main():
    """主函数"""
    global notification_enabled

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    mcp.run()


if __name__ == "__main__":
    main()

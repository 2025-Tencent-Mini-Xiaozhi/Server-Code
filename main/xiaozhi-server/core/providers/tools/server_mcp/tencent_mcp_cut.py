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
# 腾讯云CLS接口
# ==========================================

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

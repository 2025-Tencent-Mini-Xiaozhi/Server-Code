# MCP客户端自动获取集群列表功能说明

## 功能概述

MCP客户端现在支持在初始化完成后自动获取腾讯云TKE集群列表，**直接调用腾讯云API**而不依赖外部MCP工具，并提供了多个便捷的方法来访问和管理集群信息。

## 自动初始化流程

1. **客户端初始化** - MCP客户端建立连接并获取可用工具
2. **凭据检查** - 检查是否提供了`secret_id`和`secret_key`
3. **SDK验证** - 确认腾讯云SDK可用
4. **多地域扫描** - 直接调用腾讯云TKE API扫描常见地域获取集群列表
5. **缓存存储** - 将获取的集群信息缓存到客户端内存中

## 使用方法

### 1. 创建带有腾讯云凭据的MCP客户端

```python
from core.providers.tools.server_mcp.mcp_client import ServerMCPClient

# 创建MCP客户端时提供腾讯云凭据
config = {
    "command": "python",
    "args": ["path/to/tencent_mcp.py"]
}

mcp_client = ServerMCPClient(
    config=config,
    device_id="device-001",
    secret_id="AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    secret_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

# 初始化客户端（会自动获取集群列表）
await mcp_client.initialize()
```

### 2. 访问缓存的集群信息

```python
# 获取所有集群列表
clusters = mcp_client.get_cluster_list()
if clusters:
    print(f"共找到 {len(clusters)} 个集群")
    for cluster in clusters:
        print(f"  - {cluster['ClusterName']} ({cluster['ClusterId']})")

# 获取集群数量
count = mcp_client.get_cluster_count()
print(f"集群总数: {count}")

# 根据集群ID查找特定集群
cluster = mcp_client.get_cluster_by_id("cls-xxxxxxxxx")
if cluster:
    print(f"找到集群: {cluster['ClusterName']}")

# 获取原始JSON响应
raw_json = mcp_client.get_cluster_list_raw()

# 获取运行中的集群
running_clusters = mcp_client.get_running_clusters()
print(f"运行中的集群: {len(running_clusters)}")

# 根据名称查找集群
cluster = mcp_client.get_cluster_by_name("小智运维服务器")
if cluster:
    print(f"找到集群: {cluster['ClusterName']} - {cluster['ClusterVersion']}")

# 搜索集群
search_results = mcp_client.search_clusters("小智")
print(f"搜索到 {len(search_results)} 个包含'小智'的集群")

# 获取集群概要统计
summary = mcp_client.get_cluster_summary()
print(f"总集群数: {summary['total_count']}, 运行中: {summary['running_count']}")
print(f"K8s版本分布: {summary['k8s_versions']}")

# 打印详细的集群概要
mcp_client.print_cluster_summary()

# ==========================================
# 简化映射方法（推荐用于后续业务逻辑）
# ==========================================

# 获取集群ID到地域的映射（只包含核心信息）
cluster_map = mcp_client.get_cluster_map()
print(f"集群映射: {cluster_map}")  # {'cls-q11g1t9a': 'ap-guangzhou'}

# 根据集群ID获取地域
region = mcp_client.get_cluster_region("cls-q11g1t9a")
print(f"集群地域: {region}")  # ap-guangzhou

# 获取所有集群ID
cluster_ids = mcp_client.get_cluster_ids()
print(f"所有集群ID: {cluster_ids}")

# 获取所有地域
regions = mcp_client.get_regions()
print(f"覆盖地域: {regions}")

# 获取指定地域的集群
guangzhou_clusters = mcp_client.get_clusters_in_region("ap-guangzhou")
print(f"广州地域集群: {guangzhou_clusters}")

# 检查集群是否存在
exists = mcp_client.has_cluster("cls-q11g1t9a")
print(f"集群存在: {exists}")

# 打印简化映射信息
mcp_client.print_cluster_map()
```

### 3. 手动刷新集群列表

```python
# 手动刷新集群列表
success = await mcp_client.refresh_cluster_list()
if success:
    print("集群列表刷新成功")
else:
    print("集群列表刷新失败")
```

## 输出示例

### 初始化时的控制台输出

```
正在初始化MCP客户端连接...
MCP客户端准备就绪，开始等待关闭信号...
正在自动获取腾讯云TKE集群列表...
从地域 ap-guangzhou 获取到 1 个集群
✅ 自动获取集群列表成功，共找到 1 个集群
  📋 集群: 小智运维服务器 (cls-q11g1t9a)
     状态: Running | 地域: ap-guangzhou | 版本: 1.32.2
     类型: MANAGED_CLUSTER | 节点数: 3 | 系统: tlinux3.1x86_64
     容器运行时: containerd
     网络: VPC(vpc-6z8yfnj9) | 服务CIDR: 192.168.0.0/17
```

### 日志输出

```
INFO [mcp_client]: 开始自动获取集群列表...
INFO [mcp_client]: 从地域 ap-guangzhou 获取到 2 个集群
INFO [mcp_client]: 从地域 ap-shanghai 获取到 1 个集群
INFO [mcp_client]: 自动获取集群列表成功，共找到 3 个集群
INFO [mcp_client]: 集群信息 - 名称: production-cluster, ID: cls-abc12345, 状态: Running, 地域: ap-guangzhou
```

## API 方法参考

### 基础方法

### `get_cluster_list() -> Optional[List[Dict[str, Any]]]`
获取缓存的集群列表，返回包含所有集群信息的字典列表。

### `get_cluster_list_raw() -> Optional[str]` 
获取原始的集群列表JSON响应字符串。

### `get_cluster_count() -> int`
获取集群总数。

### `get_cluster_by_id(cluster_id: str) -> Optional[Dict[str, Any]]`
根据集群ID查找特定集群信息。

### `get_cluster_by_name(cluster_name: str) -> Optional[Dict[str, Any]]`
根据集群名称查找特定集群信息。

### `get_clusters_by_region(region: str) -> List[Dict[str, Any]]`
根据地域获取该地域的所有集群。

### `get_running_clusters() -> List[Dict[str, Any]]`
获取所有状态为"Running"的集群列表。

### `refresh_cluster_list() -> bool`
手动刷新集群列表，返回操作是否成功。

### 高级方法

### `get_cluster_summary() -> Dict[str, Any]`
获取集群概要统计信息，包括总数、运行中数量、地域分布、类型分布、版本分布等。

### `search_clusters(keyword: str) -> List[Dict[str, Any]]`
根据关键词搜索集群，会匹配集群名称和ID。

### `print_cluster_summary()`
在控制台打印格式化的集群概要统计信息。

## 简化映射方法（推荐）

### `get_cluster_map() -> Dict[str, str]`
获取集群ID到地域的映射字典。返回格式: `{cluster_id: region}`

### `get_cluster_region(cluster_id: str) -> Optional[str]`
根据集群ID获取对应的地域代码。

### `get_cluster_ids() -> List[str]`
获取所有集群ID的列表。

### `get_regions() -> List[str]`
获取所有地域的列表（已去重）。

### `get_clusters_in_region(region: str) -> List[str]`
获取指定地域中所有集群的ID列表。

### `has_cluster(cluster_id: str) -> bool`
检查指定的集群ID是否存在。

### `print_cluster_map()`
在控制台打印简化的集群映射信息，按地域分组显示。

## 集群信息结构

每个集群对象包含以下主要字段（基于实际腾讯云TKE响应）：

```python
{
    "ClusterId": "cls-q11g1t9a",              # 集群ID
    "ClusterName": "小智运维服务器",           # 集群名称
    "ClusterStatus": "Running",               # 集群状态
    "ClusterVersion": "1.32.2",              # Kubernetes版本
    "ClusterOs": "tlinux3.1x86_64",          # 操作系统
    "ClusterType": "MANAGED_CLUSTER",        # 集群类型
    "ClusterNodeNum": 3,                     # 节点数量
    "ContainerRuntime": "containerd",        # 容器运行时
    "RuntimeVersion": "1.6.9",              # 运行时版本
    "CreatedTime": "2025-08-18T09:00:16Z",   # 创建时间
    "ClusterLevel": "L5",                    # 集群等级
    "DeletionProtection": true,              # 删除保护
    "Region": "ap-guangzhou",                # 地域（自动添加）
    
    # 网络配置
    "ClusterNetworkSettings": {
        "ServiceCIDR": "192.168.0.0/17",     # 服务CIDR
        "VpcId": "vpc-6z8yfnj9",             # VPC ID
        "Subnets": ["subnet-oy8yu92u"],      # 子网列表
        "MaxClusterServiceNum": 32768,       # 最大服务数
        "MaxNodePodNum": 64,                 # 每节点最大Pod数
        "Cni": true,                         # CNI插件
        "Ipvs": false,                       # IPVS模式
        "IsDualStack": false                 # 双栈模式
    },
    
    # 其他字段...
    "AutoUpgradeClusterLevel": false,
    "ClusterDescription": "",
    "ProjectId": 0,
    "EnableExternalNode": false,
    "QGPUShareEnable": false
}
```

## 注意事项

1. **凭据要求**: 必须在创建MCP客户端时提供有效的`secret_id`和`secret_key`
2. **SDK依赖**: 需要安装腾讯云Python SDK (`tencentcloud-sdk-python`)
3. **地域扫描**: 自动扫描常见地域（ap-guangzhou, ap-shanghai, ap-beijing, ap-shenzhen），可能不包含所有地域
4. **缓存机制**: 集群信息缓存在内存中，重启后需要重新获取
5. **权限要求**: 腾讯云凭据需要有TKE集群的查看权限

## 错误处理

- 如果未提供腾讯云凭据，会跳过自动获取并记录日志
- 如果腾讯云SDK不可用，会记录警告并跳过
- 获取失败不会影响MCP客户端的正常初始化
- 所有错误都会被记录到日志中

## 集成示例

在智能体中使用集群信息：

```python
# 在智能体中访问集群列表
class ClusterInspectionAgent:
    def __init__(self, mcp_client, ...):
        self.mcp_client = mcp_client
        
    async def run_inspection(self):
        # 获取可用集群
        clusters = self.mcp_client.get_cluster_list()
        if not clusters:
            return "未找到可用的集群"
            
        # 对每个集群执行巡检
        for cluster in clusters:
            cluster_id = cluster["ClusterId"]
            cluster_name = cluster["ClusterName"]
            region = cluster["Region"]
            
            print(f"正在巡检集群: {cluster_name} ({cluster_id})")
            # 执行具体的巡检逻辑...
```

## 完整使用示例

```python
from core.providers.tools.server_mcp.mcp_client import ServerMCPClient

async def main():
    # 创建MCP客户端
    config = {
        "command": "python",
        "args": ["core/providers/tools/server_mcp/tencent_mcp.py"]
    }

    mcp_client = ServerMCPClient(
        config=config,
        device_id="device-001",
        secret_id="AKIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        secret_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    )

    # 初始化客户端（自动获取集群列表）
    await mcp_client.initialize()
    
    # 打印集群概要
    mcp_client.print_cluster_summary()
    
    # 获取运行中的集群
    running_clusters = mcp_client.get_running_clusters()
    print(f"\n🚀 发现 {len(running_clusters)} 个运行中的集群:")
    
    for cluster in running_clusters:
        cluster_name = cluster["ClusterName"]
        cluster_id = cluster["ClusterId"]
        version = cluster["ClusterVersion"]
        nodes = cluster["ClusterNodeNum"]
        
        print(f"  - {cluster_name} ({cluster_id})")
        print(f"    K8s版本: {version}, 节点数: {nodes}")
        
        # 获取网络信息
        if "ClusterNetworkSettings" in cluster:
            network = cluster["ClusterNetworkSettings"]
            vpc_id = network.get("VpcId", "Unknown")
            service_cidr = network.get("ServiceCIDR", "Unknown")
            max_pods = network.get("MaxNodePodNum", 0)
            
            print(f"    网络: VPC({vpc_id}), 服务CIDR: {service_cidr}")
            print(f"    每节点最大Pod数: {max_pods}")
    
    # 搜索特定集群
    search_results = mcp_client.search_clusters("小智")
    if search_results:
        print(f"\n🔍 搜索到包含'小智'的集群: {len(search_results)}个")
        for cluster in search_results:
            print(f"  - {cluster['ClusterName']} ({cluster['ClusterId']})")
    
    # 获取详细统计
    summary = mcp_client.get_cluster_summary()
    print(f"\n📊 集群统计详情:")
    print(f"  总数: {summary['total_count']}")
    print(f"  运行中: {summary['running_count']}")
    print(f"  总节点数: {summary['total_nodes']}")
    print(f"  覆盖地域: {summary['regions']}")
    print(f"  集群类型: {summary['cluster_types']}")
    print(f"  K8s版本: {summary['k8s_versions']}")
    
    # 清理资源
    await mcp_client.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 预期输出示例

```
正在自动获取腾讯云TKE集群列表...
从地域 ap-guangzhou 获取到 1 个集群
✅ 自动获取集群列表成功，共找到 1 个集群
🗂️  集群映射: {'cls-q11g1t9a': 'ap-guangzhou'}
  📋 集群: 小智运维服务器 (cls-q11g1t9a)
     状态: Running | 地域: ap-guangzhou | 版本: 1.32.2
     类型: MANAGED_CLUSTER | 节点数: 3 | 系统: tlinux3.1x86_64
     容器运行时: containerd
     网络: VPC(vpc-6z8yfnj9) | 服务CIDR: 192.168.0.0/17

📊 集群概要统计:
  总集群数: 1
  运行中: 1
  总节点数: 3
  覆盖地域: ap-guangzhou
  集群类型分布:
    - MANAGED_CLUSTER: 1个
  K8s版本分布:
    - 1.32.2: 1个

🚀 发现 1 个运行中的集群:
  - 小智运维服务器 (cls-q11g1t9a)
    K8s版本: 1.32.2, 节点数: 3
    网络: VPC(vpc-6z8yfnj9), 服务CIDR: 192.168.0.0/17
    每节点最大Pod数: 64

🔍 搜索到包含'小智'的集群: 1个
  - 小智运维服务器 (cls-q11g1t9a)

📊 集群统计详情:
  总数: 1
  运行中: 1
  总节点数: 3
  覆盖地域: ['ap-guangzhou']
  集群类型: {'MANAGED_CLUSTER': 1}
  K8s版本: {'1.32.2': 1}

🗂️  集群映射 (共1个):
  - cls-q11g1t9a → ap-guangzhou

集群映射: {'cls-q11g1t9a': 'ap-guangzhou'}
集群地域: ap-guangzhou
所有集群ID: ['cls-q11g1t9a']
覆盖地域: ['ap-guangzhou']
广州地域集群: ['cls-q11g1t9a']
集群存在: True
```

这个功能大大简化了集群管理工作流程，让智能体和其他工具能够自动发现和操作用户的TKE集群。

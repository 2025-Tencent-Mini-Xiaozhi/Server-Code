# 小智服务器告警推送接口文档

## 概述

小智服务器提供了一个HTTP告警推送接口，用于接收来自各种监控系统的告警信息。该接口会详细记录所有接收到的请求信息，便于分析和调试。

## 接口地址

- **告警推送接口**: `http://你的服务器IP:8003/api/alert/webhook`
- **接口信息查询**: `http://你的服务器IP:8003/api/alert/info`

## 支持的HTTP方法

- GET
- POST  
- PUT
- PATCH
- OPTIONS

## 支持的内容类型

- `application/json` - JSON格式数据
- `application/x-www-form-urlencoded` - 表单数据
- `multipart/form-data` - 多部分表单数据（支持文件上传）
- `text/plain` - 纯文本数据
- 其他任意格式

## 功能特性

✅ **全方位记录**: 自动记录请求方法、路径、查询参数、请求头、请求体等所有信息  
✅ **多格式支持**: 支持JSON、表单、文本等多种数据格式  
✅ **实时日志**: 控制台和日志文件双重输出，便于实时监控  
✅ **错误处理**: 完善的异常处理机制  
✅ **跨域支持**: 内置CORS支持  

## 使用示例

### 1. JSON格式告警推送

```bash
curl -X POST "http://127.0.0.1:8003/api/alert/webhook" \
  -H "Content-Type: application/json" \
  -H "User-Agent: AlertSystem/1.0" \
  -H "X-Alert-Source: CloudMonitor" \
  -d '{
    "alert_type": "cpu_high",
    "severity": "warning", 
    "server": "web-server-01",
    "message": "CPU使用率超过80%",
    "timestamp": "2025-08-29T09:50:00Z",
    "metrics": {
      "cpu_usage": 85.3,
      "memory_usage": 67.2
    }
  }'
```

### 2. 表单格式告警推送

```bash
curl -X POST "http://127.0.0.1:8003/api/alert/webhook?source=prometheus&env=production" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "User-Agent: PrometheusAlertManager/0.24.0" \
  -H "X-Alert-ID: alert-12345" \
  -d "alert_name=HighMemoryUsage&severity=critical&instance=server-02&value=92.5"
```

### 3. 文本格式告警推送

```bash
curl -X PUT "http://127.0.0.1:8003/api/alert/webhook" \
  -H "Content-Type: text/plain" \
  -H "X-Alert-System: CustomMonitor" \
  -d "ALERT: Database connection failed at 2025-08-29 09:55:00. Please check the database server."
```

### 4. GET方法告警推送（适用于简单的webhook回调）

```bash
curl -X GET "http://127.0.0.1:8003/api/alert/webhook?alert=test&status=resolved&time=1693302000"
```

## 响应格式

### 成功响应

```json
{
  "status": "success",
  "message": "告警推送已接收",
  "timestamp": "2025-08-29T09:53:45.272538",
  "received_data": {
    "method": "POST",
    "content_type": "application/json", 
    "has_query_params": false,
    "has_request_body": true
  }
}
```

### 错误响应

```json
{
  "status": "error",
  "message": "处理告警推送时发生错误: 具体错误信息",
  "timestamp": "2025-08-29T09:53:45.272538"
}
```

## 日志输出

接口会在控制台和日志文件中输出详细信息：

```
[告警推送] ========== 收到新的告警推送 ==========
[告警推送] 时间: 2025-08-29T09:53:45.272052
[告警推送] 方法: POST
[告警推送] 路径: /api/alert/webhook
[告警推送] 来源IP: 127.0.0.1
[告警推送] Content-Type: application/json
[告警推送] 请求体: {'alert_type': 'cpu_high', 'severity': 'warning', 'server': 'web-server-01', 'message': 'CPU使用率超过80%'}
[告警推送] =======================================
```

## 常见监控系统集成

### Prometheus + AlertManager

在AlertManager配置中添加webhook：

```yaml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'xiaozhi-webhook'

receivers:
- name: 'xiaozhi-webhook'
  webhook_configs:
  - url: 'http://你的服务器IP:8003/api/alert/webhook'
    send_resolved: true
```

### Zabbix

在Zabbix中创建媒体类型，设置webhook URL为：
`http://你的服务器IP:8003/api/alert/webhook`

### 自定义监控脚本

```python
import requests

def send_alert_to_xiaozhi(alert_data):
    url = "http://你的服务器IP:8003/api/alert/webhook"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "CustomMonitor/1.0"
    }
    
    response = requests.post(url, json=alert_data, headers=headers)
    return response.json()
```

## 查看接口状态

```bash
curl -X GET "http://127.0.0.1:8003/api/alert/info"
```

## 注意事项

1. **端口配置**: 默认端口为8003，请确保防火墙已开放该端口
2. **网络访问**: 如果从外网访问，请将127.0.0.1替换为实际的服务器IP地址
3. **日志监控**: 建议定期查看日志文件以监控告警推送情况
4. **编码支持**: 支持UTF-8编码，可以处理中文告警信息

## 测试脚本

项目中提供了完整的测试脚本 `test_alert_api.py`，可以运行测试各种告警格式：

```bash
cd /path/to/xiaozhi-server
python3 test_alert_api.py
```

该脚本会自动测试JSON、表单、文本等多种格式的告警推送，验证接口功能。

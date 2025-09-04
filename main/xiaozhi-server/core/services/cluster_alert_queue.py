#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集群告警队列管理器

实现生产者消费者模型，用于处理不同集群的告警：
1. 按集群ID分类存储告警
2. 生产者接收告警并放入对应队列
3. 消费者从队列中取出告警进行处理
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict, deque
from config.logger import setup_logging

TAG = __name__

class ClusterAlertQueue:
    """集群告警队列管理器"""
    
    def __init__(self, max_queue_size: int = 1000):
        """初始化告警队列管理器
        
        Args:
            max_queue_size: 每个集群队列的最大大小
        """
        self.logger = setup_logging()
        self.max_queue_size = max_queue_size
        
        # 按集群ID存储原始告警数据队列
        self.alert_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))
        
        # 统计信息
        self.stats = {
            'total_produced': 0,
            'total_consumed': 0,
            'clusters_with_alerts': set(),
            'start_time': time.time()
        }
        
        self.logger.bind(tag=TAG).info(f"集群告警队列管理器初始化完成，最大队列大小: {max_queue_size}")

    def produce_alert(self, webhook_data: Dict[str, Any]) -> bool:
        """生产告警（直接存储原始webhook数据到队列）
        
        Args:
            webhook_data: webhook原始数据
            
        Returns:
            bool: 是否成功加入队列
        """
        try:
            # 从原始数据中提取集群ID
            cluster_id = self._extract_cluster_id(webhook_data)
            if not cluster_id:
                self.logger.bind(tag=TAG).warning("无法从webhook数据中提取集群ID")
                return False
            
            # 直接将原始数据加入对应集群的队列
            self.alert_queues[cluster_id].append(webhook_data)
            
            # 更新统计
            self.stats['total_produced'] += 1
            self.stats['clusters_with_alerts'].add(cluster_id)
            
            # 提取基本信息用于日志
            alert_id = webhook_data.get('request_body', {}).get('alertId', 'unknown')
            policy_name = webhook_data.get('request_body', {}).get('alarmPolicyInfo', {}).get('policyName', 'unknown')
            
            self.logger.bind(tag=TAG).info(
                f"原始告警已加入队列 - 集群: {cluster_id}, 告警ID: {alert_id}, 策略: {policy_name}"
            )
            
            print(f"📥 原始告警已入队: {cluster_id} | {alert_id} | {policy_name}", flush=True)
            return True
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"生产告警时发生错误: {e}")
            return False

    def _extract_cluster_id(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """从webhook数据中提取集群ID
        
        Args:
            webhook_data: webhook原始数据
            
        Returns:
            Optional[str]: 集群ID，如果提取失败则返回None
        """
        try:
            request_body = webhook_data.get('request_body', {})
            dimensions = request_body.get('alarmObjInfo', {}).get('dimensions', {})
            obj_id = dimensions.get('objId', '')
            
            # 从objId中提取集群ID (格式: ...#cls-xxxxx#...)
            if '#cls-' in obj_id:
                parts = obj_id.split('#')
                for part in parts:
                    if part.startswith('cls-'):
                        return part
            
            return None
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"提取集群ID时发生错误: {e}")
            return None

    async def consume_alerts(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """消费指定集群的告警
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            Optional[Dict[str, Any]]: 原始告警数据，如果队列为空则返回None
        """
        try:
            if cluster_id in self.alert_queues and self.alert_queues[cluster_id]:
                raw_alert = self.alert_queues[cluster_id].popleft()
                self.stats['total_consumed'] += 1
                
                # 提取告警ID用于日志
                alert_id = raw_alert.get('request_body', {}).get('alertId', 'unknown')
                
                self.logger.bind(tag=TAG).info(
                    f"原始告警已消费 - 集群: {cluster_id}, 告警ID: {alert_id}"
                )
                
                return raw_alert
            return None
            
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"消费集群 {cluster_id} 告警时发生错误: {e}")
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态信息"""
        cluster_status = {}
        total_alerts = 0
        
        for cluster_id, queue in self.alert_queues.items():
            queue_size = len(queue)
            cluster_status[cluster_id] = {
                'queue_size': queue_size,
                'max_size': queue.maxlen
            }
            total_alerts += queue_size
        
        runtime = time.time() - self.stats['start_time']
        
        return {
            'total_alerts_in_queues': total_alerts,
            'cluster_count': len(self.alert_queues),
            'cluster_status': cluster_status,
            'stats': {
                'total_produced': self.stats['total_produced'],
                'total_consumed': self.stats['total_consumed'],
                'clusters_with_alerts': len(self.stats['clusters_with_alerts']),
                'runtime_seconds': runtime
            }
        }

    def print_status(self):
        """打印队列状态"""
        status = self.get_queue_status()
        
        print(f"\n📊 告警队列状态报告", flush=True)
        print(f"=" * 50, flush=True)
        print(f"队列中总告警数: {status['total_alerts_in_queues']}", flush=True)
        print(f"涉及集群数: {status['cluster_count']}", flush=True)
        print(f"已生产告警: {status['stats']['total_produced']}", flush=True)
        print(f"已消费告警: {status['stats']['total_consumed']}", flush=True)
        print(f"运行时间: {status['stats']['runtime_seconds']:.1f}秒", flush=True)
        
        if status['cluster_status']:
            print(f"\n📋 各集群队列状态:", flush=True)
            for cluster_id, cluster_info in status['cluster_status'].items():
                queue_size = cluster_info['queue_size']
                max_size = cluster_info['max_size']
                print(f"  {cluster_id}: {queue_size}/{max_size} 告警", flush=True)

    def get_queue_size(self, cluster_id: str) -> int:
        """获取指定集群的队列大小
        
        Args:
            cluster_id: 集群ID
            
        Returns:
            int: 队列中的告警数量
        """
        return len(self.alert_queues.get(cluster_id, []))

    def get_all_cluster_ids(self) -> List[str]:
        """获取所有有告警的集群ID列表
        
        Returns:
            List[str]: 集群ID列表
        """
        return list(self.alert_queues.keys())

    def print_status(self):
        """打印队列状态信息"""
        if not hasattr(self, '_last_status_time'):
            self._last_status_time = 0
            
        current_time = time.time()
        if current_time - self._last_status_time < 30:  # 最多30秒打印一次
            return
            
        self._last_status_time = current_time
        
        total_alerts = sum(len(q) for q in self.alert_queues.values())
        runtime = current_time - self.stats['start_time']
        
        print(f"\n📊 告警队列状态报告", flush=True)
        print(f"{'='*50}", flush=True)
        print(f"队列中总告警数: {total_alerts}", flush=True)
        print(f"涉及集群数: {len(self.alert_queues)}", flush=True)
        print(f"已生产告警: {self.stats['total_produced']}", flush=True)
        print(f"已消费告警: {self.stats['total_consumed']}", flush=True)
        print(f"运行时间: {runtime:.1f}秒", flush=True)
        
        if self.alert_queues:
            print(f"\n📋 各集群队列状态:", flush=True)
            for cluster_id, queue in self.alert_queues.items():
                print(f"  {cluster_id}: {len(queue)}/{self.max_queue_size} 告警", flush=True)

# 全局告警队列管理器实例
alert_queue_manager = ClusterAlertQueue()

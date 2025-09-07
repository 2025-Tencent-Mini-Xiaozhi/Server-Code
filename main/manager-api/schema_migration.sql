-- 数据库结构升级脚本
-- 将 schema_old 升级到 schema_new 的结构

-- 1. 修改 ai_agent_plugin_mapping 表的 AUTO_INCREMENT 起始值
ALTER TABLE `ai_agent_plugin_mapping` AUTO_INCREMENT = 1963436486688780293;

-- 2. 为 sys_user 表添加新字段
ALTER TABLE `sys_user` ADD COLUMN `real_name` varchar(100) DEFAULT 'root' COMMENT '用户姓名';
ALTER TABLE `sys_user` ADD COLUMN `secret_id` varchar(255) DEFAULT 'root' COMMENT '腾讯云secret_id';
ALTER TABLE `sys_user` ADD COLUMN `secret_key` varchar(255) DEFAULT 'root' COMMENT '腾讯云secret_key';
ALTER TABLE `sys_user` ADD COLUMN `face_encoding` text;
ALTER TABLE `sys_user` ADD COLUMN `face_image_path` varchar(500) DEFAULT NULL;
ALTER TABLE `sys_user` ADD COLUMN `face_registered_at` datetime DEFAULT NULL;
ALTER TABLE `sys_user` ADD COLUMN `face_enabled` tinyint(1) DEFAULT '0';

-- 3. 创建 sys_schedule 表（该表在 old 版本中不存在）
CREATE TABLE `sys_schedule` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '日程ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `content` varchar(500) NOT NULL COMMENT '日程内容',
  `schedule_date` date NOT NULL COMMENT '日程日期',
  `status` tinyint(1) NOT NULL DEFAULT '0' COMMENT '状态 0-未完成 1-已完成',
  `creator` bigint DEFAULT NULL COMMENT '创建者',
  `create_date` datetime DEFAULT NULL COMMENT '创建时间',
  `updater` bigint DEFAULT NULL COMMENT '更新者',
  `update_date` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_schedule_date` (`schedule_date`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_schedule_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1963450307880955906 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户日程表';

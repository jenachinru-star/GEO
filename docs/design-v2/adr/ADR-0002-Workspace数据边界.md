# ADR-0002：Workspace 数据边界

状态：Accepted  
日期：2026-09-14

## 问题

仅依赖 user_id 无法支持医生助理/医院团队；旧全局表又造成跨用户泄漏。

## 选择

所有 V2 业务数据归属 Workspace；User 只表示身份，WorkspaceMember 表示 owner/editor/reviewer/viewer 授权。

## 理由

个人用户可自动拥有一个个人 Workspace，不增加操作负担；未来团队协作无需再次整体修改所有权。

## 约束

- 普通业务 Repository 必须要求 workspace_id；
- Workspace 表存在不等于隔离完成；
- 客户端传入 workspace_id 必须验证成员关系；
- 旧无法识别所有者的数据不自动分配。

## 风险

比直接补 user_id 多一张成员表和上下文处理。通过自动默认 Workspace 与统一依赖控制复杂度。

## 重新评估条件

如果产品永久只允许本人使用且明确不支持任何协作，也保留 Workspace，因为它仍是安全边界和数据导出/删除单元。

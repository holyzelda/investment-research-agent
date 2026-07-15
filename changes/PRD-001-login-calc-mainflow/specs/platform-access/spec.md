# 能力规格：platform-access（平台接入与承接）

> 来源：PRD US-0.1（2026-07-04 变更）。本系统**不做**登录/用户/权限；承接平台跳转、落地对话首页；身份经平台/网关注入请求头、后端直接信任读取。

## ADDED Requirements

### Requirement: 平台跳转承接落地对话首页

The system SHALL 承接统一平台首页的跳转入口，用户点击进入后**直接落到本系统对话首页**（US-1.2 的首页对话工作台），中间无本系统的登录环节。

#### Scenario: 平台跳转承接

- **GIVEN** 用户已在平台首页登录
- **WHEN** 点击进入"朱雀投研智能体"并跳转到本系统入口 URL
- **THEN** 直接进入本系统对话首页，无需再次登录

### Requirement: 不实现登录/用户/权限

The system SHALL NOT 实现登录页、注册、图形验证码、用户管理、角色/权限（RBAC）任何界面或后台——这些由统一平台首页承担。

#### Scenario: 走查无登录/用户/权限模块

- **GIVEN** 一阶段范围
- **WHEN** 走查系统前后端功能
- **THEN** 本系统内不存在登录页、注册、验证码、用户管理、权限管理模块与对应接口

### Requirement: 后端从请求头读取身份并归属快照

The system SHALL 以轻量中间件/依赖从转发进来的请求头读取用户标识（`user_id`、`username`），header 字段名可经配置指定（默认待与平台约定），并注入 `request.state`（如 `request.state.user_id/username`）供下游快照 `conversation` 归属；**直接信任、不做 token 二次校验、不依赖外部登录态存储**。当 header 缺失时按可配策略处理（默认：开发放行匿名占位、生产按约定字段必填）。

#### Scenario: 读取注入身份

- **GIVEN** 请求头包含平台注入的用户标识字段
- **WHEN** 请求到达本系统后端受理接口
- **THEN** 后端解析出 user_id/username 并注入 `request.state`，测算生成的 `conversation` 快照归属到该用户

#### Scenario: 不做二次校验

- **WHEN** 处理任意业务请求
- **THEN** 后端不进行 token 校验、不访问外部登录态存储，仅信任 header 中的身份字段

### Requirement: header 字段名可配

The system SHALL 通过配置（Nacos / 环境变量）指定平台注入的 header 字段名（user_id、username 两项），以便在与平台确定确切字段名后无需改代码即可对接。

#### Scenario: 字段名切换

- **WHEN** 平台约定的 header 字段名确定并写入配置
- **THEN** 后端按新字段名读取身份，无需修改源码

### Requirement: 视觉风格与平台统一

The system SHALL 使本系统整体 UI 风格对齐 trader 的 XC 玄策设计体系（`--xc-*` token、品牌青→紫、涨红跌绿、`.xc-*` 组件），与平台首页观感一致；不单独设计异构风格的登录/用户界面。

#### Scenario: 风格统一

- **GIVEN** 用户进入本系统任意页面
- **WHEN** 页面加载
- **THEN** 视觉风格与 trader / 平台一致（XC 玄策体系），非独立异构风格

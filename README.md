# 微信个人增量备份系统

一个面向个人和家庭服务器/NAS 的自托管微信聊天记录归档系统。

项目目标是：多个微信账号通过 Web 管理，用户手动点击同步后，系统启动对应 Runtime，读取微信数据并增量归档到自己的存储中，再通过只读 Web 界面浏览和搜索历史记录。

## 当前状态

项目当前处于 **Phase 0 真实来源验证 + Phase 1 Import-first 归档核心实现**阶段，还没有开始实现完整的同步服务或 Web UI。

当前最高优先级是验证：

```text
微信 Runtime
  -> 登录态持久化
  -> 数据目录访问
  -> 数据库读取/解密
  -> 联系人、会话、文本消息
  -> 至少一种媒体
```

当前 V1 实现路线暂定为离线导入优先：归档核心只接收版本化导入包，不依赖 Linux Docker Runtime 的内部数据库。Linux Runtime、外置 Windows Agent 和真实数据导入仍需单独完成来源验证，不能视为已支持的真实微信同步功能。

## 产品边界

- 多微信账号；
- 用户点击后才同步；
- 首次全量归档，后续可靠增量归档；
- SQLite + FTS5 + 本地媒体文件；
- Append-only，微信删除不会自动删除 Archive；
- Web 只读浏览、搜索和媒体查看；
- Docker Compose 单机部署；
- 默认同一时间只同步一个账号；
- V1 不做定时同步、消息发送、实时监听、AI 和多人协作。

## 文档入口

- [项目计划表](./项目计划表.md)：按阶段、任务和验收条件拆分的执行清单；
- [P0 技术可行性验证报告](./docs/p0-feasibility-report.md)：当前主机基线、验证结论和下一步证据要求；
- [P0 隔离测试账号记录模板](./docs/p0-test-account-record.template.md)：在仓库外记录测试账号和 Runtime 信息；
- [P0 Runtime 验证运行手册](./docs/p0-runtime-validation-runbook.md)：启动固定候选 Runtime、扫码和回填验证证据；
- [P0 一次性 Compose 配置](./docs/p0-runtime-compose.yaml)：仅用于 Phase 0 验证，不是生产部署配置；
- [P0 Runtime 路线评估](./docs/p0-route-assessment.md)：Linux Runtime、Windows Agent 和离线导入的阶段性判断；
- [Import-first 实现路线](./docs/import-first-architecture.md)：当前 Ubuntu-only 条件下的归档核心边界和验证方式；
- [技术架构与可执行开发计划](./微信个人增量备份系统——技术架构与可执行开发计划.md)：完整架构、数据模型、同步流程、API、部署和风险说明。

## 开发顺序

```text
Phase 0  技术验证闸门
   ->
Phase 1  归档数据库与 Fixture
   ->
Phase 2  手动增量同步引擎
   ->
Phase 3  API 与同步状态
   ->
Phase 4  只读 Web 客户端
   ->
Phase 5  Docker 与低资源部署
   ->
Phase 6  V1 稳定化
```

## 设计原则

1. 先验证数据链路，再开发完整 UI。
2. 微信源数据只读，归档数据独立保存。
3. 增量同步宁可回看和重复扫描，也不要漏消息。
4. 同步任务必须幂等、可重试、可恢复、可观察。
5. 适配器隔离微信版本差异，归档层不绑定源库表名。
6. 低配置部署优先，不引入不必要的微服务和基础设施。
7. 不把未验证的社区 Runtime 或解密方案写成稳定依赖。

## 开发前置

开始 P0 前准备：

- 目标服务器架构和系统信息；
- Docker 版本；
- 候选微信 Runtime；
- 隔离测试账号；
- 可用于保存脱敏 fixture 的测试目录。

P0 的验证结果应记录到：

```text
docs/p0-feasibility-report.md
```

原始日志、截图、微信数据、媒体和填写后的测试账号记录必须保存在仓库外或被 Git 忽略的本地目录中。

## 许可证与风险

当前仓库处于早期规划阶段，许可证和 Runtime 依赖尚未最终确定。使用任何第三方微信 Runtime、Hook、解析器或数据库工具前，应单独核查其许可证、账号安全风险、版本兼容性和目标平台支持情况。

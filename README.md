# 微信个人增量备份系统

一个面向个人和家庭服务器/NAS 的自托管微信聊天记录归档系统。

项目目标是：多个微信账号通过 Web 管理，用户手动点击同步后，系统启动对应 Runtime，读取微信数据并增量归档到自己的存储中，再通过只读 Web 界面浏览和搜索历史记录。

## 当前状态

项目当前处于 **Phase 0 真实来源验证 + Phase 2 Import-first 同步编排 + Phase 3 API/Phase 4 Web 子集**阶段，已具备离线导入、归档查询、基础账号管理 API 和只读 Dashboard，但还没有接入真实微信来源。

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

当前可运行的 API 包括：

- `GET /healthz`：服务、归档数据库和基础统计；
- `GET/POST/PATCH/DELETE /api/v1/accounts`：账号管理，删除需要显式 `confirm=true`；
- `GET /api/v1/accounts/{account_id}/conversations`：分页会话列表；
- `GET /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages`：分页消息和附件元数据；
- `GET /api/v1/accounts/{account_id}/attachments/{attachment_id}/content`：受账号范围约束的媒体读取；
- `GET /api/v1/search?account_id=...&q=...`：账号范围内的 FTS5 搜索；
- `POST /api/v1/accounts/{account_id}/sync/import`：手动执行预配置导入根目录下的指定包；
- `GET /api/v1/sync/jobs/{job_id}`、`GET /api/v1/accounts/{account_id}/sync/jobs`：读取导入同步任务结果；
- `GET /api/v1/sync/jobs/{job_id}/events`、`POST /api/v1/sync/jobs/{job_id}/cancel`：读取事件和请求取消 Import-first 任务。

API 默认使用 `data/archive.db`、`data` 媒体目录和 `imports` 导入根目录，可通过 `WECHAT_ARCHIVE_DB`、`WECHAT_ARCHIVE_ROOT`、`WECHAT_IMPORT_ROOT` 调整。同步 API 只接受导入根目录下的相对包名，会拒绝绝对路径、路径穿越和符号链接逃逸。

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
- [Docker 部署配置](./deploy/compose.yaml)：单容器 API + 静态 Web、`/data` 归档卷和只读 `imports` 卷；
- [部署安全边界](./docs/deployment-security.md)：Docker Socket、导入卷、媒体路径和当前认证限制；
- [数据迁移手册](./docs/data-migration-runbook.md)：SQLite+媒体快照、恢复、升级和回滚；
- [合成演示数据](./docs/demo-data.md)：手动创建可浏览、可搜索并带媒体的纯虚构样本；
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

本地启动基础 API：

```bash
python -m uvicorn backend.app.main:app --reload
```

导入包仍建议先通过 CLI 或 `SyncOrchestrator` 执行，再从 API 浏览归档数据。API 当前不接受任意客户端文件路径，也不伪造 Runtime 启停和扫码状态。

Docker 启动：

```bash
mkdir -p data imports
docker compose -f deploy/compose.yaml up -d --build
```

默认访问 `http://localhost:8000`。归档数据库和媒体写入 `data/`，导入包从只读的 `imports/` 挂载读取。

基础维护命令：

```bash
python tools/archive_health.py --database data/archive.db --archive-root data --pretty
python tools/rebuild_fts.py --database data/archive.db
```

需要展示完整页面时，可按[合成演示数据说明](./docs/demo-data.md)手动生成专用样本账号；部署和首次启动默认不会导入示例内容。

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

# Import-first 实现路线

最后更新：2026-09-21

当前只有 Ubuntu 环境，项目采用以下实现决策：

> V1 先实现与微信 Runtime 解耦的离线导入与归档核心；真实微信数据来源以后通过 `Import Adapter` 接入。

## 当前边界

- `archive_core` 只接收版本化导入包，不读取或解密微信内部数据库；
- 合成 fixture 用于验证归档库、幂等、媒体去重和全文搜索；
- Linux Docker Runtime 保留为未来候选 `Runtime Adapter`，当前不能作为稳定消息来源；
- Windows Agent 和真实导入包属于后续适配验证，不阻塞归档核心开发；
- 当前不提供“Ubuntu 上自动读取真实微信聊天记录”的承诺。

## 已实现的归档核心

入口位于 [`archive_core`](../archive_core)：

- SQLite WAL、外键和 FTS5 初始化；
- schema version 1 的可重复迁移入口；
- accounts、contacts、conversations、conversation_members、messages、attachments、sync_jobs、sync_checkpoints 表；
- 标准化 `Source*` DTO；
- `ImportAdapter` 协议边界和离线导入 CLI；
- 导入事务和失败回滚；
- `(account_id, source_msg_id)` 消息幂等；
- 按 SHA-256 的媒体文件去重；
- 多账号隔离；
- 全文搜索。

## 当前验证命令

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
python3 -B tools/archive_import.py tests/fixtures/import-v0-minimal \
  --db /tmp/archive.db --data /tmp/archive-data --account-id demo
```

测试只证明合成输入能够正确进入归档核心，不证明真实微信数据已经可读取。

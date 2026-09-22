# 归档核心与离线导入路径

最后更新：2026-09-21

当前只有 Ubuntu 环境，归档核心采用来源无关的标准 DTO 和离线包作为开发测试路径：

> 离线导入用于独立验证归档核心；产品目标仍是首次扫码登录成功后自动开始同步，真实数据来源必须通过经过验证的 Runtime/Source Adapter 接入。

## 当前边界

- `archive_core` 只接收版本化导入包，不读取或解密微信内部数据库；
- 合成 fixture 用于验证归档库、幂等、媒体去重和全文搜索；
- Linux Docker Runtime 保留为未来候选 `Runtime Adapter`，当前不能作为稳定消息来源；
- Windows Agent、Linux Runtime 数据读取和真实导入包仍属于来源适配验证；
- 当前不提供“扫码后自动同步真实微信聊天记录已可用”的承诺；
- 不做定时后台同步：自动触发仅发生在首次扫码登录成功，之后的增量同步由用户点击。

## 已实现的归档核心

入口位于 [`archive_core`](../archive_core)：

- SQLite WAL、外键和 FTS5 初始化；
- schema version 1 的可重复迁移入口；
- accounts、contacts、conversations、conversation_members、messages、attachments、sync_jobs、sync_checkpoints 表；
- 标准化 `Source*` DTO；
- `ImportAdapter` 协议边界和离线导入 CLI；
- Import-first 同步编排：进程内锁、sync job、checkpoint、失败状态和统计；

同步编排入口为 [`archive_core/sync.py`](../archive_core/sync.py)，当前只接受离线导入包，不启动或停止微信 Runtime。
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

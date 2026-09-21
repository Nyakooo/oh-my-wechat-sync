# 数据备份、迁移与恢复手册

当前归档数据由 SQLite 数据库和 `media/` 文件组成。迁移时应同时保存两者。

## 创建快照

先停止正在执行的同步任务，再运行：

```bash
python tools/archive_snapshot.py \
  --database data/archive.db \
  --archive-root data \
  --output backups/archive-YYYYMMDD-HHMMSS
```

工具使用 SQLite online backup API 复制数据库，并复制 `data/media/`。输出目录必须为空，避免覆盖旧快照。

## 恢复到新目录

1. 停止 Compose 服务：`docker compose -f deploy/compose.yaml down`；
2. 将快照中的 `archive.db` 和 `media/` 复制到新的 `/data` 目录；
3. 将导入包重新放入 `imports/`，确认该卷继续以只读方式挂载；
4. 启动服务并访问 `/healthz`；
5. 使用 `python tools/archive_health.py --database data/archive.db --archive-root data` 检查外键、缺失媒体和孤儿媒体。

应用启动时会执行已登记的 SQLite 迁移。升级前保留旧快照；如果升级后检查失败，停止服务并恢复整个快照目录，不要只恢复数据库而遗漏媒体文件。

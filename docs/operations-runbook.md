# 部署与日常运维手册

## 启动与升级

```bash
mkdir -p data imports
docker compose -f deploy/compose.yaml up -d --build
curl -fsS http://localhost:8000/healthz
```

升级前先创建快照。升级后检查 `/healthz`、Web 首页和归档健康报告：

```bash
python tools/archive_snapshot.py --database data/archive.db --archive-root data --output backups/archive-$(date +%Y%m%d-%H%M%S)
python tools/archive_health.py --database data/archive.db --archive-root data --pretty
```

## 常见问题

- 页面显示空账号：确认导入包位于 `imports/`，并通过 Import-first 同步 API 或 CLI 导入；
- 同步返回 `409`：已有任务持有全局锁，先查询任务状态，不要并发重复点击；
- 搜索没有结果：先运行 `python tools/rebuild_fts.py --database data/archive.db`，再检查健康报告；
- 媒体缺失：健康报告会列出 `missing_media`，先从完整快照恢复 `archive.db` 和 `media/`；
- 容器无法启动：查看 `docker compose -f deploy/compose.yaml logs archive`，确认端口、`data/` 权限和镜像构建日志；
- 真实微信同步不可用：这是当前明确限制，需要外部 Windows/真实脱敏导入样本，不能用合成 fixture 代替。

当前 API 没有认证和 HTTPS，服务只应放在内网、VPN 或额外认证反向代理之后。

# 合成演示数据

可以用专门的演示账号展示 Dashboard、多个会话、消息搜索和图片/文件附件。样本完全由程序生成，不包含真实微信账号、联系人或聊天记录。

本地开发环境：

```bash
python tools/seed_demo.py
```

Docker Compose 部署：

```bash
docker compose -f deploy/compose.yaml exec archive \
  python tools/seed_demo.py --database /data/archive.db --archive-root /data
```

之后刷新 Web 页面，打开“演示微信（全为虚构数据）”账号即可。样本包含两个会话、六条消息、关键词“weekend”以及一张 SVG 示意图和一个文本文件。

安全行为：

- 不会自动运行；
- 只创建单独的演示账号；
- 如果该账号 ID 已存在，会报错退出，不覆盖已有归档；
- 不会创建、访问或模拟登录任何微信 Runtime；
- 如需清理，请使用账号 API 的显式确认删除流程；不要直接删除整个 `/data` 目录。

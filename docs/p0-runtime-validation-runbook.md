# P0 Runtime 验证运行手册

本手册用于完成 P0-02～P0-06 的人工验证准备。它使用 WechatOnCloud 作为当前候选 Runtime，但不把 WechatOnCloud 作为归档系统依赖；正式项目仍通过 Runtime Adapter 隔离运行环境。

## 安全边界

- 只使用专用隔离测试账号，不使用最重要的主账号；
- 不把密码、二维码、微信数据库、聊天正文或原始媒体提交到 Git；
- 数据目录必须放在仓库外，或使用仓库已忽略的 `.p0-data/`；
- 本配置只绑定 `127.0.0.1:39012`，不直接暴露公网；
- 不挂载 Docker Socket，不运行 Archive 服务，不进行消息发送。

## 1. 准备隔离测试账号

由账号所有者在手机微信侧准备一个专用测试账号，并准备少量可控数据：

- 一个联系人或测试群；
- 至少一条文本消息；
- 至少一种媒体消息，例如图片或文件；
- 能够在测试完成后注销、重置或删除测试数据。

账号信息只记录在仓库外的本地副本中：

```text
docs/p0-test-account-record.template.md
```

不要把填写后的文件改名后放回仓库，也不要把二维码截图上传到项目。

## 2. 启动一次性 Runtime

在仓库根目录执行：

```bash
export P0_DATA_DIR="/srv/wechat-archive-p0/runtime"
docker compose -f docs/p0-runtime-compose.yaml up -d
docker compose -f docs/p0-runtime-compose.yaml ps
```

如果只是本机临时验证，也可以不设置 `P0_DATA_DIR`，默认数据会写入被 Git 忽略的 `.p0-data/runtime`。

检查 Web 页面：

```text
http://127.0.0.1:39012/
```

首次启动后，Runtime 可能显示“微信尚未安装”。执行官方微信包安装：

```bash
docker compose -f docs/p0-runtime-compose.yaml exec wechat-runtime /woc/wechat-ctl.sh install
docker compose -f docs/p0-runtime-compose.yaml exec wechat-runtime /woc/wechat-ctl.sh status
```

安装完成后刷新 Web 页面，确认出现二维码。扫码动作由账号所有者在手机微信上完成；本项目不代替用户输入验证码或确认登录。

注意：当前候选 Runtime 的安装脚本可能在已经成功写入微信文件和 `done` 状态后，仍因 `lock: unbound variable` 返回非零。必须以 `status`、`/config/wechat/.woc-version` 和微信进程共同判断结果，不要只依据安装命令退出码。

## 3. 验证登录态持久化

扫码成功后，只记录状态和版本，不记录二维码或聊天内容：

```bash
docker compose -f docs/p0-runtime-compose.yaml exec wechat-runtime /woc/wechat-ctl.sh status
docker compose -f docs/p0-runtime-compose.yaml logs --tail=100 wechat-runtime
```

然后执行一次停止和启动：

```bash
docker compose -f docs/p0-runtime-compose.yaml stop
docker compose -f docs/p0-runtime-compose.yaml start
```

记录以下结果：

| 检查项 | 结果 |
|---|---|
| 重启后 Runtime 可启动 | |
| 重启后是否仍显示已登录 | |
| 是否要求重新扫码 | |
| 数据目录是否仍为同一目录 | |
| 是否出现登录失效或异常退出 | |

如果无法恢复登录态，也要记录为明确失败边界，不要通过复制或修改未知文件来绕过验证。

## 4. 定位数据目录和源文件

确认宿主机数据目录只对应这个隔离账号：

```bash
find "${P0_DATA_DIR:?}" -maxdepth 3 -type f -printf '%p %s bytes\\n' | sort | sed -n '1,160p'
```

在容器内只查看路径和文件类型，不直接修改源文件：

```bash
docker compose -f docs/p0-runtime-compose.yaml exec wechat-runtime \
  sh -lc 'find /config -maxdepth 4 -type f -printf "%p %s bytes\\n" | sort | sed -n "1,200p"'
```

当前候选 Runtime 已观察到以下运行路径，但必须以实际测试结果为准：

```text
/config/wechat/                 微信安装文件
/config/xwechat_files/          微信运行数据候选路径
/config/.xwechat/               微信运行组件/状态候选路径
```

不要直接假设这些路径就是可归档消息数据库；P0-05/P0-06 必须由实际登录后的测试数据确认。

## 5. 验证结束后的清理

需要保留数据以继续验证时，只停止服务：

```bash
docker compose -f docs/p0-runtime-compose.yaml stop
```

确认不再需要测试数据后，再删除临时容器和数据目录。删除前必须先确认目标路径确实是隔离测试目录：

```bash
docker compose -f docs/p0-runtime-compose.yaml down
```

本手册不提供删除宿主机数据目录的命令，避免误删微信或其他项目数据。

## 6. 需要回填的 P0 证据

完成人工步骤后，将脱敏的结论回填到 `docs/p0-feasibility-report.md`：

- P0-02：确认使用隔离测试账号；
- P0-04：登录态是否可持久化；
- P0-05：实际源数据目录、权限和文件类型；
- P0-06：数据库是否加密，以及合法、稳定的只读读取方式。

原始日志、截图和数据文件留在仓库外，不要提交到 Git。

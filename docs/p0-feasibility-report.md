# P0 技术可行性验证报告

状态：进行中

最后更新：2026-09-20

本报告是 Phase 0 的证据记录。它只记录已经在当前工作区或测试主机上验证的事实；微信 Runtime、登录、源数据目录、数据库解密和媒体读取在获得专用测试环境前均不得视为已验证。

## 1. 当前结论

当前可以固定的测试目标是：

| 项目 | 当前目标值 | 状态 |
|---|---|---|
| CPU 架构 | `x86_64` | 已确认 |
| 操作系统 | Ubuntu 24.04.4 LTS | 已确认 |
| Docker Engine | 29.7.2 | 已确认 |
| Docker Compose | v5.4.0 | 已确认 |
| CPU | 4 vCPU | 已确认 |
| 内存 | 约 7.1 GiB 可见内存 | 已确认 |
| 微信版本 | `4.1.13.23` | 已确认 |
| 微信 Runtime | WechatOnCloud `1.4.9` amd64 digest | 已确认可启动，数据链路待验证 |
| 源数据目录 | `/config/xwechat_files`，宿主绑定到 `.p0-data/runtime/xwechat_files` | 已确认可只读访问 |
| 目标数据读取方式 | 部分 SQLite 可只读打开，但聊天消息库尚未确定 | 阻塞 |

因此 P0-01、P0-03、P0-04 和 P0-05 已有可复核证据。P0-04 的结果是“登录资料保留，但重启后需要手机再次完成登录”；P0-06 仍未满足稳定、可维护的读取条件。P0-02、P0-06 至 P0-12 尚未满足退出条件。

## 2. 已执行检查

检查时间：2026-09-20（Asia/Shanghai）

```text
uname -a
Linux aqanvgvthnskz0c 6.8.0-90-generic #91-Ubuntu SMP PREEMPT_DYNAMIC Tue Nov 18 14:14:30 UTC 2025 x86_64 x86_64 x86_64 GNU/Linux

/etc/os-release
PRETTY_NAME="Ubuntu 24.04.4 LTS"
VERSION_ID="24.04"
VERSION_CODENAME=noble

docker --version
Docker version 29.7.2, build a7dcaa6

docker compose version
Docker Compose version v5.4.0

docker info
Server=29.7.2; Storage=overlayfs; CPUs=4; Mem=7623725056
```

Docker CLI 能够访问 Docker Engine。当前仓库基线为：

```text
仓库：/home/admin/workspace/oh-my-wechat-sync
分支：master
HEAD：f555004 docs: record runtime candidate validation
工作区：检查时干净（本报告更新前）
```

## 3. 候选 Runtime 证据

本轮将 [WechatOnCloud](https://github.com/Gloridust/WechatOnCloud) 作为候选 A 进行验证。其公开文档描述的运行方式是 Linux 原生微信 + Xvfb + KasmVNC，并由面板按需管理实例；候选项目声称支持 `amd64` 和 `arm64`。这些资料只能证明候选存在，不能证明本项目的只读数据读取链路成立。

### 3.1 镜像 manifest

2026-09-20 在当前 Docker Engine 上查询到以下多架构 manifest：

```text
wechat-on-cloud:1.4.9
index digest: sha256:d6079c9b2b904fbdbec16b288535921369e826e334e0ea7b1a572b40b12b9a7c
linux/amd64: sha256:1718856505d4702041a86b084607b87bce180464bd77cbcd4545573887b32682
linux/arm64: sha256:fa95854a770dbc8b09b1f3b72095dcb047fe3c3656fb66c406f02ff988f079d5

woc-panel:1.4.9
index digest: sha256:2f7b4d7a2475c20ef08ff1b5ec96342ca5c8d028b9b97094f7b3ea22312d5a93
linux/amd64: sha256:80fb02e5792d3d83434ad71be9065b5a2a5d4628dff2cd2241340ef2e6a0a972
linux/arm64: sha256:4a997483b0360c5dd6f83b6774c2a55c18dec39b0567a7dbcfef9b59d468e181
```

当前主机是 `x86_64`，因此 P0 验证固定使用上述 `linux/amd64` digest，而不是 `latest` 标签。候选项目公开技术说明中的微信版本描述不是本项目的版本证据；本轮已在容器内从官方 CDN 安装并确认微信版本为 `4.1.13.23`。

### 3.2 镜像获取结果

曾按不可变 digest 两次执行：

```text
docker pull docker.io/gloridust/wechat-on-cloud@sha256:1718856505d4702041a86b084607b87bce180464bd77cbcd4545573887b32682
```

两次均因远端层下载中断失败，错误为：

```text
short read: expected <layer-bytes> bytes but got 0: unexpected EOF
```

随后从 GHCR 使用相同 amd64 digest 拉取成功，并完成 Runtime 启动验证。Docker Hub 的传输失败仍保留为部署风险记录，不影响 GHCR 镜像的本轮验证。

### 3.3 未登录 Runtime 启动验证

使用独立临时数据卷启动 `wechat-on-cloud` 镜像，验证结果如下：

```text
容器：启动成功
KasmVNC Web：HTTP 200
初始状态：微信未安装，status=idle
官方微信安装：成功
微信版本：4.1.13.23
微信进程：已启动
扫码页面：可视化确认存在二维码和“扫码登录”入口
真实账号：未使用
临时容器/数据卷：验证结束后已清理
```

本节只记录“运行环境和登录入口”的验证；实际扫码及重启结果见第 3.4 节，仍不代表数据库读取或媒体读取已经成立。

在使用固定 Compose 配置重复安装时，脚本在已经写入 `done` 状态、版本文件和可执行文件后，进程末尾仍报告：

```text
/woc/wechat-ctl.sh: line 1: lock: unbound variable
```

这表示候选 Runtime 的安装脚本存在“实际安装成功但命令返回非零”的退出码问题。验证和生产编排不能只依据 `docker compose exec` 的退出码判断安装结果，必须同时检查 `wechat-ctl.sh status`、版本文件和微信进程。该问题属于候选 Runtime 风险，不应由 Archive 业务层掩盖。

### 3.4 扫码和重启登录态验证

使用测试账号完成扫码后，微信界面进入联系人/会话列表，二维码消失；宿主数据目录统计从初始约 `40 KB` 增长到 `159 MB`，`.xwechat` 从约 `2 MB` 增长到 `104 MB`。

随后执行 `docker compose stop` 和 `docker compose start`：

```text
Runtime：启动成功
微信版本：4.1.13.23
status：installed=true
xwechat_files：159 MB，仍存在
.xwechat：104 MB，仍存在
重启后的客户端：保留账号头像，但点击“登录”后显示“需在手机上完成登录”
```

结论：登录资料和数据目录确实持久化，但当前 Runtime 不能在重启后静默恢复到已登录会话；需要手机再次确认。这是 P0-04 的明确失败边界，不能把它描述为“登录态完全持久化”。

### 3.5 初步资源与存储观察

通过 `docker image inspect` 记录到：

```text
wechat-on-cloud amd64 image rootfs size：1,243,893,386 bytes（约 1.24 GB）
woc-panel amd64 image rootfs size：111,145,641 bytes（约 111 MB）
```

这只是镜像磁盘占用，不是 Runtime 运行时内存占用。低配置服务器是否可接受仍需在 P0-11 中使用 `docker stats` 和同步场景实测。

当前登录/等待手机确认状态下的资源快照：

```text
CPU：4.52%
内存：215.2 MiB / 14.72 GiB（容器未设置内存上限）
进程数：179
共享内存：1 GiB
Runtime 数据卷：约 1.0 GiB（包含微信安装文件、运行状态和测试数据）
宿主磁盘：79 GiB，总可用约 32 GiB
```

这是空闲 Runtime 快照，不包含扫描、导入和媒体处理压力；P0-11 仍需在实际同步场景下完成。

### 3.6 Runtime 可用接口盘点

对固定镜像内的 `/woc`、初始化脚本和控制脚本进行了只读检索。目前能确认的脚本主要负责应用启动、微信安装/更新和状态查询，没有发现面向 Archive 的消息导出、数据库解密或备份接口。因此当前 Runtime 只能作为“微信运行环境和数据卷提供者”，不能直接作为已完成的消息 Adapter。

## 3. 目标环境冻结建议

在 P0 期间先以以下组合作为复现基线：

```text
平台：Linux x86_64
操作系统：Ubuntu 24.04 LTS
Docker Engine：29.7.2
Docker Compose：v5.4.0
并发约束：同一时间只运行一个微信 Runtime 验证实例
数据约束：Runtime 数据目录使用独立测试卷，源数据以只读方式挂载/复制
```

以上版本是当前验证主机的事实记录，不代表最终生产环境必须锁死到完全相同的补丁版本。若后续 Runtime 对内核、图形栈、架构或 Docker 版本有额外要求，必须在本报告中追加兼容性证据并重新评审。

## 4. 尚未验证的关键问题

### 4.1 Runtime 与微信版本

当前候选 Runtime 已经可以在本机启动并展示扫码入口，但项目仍没有完成数据读取验证，因此还不能声称“微信聊天归档链路可用”。下一步需要记录：

- Runtime 项目和具体版本/提交；
- 微信客户端具体版本；
- 镜像架构和基础系统；
- 启动命令、持久化卷和 Web 登录入口；
- 是否允许在测试主机上以隔离账号进行扫码登录。

### 4.2 账号与隐私边界

P0 必须使用专用隔离测试账号，不使用用户最重要的主账号。仓库不得提交二维码截图、登录凭据、微信数据库、聊天正文或未脱敏媒体。测试账号信息只保存在本地受控记录中，不进入 Git。

### 4.3 数据读取

P0-05 已确认源数据候选目录为 `/config/xwechat_files`。宿主绑定目录可以用独立容器以 `:ro` 方式挂载，容器运行用户对目录可读、可遍历，盘点时没有不可读文件。

只读 SQLite 探针得到：

```text
/config/xwechat_files：20 个命名数据库，1 个可用 SQLite 只读打开，19 个打开失败
/config/.xwechat：5 个命名数据库，4 个可用 SQLite 只读打开，1 个打开失败
全部文件扫描：/config/xwechat_files 有 276 个文件、仅 1 个标准 SQLite 文件；/config/.xwechat 有 745 个文件、24 个标准 SQLite 文件
可读库的表：LoginKeyInfoTable 或预览相关表
```

`LoginKeyInfoTable` 只检查了列定义，没有读取 `key_info_data` 等任何行值。当前看到的可读数据库不是聊天消息归档库；其余文件可能是加密数据库或专有格式，但尚未获得合法、稳定的读取方式。在没有完成数据库识别和读取验证前，不实现猜测性的解密、表结构解析或消息导入代码。P0-06 仍需证明：

1. 源数据可以被稳定访问；
2. 读取过程不修改源数据；
3. 联系人、会话、文本消息至少有一个可解释样本；
4. 至少一种媒体可以复制、哈希并关联到消息；
5. Runtime 重启后可以重复得到可比较结果。

## 5. P0 证据目录约定

敏感证据不进入 Git。建议本地验证时使用以下目录，并通过 `.gitignore` 或仓库外目录保存原始数据：

```text
本地验证目录（不提交）
├── runtime-logs/
├── screenshots/
├── source-snapshots/
├── fixtures-redacted/
├── media-redacted/
└── measurements/
```

提交到仓库的内容只能是脱敏后的结构说明、字段说明、哈希、统计值和可重复的测试脚本；不能提交真实聊天内容、账号标识、二维码、密钥或原始微信数据。

## 6. 下一步执行清单

| 编号 | 下一步 | 前置条件 | 产物 |
|---|---|---|---|
| P0-01 | 选定候选 Runtime 和具体微信版本，补齐环境冻结信息 | 候选 Runtime 可获取 | 已完成：本报告第 1、3 节记录 amd64 digest 和微信 `4.1.13.23` |
| P0-02 | 准备隔离测试账号并填写本地记录模板 | 用户提供/操作专用账号 | 账号已完成扫码，但是否为专用隔离账号仍需记录确认 |
| P0-03 | 启动 Runtime，验证 Web 登录页/二维码 | P0-01、临时隔离数据卷 | 已完成：KasmVNC HTTP 200，二维码登录页面可视化确认 |
| P0-04 | 验证扫码登录和登录态持久化 | P0-03 | 已完成：首次扫码成功；重启后需手机再次确认，失败边界已记录 |
| P0-05 | 定位源数据目录并验证只读访问 | P0-04 | 已完成：`/config/xwechat_files` 可通过宿主绑定目录只读挂载和盘点 |
| P0-06 | 判断数据库加密状态及稳定读取方式 | P0-05 | 读取验证记录 |
| P0-07 | 导出联系人、会话、文本最小样本 | P0-06 | 脱敏 fixture |
| P0-08 | 导出一种媒体并建立消息关联 | P0-07 | 脱敏媒体 fixture 与哈希 |
| P0-09～P0-11 | 重启复读、增量变化和资源评估 | P0-07、P0-08 | 对比日志和资源记录 |
| P0-12 | 在 Linux Runtime、Windows Agent、离线导入中确定 V1 路线 | P0-01～P0-11 | 本报告结论 |

## 7. 当前路线判断

暂不做最终路线选择，当前评估状态：

- Linux Docker Runtime：WechatOnCloud 已通过 GHCR 固定 digest 启动、扫码并生成数据，但重启需手机再次确认，且消息数据库读取方式未确定；暂列为候选验证路线，不是最终依赖；
- 外置 Windows Agent：待评估；
- 导入已有数据目录：可作为 A/B 均失败时的降级路线，但尚未实现。

在 P0-12 完成前，项目不进入大规模 Web UI 开发，也不勾选 Phase 1 及之后的功能任务。

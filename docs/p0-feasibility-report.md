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
| 微信版本 | 尚未固定 | 阻塞 |
| 微信 Runtime | 尚未选择并验证 | 阻塞 |
| 目标数据读取方式 | 尚未验证 | 阻塞 |

因此 P0-01 当前为“环境基线已完成、Runtime/微信版本待固定”，不能勾选为完全完成。P0-02 至 P0-12 尚未满足退出条件。

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
HEAD：97dc7c6 docs: add project checklist and readme
工作区：检查时干净
```

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

当前仓库没有 Runtime 镜像、Compose 配置或微信安装包，因此还不能声称 Linux Docker Runtime 可用。下一步需要选定候选实现，并记录：

- Runtime 项目和具体版本/提交；
- 微信客户端具体版本；
- 镜像架构和基础系统；
- 启动命令、持久化卷和 Web 登录入口；
- 是否允许在测试主机上以隔离账号进行扫码登录。

### 4.2 账号与隐私边界

P0 必须使用专用隔离测试账号，不使用用户最重要的主账号。仓库不得提交二维码截图、登录凭据、微信数据库、聊天正文或未脱敏媒体。测试账号信息只保存在本地受控记录中，不进入 Git。

### 4.3 数据读取

在没有完成登录和数据目录定位前，不实现猜测性的数据库解密、表结构解析或消息导入代码。读取验证必须证明：

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
| P0-01 | 选定候选 Runtime 和具体微信版本，补齐环境冻结信息 | 候选 Runtime 可获取 | 本报告第 1、3 节更新 |
| P0-02 | 准备隔离测试账号并填写本地记录模板 | 用户提供/操作专用账号 | `docs/p0-test-account-record.template.md` 的本地副本 |
| P0-03 | 启动 Runtime，验证 Web 登录页/二维码 | P0-01、P0-02 | 启动日志和脱敏截图 |
| P0-04 | 验证扫码登录和登录态持久化 | P0-03 | 登录/重启记录 |
| P0-05 | 定位源数据目录并验证只读访问 | P0-04 | 数据目录与权限记录 |
| P0-06 | 判断数据库加密状态及稳定读取方式 | P0-05 | 读取验证记录 |
| P0-07 | 导出联系人、会话、文本最小样本 | P0-06 | 脱敏 fixture |
| P0-08 | 导出一种媒体并建立消息关联 | P0-07 | 脱敏媒体 fixture 与哈希 |
| P0-09～P0-11 | 重启复读、增量变化和资源评估 | P0-07、P0-08 | 对比日志和资源记录 |
| P0-12 | 在 Linux Runtime、Windows Agent、离线导入中确定 V1 路线 | P0-01～P0-11 | 本报告结论 |

## 7. 当前路线判断

暂不做最终路线选择：

- Linux Docker Runtime：待验证；
- 外置 Windows Agent：待评估；
- 导入已有数据目录：可作为 A/B 均失败时的降级路线，但尚未实现。

在 P0-12 完成前，项目不进入大规模 Web UI 开发，也不勾选 Phase 1 及之后的功能任务。

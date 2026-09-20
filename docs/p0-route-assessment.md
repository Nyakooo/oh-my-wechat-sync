# P0 Runtime 路线评估

状态：阶段性评估，最终路线尚未冻结

最后更新：2026-09-20

本评估用于完成 P0-12 的决策准备。它不把任何第三方 Runtime 写成 Archive 的核心依赖。

## 1. 证据结论

| 路线 | 已验证事实 | 当前结论 |
|---|---|---|
| A：Linux Docker Runtime | WechatOnCloud 可启动、可扫码、可生成持久化数据目录；重启后需要手机再次确认；消息数据库未形成可维护读取方式 | 不足以直接进入消息归档开发 |
| B：外置 Windows Agent | 当前主机没有 Windows Agent 或真实 Windows 微信数据读取证据；PyWxDump 文档显示其可在 Windows 侧定位、解密和导出微信数据库，但尚未在隔离 Windows 环境验证 | 有候选，但不能作为已验证路线 |
| C：离线数据导入 | 不依赖服务器常驻微信；WxBackup 的公开文档明确不支持把 Windows 微信聊天记录导入/迁移到其产品；仍需要定义本项目自己的合法、稳定、可脱敏输入格式 | 可作为降级/替代路线，待样本验证 |

详细证据见 [`docs/p0-feasibility-report.md`](./p0-feasibility-report.md)。

## 2. 对项目架构的影响

Archive 核心必须依赖一个抽象的 `Runtime Adapter` 或 `Import Adapter`，而不是依赖 WechatOnCloud 的容器内部实现：

```text
Archive Sync Engine
        │
        ├── Runtime Adapter（启动、状态、数据目录）
        │       └── Linux Docker Runtime（当前候选）
        │
        └── Import Adapter（版本化导入包）
                ├── Windows Agent 导出包
                └── 离线数据目录/工具导出包
```

WeChat Runtime 的“能登录”与 Archive 的“能读取消息”是两个独立验收条件，不能合并为一个结论。

## 3. 当前推荐的下一步

在没有稳定消息读取方式之前，不实现针对 WechatOnCloud 内部数据库的猜测性解密代码。下一步按以下顺序推进：

1. 补齐 P0-02 的隔离账号记录，不在仓库提交账号信息；
2. 准备一台可运行 Windows 微信的隔离环境，评估 PyWxDump 是否能稳定导出本项目所需的最小样本；
3. 如果无法提供 Windows 环境，则改走 C，先取得合法、脱敏、可重复使用的离线导入样本；
4. 为样本定义版本化输入协议，验证联系人、会话、文本消息和一种媒体；
5. 只有样本可重复读取后，才进入 Phase 1 的归档数据库和 Fixture 实现。

### 3.1 外部候选核验记录

- [PyWxDump README](https://github.com/JellyHoney/PyWxDump)：公开说明包含微信信息读取、数据库解密、聊天查看和 HTML/CSV 导出能力，同时注明当前只在 Windows 测试；这证明了候选能力边界，但不等于已验证可作为本项目 Agent。
- [PyWxDump 用户指南](https://github.com/JellyHoney/PyWxDump/blob/master/doc/UserGuide.md)：公开命令包含 `wx_path`、`decrypt`、`ui` 和 `api`，并提供 Python 调用示例；其 `all` 模式已标记废弃，不能直接把该命令当成稳定协议。
- [PyWxDump LICENSE](https://github.com/JellyHoney/PyWxDump/blob/master/LICENSE)：代码采用 MIT License；但 README 同时包含“仅供学习交流”和“不允许二次开发”等项目声明，正式集成前必须完成法律、供应链和安全审查。
- [WxBackup README](https://github.com/weibeifen/wxbackup)：其 FAQ 明确回答“不支持把 Windows 微信上的聊天记录迁移/导入到微备份”，因此它不是本项目所需的 Windows Agent 输入桥接方案。

本节只记录公开文档核验结果，没有下载、安装或运行上述第三方工具，也没有把它们引入仓库依赖。

### 3.2 本地验证环境边界

2026-09-20 再次检查当前主机：系统为 Linux x86_64，仅发现 `/usr/bin/wine`，没有 Windows 微信、Windows Agent 或可供读取的 Windows 数据样本。Wine 的存在不能替代真实 Windows 微信进程验证，因此本机当前无法完成路线 B 的有效验收。

当前 Docker Runtime 容器处于停止状态；本次检查没有启动容器、重新登录或修改已有测试数据。

路线 B 的下一项实际动作必须在外部隔离 Windows 环境完成，或由用户提供一份合法脱敏的导出样本后转入路线 C。未满足其一前，不继续安装第三方工具，也不勾选 P0-06～P0-12。

## 4. 决策门槛

### 选择 B：Windows Agent

必须先证明：

- Agent 可以在运行微信的 Windows 主机上稳定读取或导出数据；
- 输出协议不依赖 Archive 直接猜测微信内部数据库密钥；
- Agent 与服务器之间有认证、断点、重试和数据清理边界；
- 至少一份脱敏样本可以重复导入。

当前候选 PyWxDump 还额外需要确认：微信版本变化后的兼容性、导出过程中是否修改源目录、是否能导出媒体关联，以及其 API 是否足够稳定。未完成这些验证前，不能勾选 P0-12。

### 选择 C：离线导入

必须先证明：

- 用户可以合法取得导入包或数据目录；
- 导入包包含来源版本、账号标识、消息、媒体和校验信息；
- 导入过程完全离线、可重试、幂等且不修改源数据；
- 至少一份脱敏样本可以重复导入并建立媒体关联。

在 B/C 任一方案满足上述门槛前，P0-12 保持未完成，Phase 1 不勾选。

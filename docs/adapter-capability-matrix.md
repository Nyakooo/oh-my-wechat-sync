# Adapter Capability Matrix

这张表区分“归档层已实现”和“真实微信来源已验证”，避免把合成 fixture 或 Runtime 登录页误认为消息同步能力。

| 来源/适配器 | 平台 | 登录/运行 | 联系人/会话/文本 | 媒体关联 | 增量读取 | 当前结论 |
|---|---|---|---|---|---|---|
| Import-first v0 | Ubuntu/Linux | 不负责登录 | 已实现标准 DTO 和 SQLite 导入 | 已实现复制、哈希去重、受控读取 | 依赖导入包的 export/checkpoint | 当前 V1 可执行路线；已用合成 fixture 验证 |
| WechatOnCloud Linux Runtime | Ubuntu/Linux | Web 登录页和扫码入口已观察 | 未发现稳定 Archive 导出接口 | 未验证 | 未验证 | 只能作为 Runtime 候选，当前不作为消息 Adapter |
| Windows Agent 候选 | Windows | 当前环境没有 Windows 微信/Agent | 未验证 | 未验证 | 未验证 | 需要外部隔离 Windows 环境和合法脱敏样本 |

版本变化至少要记录：微信版本、Runtime 镜像 digest、Agent/导出工具版本、导入包格式版本和验证日期。任何一项变化都不能自动宣称兼容，必须重新通过对应样本验收。

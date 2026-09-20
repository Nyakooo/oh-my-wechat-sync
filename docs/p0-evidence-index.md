# P0 验证证据索引

状态：持续更新，P0-12 尚未完成

本索引只列出仓库内的可提交证据和验证工具。真实账号记录、原始微信数据、运行日志和未脱敏样本必须存放在仓库外受控目录。

## 已有证据

| 证据 | 位置 | 当前结论 |
|---|---|---|
| 主机、Docker、Runtime 和数据目录检查 | [`p0-feasibility-report.md`](./p0-feasibility-report.md) | Linux Runtime 可启动并产生持久化数据，但消息读取方式未确定 |
| Runtime 人工验证步骤 | [`p0-runtime-validation-runbook.md`](./p0-runtime-validation-runbook.md) | 可重复启动、扫码和检查数据目录 |
| A/B/C 路线评估 | [`p0-route-assessment.md`](./p0-route-assessment.md) | A 不足以直接作为消息 Adapter，B/C 待外部样本 |
| 导入包协议草案 | [`p0-import-package-draft.md`](./p0-import-package-draft.md) | 仅为未验证输入边界 |
| 外部样本交接清单 | [`p0-external-sample-intake.md`](./p0-external-sample-intake.md) | 等待隔离 Windows 环境或合法脱敏样本 |
| 路线决策模板 | [`p0-route-decision-template.md`](./p0-route-decision-template.md) | 待 P0-06～P0-11 证据填充 |
| 合成导入包 | [`../tests/fixtures/import-v0-minimal`](../tests/fixtures/import-v0-minimal) | 只验证校验器，不代表真实来源链路 |
| 导入包安全校验 | [`../tools/validate_import_package.py`](../tools/validate_import_package.py) | 包含严格整数、哈希、引用、路径和符号链接边界检查 |
| 导入包脱敏摘要 | [`../tools/report_import_package.py`](../tools/report_import_package.py) | 生成不含账号标识和消息正文的记录/媒体统计 |
| P0 预检闸门 | [`../tools/p0_preflight.py`](../tools/p0_preflight.py) | 汇总文档、合成 fixture、自动化测试和外部样本状态，证据不足时保持阻塞 |

## 当前未满足

- 没有可重复读取的真实消息数据库或稳定导出协议；
- 没有真实脱敏的联系人、会话、文本消息和媒体样本；
- 没有完成 Windows Agent 的隔离环境验证；
- 没有完成 P0-10 增量发现和实际同步负载下的 P0-11 资源评估；
- 因此 P0-12 未完成，Phase 1 不启动。

## 复核顺序

拿到外部样本后，按以下顺序复核：

1. 运行 [`validate_import_package.py`](../tools/validate_import_package.py)；
2. 保存校验输出和样本统计，不提交原始数据；
3. 根据 [`p0-route-decision-template.md`](./p0-route-decision-template.md) 填写 P0-06～P0-11；
4. 通过所有门槛后再决定是否进入 Phase 1。

也可以直接运行仓库级预检：

```bash
python3 tools/p0_preflight.py --pretty
```

没有外部样本时，命令应返回 `status=blocked` 和非零退出码；这是预期结果，不代表工具运行失败。

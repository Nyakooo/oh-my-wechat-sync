# P0 离线导入包协议草案

状态：草案，未通过真实样本验证

最后更新：2026-09-20

本文件只定义后续验证使用的输入边界，不代表已经支持任何具体微信版本、第三方工具或数据格式。导入包必须来自用户有权访问的数据，并且不得要求 Archive 猜测微信数据库密钥。

## 1. 目标

导入 Adapter 接收一个可校验、可脱敏、可重复导入的目录或压缩包，向归档引擎提供标准化对象：

- 账号元数据；
- 联系人；
- 会话及成员；
- 文本或可索引消息；
- 消息关联的媒体；
- 来源版本、统计值和校验信息。

导入 Adapter 不修改源包，不执行任意脚本，不把原始微信数据库直接暴露给 Web 层。

## 2. 建议目录

```text
wechat-archive-import-v0/
├── manifest.json
├── contacts.ndjson
├── conversations.ndjson
├── conversation-members.ndjson
├── messages.ndjson
├── attachments.ndjson
└── media/
    └── <sha256>
```

所有文本文件使用 UTF-8 和 LF；每行一个 JSON 对象。`conversation-members.ndjson` 可以省略，但只要存在就必须在 manifest 中声明。顺序不能作为唯一依据，导入必须按来源 ID 和内容哈希幂等处理。

## 3. Manifest 最小字段

```json
{
  "format": "wechat-archive-import",
  "format_version": 0,
  "export_id": "opaque-export-id",
  "source": {
    "kind": "windows-agent|offline-tool|data-directory",
    "tool_name": "opaque-name",
    "tool_version": "opaque-version",
    "wechat_version": "opaque-version"
  },
  "account": {
    "source_account_id": "redacted-or-stable-id",
    "display_name": "redacted"
  },
  "files": {
    "messages.ndjson": {"records": 0, "sha256": "hex"}
  },
  "created_at": "RFC3339 timestamp"
}
```

`manifest.json` 不能包含手机号、登录凭据、数据库密钥、二维码或原始微信目录路径。`source_account_id` 必须稳定但可脱敏；如果无法提供稳定标识，必须由用户在导入时显式绑定 Archive 账号。

## 4. 标准记录要求

字段名称与归档模型保持一致，原始字段只能放在受限的 `raw_payload` 中，且默认不进入全文索引。

### 联系人

```json
{"source_contact_id":"contact-1","display_name":"脱敏联系人","alias":null}
```

必需：`source_contact_id`。推荐：`display_name`、`alias`、`avatar_sha256`。

### 会话

```json
{"source_chat_id":"chat-1","kind":"direct","title":"脱敏会话","member_source_ids":["contact-1"]}
```

必需：`source_chat_id`、`kind`。`kind` 仅允许 `direct`、`group`、`unknown`。

### 消息

```json
{
  "source_msg_id":"msg-1",
  "source_chat_id":"chat-1",
  "sender_source_contact_id":"contact-1",
  "source_created_at":1726652160000,
  "type":"text",
  "content":"脱敏文本",
  "is_self":false,
  "reply_to_source_msg_id":null
}
```

必需：`source_msg_id`、`source_chat_id`、`source_created_at`、`type`。同一账号内 `source_msg_id` 必须稳定；如果来源 ID 不稳定，导出器必须提供明确的替代唯一键和生成规则，不能由导入器凭正文猜测。

### 附件

```json
{
  "source_msg_id":"msg-2",
  "kind":"image",
  "mime_type":"image/jpeg",
  "original_name":null,
  "size":1234,
  "sha256":"hex",
  "path":"media/<sha256>"
}
```

必需：`source_msg_id`、`kind`、`sha256`、`path`。导入器必须重新计算文件哈希和大小；manifest 或记录中的值不一致时拒绝该附件，不能静默修正。

## 5. 导入验收顺序

1. 校验目录结构、格式版本和 JSONL 语法；
2. 校验 manifest 文件数量、记录数和 SHA-256；
3. 校验账号绑定、会话引用、联系人引用和消息引用；
4. 校验媒体路径位于包根目录内，拒绝 `..`、绝对路径和符号链接穿越；
5. 在临时事务中导入联系人、会话、消息和媒体；
6. 使用 `(account_id, source_msg_id)` 和 `(account_id, message_id, kind, sha256)` 验证重复导入不增加记录；
7. 只有全部校验通过后才提交事务和更新 checkpoint。

## 6. P0 样本退出条件

该草案只有在以下证据齐全后才能升级为 `v0`：

- 一份合法取得、脱敏且不含密钥的真实来源样本；
- 至少联系人、一个会话、文本消息和一种媒体；
- 首次导入成功，消息与媒体关联正确；
- 原包不被修改；
- 完整重复导入不产生重复消息或媒体；
- 中途失败后可重试，且失败批次不会推进 checkpoint；
- 第二份账号样本不会覆盖第一份账号的同名或同 ID 数据。

在上述条件满足前，本文件不得被当作已实现协议，也不创建 Phase 1 的导入代码。

## 7. 脱敏和提交边界

仓库只允许提交字段说明、统计值、哈希和人工构造 fixture。不得提交真实聊天正文、手机号、微信号、头像原图、二维码、密钥、运行时目录或原始数据库。

## 8. 当前校验工具

仓库提供只读静态校验器 [`tools/validate_import_package.py`](../tools/validate_import_package.py)。它只检查目录格式、JSONL、manifest 记录数和 SHA-256、跨文件引用、媒体大小/哈希以及路径穿越；它不会导入归档库、修改源包、解密数据库或启动微信。

```bash
python3 tools/validate_import_package.py /path/to/wechat-archive-import-v0
```

该工具验证通过只代表“输入包符合草案格式”，不代表来源数据完整、来源工具稳定或路线 B/C 已通过 P0。

仓库中的 [`tests/fixtures/import-v0-minimal`](../tests/fixtures/import-v0-minimal) 是人工构造的正向 fixture，仅包含合成标识、合成文本和合成媒体，可用于验证校验器本身：

```bash
python3 tools/validate_import_package.py tests/fixtures/import-v0-minimal
```

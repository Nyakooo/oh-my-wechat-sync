#!/usr/bin/env python3
"""Validate the draft wechat-archive-import-v0 package without importing data."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = (
    "contacts.ndjson",
    "conversations.ndjson",
    "messages.ndjson",
    "attachments.ndjson",
)


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path.name}")
    return value


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationError(f"cannot read {path.name}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"invalid JSON at {path.name}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValidationError(f"record must be an object at {path.name}:{line_number}")
        records.append(value)
    return records


def required_string(record: dict[str, Any], key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{context}: {key} must be a non-empty string")
    return value


def unique_ids(records: list[dict[str, Any]], key: str, context: str) -> set[str]:
    values: set[str] = set()
    for index, record in enumerate(records, 1):
        value = required_string(record, key, f"{context} record {index}")
        if value in values:
            raise ValidationError(f"duplicate {key} in {context}: {value}")
        values.add(value)
    return values


def safe_relative_path(value: Any, package_root: Path, context: str) -> Path:
    relative = required_string({"path": value}, "path", context)
    if "\\" in relative or posixpath.isabs(relative) or Path(relative).is_absolute():
        raise ValidationError(f"{context}: path must be relative and use '/' separators")
    normalized = posixpath.normpath(relative)
    if normalized in (".", "..") or normalized.startswith("../"):
        raise ValidationError(f"{context}: path escapes package root")
    candidate = package_root / Path(*normalized.split("/"))
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{context}: missing path: {relative}") from exc
    try:
        resolved.relative_to(package_root.resolve())
    except ValueError as exc:
        raise ValidationError(f"{context}: path escapes package root: {relative}") from exc
    if candidate.is_symlink():
        raise ValidationError(f"{context}: symbolic links are not allowed: {relative}")
    return resolved


def sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def validate_manifest(package_root: Path, manifest: dict[str, Any]) -> None:
    if manifest.get("format") != "wechat-archive-import":
        raise ValidationError("manifest.format must be wechat-archive-import")
    if manifest.get("format_version") != 0:
        raise ValidationError("only manifest.format_version 0 is supported")
    required_string(manifest, "export_id", "manifest")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValidationError("manifest.source must be an object")
    required_string(source, "kind", "manifest.source")
    account = manifest.get("account")
    if not isinstance(account, dict):
        raise ValidationError("manifest.account must be an object")
    required_string(account, "source_account_id", "manifest.account")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValidationError("manifest.files must be an object")

    for file_name in REQUIRED_FILES:
        entry = files.get(file_name)
        if not isinstance(entry, dict):
            raise ValidationError(f"manifest.files.{file_name} is required")
        if not isinstance(entry.get("records"), int) or entry["records"] < 0:
            raise ValidationError(f"manifest.files.{file_name}.records must be a non-negative integer")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValidationError(f"manifest.files.{file_name}.sha256 must be a 64-character hex string")
        try:
            int(expected_hash, 16)
        except ValueError as exc:
            raise ValidationError(f"manifest.files.{file_name}.sha256 must be hexadecimal") from exc
        actual_path = safe_relative_path(file_name, package_root, f"manifest file {file_name}")
        actual_hash, _ = sha256_and_size(actual_path)
        if actual_hash != expected_hash.lower():
            raise ValidationError(f"manifest hash mismatch: {file_name}")


def validate_records(package_root: Path, manifest: dict[str, Any]) -> dict[str, int]:
    records_by_file: dict[str, list[dict[str, Any]]] = {}
    for file_name in REQUIRED_FILES:
        path = package_root / file_name
        records = load_ndjson(path)
        records_by_file[file_name] = records
        expected = manifest["files"][file_name]["records"]
        if len(records) != expected:
            raise ValidationError(f"record count mismatch: {file_name}: expected {expected}, got {len(records)}")

    contact_ids = unique_ids(records_by_file["contacts.ndjson"], "source_contact_id", "contacts.ndjson")
    conversation_ids = unique_ids(records_by_file["conversations.ndjson"], "source_chat_id", "conversations.ndjson")
    message_ids = unique_ids(records_by_file["messages.ndjson"], "source_msg_id", "messages.ndjson")

    for index, conversation in enumerate(records_by_file["conversations.ndjson"], 1):
        kind = required_string(conversation, "kind", f"conversations.ndjson record {index}")
        if kind not in {"direct", "group", "unknown"}:
            raise ValidationError(f"conversations.ndjson record {index}: unsupported kind: {kind}")
        members = conversation.get("member_source_ids", [])
        if not isinstance(members, list) or any(member not in contact_ids for member in members):
            raise ValidationError(f"conversations.ndjson record {index}: unknown member reference")

    for index, message in enumerate(records_by_file["messages.ndjson"], 1):
        context = f"messages.ndjson record {index}"
        source_chat_id = required_string(message, "source_chat_id", context)
        if source_chat_id not in conversation_ids:
            raise ValidationError(f"{context}: unknown source_chat_id")
        if not isinstance(message.get("source_created_at"), int):
            raise ValidationError(f"{context}: source_created_at must be an integer")
        required_string(message, "type", context)
        sender = message.get("sender_source_contact_id")
        if sender is not None and sender not in contact_ids:
            raise ValidationError(f"{context}: unknown sender_source_contact_id")

    for index, attachment in enumerate(records_by_file["attachments.ndjson"], 1):
        context = f"attachments.ndjson record {index}"
        if attachment.get("source_msg_id") not in message_ids:
            raise ValidationError(f"{context}: unknown source_msg_id")
        required_string(attachment, "kind", context)
        expected_hash = required_string(attachment, "sha256", context)
        if len(expected_hash) != 64:
            raise ValidationError(f"{context}: sha256 must be a 64-character hex string")
        try:
            int(expected_hash, 16)
        except ValueError as exc:
            raise ValidationError(f"{context}: sha256 must be hexadecimal") from exc
        media_path = safe_relative_path(attachment.get("path"), package_root, context)
        actual_hash, actual_size = sha256_and_size(media_path)
        if actual_hash != expected_hash.lower():
            raise ValidationError(f"{context}: media hash mismatch")
        declared_size = attachment.get("size")
        if declared_size is not None and declared_size != actual_size:
            raise ValidationError(f"{context}: media size mismatch")

    return {file_name: len(records) for file_name, records in records_by_file.items()}


def validate(package_root: Path) -> dict[str, int]:
    if not package_root.is_dir():
        raise ValidationError(f"package directory does not exist: {package_root}")
    manifest_path = package_root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValidationError("manifest.json is required and must be a regular file")
    manifest = load_json(manifest_path)
    validate_manifest(package_root, manifest)
    return validate_records(package_root, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="path to a wechat-archive-import-v0 directory")
    args = parser.parse_args()
    try:
        counts = validate(args.package)
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID")
    for file_name, count in counts.items():
        print(f"{file_name}: {count} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

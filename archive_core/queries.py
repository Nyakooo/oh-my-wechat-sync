from __future__ import annotations

import sqlite3


def account_summary(connection: sqlite3.Connection, account_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT accounts.*,
               (SELECT COUNT(*) FROM conversations WHERE account_id = accounts.id) AS conversation_count,
               (SELECT COUNT(*) FROM messages WHERE account_id = accounts.id) AS message_count,
               (SELECT COUNT(*) FROM attachments WHERE account_id = accounts.id) AS attachment_count
        FROM accounts
        WHERE accounts.id = ?
        """,
        (account_id,),
    ).fetchone()


def list_account_summaries(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT accounts.*,
               (SELECT COUNT(*) FROM conversations WHERE account_id = accounts.id) AS conversation_count,
               (SELECT COUNT(*) FROM messages WHERE account_id = accounts.id) AS message_count,
               (SELECT COUNT(*) FROM attachments WHERE account_id = accounts.id) AS attachment_count
        FROM accounts
        ORDER BY accounts.updated_at DESC, accounts.id
        """
    ).fetchall()


def list_conversations(
    connection: sqlite3.Connection,
    account_id: str,
    limit: int,
    offset: int,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT conversations.*,
               (SELECT COUNT(*) FROM messages WHERE conversation_id = conversations.id) AS message_count
        FROM conversations
        WHERE account_id = ?
        ORDER BY COALESCE(last_message_at, 0) DESC, id
        LIMIT ? OFFSET ?
        """,
        (account_id, limit, offset),
    ).fetchall()


def list_messages(
    connection: sqlite3.Connection,
    account_id: str,
    conversation_id: str,
    limit: int,
    offset: int,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT messages.*, contacts.display_name AS sender_display_name
        FROM messages
        LEFT JOIN contacts ON contacts.id = messages.sender_contact_id
        WHERE messages.account_id = ? AND messages.conversation_id = ?
        ORDER BY messages.source_created_at ASC, messages.id ASC
        LIMIT ? OFFSET ?
        """,
        (account_id, conversation_id, limit, offset),
    ).fetchall()


def list_attachments(connection: sqlite3.Connection, message_id: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM attachments WHERE message_id = ? ORDER BY id",
        (message_id,),
    ).fetchall()

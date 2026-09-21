CREATE TABLE IF NOT EXISTS archive_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    wechat_id TEXT,
    avatar_path TEXT,
    runtime_kind TEXT NOT NULL,
    runtime_ref TEXT,
    status TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_sync_at INTEGER
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    source_contact_id TEXT NOT NULL,
    display_name TEXT,
    alias TEXT,
    avatar_path TEXT,
    raw_payload TEXT,
    UNIQUE (account_id, source_contact_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    source_chat_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT,
    avatar_path TEXT,
    last_message_at INTEGER,
    UNIQUE (account_id, source_chat_id)
);

CREATE TABLE IF NOT EXISTS conversation_members (
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    contact_id TEXT NOT NULL REFERENCES contacts(id),
    PRIMARY KEY (conversation_id, contact_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    sender_contact_id TEXT REFERENCES contacts(id),
    source_msg_id TEXT NOT NULL,
    source_created_at INTEGER NOT NULL,
    type TEXT NOT NULL,
    content TEXT,
    is_self INTEGER NOT NULL DEFAULT 0 CHECK (is_self IN (0, 1)),
    reply_to_id TEXT REFERENCES messages(id),
    raw_payload TEXT,
    archived_at INTEGER NOT NULL,
    UNIQUE (account_id, source_msg_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    message_id TEXT NOT NULL REFERENCES messages(id),
    kind TEXT NOT NULL,
    mime_type TEXT,
    original_name TEXT,
    size INTEGER,
    source_path TEXT,
    archive_path TEXT,
    sha256 TEXT,
    status TEXT NOT NULL,
    UNIQUE (account_id, message_id, kind, sha256)
);

CREATE TABLE IF NOT EXISTS sync_jobs (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    trigger TEXT NOT NULL,
    status TEXT NOT NULL,
    phase TEXT,
    started_at INTEGER,
    finished_at INTEGER,
    error_code TEXT,
    error_message TEXT,
    stats_json TEXT
);

CREATE TABLE IF NOT EXISTS sync_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES sync_jobs(id),
    event_type TEXT NOT NULL,
    detail TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_checkpoints (
    account_id TEXT NOT NULL REFERENCES accounts(id),
    source_name TEXT NOT NULL,
    source_fingerprint TEXT,
    last_source_id TEXT,
    last_source_time INTEGER,
    overlap_size INTEGER NOT NULL DEFAULT 1000,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (account_id, source_name)
);

CREATE TABLE IF NOT EXISTS sync_locks (
    lock_name TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    acquired_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contacts_account ON contacts(account_id);
CREATE INDEX IF NOT EXISTS idx_conversations_account ON conversations(account_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_time ON messages(conversation_id, source_created_at);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_sync_events_job ON sync_events(job_id, id);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    message_id UNINDEXED,
    account_id UNINDEXED,
    conversation_id UNINDEXED,
    content,
    tokenize = 'unicode61'
);

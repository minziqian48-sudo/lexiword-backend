-- Lexiword 数据库 schema
-- 前后端分离 + JWT 用户认证

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS word_states (
    user_id INTEGER NOT NULL REFERENCES users(id),
    day INTEGER NOT NULL,
    word TEXT NOT NULL,
    state INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (user_id, day, word)
);

CREATE TABLE IF NOT EXISTS starred_words (
    user_id INTEGER NOT NULL REFERENCES users(id),
    word TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (user_id, word)
);

CREATE TABLE IF NOT EXISTS checkin_records (
    user_id INTEGER NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (user_id, date)
);

CREATE TABLE IF NOT EXISTS word_sets (
    id TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    words TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (id, user_id)
);

CREATE TABLE IF NOT EXISTS pinned_bookmarks (
    user_id INTEGER NOT NULL REFERENCES users(id),
    id TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (user_id, id)
);

CREATE TABLE IF NOT EXISTS custom_meanings (
    user_id INTEGER NOT NULL REFERENCES users(id),
    word TEXT NOT NULL,
    meaning TEXT NOT NULL,
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (user_id, word)
);

CREATE TABLE IF NOT EXISTS vocab_bookmark (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    word TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS visit_records (
    user_id INTEGER NOT NULL REFERENCES users(id),
    day INTEGER NOT NULL,
    visited_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS daybook_words (
    day INTEGER NOT NULL,
    word TEXT NOT NULL,
    meaning TEXT NOT NULL,
    PRIMARY KEY (day, word)
);

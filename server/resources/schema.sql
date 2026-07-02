-- ==============================================================
-- UNMESSIT AI: Source Chunk + Recall Link Storage Schema
-- ==============================================================

CREATE TABLE IF NOT EXISTS raw_inputs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    content_hash TEXT,
    content TEXT NOT NULL,
    user_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_raw_inputs_job_id ON raw_inputs(job_id);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    identifier TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingest_jobs (
    id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    raw_input_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'waiting_retry', 'complete', 'failed', 'aborted', 'paused')),
    stage TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_run_at DATETIME,
    error TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE SET NULL
);


CREATE UNIQUE INDEX IF NOT EXISTS idx_ingest_jobs_content_hash ON ingest_jobs(content_hash);
CREATE INDEX IF NOT EXISTS idx_ingest_jobs_status_next_run ON ingest_jobs(status, next_run_at);

CREATE TABLE IF NOT EXISTS ingest_checkpoints (
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    unit_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running', 'complete', 'failed')),
    output_ref TEXT,
    error TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(job_id, stage, unit_key),
    FOREIGN KEY(job_id) REFERENCES ingest_jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ingest_checkpoints_job_stage ON ingest_checkpoints(job_id, stage, status);

CREATE TABLE IF NOT EXISTS event_outbox (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSON NOT NULL,
    idempotency_key TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'published', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_outbox_idempotency ON event_outbox(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_event_outbox_status_created ON event_outbox(status, created_at);

CREATE TABLE IF NOT EXISTS event_handler_runs (
    event_id TEXT NOT NULL,
    handler_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(event_id, handler_name)
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id TEXT PRIMARY KEY,
    raw_input_id TEXT NOT NULL,
    text TEXT NOT NULL,
    summary TEXT NOT NULL,
    spans JSON NOT NULL,
    source_time TEXT,
    user_id TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    directory_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_source_chunks_raw_input ON source_chunks(raw_input_id);

CREATE INDEX IF NOT EXISTS idx_source_chunks_created_at ON source_chunks(created_at);
CREATE INDEX IF NOT EXISTS idx_source_chunks_source_time ON source_chunks(source_time);

CREATE TABLE IF NOT EXISTS recall_keys (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('entity', 'topic', 'event', 'task', 'question', 'other')),
    kind_label TEXT,
    aliases JSON NOT NULL,
    summary TEXT NOT NULL,
    user_id TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recall_keys_name ON recall_keys(name);

CREATE INDEX IF NOT EXISTS idx_recall_keys_updated_at ON recall_keys(updated_at);

CREATE TABLE IF NOT EXISTS recall_key_terms (
    recall_key_id TEXT NOT NULL,
    term TEXT NOT NULL,
    normalized_term TEXT NOT NULL,
    term_type TEXT NOT NULL CHECK(term_type IN ('name', 'alias')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(recall_key_id) REFERENCES recall_keys(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recall_key_terms_normalized ON recall_key_terms(normalized_term);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recall_key_terms_unique_name ON recall_key_terms(normalized_term) WHERE term_type = 'name';
CREATE INDEX IF NOT EXISTS idx_recall_key_terms_key ON recall_key_terms(recall_key_id);

CREATE VIRTUAL TABLE IF NOT EXISTS recall_keys_fts USING fts5(
    recall_key_id UNINDEXED,
    name,
    aliases,
    summary,
    kind_label
);

CREATE TABLE IF NOT EXISTS recall_links (
    id TEXT PRIMARY KEY,
    recall_key_id TEXT NOT NULL,
    source_chunk_id TEXT NOT NULL,
    relation TEXT NOT NULL CHECK(relation IN ('mentions', 'about', 'updates', 'contradicts', 'supports', 'other')),
    relation_label TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    reason TEXT NOT NULL,
    event_time TEXT,
    time_label TEXT,
    user_id TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(recall_key_id) REFERENCES recall_keys(id) ON DELETE CASCADE,
    FOREIGN KEY(source_chunk_id) REFERENCES source_chunks(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(recall_key_id, source_chunk_id, relation, relation_label)
);

CREATE INDEX IF NOT EXISTS idx_recall_links_key ON recall_links(recall_key_id);

CREATE INDEX IF NOT EXISTS idx_recall_links_source_chunk ON recall_links(source_chunk_id);
CREATE INDEX IF NOT EXISTS idx_recall_links_created_at ON recall_links(created_at);
CREATE INDEX IF NOT EXISTS idx_recall_links_event_time ON recall_links(event_time);

-- ==============================================================
-- UNMESSIT AI: Notes and Organization Schema
-- ==============================================================

CREATE TABLE IF NOT EXISTS directories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT,
    path TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parent_id) REFERENCES directories(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_directories_user ON directories(user_id);
CREATE INDEX IF NOT EXISTS idx_directories_path ON directories(path);
CREATE INDEX IF NOT EXISTS idx_directories_parent ON directories(user_id, parent_id);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    directory_id TEXT,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME,
    metadata JSON NOT NULL DEFAULT '{}',
    FOREIGN KEY(directory_id) REFERENCES directories(id) ON DELETE SET NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notes_user ON notes(user_id);
CREATE INDEX IF NOT EXISTS idx_notes_directory ON notes(user_id, directory_id, deleted_at);

CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(name, user_id)
);
CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id);

CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY(note_id, tag_id),
    FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- ==============================================================
-- UNMESSIT AI: Configuration Schema
-- ==============================================================

CREATE TABLE IF NOT EXISTS user_config_presets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0,
    
    llm_provider TEXT NOT NULL,
    llm_model TEXT NOT NULL,
    llm_base_url TEXT,
    llm_api_key TEXT,
    llm_temperature REAL NOT NULL,
    llm_max_retries INTEGER NOT NULL,
    llm_max_tokens INTEGER,
    
    embedding_provider TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_base_url TEXT,
    embedding_api_key TEXT,
    
    llm_rate_limit_per_minute INTEGER NOT NULL DEFAULT 0,
    embedding_rate_limit_per_minute INTEGER NOT NULL DEFAULT 0,
    embedding_batch_size INTEGER NOT NULL DEFAULT 100,
    
    chunk_size INTEGER NOT NULL DEFAULT 1000,
    chunk_overlap INTEGER NOT NULL DEFAULT 200,
    ingest_retry_backoff_seconds TEXT NOT NULL DEFAULT '5,15,30,60,120',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_presets_active ON user_config_presets(user_id) WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS user_processing_settings (
    user_id TEXT PRIMARY KEY,
    embedding_provider TEXT NOT NULL DEFAULT 'openai',
    embedding_model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    embedding_batch_size INTEGER NOT NULL DEFAULT 100,
    chunk_size INTEGER NOT NULL DEFAULT 1000,
    chunk_overlap INTEGER NOT NULL DEFAULT 200,
    ingest_retry_backoff_seconds TEXT NOT NULL DEFAULT '5,15,30,60,120',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_rotation_config (
    user_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0,
    preset_ids JSON NOT NULL DEFAULT '[]',
    llm_enabled INTEGER NOT NULL DEFAULT 0,
    llm_preset_ids JSON NOT NULL DEFAULT '[]',
    llm_active_preset_id TEXT,
    embedding_enabled INTEGER NOT NULL DEFAULT 0,
    embedding_preset_ids JSON NOT NULL DEFAULT '[]',
    embedding_active_preset_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

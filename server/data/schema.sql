-- ==============================================================
-- UNMESSIT AI: SEAI + Legacy Hierarchical Memory Storage Schema
-- ==============================================================

CREATE TABLE IF NOT EXISTS raw_inputs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    raw_input_id TEXT NOT NULL,
    text TEXT NOT NULL,
    summary TEXT NOT NULL,
    spans JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS atoms (
    id TEXT PRIMARY KEY,
    raw_input_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    content TEXT NOT NULL,
    atom_role TEXT NOT NULL CHECK(atom_role IN ('direct', 'relation')),
    annotations JSON NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    evidence_spans JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE CASCADE,
    FOREIGN KEY(episode_id) REFERENCES episodes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    type TEXT NOT NULL,
    certainty TEXT NOT NULL,
    entities JSON,
    extra_properties JSON,
    notes TEXT,
    source_input_id TEXT,
    parent_id TEXT,
    next_id TEXT,
    level INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_input_id) REFERENCES raw_inputs(id) ON DELETE CASCADE,
    FOREIGN KEY(parent_id) REFERENCES memory_items(id) ON DELETE CASCADE,
    FOREIGN KEY(next_id) REFERENCES memory_items(id) ON DELETE SET NULL
);


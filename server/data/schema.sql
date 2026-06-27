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

CREATE TABLE IF NOT EXISTS memory_subjects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN (
        'project', 'person', 'place', 'topic', 'theme', 'question',
        'decision', 'problem', 'event', 'story', 'research', 'other'
    )),
    aliases JSON NOT NULL,
    summary TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_subjects_name ON memory_subjects(name);
CREATE INDEX IF NOT EXISTS idx_memory_subjects_updated_at ON memory_subjects(updated_at);

CREATE TABLE IF NOT EXISTS memory_subject_links (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    raw_input_id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    atom_id TEXT,
    relation TEXT NOT NULL CHECK(relation IN (
        'mentions', 'problem', 'decision', 'event', 'question',
        'change', 'plan', 'evidence', 'status', 'other'
    )),
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    reason TEXT NOT NULL,
    event_time TEXT,
    time_label TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(subject_id) REFERENCES memory_subjects(id) ON DELETE CASCADE,
    FOREIGN KEY(raw_input_id) REFERENCES raw_inputs(id) ON DELETE CASCADE,
    FOREIGN KEY(episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY(atom_id) REFERENCES atoms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_subject_links_subject ON memory_subject_links(subject_id);
CREATE INDEX IF NOT EXISTS idx_memory_subject_links_raw_input ON memory_subject_links(raw_input_id);
CREATE INDEX IF NOT EXISTS idx_memory_subject_links_episode ON memory_subject_links(episode_id);
CREATE INDEX IF NOT EXISTS idx_memory_subject_links_atom ON memory_subject_links(atom_id);
CREATE INDEX IF NOT EXISTS idx_memory_subject_links_created_at ON memory_subject_links(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_subject_links_event_time ON memory_subject_links(event_time);

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

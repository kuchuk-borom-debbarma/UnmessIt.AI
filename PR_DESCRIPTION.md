# Pull Request Description

## Overview

This major update transforms UnmessIt.AI into a robust, multi-tenant, event-driven RAG application with a completely overhauled React frontend and fully dockerized deployment. The system now enforces strict per-user data isolation across all domains and introduces advanced retrieval tracing, context engineering, and comprehensive note management capabilities.

## Major Changes

### 1. Multi-Tenancy & Unified Auth
- Enforced strict `user_id` multi-tenancy across all core tables (notes, directories, tags, vectors, recall keys).
- Unified authentication state machine with local auth and decoupled notification interfaces.
- Included an automated migration script to assign existing data to a default user.

### 2. Event-Driven Ingestion & Note Management
- Extracted Notes into a dedicated service with an in-memory event bus that decouples note operations from RAG ingestion.
- Implemented comprehensive Folder CRUD, Note Pagination, and a Soft/Hard Delete Trash system.
- Added advanced Job Controls: users can now pause, stop, resume, and track detailed progress of background ingestion jobs.
- Display job status directly on note cards and jobs lists.

### 3. Advanced Retrieval & Context Engineering
- Replaced global memory with a dedicated, paginated Note Insights page (Recall Keys and Links).
- Introduced Context Engineering in the Ask View, providing transparency on token optimization and reduction metrics.
- Added an expandable Retrieval Analysis Trace in the Ask View, allowing users to see exactly how their query was broken down and searched.
- Optimized vector persistence by making the ChromaDB client a global singleton, preventing SQLite database locking issues.
- Fixed citation links to accurately point to specific `note_id`s.

### 4. UI/UX Rewrite & Polish
- Completely redesigned the Frontend using Vite, React, Tailwind CSS 4, and Framer Motion.
- Brand new public Landing Page with animated geometric showcases and user-centric features.
- Redesigned Ask View with modern animations, preserving query state across tab navigation.
- Added debounced loading spinners to prevent tab flickering and UI jumps.
- Configurable settings now support edit functionality and specify rate limits.

### 5. Deployment & Performance
- Introduced full dockerization with multi-stage builds for the backend server and Nginx for the frontend.
- Added necessary DB indexes to optimize performance for multi-tenant data access.
- Implemented `lru_cache` for user settings to speed up frequent lookups, clearing on preset updates.

## Verification

- `cd web && npm run build`
- `cd web && npm run lint`
- `cd server && uv run pytest src`

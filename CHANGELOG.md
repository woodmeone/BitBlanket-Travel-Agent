# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2025-02-04

### Added

#### Infrastructure Integration

- **Redis Memory Manager** (`agent/src/memory/redis_memory.py`)
  - Redis-backed conversation history storage
  - Session state management
  - User preferences with TTL
  - Automatic fallback to in-memory mode when Redis unavailable

- **Milvus RAG Retriever** (`agent/src/middleware/milvus_rag.py`)
  - Milvus vector database integration for semantic search
  - Hybrid retrieval (vector + keyword)
  - Automatic fallback to memory mode
  - Support for Chinese text keyword extraction

- **Config Hot-Reload** (`agent/src/infrastructure/config_hot_reload.py`)
  - Configuration hot-reload manager
  - Nacos configuration center integration
  - Local file monitoring
  - Event-based change notifications

#### Docker Infrastructure

- **docker-compose.infra.yaml**
  - Redis 7 (6379)
  - Milvus v2.5.10 (19530)
  - Nacos v2.3.2 (8848)
  - MySQL 8.0 for Nacos (3306)
  - MinIO for Milvus storage (9000)

### Changed

- Updated `pyproject.toml` to version 2.0.0
- Added infrastructure dependencies as optional
- Enhanced keyword extraction for Chinese text
- Improved documentation with RAG and hot-reload examples

### Fixed

- Fixed async Redis client issue (changed to sync import)
- Fixed Chinese keyword extraction using character n-gram fallback

---

## [1.0.0] - 2024-XX-XX

### Added

- Initial release with base functionality
- Five-layer architecture (Application → Algorithm → Middleware → Framework → Infrastructure)
- RAG retrieval with in-memory storage
- Streaming response support (SSE)
- Snowflake ID generation
- HTTP client utilities
- Prompt management system

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_paths_gin
  ON messages USING GIN (paths jsonb_path_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_fts
  ON messages USING GIN (to_tsvector('spanish', coalesce(content, '')));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_thread_not_deleted_created_part
  ON messages (thread_id, created_at DESC) WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_content_trgm
  ON messages USING GIN (content gin_trgm_ops);

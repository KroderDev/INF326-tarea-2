DROP INDEX IF EXISTS idx_messages_content_trgm;
DROP INDEX IF EXISTS idx_messages_thread_not_deleted_created_part;
DROP INDEX IF EXISTS idx_messages_fts;
DROP INDEX IF EXISTS idx_messages_paths_gin;
DROP EXTENSION IF EXISTS pg_trgm;

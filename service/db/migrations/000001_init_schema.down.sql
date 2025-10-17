DROP INDEX IF EXISTS idx_messages_content_lower;
DROP INDEX IF EXISTS idx_messages_created_at;
DROP INDEX IF EXISTS idx_messages_thread_seek;
DROP INDEX IF EXISTS idx_messages_user_created;
DROP INDEX IF EXISTS idx_messages_thread_not_deleted_created;
DROP INDEX IF EXISTS idx_messages_thread_type_created;
DROP INDEX IF EXISTS idx_messages_thread_user;
DROP TABLE IF EXISTS messages;

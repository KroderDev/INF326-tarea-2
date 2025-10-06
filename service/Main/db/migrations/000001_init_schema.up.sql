CREATE TABLE "messages" (
  "id" uuid PRIMARY KEY,
  "thread_id" uuid NOT NULL,
  "user_id" uuid NOT NULL,
  "type" enum,
  "content" text DEFAULT '',
  "paths" jsonb DEFAULT null,
  "created_at" timestampz,
  "updated_at" timestampz,
  "deleted_at" timestampz
);

CREATE INDEX "idx_messages_thread_user" ON "messages" ("thread_id", "user_id");

CREATE INDEX "idx_messages_thread_type_created" ON "messages" ("thread_id", "type", "created_at");

CREATE INDEX "idx_messages_thread_not_deleted_created" ON "messages" ("thread_id", "deleted_at", "created_at");

CREATE INDEX "idx_messages_user_created" ON "messages" ("user_id", "created_at");

CREATE INDEX "idx_messages_thread_seek" ON "messages" ("thread_id", "id");

CREATE INDEX "idx_messages_created_at" ON "messages" ("created_at");

CREATE INDEX "idx_messages_content_lower" ON "messages" ((lower(content)));

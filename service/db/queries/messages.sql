-- name: GetMessageByID :one
SELECT * FROM messages
WHERE id = $1;

-- name: GetMessageByIDForUpdate :one
SELECT * FROM messages
WHERE id = $1
FOR UPDATE;

-- name: CreateMessage :one
INSERT INTO messages (
  thread_id, user_id, type, content, paths, created_at, updated_at
) VALUES (
  $1, $2, $3, COALESCE($4, ''), $5, COALESCE($6, NOW()), COALESCE($7, NOW())
)
RETURNING *;

-- name: UpdateMessageContentAndPaths :one
UPDATE messages
SET
  content    = COALESCE($2, content),
  paths      = COALESCE($3, paths),
  updated_at = COALESCE($4, NOW())
WHERE id = $1
RETURNING *;

-- name: SoftDeleteMessage :one
UPDATE messages
SET deleted_at = COALESCE($2, NOW()),
    updated_at = NOW()
WHERE id = $1 AND deleted_at IS NULL
RETURNING *;

-- name: RestoreMessage :one
UPDATE messages
SET deleted_at = NULL,
    updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteMessageHard :exec
DELETE FROM messages
WHERE id = $1;

-- name: CountThreadMessages :one
SELECT count(*) FROM messages
WHERE thread_id = $1;

-- name: CountThreadMessagesNotDeleted :one
SELECT count(*) FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL;

-- name: CountUserMessages :one
SELECT count(*) FROM messages
WHERE user_id = $1;

-- name: ListThreadMessagesNotDeletedDescFirst :many
SELECT * FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT $2;

-- name: ListThreadMessagesNotDeletedDescBefore :many
SELECT * FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL
  AND (created_at, id) < ($2, $3)
ORDER BY created_at DESC, id DESC
LIMIT $4;

-- name: ListThreadMessagesSeekAfter :many
SELECT * FROM messages
WHERE thread_id = $1
  AND id > $2
ORDER BY id ASC
LIMIT $3;

-- name: ListThreadMessagesSeekBefore :many
SELECT * FROM messages
WHERE thread_id = $1
  AND id < $2
ORDER BY id DESC
LIMIT $3;

-- name: ListThreadMessagesByTypeDescFirst :many
SELECT * FROM messages
WHERE thread_id = $1
  AND type = $2
ORDER BY created_at DESC
LIMIT $3;

-- name: ListThreadMessagesByTypeDescBefore :many
SELECT * FROM messages
WHERE thread_id = $1
  AND type = $2
  AND (created_at, id) < ($3, $4)
ORDER BY created_at DESC, id DESC
LIMIT $5;

-- name: ListUserMessagesSince :many
SELECT * FROM messages
WHERE user_id = $1
  AND created_at >= $2
ORDER BY created_at DESC
LIMIT $3;

-- name: ListThreadMessagesByUser :many
SELECT * FROM messages
WHERE thread_id = $1
  AND user_id = $2
ORDER BY created_at DESC
LIMIT $3;

-- name: SearchThreadMessagesFTS :many
SELECT * FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL
  AND to_tsvector('spanish', coalesce(content, '')) @@ plainto_tsquery('spanish', $2)
ORDER BY created_at DESC
LIMIT $3;

-- name: SearchThreadMessagesTrgm :many
SELECT * FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL
  AND content ILIKE '%' || $2 || '%'
ORDER BY created_at DESC
LIMIT $3;

-- name: FindMessagesByContentLowerPrefix :many
SELECT * FROM messages
WHERE lower(content) LIKE lower($1) || '%'
ORDER BY created_at DESC
LIMIT $2;

-- name: ListThreadMessagesByPathContains :many
SELECT * FROM messages
WHERE thread_id = $1
  AND paths @> $2::jsonb
ORDER BY created_at DESC
LIMIT $3;

-- name: ListMessagesByCreatedAtRange :many
SELECT * FROM messages
WHERE created_at >= $1
  AND created_at < $2
ORDER BY created_at ASC
LIMIT $3;

-- name: GetLatestMessageInThread :one
SELECT * FROM messages
WHERE thread_id = $1
ORDER BY created_at DESC, id DESC
LIMIT 1;

-- name: GetLatestNotDeletedMessageInThread :one
SELECT * FROM messages
WHERE thread_id = $1
  AND deleted_at IS NULL
ORDER BY created_at DESC, id DESC
LIMIT 1;

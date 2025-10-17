postgres:
	docker run --name postgres-messages -p 5432:5432 -e POSTGRES_USER=root -e POSTGRES_PASSWORD=secret -d postgres:17-alpine

createdb:
	docker exec -it postgres-messages createdb --username=root --owner=root messages_service

dropdb:
	docker exec -it postgres-messages dropdb messages_service

migrateup:
	migrate -path db/migrations -database "postgresql://root:secret@localhost:5432/messages_service?sslmode=disable" -verbose up

migratedown:
	migrate -path db/migrations -database "postgresql://root:secret@localhost:5432/messages_service?sslmode=disable" -verbose down

sqlc:
	sqlc generate

deps:
	python -m pip install -r requirements.txt

compose:
	docker-compose up -d --build

compose-down:
	docker-compose down

image:
	docker build -t messages-service .

test:
	python -m pytest -q

print:
	python -m black .
	python -m isort .

.PHONY: postgres createdb dropdb migrateup migratedown sqlc deps compose compose-down image test print

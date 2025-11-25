deps:
	python -m pip install -r requirements.txt

up:
	docker-compose up -d --build

down:
	docker-compose down

restart:
	docker-compose down
	docker-compose up -d --build

image:
	docker build -t chat-utfsm .

print:
	python -m black .
	python -m isort .

.PHONY: deps up down restart image test print
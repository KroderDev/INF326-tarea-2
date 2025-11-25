deps:
	python -m pip install -r requirements.txt

up:
	docker-compose up -d --build

down:
	docker-compose down

image:
	docker build -t chat-utfsm .

print:
	python -m black .
	python -m isort .

.PHONY: deps up down image test print
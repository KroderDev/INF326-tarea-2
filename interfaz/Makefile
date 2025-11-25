deps:
	python -m pip install -r requirements.txt

compose:
	docker-compose up -d --build

compose-down:
	docker-compose down

image:
	docker build -t chat-utfsm .

print:
	python -m black .
	python -m isort .

.PHONY: deps compose compose-down image test print
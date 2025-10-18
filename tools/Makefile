PY ?= python
VENV_DIR ?= .venv-tools

ifeq ($(OS),Windows_NT)
  VENV_PY := $(VENV_DIR)/Scripts/python.exe
  VENV_PIP := $(VENV_DIR)/Scripts/pip.exe
  DELTREE := cmd /c rmdir /s /q
else
  VENV_PY := $(VENV_DIR)/bin/python
  VENV_PIP := $(VENV_DIR)/bin/pip
  DELTREE := rm -rf
endif

BASE_URL ?= http://127.0.0.1:3000
THREADS ?= 10
MESSAGES ?= 500
USERS ?= 10
CONCURRENCY ?= 100
TIMEOUT ?= 10

.PHONY: seed-install seed seed-medium seed-high seed-extreme seed-clean consume consume-medium consume-high consume-extreme

ifeq ($(OS),Windows_NT)
seed-install:
	@if not exist "$(VENV_PY)" ( $(PY) -m venv $(VENV_DIR) || "$(PY)" -m venv --clear $(VENV_DIR) || ( echo Failed to create venv. Run 'make seed-clean' and retry. & exit /b 1 ) )
	"$(VENV_PY)" -m pip install --upgrade pip
	"$(VENV_PIP)" install -r requirements.txt
else
seed-install:
	@if [ ! -x "$(VENV_PY)" ]; then \
		$(PY) -m venv $(VENV_DIR) || "$(PY)" -m venv --clear $(VENV_DIR) || (echo "Failed to create venv. Run 'make seed-clean' and retry." && exit 1); \
	fi
	"$(VENV_PY)" -m pip install --upgrade pip
	"$(VENV_PIP)" install -r requirements.txt
endif

seed: seed-install
	"$(VENV_PY)" seed_messages.py \
		--base-url $(BASE_URL) \
		--threads $(THREADS) \
		--messages $(MESSAGES) \
		--users $(USERS) \
		--concurrency $(CONCURRENCY) \
		--timeout $(TIMEOUT)

seed-medium: THREADS=10
seed-medium: MESSAGES=1000
seed-medium: CONCURRENCY=150
seed-medium: seed

seed-high: THREADS=20
seed-high: MESSAGES=1500
seed-high: CONCURRENCY=300
seed-high: seed

# Ajuste extremo (alto estrés)
seed-extreme: THREADS=30
seed-extreme: MESSAGES=10000
seed-extreme: CONCURRENCY=1000
seed-extreme: seed

seed-clean:
	-$(DELTREE) $(VENV_DIR)

# Consumers
consume: seed-install
	"$(VENV_PY)" consume_messages.py \
		--base-url $(BASE_URL) \
		--threads-file seed_threads.json \
		--reads 1000 \
		--concurrency $(CONCURRENCY) \
		--limit 50 \
		--timeout $(TIMEOUT)

consume-medium: CONCURRENCY=100
consume-medium: TIMEOUT=10
consume-medium: consume

consume-high: CONCURRENCY=200
consume-high: TIMEOUT=10
consume-high: consume

consume-extreme: CONCURRENCY=500
consume-extreme: TIMEOUT=10
consume-extreme: consume

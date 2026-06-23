ifeq ($(OS),Windows_NT)
PYTHON ?= python
VENV_PYTHON := .venv/Scripts/python.exe
else
PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
endif

.PHONY: setup run

setup: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt

$(VENV_PYTHON):
	$(PYTHON) -m venv .venv

run:
	$(VENV_PYTHON) -m uvicorn app.main:app

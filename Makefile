# Convenience wrappers around the backend virtualenv and the frontend test runner.
VENV := backend/.venv
PIP := $(VENV)/bin/pip

BUNDLES ?= 3
BANK ?= backend/data/tests_bundle_cache.json

.PHONY: help install run test test-backend test-frontend validate stats generate clean

help:
	@echo "make install       - create backend/.venv and install dependencies"
	@echo "make run           - run the API and serve the frontend on :5000"
	@echo "make test          - run both test suites"
	@echo "make test-backend  - run the pytest suite"
	@echo "make test-frontend - run the jsdom suite (needs npm)"
	@echo "make validate      - check the question bank against the schema"
	@echo "make stats         - summarise the question bank"
	@echo "make generate      - build a bank of original questions (BUNDLES=$(BUNDLES))"
	@echo "make clean         - remove the virtualenv, node_modules and caches"

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements-dev.txt

run: install
	cd backend && .venv/bin/python wsgi.py

test: test-backend test-frontend

test-backend: install
	cd backend && .venv/bin/python -m pytest

node_modules:
	npm install

test-frontend: node_modules
	npm test

validate: install
	cd backend && .venv/bin/python -m app.cli validate

stats: install
	cd backend && .venv/bin/python -m app.cli stats

generate: install
	cd backend && .venv/bin/python -m app.cli generate --bundles $(BUNDLES) --force

clean:
	rm -rf $(VENV) backend/.pytest_cache node_modules
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

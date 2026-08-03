.PHONY: install run test lint format typecheck infra-up infra-down

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn tal.main:app --reload

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

typecheck:
	mypy

infra-up:
	docker compose up -d

infra-down:
	docker compose down


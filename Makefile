.PHONY: dev db migrate seed test

db:
	docker compose up -d

db-down:
	docker compose down

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python -m cbrain.db.seed

dev:
	uvicorn cbrain.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

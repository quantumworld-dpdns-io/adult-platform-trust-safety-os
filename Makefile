.PHONY: install dev test test-unit test-integration test-security test-e2e lint format typecheck security build docker release docs

install:
	pip install -e ".[dev,full]"

install-dev:
	pip install -e ".[dev]"

dev:
	docker compose up -d
	uvicorn src.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000

test:
	pytest --cov=src --cov-report=term-missing --cov-report=html -n auto

test-unit:
	pytest tests/unit -m unit -v

test-integration:
	pytest tests/integration -m integration -v

test-security:
	cd tests/robot && robot --loglevel DEBUG run_all_security.robot

test-e2e:
	pytest tests/e2e -m e2e -v

test-quantum:
	pytest tests/quantum -m quantum -v

test-performance:
	locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff check --fix src tests
	ruff format src tests

typecheck:
	mypy src

security:
	bandit -r src -c pyproject.toml
	pip-audit
	detect-secrets scan

security-scan:
	bandit -r src -c pyproject.toml -f json -o bandit-report.json
	pip-audit --output pip-audit-report.json

build:
	python -m build

docker:
	docker build -t adult-platform-trust-safety:latest -f deploy/docker/Dockerfile .

docker-push:
	docker build -t ghcr.io/quantumworld-dpdns-io/adult-platform-trust-safety:latest -f deploy/docker/Dockerfile .
	docker push ghcr.io/quantumworld-dpdns-io/adult-platform-trust-safety:latest

release:
	scripts/release.sh

docs:
	mkdocs serve

docs-build:
	mkdocs build

helm-template:
	helm template adult-platform-trust-safety deploy/helm/adult-platform-trust-safety

helm-install:
	helm install adult-platform-trust-safety deploy/helm/adult-platform-trust-safety -f deploy/helm/adult-platform-trust-safety/values.yaml

robot-tests:
	cd tests/robot && robot run_all_security.robot

robot-owasp:
	cd tests/robot && robot run_owasp.robot

robot-functional:
	cd tests/robot && robot run_functional.robot

robot-api:
	cd tests/robot && robot run_api_security.robot

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .pytest_cache htmlcov .coverage dist build *.egg-info

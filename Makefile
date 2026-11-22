# airflow-ml convenience commands
#
#   make build    - build airflow image (3.3.1 + providers) and job-runner image
#   make up       - start the stack (postgres, redis, minio, airflow)
#   make unpause  - unpause DAGs so they can run
#   make trigger  - trigger a DAG run        (DAG_ID=ml_pipeline_example make trigger)
#   make runinfo  - show runs/tasks for a DAG
#   make status   - container status/health
#   make logs     - tail logs                (SERVICE=airflow-worker make logs)
#   make down     - stop the stack (volumes kept; use `docker volume rm` to wipe)
AIRFLOW_HOST ?= http://localhost:2405
SHELL := /bin/bash
COMPOSE ?= docker compose
AIRFLOW_USER ?= airflow
AIRFLOW_PASS ?= airflow
DAG_ID ?= ml_pipeline_example
SERVICE ?= airflow-worker
POLL ?= 15

.PHONY: help build jobs up down status logs trigger unpause runinfo wipe

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

build: ## Build airflow + job-runner images
	$(COMPOSE) build
	$(COMPOSE) --profile build build jobrunner

jobs: ## Build only the job-runner image
	$(COMPOSE) --profile build build jobrunner

up: ## Start the stack
	$(COMPOSE) up -d

down: ## Stop the stack
	$(COMPOSE) down

wipe: ## FULLY wipe the stack: containers + named volumes (DESTROYS all data)
	$(COMPOSE) down -v
	@for v in $$(docker volume ls --filter name=airflow-ml_ -q); do docker volume rm $$v >/dev/null 2>&1 || true; done
	@echo "volumes removed; images remain (docker image prune / rmi to drop them)"

status: ## Container status and health
	$(COMPOSE) ps

logs: ## Tail service logs (SERVICE=airflow-worker)
	$(COMPOSE) logs -f --tail=200 $(SERVICE)

token: ## (helper) fetch API token to /tmp/.airflow-ml-token
	@token=$$(curl -s -X POST $(AIRFLOW_HOST)/auth/token -H 'Content-Type: application/json' -d '{"username":"$(AIRFLOW_USER)","password":"$(AIRFLOW_PASS)"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])') && \
		printf '%s' "$$token" > /tmp/.airflow-ml-token && \
		echo "token cached"

unpause: token ## Unpause a DAG (DAG_ID=...)
	@curl -s -X PATCH $(AIRFLOW_HOST)/api/v2/dags/$(DAG_ID) \
		-H "Authorization: Bearer $$(cat /tmp/.airflow-ml-token)" \
		-H 'Content-Type: application/json' -d '{"is_paused": false}' | python3 -m json.tool

trigger: token ## Trigger a DAG run (DAG_ID=...)
	@curl -s -X POST $(AIRFLOW_HOST)/api/v2/dags/$(DAG_ID)/dagRuns \
		-H "Authorization: Bearer $$(cat /tmp/.airflow-ml-token)" \
		-H 'Content-Type: application/json' -d "{\"logical_date\": \"$$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" | python3 -m json.tool

runinfo: token ## Show latest DAG runs + task states (DAG_ID=...)
	@python3 scripts/runinfo.py "$$(cat /tmp/.airflow-ml-token)" "$(DAG_ID)" "$(AIRFLOW_HOST)"
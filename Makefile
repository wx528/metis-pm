# Metis PM v2.0 - Docker Compose Management

COMPOSE = docker compose

.PHONY: up down logs clean build help

up:
	@echo "Starting services..."
	$(COMPOSE) up -d

build:
	@echo "Building Docker images..."
	$(COMPOSE) build

down:
	@echo "Stopping and removing containers..."
	$(COMPOSE) down

logs:
	@echo "Viewing all service logs..."
	$(COMPOSE) logs -f

clean:
	@echo "Cleaning containers, volumes, and orphans..."
	$(COMPOSE) down -v --remove-orphans

help:
	@echo "Available commands:"
	@echo ""
	@echo "  make up      - Start all services"
	@echo "  make build   - Build Docker images"
	@echo "  make down    - Stop and remove containers"
	@echo "  make logs    - View all service logs"
	@echo "  make clean   - Remove containers, volumes, and orphans"

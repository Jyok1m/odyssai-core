# Makefile for Odyssai
# Usage: make [target]

.PHONY: help dev prod docker docker-dev clean install setup test

# Variables
PORT ?= 9000
CONDA_ENV = odyssai

# Colors for display
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Show this help
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)       Odyssai - Makefile Help         $(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Variables:$(NC)"
	@echo "  $(GREEN)PORT$(NC)        Port to use (default: 9000)"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make dev"
	@echo "  make prod PORT=8080"
	@echo "  make docker"

setup: ## Create conda environment from environment.yml
	@echo "$(BLUE)🔧 Setting up conda environment...$(NC)"
	conda env create -f environment.yml
	@echo "$(GREEN)✅ Conda environment created$(NC)"

install: ## Install dependencies in existing environment
	@echo "$(BLUE)📦 Installing dependencies...$(NC)"
	conda env update -f environment.yml
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

dev: ## Start in development mode
	@echo "$(BLUE)🚀 Starting in development mode...$(NC)"
	@echo "$(YELLOW)Port: $(PORT)$(NC)"
	@echo "$(YELLOW)URL: http://localhost:$(PORT)$(NC)"
	@echo ""
	@eval "$$(conda shell.bash hook)" && \
	conda activate $(CONDA_ENV) && \
	export PYTHONPATH=./src && \
	export BACKEND_PORT=$(PORT) && \
	python src/odyssai_core/app.py

prod: ## Start in production mode with Gunicorn
	@echo "$(BLUE)🚀 Starting in production mode...$(NC)"
	@echo "$(YELLOW)Port: $(PORT)$(NC)"
	@echo "$(YELLOW)URL: http://localhost:$(PORT)$(NC)"
	@echo ""
	@eval "$$(conda shell.bash hook)" && \
	conda activate $(CONDA_ENV) && \
	export PYTHONPATH=./src && \
	export BACKEND_PORT=$(PORT) && \
	gunicorn -c gunicorn.conf.py src.odyssai_core.app:app

docker: ## Start with Docker Compose
	@echo "$(BLUE)🐳 Starting with Docker...$(NC)"
	docker-compose down
	docker-compose up --build

docker-dev: ## Start with Docker Compose in development mode (detached)
	@echo "$(BLUE)🐳 Starting with Docker in development mode...$(NC)"
	docker-compose down
	docker-compose up --build -d
	@echo "$(GREEN)✅ Containers started in background$(NC)"
	@echo "$(YELLOW)URL: http://localhost$(NC)"
	@echo ""
	@echo "$(BLUE)Useful commands:$(NC)"
	@echo "  docker-compose logs -f    # View logs"
	@echo "  docker-compose down       # Stop containers"
	@echo "  docker-compose ps         # View container status"

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-stop: ## Stop Docker containers
	docker-compose down

docker-ps: ## View Docker container status
	docker-compose ps

test: ## Run tests (to be implemented)
	@echo "$(YELLOW)⚠️  Tests not yet implemented$(NC)"
	@eval "$$(conda shell.bash hook)" && \
	conda activate $(CONDA_ENV) && \
	export PYTHONPATH=./src

clean: ## Clean temporary files and caches
	@echo "$(BLUE)🧹 Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

docker-clean: ## Clean Docker images and containers
	@echo "$(BLUE)🧹 Cleaning Docker...$(NC)"
	docker-compose down --rmi all --volumes --remove-orphans
	@echo "$(GREEN)✅ Docker cleanup completed$(NC)"

env-info: ## Display environment information
	@echo "$(BLUE)📋 Environment information:$(NC)"
	@echo "$(YELLOW)Python:$(NC)"
	@eval "$$(conda shell.bash hook)" && conda activate $(CONDA_ENV) && export PYTHONPATH=./src && python --version
	@echo "$(YELLOW)Conda environment:$(NC)"
	@conda info --envs | grep $(CONDA_ENV) || echo "Environment $(CONDA_ENV) not found"
	@echo "$(YELLOW)Docker:$(NC)"
	@docker --version 2>/dev/null || echo "Docker not installed"
	@echo "$(YELLOW)Docker Compose:$(NC)"
	@docker-compose --version 2>/dev/null || echo "Docker Compose not installed"

# Default target
.DEFAULT_GOAL := help

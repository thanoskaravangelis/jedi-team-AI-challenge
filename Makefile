.PHONY: help install init serve test evaluate clean docker-build docker-run docker-stop

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install Python dependencies"
	@echo "  install-minimal - Install minimal dependencies (if full fails)"
	@echo "  install-safe - Try full install with fallback to minimal"
	@echo "  init         - Initialize database with market research data"
	@echo "  serve        - Start the API server"
	@echo "  test         - Run the test suite"
	@echo "  evaluate     - Run comprehensive evaluation report"
	@echo "  evaluate-json - Run evaluation with JSON output"
	@echo "  evaluate-week - Run evaluation for last 7 days"
	@echo "  evaluate-docker - Run evaluation inside Docker container"
	@echo "  clean        - Clean up generated files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run with Docker Compose"
	@echo "  docker-stop  - Stop Docker containers"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code with black"

# Python environment setup
install:
	pip install -r requirements.txt

# Install minimal requirements (if full install fails)
install-minimal:
	pip install -r requirements-minimal.txt

# Try full install with fallback to minimal
install-safe:
	pip install -r requirements.txt || pip install -r requirements-minimal.txt

# Initialize the system
init:
	python main.py init

# Start the server (with initialization)
serve:
	python main.py serve

# Start the server (skip initialization)
serve-quick:
	python main.py serve --skip-init

# Run tests
test:
	python main.py test

# Run evaluation
evaluate:
	python evaluate.py

# Run evaluation with JSON output
evaluate-json:
	python evaluate.py --format json

# Run evaluation for specific period
evaluate-week:
	python evaluate.py --days 7

# Run evaluation inside Docker
evaluate-docker:
	docker-compose exec jedi-agent python /app/evaluate.py

# Code quality
lint:
	flake8 app/ tests/ --max-line-length=100 --ignore=E203,W503

# Cleanup
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf *.egg-info/
	rm -f jedi_agent.db
	rm -f test_jedi_agent.db
	rm -rf vector_db/
	rm -rf test_vector_db/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.db" -delete

# Docker commands
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-build-and-run:
	docker-compose up --build -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Development helpers
dev-setup: install init
	@echo "Development environment ready!"

# Production helpers
prod-check: lint test
	@echo "Production checks passed!"

# Database operations
reset-db:
	rm -f jedi_agent.db
	rm -rf data/vector_db/
	python main.py init

# Full reset and restart
restart: clean reset-db serve

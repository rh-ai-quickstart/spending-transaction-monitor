# OpenShift Deployment Makefile for Spending Transaction Monitor

# Configuration
PROJECT_NAME = spending-monitor
REGISTRY_URL ?= quay.io
REPOSITORY ?= rh-ai-quickstart
NAMESPACE ?= spending-transaction-monitor
IMAGE_TAG ?= latest
GIT_BRANCH ?= main

# Component image names
UI_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-ui:$(IMAGE_TAG)
API_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-api:$(IMAGE_TAG)
DB_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-db:$(IMAGE_TAG)

# Environment file paths
ENV_FILE_DEV = .env.development
ENV_FILE_PROD = .env.production
ENV_FILE = $(ENV_FILE_DEV)  # Default to development for backwards compatibility

# Helper function to generate helm parameters from environment variables
define HELM_SECRET_PARAMS
--set secrets.POSTGRES_DB="$$POSTGRES_DB" \
--set secrets.POSTGRES_USER="$$POSTGRES_USER" \
--set secrets.POSTGRES_PASSWORD="$$POSTGRES_PASSWORD" \
--set secrets.DATABASE_URL="$$DATABASE_URL" \
--set secrets.API_KEY="$$API_KEY" \
--set secrets.BASE_URL="$$BASE_URL" \
--set secrets.LLM_PROVIDER="$$LLM_PROVIDER" \
--set secrets.MODEL="$$MODEL" \
--set secrets.ENVIRONMENT="$$ENVIRONMENT" \
--set secrets.DEBUG="$$DEBUG" \
--set secrets.BYPASS_AUTH="$$BYPASS_AUTH" \
--set secrets.CORS_ALLOWED_ORIGINS="$${CORS_ALLOWED_ORIGINS//,/\\,}" \
--set secrets.ALLOWED_ORIGINS="$${ALLOWED_ORIGINS//,/\\,}" \
--set secrets.SMTP_HOST="$$SMTP_HOST" \
--set secrets.SMTP_PORT="$$SMTP_PORT" \
--set secrets.SMTP_FROM_EMAIL="$$SMTP_FROM_EMAIL" \
--set secrets.SMTP_USE_TLS="$$SMTP_USE_TLS" \
--set secrets.SMTP_USE_SSL="$$SMTP_USE_SSL" \
--set secrets.KEYCLOAK_URL="$$KEYCLOAK_URL" \
--set secrets.KEYCLOAK_REALM="$$KEYCLOAK_REALM" \
--set secrets.KEYCLOAK_CLIENT_ID="$$KEYCLOAK_CLIENT_ID" \
--set secrets.VITE_API_BASE_URL="$$VITE_API_BASE_URL"
endef

# Default target when running 'make' without arguments
.DEFAULT_GOAL := help

# Check if development environment file exists
.PHONY: check-env-dev
check-env-dev:
	@if [ ! -f "$(ENV_FILE_DEV)" ]; then \
		echo "❌ Error: Development environment file not found at $(ENV_FILE_DEV)"; \
		echo ""; \
		echo "Please create the development environment file by copying the example:"; \
		echo "  cp env.example $(ENV_FILE_DEV)"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Development environment file found at $(ENV_FILE_DEV)"

# Check if production environment file exists  
.PHONY: check-env-prod
check-env-prod:
	@if [ ! -f "$(ENV_FILE_PROD)" ]; then \
		echo "❌ Error: Production environment file not found at $(ENV_FILE_PROD)"; \
		echo ""; \
		echo "Please create the production environment file by copying the example:"; \
		echo "  cp env.example $(ENV_FILE_PROD)"; \
		echo ""; \
		echo "Remember to update production values:"; \
		echo "  - Set ENVIRONMENT=production"; \
		echo "  - Set BYPASS_AUTH=false"; \
		echo "  - Use strong production passwords"; \
		echo "  - Update DATABASE_URL to use Kubernetes service names"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Production environment file found at $(ENV_FILE_PROD)"

# Set up environment file for local development
.PHONY: setup-dev-env
setup-dev-env: check-env-dev
	@echo "Using development environment file: $(ENV_FILE_DEV)"
	@echo "✅ Development environment file is ready"

# Create environment file from example
.PHONY: create-env-file
create-env-file:
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file already exists at $(ENV_FILE)"; \
		echo "Remove it first if you want to recreate it."; \
		exit 1; \
	fi
	@echo "📄 Creating environment file from example..."
	@cp env.example "$(ENV_FILE)"
	@echo "✅ Environment file created at $(ENV_FILE)"
	@echo ""
	@echo "🔧 Please edit .env and update the following required values:"
	@echo "  - API_KEY: Your OpenAI API key"
	@echo "  - POSTGRES_PASSWORD: Your desired database password"
	@echo "  - Other values as needed for your environment"

# Default target
.PHONY: help
help:
	@echo "Spending Transaction Monitor - Makefile Commands"
	@echo ""
	@echo "🚀 Common Commands:"
	@echo "  Local Development:"
	@echo "    make build-run-local              Build & run with Keycloak (default)"
	@echo "    make build-run-local MODE=noauth  Build & run with auth bypass"
	@echo "    make setup-keycloak               Setup Keycloak with DB users"
	@echo "    make stop-local                   Stop local services"
	@echo ""
	@echo "  OpenShift Deployment:"
	@echo "    make deploy MODE=noauth           Deploy with auth bypass"
	@echo "    make deploy MODE=keycloak         Deploy with Keycloak"
	@echo "    make deploy MODE=dev              Deploy with reduced resources"
	@echo "    make undeploy                     Remove deployment"
	@echo ""
	@echo "📦 Build & Push:"
	@echo "  make build-all        Build all images"
	@echo "  make push-all         Push all images to registry"
	@echo "  make deploy-all       Build, push, and deploy"
	@echo ""
	@echo "🗄️  Data Management:"
	@echo "  make seed-db                      Seed database"
	@echo "  make seed-keycloak-with-users     Setup Keycloak + sync users"
	@echo "  make setup-data                   Migrate + seed all"
	@echo ""
	@echo "🔧 Utilities:"
	@echo "  make status           Show deployment status"
	@echo "  make logs-local       Show local service logs"
	@echo "  make helm-lint        Lint Helm chart"
	@echo "  make clean-all        Clean up all resources"
	@echo ""
	@echo "📝 Environment Files:"
	@echo "  .env.development      Local development"
	@echo "  .env.production       OpenShift deployment"
	@echo ""
	@echo "💡 Examples:"
	@echo "  make build-run-local MODE=noauth"
	@echo "  make deploy MODE=keycloak NAMESPACE=my-app"

# Login to OpenShift registry
.PHONY: login
login:
	@echo "Logging into OpenShift registry..."
	@oc whoami --show-token | podman login --username=$(shell oc whoami) --password-stdin $(REGISTRY_URL)

# Create OpenShift project
.PHONY: create-project
create-project:
	@echo "Creating OpenShift project: $(NAMESPACE)"
	@oc new-project $(NAMESPACE) || echo "Project $(NAMESPACE) already exists"

# Build targets
.PHONY: build-ui
build-ui:
	@echo "Building UI image..."
	podman build --platform=linux/amd64 -t $(UI_IMAGE) -f ./packages/ui/Containerfile .

.PHONY: build-api
build-api:
	@echo "Building API image..."
	podman build --platform=linux/amd64 -t $(API_IMAGE) -f ./packages/api/Containerfile .

.PHONY: build-db
build-db:
	@echo "Building database image..."
	podman build --platform=linux/amd64 -t $(DB_IMAGE) -f ./packages/db/Containerfile .

.PHONY: build-all
build-all: build-ui build-api build-db
	@echo "All images built successfully"

# Push targets
.PHONY: push-ui
push-ui: build-ui
	@echo "Pushing UI image..."
	podman push $(UI_IMAGE)

.PHONY: push-api
push-api: build-api
	@echo "Pushing API image..."
	podman push $(API_IMAGE)

.PHONY: push-db
push-db: build-db
	@echo "Pushing database image..."
	podman push $(DB_IMAGE)

.PHONY: push-all
push-all: push-ui push-api push-db
	@echo "All images pushed successfully"

# Deploy targets
# Usage: make deploy [MODE=noauth|keycloak|dev]
# Examples:
#   make deploy                  # Deploy with production settings
#   make deploy MODE=noauth      # Deploy with auth bypass (dev/testing)
#   make deploy MODE=keycloak    # Deploy with Keycloak authentication
#   make deploy MODE=dev         # Deploy with reduced resources

MODE ?= default

.PHONY: deploy
deploy: create-project
ifeq ($(MODE),noauth)
	@echo "🔓 Deploying with AUTH BYPASS (development/testing)..."
	@echo "⚠️  WARNING: Authentication is DISABLED"
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-dev-noauth.yaml \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG)
	@echo "✅ Deployment complete (no-auth mode)"
	@echo "📍 Route: oc get route $(PROJECT_NAME)-nginx-route -n $(NAMESPACE)"
else ifeq ($(MODE),keycloak)
	$(MAKE) check-env-prod
	@echo "🔐 Deploying with KEYCLOAK AUTHENTICATION..."
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-keycloak.yaml \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)
	@echo "✅ Deployment complete (Keycloak auth)"
	@echo "📍 Route: oc get route $(PROJECT_NAME)-nginx-route -n $(NAMESPACE)"
else ifeq ($(MODE),dev)
	$(MAKE) check-env-prod
	@echo "⚙️  Deploying with REDUCED RESOURCES (dev mode)..."
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		--set database.persistence.enabled=false \
		--set api.replicas=1 \
		--set ui.replicas=1 \
		$(HELM_SECRET_PARAMS)
	@echo "✅ Deployment complete (dev mode)"
else
	$(MAKE) check-env-prod
	@echo "🚀 Deploying with PRODUCTION SETTINGS..."
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)
	@echo "✅ Deployment complete (production)"
endif

.PHONY: deploy-all
deploy-all: build-all push-all deploy
	@echo "Complete deployment finished successfully"

# Undeploy targets
.PHONY: undeploy
undeploy:
	@echo "Undeploying application..."
	helm uninstall $(PROJECT_NAME) --namespace $(NAMESPACE) || echo "Release $(PROJECT_NAME) not found"

.PHONY: undeploy-all
undeploy-all: undeploy
	@echo "Cleaning up namespace..."
	oc delete project $(NAMESPACE) || echo "Project $(NAMESPACE) not found or cannot be deleted"

# Full deployment pipeline
.PHONY: full-deploy
full-deploy: login create-project build-all push-all deploy
	@echo "Full deployment completed!"

# Development helpers
.PHONY: port-forward-api
port-forward-api:
	@echo "Port forwarding API service to localhost:8000..."
	oc port-forward service/spending-monitor-api 8000:8000 --namespace $(NAMESPACE)

.PHONY: port-forward-ui
port-forward-ui:
	@echo "Port forwarding UI service to localhost:8080..."
	oc port-forward service/spending-monitor-ui 8080:8080 --namespace $(NAMESPACE)

.PHONY: port-forward-db
port-forward-db:
	@echo "Port forwarding database service to localhost:5432..."
	oc port-forward service/spending-monitor-db 5432:5432 --namespace $(NAMESPACE)

# Helm helpers
.PHONY: helm-lint
helm-lint:
	@echo "Linting Helm chart..."
	helm lint ./deploy/helm/spending-monitor

.PHONY: helm-template
helm-template: check-env-prod
	@echo "Rendering Helm templates with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm template $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)

.PHONY: helm-debug
helm-debug: check-env-prod
	@echo "Debugging Helm deployment with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS) \
		--dry-run --debug

# Clean up targets
.PHONY: clean-images
clean-images:
	@echo "Cleaning up local images..."
	@podman rmi $(UI_IMAGE) $(API_IMAGE) $(DB_IMAGE) || true

.PHONY: clean-local-images
clean-local-images:
	@echo "Cleaning up local development images..."
	@podman rmi spending-monitor-ui:local spending-monitor-api:local spending-monitor-db:local || true

.PHONY: clean-all
clean-all: undeploy-all clean-images clean-local-images
	@echo "Complete cleanup finished"

# Status and logs
.PHONY: status
status:
	@echo "Checking application status..."
	@helm status $(PROJECT_NAME) --namespace $(NAMESPACE) || echo "Release not found"
	@echo "\nPod status:"
	@oc get pods --namespace $(NAMESPACE) || echo "No pods found"
	@echo "\nServices:"
	@oc get svc --namespace $(NAMESPACE) || echo "No services found"
	@echo "\nIngress:"
	@oc get ingress --namespace $(NAMESPACE) || echo "No ingress found"

.PHONY: logs
logs:
	@echo "Getting application logs..."
	@echo "=== API Logs ==="
	@oc logs -l app.kubernetes.io/component=api --namespace $(NAMESPACE) --tail=20 || echo "No API logs found"
	@echo "\n=== UI Logs ==="
	@oc logs -l app.kubernetes.io/component=ui --namespace $(NAMESPACE) --tail=20 || echo "No UI logs found"
	@echo "\n=== Database Logs ==="
	@oc logs -l app.kubernetes.io/component=database --namespace $(NAMESPACE) --tail=20 || echo "No database logs found"

.PHONY: logs-ui
logs-ui:
	@oc logs -f -l app.kubernetes.io/component=ui --namespace $(NAMESPACE)

.PHONY: logs-api
logs-api:
	@oc logs -f -l app.kubernetes.io/component=api --namespace $(NAMESPACE)

.PHONY: logs-db
logs-db:
	@oc logs -f -l app.kubernetes.io/component=database --namespace $(NAMESPACE)

# Local development targets using Podman Compose
.PHONY: run-local
run-local: setup-dev-env
	@echo "Starting all services locally with Podman Compose using development environment..."
	@echo "Using development environment file: $(ENV_FILE_DEV)"
	@echo "This will start: PostgreSQL, API, UI, nginx proxy, and SMTP server"
	@echo "Services will be available at:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - API (proxied): http://localhost:3000/api/*"
	@echo "  - API (direct): http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - SMTP Web UI: http://localhost:3002"
	@echo "  - Database: localhost:5432"
	@echo ""
	@echo "Pulling latest images from quay.io registry..."
	IMAGE_TAG=latest podman-compose -f podman-compose.yml pull
	IMAGE_TAG=latest podman-compose -f podman-compose.yml up -d
	@echo ""
	@echo "Waiting for database to be ready..."
	@sleep 15
	@echo ""
	@echo "✅ All services started and database is ready!"
	@echo ""
	@echo "To also start pgAdmin for database management, run:"
	@echo "  podman-compose -f podman-compose.yml --profile tools up -d pgadmin"
	@echo "  Then access pgAdmin at: http://localhost:8080"
	@echo ""
	@echo "To view logs: make logs-local"
	@echo "To stop services: make stop-local"

.PHONY: stop-local
stop-local:
	@echo "Stopping local Podman Compose services..."
	podman-compose -f podman-compose.yml down
	@echo "Removing db data..."
	podman volume rm --all || true

.PHONY: build-local
build-local:
	@echo "Building local Podman images with 'local' tag..."
	podman-compose -f podman-compose.yml -f podman-compose.build.yml build
	@echo "✅ Local images built successfully"

.PHONY: pull-local
pull-local:
	@echo "Pulling latest images from quay.io registry..."
	IMAGE_TAG=latest podman-compose -f podman-compose.yml pull

.PHONY: logs-local
logs-local:
	@echo "Showing logs from local services..."
	podman-compose -f podman-compose.yml logs -f

.PHONY: reset-local
reset-local: setup-dev-env
	@echo "Resetting local environment..."
	@echo "This will stop services, remove containers and volumes, pull latest images, and restart"
	podman-compose -f podman-compose.yml down -v
	@echo "Pulling latest images from quay.io registry..."
	IMAGE_TAG=latest podman-compose -f podman-compose.yml pull
	IMAGE_TAG=latest podman-compose -f podman-compose.yml up -d
	@echo ""
	@echo "Waiting for database to be ready..."
	@sleep 15
	@echo "Running database migrations..."
	@pnpm db:upgrade || (echo "❌ Database upgrade failed. Check if database is running." && exit 1)
	@echo "Seeding database with test data..."
	@pnpm db:seed || (echo "❌ Database seeding failed. Check migration status." && exit 1)
	@echo ""
	@echo "✅ Local environment has been reset and database is ready!"

# Clean UI images to ensure fresh build with correct environment variables
.PHONY: clean-ui-images
clean-ui-images:
	@echo "🗑️  Removing old UI images to ensure clean build..."
	@podman rmi -f spending-monitor-ui:local localhost/spending-transaction-monitor_ui:latest 2>/dev/null || true
	@echo "✅ UI images removed"

# Helper target for building local images (used by build-run-local and build-run-local-noauth)
.PHONY: build-local-images
build-local-images: setup-dev-env clean-ui-images
	@echo "🔨 Building images (environment-agnostic)..."
	podman-compose -f podman-compose.yml -f podman-compose.build.yml build --no-cache migrations api ui
	@echo "✅ Images built successfully"

# Build and run locally
# Usage: make build-run-local [MODE=noauth]
# Examples:
#   make build-run-local              # Build and run with Keycloak auth (default)
#   make build-run-local MODE=noauth  # Build and run with auth bypass

.PHONY: build-run-local
build-run-local: build-local-images
ifeq ($(MODE),noauth)
	@echo ""
	@echo "✅ Starting with AUTH BYPASS (runtime config)..."
	@echo "   - No login required"
	@echo "   - Yellow dev banner visible"
	@echo "   - Frontend: http://localhost:3000"
	@echo "   - API (proxied): http://localhost:3000/api/*"
	@echo "   - API (direct): http://localhost:8000"
	@echo ""
	IMAGE_TAG=local BYPASS_AUTH=true VITE_BYPASS_AUTH=true VITE_ENVIRONMENT=development \
		podman-compose -f podman-compose.yml up -d --no-build
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo "Running database migrations..."
	@pnpm db:upgrade || (echo "❌ Database upgrade failed." && exit 1)
	@echo "Seeding database with test data..."
	@pnpm db:seed || (echo "❌ Database seeding failed." && exit 1)
	@echo "✅ All services started and database ready!"
else
	@echo ""
	@echo "✅ Starting with KEYCLOAK AUTHENTICATION (runtime config)..."
	@echo "   - Login required (user1@example.com / password123)"
	@echo "   - Keycloak authentication enabled"
	@echo "   - Frontend: http://localhost:3000"
	@echo "   - API (proxied): http://localhost:3000/api/*"
	@echo "   - API (direct): http://localhost:8000"
	@echo "   - Keycloak: http://localhost:8080"
	@echo ""
	IMAGE_TAG=local BYPASS_AUTH=false VITE_BYPASS_AUTH=false VITE_ENVIRONMENT=staging \
		podman-compose -f podman-compose.yml up -d --no-build
	@echo "✅ Services started with Keycloak!"
	@echo "Setup Keycloak: make setup-keycloak"
endif
	@echo ""
	@echo "💡 To view logs: make logs-local"
	@echo "💡 To stop: make stop-local"

# Setup Keycloak with database users using pnpm
.PHONY: setup-keycloak
setup-keycloak: setup-dev-env
	@echo "Setting up Keycloak with database users using pnpm..."
	@echo "Waiting for Keycloak to be ready..."
	@timeout 60 bash -c 'until curl -sf http://localhost:8080/health/ready >/dev/null 2>&1; do sleep 2; done' || (echo "❌ Keycloak not ready after 60s" && exit 1)
	@echo "Keycloak is ready, running setup..."
	pnpm auth:setup-keycloak-with-users
	@echo "✅ Keycloak setup completed!"

.PHONY: setup-local
setup-local: check-env-dev pull-local run-local
	@echo "✅ Local development environment is fully set up and ready!"
	@echo "Database has been migrated and seeded with test data."

# Seeding targets
.PHONY: seed-db
seed-db:
	@echo "🌱 Seeding database with sample data..."
	@echo "Running seed script inside API container..."
	podman exec spending-monitor-api python -m db.scripts.seed
	@echo "✅ Database seeded successfully"

.PHONY: seed-keycloak
seed-keycloak:
	@echo "🔐 Setting up Keycloak realm..."
	pnpm seed:keycloak

.PHONY: seed-keycloak-with-users
seed-keycloak-with-users:
	@echo "🔐 Setting up Keycloak realm and syncing database users..."
	pnpm seed:keycloak-with-users

.PHONY: seed-all
seed-all: seed-keycloak-with-users seed-db
	@echo "✅ All data seeded successfully (database + Keycloak)"

.PHONY: setup-data
setup-data:
	@echo "🚀 Setting up data: Running migrations, then seeding database and Keycloak..."
	pnpm setup:data
# OpenShift Deployment Makefile for Spending Transaction Monitor

# Configuration
PROJECT_NAME = spending-monitor
REGISTRY_URL ?= quay.io
REPOSITORY ?= rh-ai-quickstart
NAMESPACE ?= spending-transaction-monitor
IMAGE_TAG ?= latest

# Component image names
UI_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-ui:$(IMAGE_TAG)
API_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-api:$(IMAGE_TAG)
DB_IMAGE = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-db:$(IMAGE_TAG)

# Local development image names (tagged as 'local')
UI_IMAGE_LOCAL = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-ui:local
API_IMAGE_LOCAL = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-api:local
DB_IMAGE_LOCAL = $(REGISTRY_URL)/$(REPOSITORY)/$(PROJECT_NAME)-db:local

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

# Check if environment file exists
.PHONY: check-env-file
check-env-file:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "❌ Error: Environment file not found at $(ENV_FILE)"; \
		echo ""; \
		echo "Please create the environment file by copying the example:"; \
		echo "  cp env.example $(ENV_FILE)"; \
		echo ""; \
		echo "Then edit $(ENV_FILE) and update the values for your environment."; \
		echo ""; \
		echo "Key variables to update:"; \
		echo "  - API_KEY: Your OpenAI API key"; \
		echo "  - BASE_URL: Your LLM provider base URL"; \
		echo "  - POSTGRES_PASSWORD: Your database password"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Environment file found at $(ENV_FILE)"

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

# List available alert rule samples
.PHONY: list-alert-samples
list-alert-samples:
	@echo "📋 Available Alert Rule Sample Files:"
	@echo "============================================"
	@echo ""
	@for file in packages/db/src/db/scripts/json/*.json; do \
		if [ -f "$$file" ]; then \
			filename=$$(basename "$$file"); \
			alert_text=$$(jq -r '.alert_text // "No alert_text found"' "$$file" 2>/dev/null || echo "Invalid JSON"); \
			printf "🔹 %-45s\n" "$$filename"; \
			printf "   %s\n\n" "$$alert_text"; \
		fi; \
	done

# Interactive alert rule testing menu
.PHONY: test-alert-rules
test-alert-rules:
	@echo "🧪 Alert Rule Testing Menu"
	@echo "============================================"
	@echo ""
	@echo "Select an alert rule to test:"
	@echo ""
	@i=1; \
	declare -a files; \
	declare -a alert_texts; \
	for file in packages/db/src/db/scripts/json/*.json; do \
		if [ -f "$$file" ]; then \
			filename=$$(basename "$$file"); \
			alert_text=$$(jq -r '.alert_text // "No alert_text found"' "$$file" 2>/dev/null || echo "Invalid JSON"); \
			files[$$i]="$$filename"; \
			alert_texts[$$i]="$$alert_text"; \
			printf "%-3s %s\n" "$$i)" "$$alert_text"; \
			i=$$((i + 1)); \
		fi; \
	done; \
	echo ""; \
	printf "Enter your choice (1-$$((i-1))) or 'q' to quit: "; \
	read choice; \
	if [ "$$choice" = "q" ] || [ "$$choice" = "Q" ]; then \
		echo "👋 Exiting..."; \
		exit 0; \
	fi; \
	if [ "$$choice" -ge 1 ] && [ "$$choice" -le $$((i-1)) ] 2>/dev/null; then \
		selected_file="$${files[$$choice]}"; \
		selected_alert_text="$${alert_texts[$$choice]}"; \
		echo ""; \
		echo "📋 Selected Alert Rule: $$selected_alert_text"; \
		echo "============================================"; \
		echo ""; \
		echo "📊 Data Preview will be shown by the test script..."; \
		echo ""; \
		printf "🤔 Do you want to proceed with this test? (y/N): "; \
		read confirm; \
		if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || [ "$$confirm" = "yes" ] || [ "$$confirm" = "Yes" ]; then \
			echo ""; \
			echo "🚀 Running test for: $$selected_alert_text"; \
			echo "============================================"; \
			cd packages/db/src/db/scripts && ./test_alert_rules.sh "$$selected_file"; \
		else \
			echo ""; \
			echo "❌ Test cancelled. Returning to main menu..."; \
			echo ""; \
			make test-alert-rules; \
		fi; \
	else \
		echo "❌ Invalid choice. Please enter a number between 1 and $$((i-1)), or 'q' to quit."; \
		exit 1; \
	fi

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  Building:"
	@echo "    build-all          Build all Podman images"
	@echo "    build-ui           Build UI image"
	@echo "    build-api          Build API image"
	@echo "    build-db           Build database migration image (includes CSV data loading)"
	@echo ""
	@echo "  Pushing:"
	@echo "    push-all           Push all images to registry"
	@echo "    push-ui            Push UI image to registry"
	@echo "    push-api           Push API image to registry"
	@echo "    push-db            Push database migration image to registry"
	@echo ""
	@echo "  Deploying:"
	@echo "    deploy             Deploy application using Helm (production with env vars)"
	@echo "    deploy-noauth      🔓 Deploy with AUTH BYPASS (dev/testing only)"
	@echo "    deploy-keycloak    🔐 Deploy with KEYCLOAK AUTH (production)"
	@echo "    deploy-dev         Deploy in development mode (reduced resources)"
	@echo "    deploy-all         Build, push and deploy all components"
	@echo "    full-deploy        Complete pipeline: login, build, push, deploy"
	@echo ""
	@echo "  OpenShift Builds (build images in-cluster):"
	@echo "    openshift-create-builds       Create BuildConfigs and ImageStreams"
	@echo "    openshift-build-all          Build all images in OpenShift"
	@echo "    openshift-build-api          Build API image only"
	@echo "    openshift-build-ui           Build UI image only"
	@echo "    openshift-build-db           Build DB image only"
	@echo "    openshift-deploy-noauth      Build in OpenShift and deploy (no auth)"
	@echo "    openshift-deploy-keycloak    Build in OpenShift and deploy (Keycloak)"
	@echo ""
	@echo "  Undeploying:"
	@echo "    undeploy           Remove application deployment"
	@echo "    undeploy-all       Remove deployment and namespace"
	@echo ""
	@echo "  Development:"
	@echo "    port-forward-api   Forward API service to localhost:8000"
	@echo "    port-forward-ui    Forward UI service to localhost:8080"
	@echo "    port-forward-db    Forward database to localhost:5432"
	@echo ""
	@echo   "  Local Development:"
	@echo "    run-local          Start all services (always pull latest from quay.io registry)"
	@echo "    build-local        Build local Podman images and tag them as 'local'"
	@echo "    build-run-local    Build and run all services locally using 'local' tagged images"
	@echo "    stop-local         Stop local Podman Compose services"
	@echo "    logs-local         Show logs from local services"
	@echo "    reset-local        Reset environment (pull latest, restart with fresh data)"
	@echo "    pull-local         Pull latest images from quay.io registry"
	@echo "    setup-local        Complete local setup (pull, run, migrate, seed)"
	@echo ""
	@echo "  Helm:"
	@echo "    helm-lint          Lint Helm chart"
	@echo "    helm-template      Render Helm templates"
	@echo "    helm-debug         Debug Helm deployment"
	@echo ""
	@echo "  Testing:"
	@echo "    test-alert-rules   Interactive menu to test alert rules"
	@echo "    list-alert-samples List available sample alert rule files"
	@echo ""
	@echo "  Setup:"
	@echo "    setup-data         Complete data setup (migrations + seed all)"
	@echo ""
	@echo "  Seeding:"
	@echo "    seed-db            Seed database with sample data"
	@echo "    seed-keycloak      Set up Keycloak realm (without DB user sync)"
	@echo "    seed-keycloak-with-users  Set up Keycloak and sync DB users"
	@echo "    seed-all           Seed both database and Keycloak with users"
	@echo ""
	@echo "  Utilities:"
	@echo "    login              Login to OpenShift registry"
	@echo "    create-project     Create OpenShift project"
	@echo "    status             Show deployment status"
	@echo "    clean-all          Clean up all resources"
	@echo "    clean-images       Remove local Podman images"
	@echo "    clean-local-images Remove local development images (tagged as 'local')"
	@echo "    check-env-file     Check if environment file exists"
	@echo "    create-env-file    Create environment file from example"
	@echo ""
	@echo "  Environment Setup:"
	@echo "    This project uses separate environment files for different scenarios:"
	@echo "      .env.development  - For local development (run-local, build-run-local, etc.)"
	@echo "      .env.production   - For OpenShift deployment (deploy, deploy-dev, etc.)"
	@echo ""
	@echo "    Environment file checks:"
	@echo "      make check-env-dev    # Check development environment file"
	@echo "      make check-env-prod   # Check production environment file"
	@echo "      make setup-dev-env    # Set up .env from .env.development for local use"
	@echo ""
	@echo "Examples:"
	@echo "  make setup-local                    # Complete local setup (pulls from quay.io)"
	@echo "  make run-local                      # Start all services (pulls latest from quay.io)"
	@echo "  make build-run-local                # Build and run with local images (tagged as 'local')"
	@echo "  make test-alert-rules               # Interactive alert rule testing"
	@echo "  make list-alert-samples             # List available alert samples"
	@echo "  make NAMESPACE=my-app deploy        # Deploy to custom namespace"

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
.PHONY: deploy
deploy: create-project check-env-prod
	@echo "Deploying application using Helm with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH CORS_ALLOWED_ORIGINS ALLOWED_ORIGINS ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID VITE_API_BASE_URL; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)

# Deploy in development mode with auth bypass (no authentication required)
.PHONY: deploy-noauth
deploy-noauth: create-project
	@echo "🔓 Deploying in DEVELOPMENT mode with AUTH BYPASS..."
	@echo "⚠️  WARNING: Authentication is DISABLED - use only for development/testing"
	@echo ""
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-dev-noauth.yaml \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG)
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "🔓 Auth bypass is ENABLED - no login required"
	@echo "📍 Get your route: oc get route $(PROJECT_NAME)-nginx-route -n $(NAMESPACE)"

# Deploy in production mode with Keycloak authentication
.PHONY: deploy-keycloak
deploy-keycloak: create-project check-env-prod
	@echo "🔐 Deploying in PRODUCTION mode with KEYCLOAK AUTH..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-prod-keycloak.yaml \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)
	@echo ""
	@echo "✅ Deployment complete!"
	@echo "🔐 Keycloak authentication is ENABLED"
	@echo "⚠️  Make sure Keycloak is deployed and configured"
	@echo "📍 Get your route: oc get route $(PROJECT_NAME)-nginx-route -n $(NAMESPACE)"

.PHONY: deploy-dev
deploy-dev: create-project check-env-prod
	@echo "Deploying application in development mode with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@echo "Note: This is still a production deployment with reduced resources for development/testing"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH CORS_ALLOWED_ORIGINS ALLOWED_ORIGINS ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID VITE_API_BASE_URL; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		--set database.persistence.enabled=false \
		--set api.replicas=1 \
		--set ui.replicas=1 \
		$(HELM_SECRET_PARAMS)

.PHONY: deploy-all
deploy-all: build-all push-all deploy
	@echo "Complete deployment finished successfully"

# OpenShift Build targets (build images in-cluster)
.PHONY: openshift-create-builds
openshift-create-builds:
	@echo "Creating OpenShift BuildConfigs and ImageStreams..."
	@cat deploy/openshift-builds-template.yaml | \
		sed 's/$${GIT_URI}/https:\/\/github.com\/rh-ai-quickstart\/spending-transaction-monitor.git/g' | \
		sed 's/$${GIT_REF}/$(GIT_BRANCH)/g' | \
		sed 's/$${VITE_BYPASS_AUTH}/false/g' | \
		sed 's/$${VITE_ENVIRONMENT}/staging/g' | \
		oc apply -f - -n $(NAMESPACE)
	@echo "✅ BuildConfigs and ImageStreams created!"
	@echo "To start builds, run: make openshift-build-all"

.PHONY: openshift-build-all
openshift-build-all:
	@echo "Starting all OpenShift builds..."
	@echo "This will take 10-20 minutes depending on cluster resources"
	@oc start-build spending-monitor-db -n $(NAMESPACE) --follow &
	@oc start-build spending-monitor-api -n $(NAMESPACE) --follow &
	@oc start-build spending-monitor-ui -n $(NAMESPACE) --follow &
	@wait
	@echo "✅ All builds completed!"

.PHONY: openshift-build-api
openshift-build-api:
	@echo "Building API in OpenShift..."
	oc start-build spending-monitor-api -n $(NAMESPACE) --follow

.PHONY: openshift-build-ui
openshift-build-ui:
	@echo "Building UI in OpenShift..."
	oc start-build spending-monitor-ui -n $(NAMESPACE) --follow

.PHONY: openshift-build-db
openshift-build-db:
	@echo "Building DB in OpenShift..."
	oc start-build spending-monitor-db -n $(NAMESPACE) --follow

.PHONY: openshift-deploy-noauth
openshift-deploy-noauth: openshift-create-builds openshift-build-all
	@echo "Deploying with OpenShift-built images (no auth)..."
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-dev-noauth.yaml \
		--set global.imageRegistry=image-registry.openshift-image-registry.svc:5000 \
		--set global.imageRepository=$(NAMESPACE) \
		--set global.imageTag=latest
	@echo "✅ Deployment complete with OpenShift-built images!"

.PHONY: openshift-deploy-keycloak
openshift-deploy-keycloak: create-project check-env-prod openshift-create-builds openshift-build-all
	@echo "Deploying with OpenShift-built images (Keycloak auth)..."
	@set -a; source $(ENV_FILE_PROD); set +a; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--values ./deploy/helm/spending-monitor/values-prod-keycloak.yaml \
		--set global.imageRegistry=image-registry.openshift-image-registry.svc:5000 \
		--set global.imageRepository=$(NAMESPACE) \
		--set global.imageTag=latest \
		$(HELM_SECRET_PARAMS)
	@echo "✅ Deployment complete with OpenShift-built images!"

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
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH CORS_ALLOWED_ORIGINS ALLOWED_ORIGINS ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID VITE_API_BASE_URL; \
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
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH CORS_ALLOWED_ORIGINS ALLOWED_ORIGINS ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID VITE_API_BASE_URL; \
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
	@podman rmi $(UI_IMAGE_LOCAL) $(API_IMAGE_LOCAL) $(DB_IMAGE_LOCAL) || true

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
	@echo "Tagging built images as 'local'..."
	podman tag $(UI_IMAGE) $(UI_IMAGE_LOCAL) || true
	podman tag $(API_IMAGE) $(API_IMAGE_LOCAL) || true
	podman tag $(DB_IMAGE) $(DB_IMAGE_LOCAL) || true
	@echo "✅ Local images built and tagged successfully"

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

# Build and run locally with Keycloak authentication (default/production mode)
.PHONY: build-run-local
build-run-local: setup-dev-env clean-ui-images
	@echo "🔨 Building images (environment-agnostic)..."
	podman-compose -f podman-compose.yml -f podman-compose.build.yml build --no-cache migrations api ui
	@echo "Tagging built images as 'local'..."
	podman tag $(UI_IMAGE) $(UI_IMAGE_LOCAL) || true
	podman tag $(API_IMAGE) $(API_IMAGE_LOCAL) || true
	podman tag $(DB_IMAGE) $(DB_IMAGE_LOCAL) || true
	podman tag $(INGESTION_IMAGE) $(INGESTION_IMAGE_LOCAL) || true
	@echo ""
	@echo "✅ Starting with Keycloak authentication (runtime config)..."
	@echo "   - Login required (user1@example.com / password123)"
	@echo "   - Keycloak authentication enabled"
	@echo "   - Frontend: http://localhost:3000"
	@echo "   - API (proxied): http://localhost:3000/api/*"
	@echo "   - API (direct): http://localhost:8000"
	@echo "   - Keycloak: http://localhost:8080"
	@echo ""
	IMAGE_TAG=local BYPASS_AUTH=false VITE_BYPASS_AUTH=false VITE_ENVIRONMENT=staging \
		podman-compose -f podman-compose.yml up -d --no-build

# Build and run locally with auth bypass (no authentication)
.PHONY: build-run-local-noauth
build-run-local-noauth: setup-dev-env clean-ui-images
	@echo "🔨 Building images (environment-agnostic)..."
	podman-compose -f podman-compose.yml -f podman-compose.build.yml build --no-cache migrations api ui
	@echo "Tagging built images as 'local'..."
	podman tag $(UI_IMAGE) $(UI_IMAGE_LOCAL) || true
	podman tag $(API_IMAGE) $(API_IMAGE_LOCAL) || true
	podman tag $(DB_IMAGE) $(DB_IMAGE_LOCAL) || true
	@echo ""
	@echo "✅ Starting with auth bypass (runtime config)..."
	@echo "   - No login required"
	@echo "   - Yellow dev banner will be visible"
	@echo "   - Frontend: http://localhost:3000"
	@echo "   - API (proxied): http://localhost:3000/api/*"
	@echo "   - API (direct): http://localhost:8000"
	@echo ""
	IMAGE_TAG=local BYPASS_AUTH=true VITE_BYPASS_AUTH=true VITE_ENVIRONMENT=development \
		podman-compose -f podman-compose.yml up -d --no-build
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo "Running database migrations..."
	@pnpm db:upgrade || (echo "❌ Database upgrade failed. Check if database is running." && exit 1)
	@echo "Seeding database with test data..."
	@pnpm db:seed || (echo "❌ Database seeding failed. Check migration status." && exit 1)
	@echo ""
	@echo "✅ All services started including Keycloak and database is ready!"
	@echo ""
	@echo "To also start pgAdmin for database management, run:"
	@echo "  IMAGE_TAG=local podman-compose -f podman-compose.yml --profile tools up -d pgadmin"
	@echo "  Then access pgAdmin at: http://localhost:8081"
	@echo ""
	@echo "To setup Keycloak with database users:"
	@echo "  make setup-keycloak"
	@echo "  or directly: pnpm auth:setup-keycloak-with-users"
	@echo ""
	@echo "💡 Auth Bypass (Development Mode):"
	@echo "  To disable authentication in development, set:"
	@echo "    export BYPASS_AUTH=true"
	@echo "  This affects both backend API and frontend UI"
	@echo "  Default: BYPASS_AUTH=false (authentication required)"
	@echo ""
	@echo "To view logs: make logs-local"
	@echo "To stop services: make stop-local"

# New target for running with Keycloak enabled
.PHONY: run-local-with-auth
run-local-with-auth: setup-dev-env
	@echo "Starting all services including Keycloak locally with Podman Compose using development environment..."
	@echo "Using development environment file: $(ENV_FILE_DEV)"
	@echo "This will start: PostgreSQL, API, UI, nginx proxy, SMTP server, and Keycloak"
	@echo "Services will be available at:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - API (proxied): http://localhost:3000/api/*"
	@echo "  - API (direct): http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - SMTP Web UI: http://localhost:3002"
	@echo "  - Keycloak: http://localhost:8080"
	@echo "  - Database: localhost:5432"
	@echo ""
	@echo "Pulling latest images from quay.io registry..."
	IMAGE_TAG=latest podman-compose -f podman-compose.yml pull
	IMAGE_TAG=latest podman-compose -f podman-compose.yml up -d
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo ""
	@echo "✅ All services started including Keycloak!"
	@echo "Use 'make setup-keycloak' to configure Keycloak with database users"

# Setup Keycloak with database users using pnpm
.PHONY: setup-keycloak
setup-keycloak: setup-dev-env
	@echo "Setting up Keycloak with database users using pnpm..."
	@echo "Waiting for Keycloak to be ready..."
	@timeout 60 bash -c 'until curl -sf http://localhost:8080/health/ready >/dev/null 2>&1; do sleep 2; done' || (echo "❌ Keycloak not ready after 60s" && exit 1)
	@echo "Keycloak is ready, running setup..."
	pnpm auth:setup-keycloak-with-users
	@echo "✅ Keycloak setup completed!"

# Setup Keycloak with database users (alias for consistency)
.PHONY: setup-keycloak-local
setup-keycloak-local: setup-keycloak
	@echo "ℹ️  Note: setup-keycloak-local is now an alias for setup-keycloak (both use pnpm)"

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
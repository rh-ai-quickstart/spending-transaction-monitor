# OpenShift Deployment Makefile for Spending Transaction Monitor

# Configuration
PROJECT_NAME = spending-monitor
REGISTRY_URL ?= quay.io
REPOSITORY ?= rh-ai-quickstart
NAMESPACE ?= spending-transaction-monitor
IMAGE_TAG ?= latest
CLUSTER_DOMAIN ?= $(shell oc whoami --show-server 2>/dev/null | sed -E 's|https://api\.([^:]+).*|apps.\1|')

# OpenShift internal registry nuance:
# - OpenShift's internal registry uses the project/namespace as the repository path:
#     <registry>/<namespace>/<image>:<tag>
# - Quay and other registries typically use an org/repo namespace (e.g. quay.io/<org>/...)
#
# To reduce friction for OpenShift deployments, if the user sets REGISTRY_URL to an OpenShift
# image-registry host and does NOT explicitly set REPOSITORY, default REPOSITORY to NAMESPACE.
ifeq ($(origin REPOSITORY), default)
  ifneq (,$(findstring openshift-image-registry,$(REGISTRY_URL)))
    REPOSITORY := $(NAMESPACE)
  endif
  ifneq (,$(findstring image-registry.openshift-image-registry,$(REGISTRY_URL)))
    REPOSITORY := $(NAMESPACE)
  endif
endif

# Dynamically generated URLs for production deployment
# Note: The route format follows OpenShift's pattern: <app-name>-<namespace>.<cluster-domain>
# These override any values set in .env.production during deployment

# Internal Keycloak URL (for API to reach Keycloak via cluster network)
KEYCLOAK_URL_DYNAMIC := http://$(PROJECT_NAME)-keycloak:8080

# External Keycloak URL (for browser access and token issuer)
KEYCLOAK_FRONTEND_URL_DYNAMIC := https://$(PROJECT_NAME)-keycloak-$(NAMESPACE).$(CLUSTER_DOMAIN)

# Application URLs
APP_URL_DYNAMIC := https://$(PROJECT_NAME)-$(NAMESPACE).$(CLUSTER_DOMAIN)
CORS_ALLOWED_ORIGINS_DYNAMIC := $(APP_URL_DYNAMIC)
ALLOWED_ORIGINS_DYNAMIC := $(APP_URL_DYNAMIC)
KEYCLOAK_REDIRECT_URIS_DYNAMIC := $(APP_URL_DYNAMIC)/*,$(APP_URL_DYNAMIC)
KEYCLOAK_WEB_ORIGINS_DYNAMIC := $(APP_URL_DYNAMIC)

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

TOLERATIONS_TEMPLATE=[{"key":"$(1)","effect":"NoSchedule","operator":"Exists"}]

# Helper function to generate helm parameters from environment variables
define HELM_SECRET_PARAMS
$$(if [ -n "$$POSTGRES_DB" ]; then echo "--set secrets.POSTGRES_DB=$$POSTGRES_DB"; fi) \
$$(if [ -n "$$POSTGRES_USER" ]; then echo "--set secrets.POSTGRES_USER=$$POSTGRES_USER"; fi) \
$$(if [ -n "$$POSTGRES_PASSWORD" ]; then echo "--set secrets.POSTGRES_PASSWORD=$$POSTGRES_PASSWORD"; fi) \
$$(if [ -n "$$DATABASE_URL" ]; then echo "--set secrets.DATABASE_URL=$$DATABASE_URL"; fi) \
$$(if [ -n "$$API_KEY" ]; then echo "--set secrets.API_KEY=$$API_KEY"; fi) \
$$(if [ -n "$$BASE_URL" ]; then echo "--set secrets.BASE_URL=$$BASE_URL"; fi) \
$$(if [ -n "$$LLM_PROVIDER" ]; then echo "--set secrets.LLM_PROVIDER=$$LLM_PROVIDER"; fi) \
$$(if [ -n "$$MODEL" ]; then echo "--set secrets.MODEL=$$MODEL"; fi) \
$$(if [ -n "$$ENVIRONMENT" ]; then echo "--set secrets.ENVIRONMENT=$$ENVIRONMENT"; fi) \
$$(if [ -n "$$DEBUG" ]; then echo "--set secrets.DEBUG=$$DEBUG"; fi) \
$$(if [ -n "$$BYPASS_AUTH" ]; then echo "--set secrets.BYPASS_AUTH=$$BYPASS_AUTH"; fi) \
$$(if [ -n "$$CORS_ALLOWED_ORIGINS" ]; then echo "--set secrets.CORS_ALLOWED_ORIGINS=$${CORS_ALLOWED_ORIGINS//,/\\,}"; fi) \
$$(if [ -n "$$ALLOWED_ORIGINS" ]; then echo "--set secrets.ALLOWED_ORIGINS=$${ALLOWED_ORIGINS//,/\\,}"; fi) \
$$(if [ -n "$$ALLOWED_HOSTS" ]; then echo "--set secrets.ALLOWED_HOSTS=$$ALLOWED_HOSTS"; fi) \
$$(if [ -n "$$SMTP_HOST" ]; then echo "--set secrets.SMTP_HOST=$$SMTP_HOST"; fi) \
$$(if [ -n "$$SMTP_PORT" ]; then echo "--set secrets.SMTP_PORT=$$SMTP_PORT"; fi) \
$$(if [ -n "$$SMTP_FROM_EMAIL" ]; then echo "--set secrets.SMTP_FROM_EMAIL=$$SMTP_FROM_EMAIL"; fi) \
$$(if [ -n "$$SMTP_USE_TLS" ]; then echo "--set secrets.SMTP_USE_TLS=$$SMTP_USE_TLS"; fi) \
$$(if [ -n "$$SMTP_USE_SSL" ]; then echo "--set secrets.SMTP_USE_SSL=$$SMTP_USE_SSL"; fi) \
$$(if [ -n "$$KEYCLOAK_URL" ]; then echo "--set secrets.KEYCLOAK_URL=$$KEYCLOAK_URL"; fi) \
$$(if [ -n "$$KEYCLOAK_FRONTEND_URL" ]; then echo "--set secrets.KEYCLOAK_FRONTEND_URL=$$KEYCLOAK_FRONTEND_URL"; fi) \
$$(if [ -n "$$KEYCLOAK_REALM" ]; then echo "--set secrets.KEYCLOAK_REALM=$$KEYCLOAK_REALM"; fi) \
$$(if [ -n "$$KEYCLOAK_CLIENT_ID" ]; then echo "--set secrets.KEYCLOAK_CLIENT_ID=$$KEYCLOAK_CLIENT_ID"; fi) \
$$(if [ -n "$$KEYCLOAK_REDIRECT_URIS" ]; then echo "--set secrets.KEYCLOAK_REDIRECT_URIS=$${KEYCLOAK_REDIRECT_URIS//,/\\,}"; fi) \
$$(if [ -n "$$KEYCLOAK_WEB_ORIGINS" ]; then echo "--set secrets.KEYCLOAK_WEB_ORIGINS=$$KEYCLOAK_WEB_ORIGINS"; fi) \
$$(if [ -n "$$KEYCLOAK_DB_USER" ]; then echo "--set secrets.KEYCLOAK_DB_USER=$$KEYCLOAK_DB_USER"; fi) \
$$(if [ -n "$$KEYCLOAK_DB_PASSWORD" ]; then echo "--set secrets.KEYCLOAK_DB_PASSWORD=$$KEYCLOAK_DB_PASSWORD"; fi) \
$$(if [ -n "$$KEYCLOAK_ADMIN_PASSWORD" ]; then echo "--set secrets.KEYCLOAK_ADMIN_PASSWORD=$$KEYCLOAK_ADMIN_PASSWORD"; fi) \
$$(if [ -n "$$KEYCLOAK_ADMIN_PASSWORD" ]; then echo "--set keycloak.admin.password=$$KEYCLOAK_ADMIN_PASSWORD"; fi) \
$$(if [ -n "$$KEYCLOAK_DB_PASSWORD" ]; then echo "--set keycloak.pgvector.secret.password=$$KEYCLOAK_DB_PASSWORD"; fi) \
$$(if [ -n "$$KEYCLOAK_FRONTEND_URL" ]; then echo "--set keycloak.config.hostname=$$(echo "$$KEYCLOAK_FRONTEND_URL" | sed 's|http://||' | sed 's|https://||' | sed 's|/.*||' | sed 's|:[0-9]*$$||')"; fi) \
$$(if [ -n "$$VITE_API_BASE_URL" ]; then echo "--set secrets.VITE_API_BASE_URL=$$VITE_API_BASE_URL"; fi) \
$$(if [ -n "$$VITE_BYPASS_AUTH" ]; then echo "--set secrets.VITE_BYPASS_AUTH=$$VITE_BYPASS_AUTH"; fi) \
$$(if [ -n "$$VITE_ENVIRONMENT" ]; then echo "--set secrets.VITE_ENVIRONMENT=$$VITE_ENVIRONMENT"; fi) \
$$(if [ -n "$$LLAMASTACK_BASE_URL" ]; then echo "--set secrets.LLAMASTACK_BASE_URL=$$LLAMASTACK_BASE_URL"; fi) \
$$(if [ -n "$$LLAMASTACK_MODEL" ]; then echo "--set secrets.LLAMASTACK_MODEL=$$LLAMASTACK_MODEL"; fi) \
$$(if [ -n "$$LLM_PROVIDER" ]; then echo "--set secrets.LLM_PROVIDER=$$LLM_PROVIDER"; fi) \
$$(if [ -n "$$USE_ML_RECOMMENDATIONS" ]; then echo "--set secrets.USE_ML_RECOMMENDATIONS=$$USE_ML_RECOMMENDATIONS"; fi) \
$$(if [ -n "$$USE_ML_INFERENCE_SERVICE" ]; then echo "--set secrets.USE_ML_INFERENCE_SERVICE=$$USE_ML_INFERENCE_SERVICE"; fi) \
$$(if [ -n "$$ML_INFERENCE_ENDPOINT" ]; then echo "--set secrets.ML_INFERENCE_ENDPOINT=$$ML_INFERENCE_ENDPOINT"; fi)
endef

define HELM_LLAMASTACK_PARAMS
$$(if [ -n "$$LLM_PROVIDER_ID" ]; then echo "--set global.models.$$LLM_PROVIDER_ID.enabled=true"; fi) \
$$(if [ -n "$$MODEL" ]; then echo "--set global.models.$$LLM_PROVIDER_ID.id=$$MODEL"; fi) \
$$(if [ -n "$$BASE_URL" ]; then echo "--set global.models.$$LLM_PROVIDER_ID.url=$$BASE_URL"; fi) \
$$(if [ -n "$$API_KEY" ]; then echo "--set global.models.$$LLM_PROVIDER_ID.apiToken=$$API_KEY"; fi) \
$$(if [ -n "$$LLAMA_STACK_ENV" ]; then echo "--set-json llama-stack.secrets=$$LLAMA_STACK_ENV"; fi) \
$$(if [ "$$LLM_PROVIDER" = "llamastack" ]; then echo "--set llama-stack.enabled=true"; else echo "--set llama-stack.enabled=false"; fi) 
endef

define HELM_LLM_SERVICE_PARAMS
$$(if [ -n "$$HF_TOKEN" ]; then echo "--set llm-service.secret.hf_token=$$HF_TOKEN"; fi) \
$$(if [ -n "$$LLM_TOLERATION" ]; then echo "--set-json global.models.$$LLM_PROVIDER_ID.tolerations=[{\"key\":\"$$LLM_TOLERATION\",\"effect\":\"NoSchedule\",\"operator\":\"Exists\"}]"; fi) \
$$(if [ "$$LLM_PROVIDER" = "llamastack" ]; then echo "--set llm-service.enabled=true"; else echo "--set llm-service.enabled=false"; fi)
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

# Check if required Keycloak environment variables are set
.PHONY: check-keycloak-vars
check-keycloak-vars: check-env-prod
	@echo "Checking Keycloak environment variables..."
	@set -a; source $(ENV_FILE_PROD); set +a; \
	if [ -z "$$KEYCLOAK_ADMIN_PASSWORD" ]; then \
		echo "❌ Error: KEYCLOAK_ADMIN_PASSWORD is not set in $(ENV_FILE_PROD)"; \
		echo ""; \
		echo "Please add the following to your $(ENV_FILE_PROD):"; \
		echo "  KEYCLOAK_ADMIN_PASSWORD=your-secure-admin-password"; \
		echo ""; \
		exit 1; \
	fi; \
	if [ -z "$$KEYCLOAK_DB_PASSWORD" ]; then \
		echo "❌ Error: KEYCLOAK_DB_PASSWORD is not set in $(ENV_FILE_PROD)"; \
		echo ""; \
		echo "Please add the following to your $(ENV_FILE_PROD):"; \
		echo "  KEYCLOAK_DB_PASSWORD=your-secure-db-password"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Keycloak environment variables are set"

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

# Non-interactive alert rule testing - run specific test by file name
# Usage: make test-alert-rule FILE=alert_charged_significantly_more_same_merchant.json
.PHONY: test-alert-rule
test-alert-rule:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: FILE parameter is required"; \
		echo ""; \
		echo "Usage: make test-alert-rule FILE=<filename>"; \
		echo ""; \
		echo "Example: make test-alert-rule FILE=alert_charged_significantly_more_same_merchant.json"; \
		echo ""; \
		echo "To see available files, run: make list-alert-samples"; \
		exit 1; \
	fi
	@echo "🚀 Running test for: $(FILE)"
	@echo "============================================"
	@cd packages/db/src/db/scripts && ./test_alert_rules.sh "$(FILE)"

# Run all alert rule tests non-interactively
.PHONY: test-all-alert-rules
test-all-alert-rules:
	@echo "🚀 Running all alert rule tests..."
	@echo "============================================"
	@cd packages/db/src/db/scripts && ./test_alert_rules.sh

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
	@echo "    deploy             Deploy application using Helm"
	@echo "    deploy-dev         Deploy in development mode"
	@echo "    build-deploy       Complete pipeline: login, build, push, deploy"
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
	@echo "    dev                🚀 Start infrastructure + dev servers (RECOMMENDED for development)"
	@echo "    stop-dev           🛑 Stop development servers (keeps infrastructure running)"
	@echo "    check-ports        🔍 Check if development server ports are available"
	@echo "    check-all-ports    🔍 Check all ports (dev servers + infrastructure)"
	@echo "    port-info          📋 Show port assignments for development environment"
	@echo "    run-local          Start all services (always pull latest from quay.io registry)"
	@echo "    build-local        Build local Podman images and tag them as 'local'"
	@echo "    build-run-local    Build and run all services locally using 'local' tagged images"
	@echo "    stop-local         Stop local Podman Compose services"
	@echo "    logs-local         Show logs from local services"
	@echo "    reset-local        Reset environment (pull latest, restart with fresh data)"
	@echo ""
	@echo "  Helm:"
	@echo "    helm-dep-update    Update Helm chart dependencies"
	@echo "    helm-dep-build     Build Helm chart dependencies"
	@echo "    helm-dep-list      List Helm chart dependencies"
	@echo "    helm-lint          Lint Helm chart (includes dependency update)"
	@echo "    helm-template      Render Helm templates (includes dependency update)"
	@echo "    helm-debug         Debug Helm deployment (includes dependency update)"
	@echo ""
	@echo "  Testing:"
	@echo "    test-alert-rules       Interactive menu to test alert rules"
	@echo "    test-alert-rule        Run specific test non-interactively (requires FILE=<name>)"
	@echo "    test-all-alert-rules   Run all alert rule tests non-interactively"
	@echo "    list-alert-samples     List available sample alert rule files"
	@echo ""
	@echo "  Setup:"
	@echo "    setup-data         Complete data setup (migrations + seed all)"
	@echo ""
	@echo "  Seeding:"
	@echo "    seed-db            Seed database (local only, for OpenShift use migration job)"
	@echo "    seed-keycloak-with-users  Set up Keycloak and manually sync DB users"
	@echo "    Note: OpenShift deployments automatically sync users in migration job if BYPASS_AUTH=false"
	@echo ""
	@echo "  Keycloak Management:"
	@echo "    keycloak-users              List database-synced users (excludes test users)"
	@echo "    keycloak-users-all          List all users including test users (adminuser, testuser)"
	@echo "    keycloak-sync-users         Sync database users to Keycloak"
	@echo ""
	@echo "  Utilities:"
	@echo "    login              Login to OpenShift registry"
	@echo "    create-project     Create OpenShift project"
	@echo "    status             Show deployment status"
	@echo "    clean-all          Clean up all resources"
	@echo "    clean-migration    Clean up stuck migration jobs/pods"
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
	@echo "  make dev                            # Start development environment (RECOMMENDED)"
	@echo "  make stop-dev                       # Stop dev servers (keeps containers running)"
	@echo "  make setup-local                    # Complete local setup (pulls from quay.io)"
	@echo "  make run-local                      # Start all services (pulls latest from quay.io)"
	@echo "  make build-run-local                # Build and run with local images (tagged as 'local')"
	@echo "  make test-alert-rules               # Interactive alert rule testing"
	@echo "  make test-alert-rule FILE=alert_charged_significantly_more_same_merchant.json  # Run specific test"
	@echo "  make test-all-alert-rules           # Run all alert tests non-interactively"
	@echo "  make list-alert-samples             # List available alert samples"
	@echo "  make NAMESPACE=my-app deploy        # Deploy to custom namespace"

# Login to OpenShift registry
.PHONY: login
login:
	@if [ -z "$(REGISTRY_URL)" ]; then \
		echo "❌ Error: REGISTRY_URL is not set"; \
		exit 1; \
	fi
	@echo "Logging into registry: $(REGISTRY_URL)"
	@if [ "$(REGISTRY_URL)" = "quay.io" ]; then \
		if [ -z "$$QUAY_USERNAME" ]; then \
			echo "❌ Error: QUAY_USERNAME is required when REGISTRY_URL=quay.io"; \
			echo "   Provide QUAY_USERNAME + QUAY_TOKEN (or QUAY_PASSWORD), or run: podman login quay.io"; \
			exit 1; \
		fi; \
		if [ -n "$$QUAY_TOKEN" ]; then \
			echo "Using Quay credentials for user: $$QUAY_USERNAME (token)"; \
			echo "$$QUAY_TOKEN" | podman login --username="$$QUAY_USERNAME" --password-stdin "$(REGISTRY_URL)"; \
		elif [ -n "$$QUAY_PASSWORD" ]; then \
			echo "Using Quay credentials for user: $$QUAY_USERNAME (password)"; \
			echo "$$QUAY_PASSWORD" | podman login --username="$$QUAY_USERNAME" --password-stdin "$(REGISTRY_URL)"; \
		else \
			echo "❌ Error: QUAY_TOKEN or QUAY_PASSWORD is required when REGISTRY_URL=quay.io"; \
			echo "   Provide QUAY_USERNAME + QUAY_TOKEN (recommended), or run: podman login quay.io"; \
			exit 1; \
		fi; \
	else \
		OC_USER=$$(oc whoami); \
		echo "Using OpenShift token for user: $$OC_USER"; \
		oc whoami --show-token | podman login --username="$$OC_USER" --password-stdin "$(REGISTRY_URL)"; \
	fi

# Create OpenShift project
.PHONY: create-project
create-project:
	@echo "Creating OpenShift project: $(NAMESPACE)"
	@oc new-project $(NAMESPACE) || echo "Project $(NAMESPACE) already exists"

# Build targets
.PHONY: build-ui
build-ui:
	@echo "Building UI image..."
	podman build --no-cache --platform=linux/amd64 -t $(UI_IMAGE) -f ./packages/ui/Containerfile .

.PHONY: build-api
build-api:
	@echo "Building API image..."
	podman build --no-cache --platform=linux/amd64 -t $(API_IMAGE) -f ./packages/api/Containerfile .

.PHONY: build-db
build-db:
	@echo "Building database image..."
	podman build --no-cache --platform=linux/amd64 -t $(DB_IMAGE) -f ./packages/db/Containerfile .

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
deploy: create-project helm-dep-update check-keycloak-vars
	@echo "Deploying application using Helm with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@echo "Dynamically generated URLs (overriding .env.production):"
	@echo "  KEYCLOAK_URL (internal): $(KEYCLOAK_URL_DYNAMIC)"
	@echo "  KEYCLOAK_FRONTEND_URL (external): $(KEYCLOAK_FRONTEND_URL_DYNAMIC)"
	@echo "  APP_URL: $(APP_URL_DYNAMIC)"
	@echo "  CORS_ALLOWED_ORIGINS: $(CORS_ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  ALLOWED_ORIGINS: $(ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  KEYCLOAK_REDIRECT_URIS: $(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"
	@echo "  KEYCLOAK_WEB_ORIGINS: $(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export KEYCLOAK_URL="$(KEYCLOAK_URL_DYNAMIC)"; \
	export KEYCLOAK_FRONTEND_URL="$(KEYCLOAK_FRONTEND_URL_DYNAMIC)"; \
	export CORS_ALLOWED_ORIGINS="$(CORS_ALLOWED_ORIGINS_DYNAMIC)"; \
	export ALLOWED_ORIGINS="$(ALLOWED_ORIGINS_DYNAMIC)"; \
	export KEYCLOAK_REDIRECT_URIS="$(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"; \
	export KEYCLOAK_WEB_ORIGINS="$(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL MODEL_ID MODEL_URL MODEL_API_KEY ENVIRONMENT DEBUG BYPASS_AUTH ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID KEYCLOAK_DB_USER KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD VITE_API_BASE_URL VITE_BYPASS_AUTH VITE_ENVIRONMENT LLAMASTACK_BASE_URL LLAMASTACK_MODEL USE_ML_RECOMMENDATIONS USE_ML_INFERENCE_SERVICE ML_INFERENCE_ENDPOINT; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--timeout 15m \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		--set routes.sharedHost="$(PROJECT_NAME)-$(NAMESPACE).$(CLUSTER_DOMAIN)" \
		$(HELM_SECRET_PARAMS) \
		$(HELM_LLAMASTACK_PARAMS) \
		$(HELM_LLM_SERVICE_PARAMS)

.PHONY: deploy-dev
deploy-dev: create-project helm-dep-update check-keycloak-vars
	@echo "Deploying application in development mode with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@echo "Note: This is still a production deployment with reduced resources for development/testing"
	@echo "Dynamically generated URLs (overriding .env.production):"
	@echo "  KEYCLOAK_URL (internal): $(KEYCLOAK_URL_DYNAMIC)"
	@echo "  KEYCLOAK_FRONTEND_URL (external): $(KEYCLOAK_FRONTEND_URL_DYNAMIC)"
	@echo "  APP_URL: $(APP_URL_DYNAMIC)"
	@echo "  CORS_ALLOWED_ORIGINS: $(CORS_ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  ALLOWED_ORIGINS: $(ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  KEYCLOAK_REDIRECT_URIS: $(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"
	@echo "  KEYCLOAK_WEB_ORIGINS: $(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export KEYCLOAK_URL="$(KEYCLOAK_URL_DYNAMIC)"; \
	export KEYCLOAK_FRONTEND_URL="$(KEYCLOAK_FRONTEND_URL_DYNAMIC)"; \
	export CORS_ALLOWED_ORIGINS="$(CORS_ALLOWED_ORIGINS_DYNAMIC)"; \
	export ALLOWED_ORIGINS="$(ALLOWED_ORIGINS_DYNAMIC)"; \
	export KEYCLOAK_REDIRECT_URIS="$(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"; \
	export KEYCLOAK_WEB_ORIGINS="$(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL MODEL_ID MODEL_URL MODEL_API_KEY ENVIRONMENT DEBUG BYPASS_AUTH ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID KEYCLOAK_DB_USER KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD VITE_API_BASE_URL VITE_BYPASS_AUTH VITE_ENVIRONMENT LLAMASTACK_BASE_URL LLAMASTACK_MODEL USE_ML_RECOMMENDATIONS USE_ML_INFERENCE_SERVICE ML_INFERENCE_ENDPOINT; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--timeout 15m \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		--set database.persistence.enabled=false \
		--set api.replicas=1 \
		--set ui.replicas=1 \
		$(HELM_SECRET_PARAMS) \
		$(HELM_LLAMASTACK_PARAMS) \
		$(HELM_LLM_SERVICE_PARAMS)

# Undeploy targets
.PHONY: undeploy
undeploy:
	@echo "Undeploying application..."
	helm uninstall $(PROJECT_NAME) --namespace $(NAMESPACE) || echo "Release $(PROJECT_NAME) not found"
	@echo "Cleaning up migration jobs and pods..."
	@oc delete job -l app.kubernetes.io/component=migration -n $(NAMESPACE) 2>/dev/null || true
	@oc delete pod -l app.kubernetes.io/component=migration -n $(NAMESPACE) 2>/dev/null || true
	@echo "Cleanup complete"

.PHONY: undeploy-all
undeploy-all: undeploy
	@echo "Cleaning up namespace..."
	oc delete project $(NAMESPACE) || echo "Project $(NAMESPACE) not found or cannot be deleted"

.PHONY: clean-migration
clean-migration:
	@echo "Cleaning up migration jobs and pods..."
	@oc delete job -l app.kubernetes.io/component=migration -n $(NAMESPACE) 2>/dev/null || echo "No migration jobs found"
	@oc delete pod -l app.kubernetes.io/component=migration -n $(NAMESPACE) 2>/dev/null || echo "No migration pods found"
	@echo "Migration cleanup complete"


# Full deployment pipeline
.PHONY: build-deploy
build-deploy: login build-all push-all deploy
	@echo "Build + deploy pipeline completed!"

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
.PHONY: helm-dep-update
helm-dep-update:
	@echo "Updating Helm chart dependencies..."
	@echo "📦 Updating keycloak chart dependencies (pgvector)..."
	@helm dependency update ./deploy/helm/keycloak
	@echo "📦 Updating spending-monitor chart dependencies (keycloak)..."
	@helm dependency update ./deploy/helm/spending-monitor
	@echo "✅ Helm dependencies updated successfully"

.PHONY: helm-dep-build
helm-dep-build:
	@echo "Building Helm chart dependencies..."
	@echo "📦 Building keycloak chart dependencies (pgvector)..."
	@helm dependency build ./deploy/helm/keycloak
	@echo "📦 Building spending-monitor chart dependencies (keycloak)..."
	@helm dependency build ./deploy/helm/spending-monitor
	@echo "✅ Helm dependencies built successfully"

.PHONY: helm-dep-list
helm-dep-list:
	@echo "Listing Helm chart dependencies..."
	@echo ""
	@echo "📦 Keycloak chart dependencies:"
	@helm dependency list ./deploy/helm/keycloak
	@echo ""
	@echo "📦 Spending-monitor chart dependencies:"
	@helm dependency list ./deploy/helm/spending-monitor

.PHONY: helm-lint
helm-lint: helm-dep-update
	@echo "Linting Helm chart..."
	helm lint ./deploy/helm/spending-monitor

.PHONY: helm-template
helm-template: helm-dep-update check-env-prod
	@echo "Rendering Helm templates with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@echo "Dynamically generated URLs (overriding .env.production):"
	@echo "  KEYCLOAK_URL (internal): $(KEYCLOAK_URL_DYNAMIC)"
	@echo "  KEYCLOAK_FRONTEND_URL (external): $(KEYCLOAK_FRONTEND_URL_DYNAMIC)"
	@echo "  APP_URL: $(APP_URL_DYNAMIC)"
	@echo "  CORS_ALLOWED_ORIGINS: $(CORS_ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  ALLOWED_ORIGINS: $(ALLOWED_ORIGINS_DYNAMIC)"
	@echo "  KEYCLOAK_REDIRECT_URIS: $(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"
	@echo "  KEYCLOAK_WEB_ORIGINS: $(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export KEYCLOAK_URL="$(KEYCLOAK_URL_DYNAMIC)"; \
	export KEYCLOAK_FRONTEND_URL="$(KEYCLOAK_FRONTEND_URL_DYNAMIC)"; \
	export CORS_ALLOWED_ORIGINS="$(CORS_ALLOWED_ORIGINS_DYNAMIC)"; \
	export ALLOWED_ORIGINS="$(ALLOWED_ORIGINS_DYNAMIC)"; \
	export KEYCLOAK_REDIRECT_URIS="$(KEYCLOAK_REDIRECT_URIS_DYNAMIC)"; \
	export KEYCLOAK_WEB_ORIGINS="$(KEYCLOAK_WEB_ORIGINS_DYNAMIC)"; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID KEYCLOAK_DB_USER KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD VITE_API_BASE_URL VITE_BYPASS_AUTH VITE_ENVIRONMENT USE_ML_RECOMMENDATIONS; \
	helm template $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		$(HELM_SECRET_PARAMS)

.PHONY: helm-debug
helm-debug: helm-dep-update check-env-prod
	@echo "Debugging Helm deployment with production environment variables..."
	@echo "Using production environment file: $(ENV_FILE_PROD)"
	@echo "Dynamically generated URLs:"
	@echo "  KEYCLOAK_URL: $(KEYCLOAK_URL)"
	@echo "  APP_URL: $(APP_URL)"
	@echo "  CORS_ALLOWED_ORIGINS: $(CORS_ALLOWED_ORIGINS)"
	@echo "  ALLOWED_ORIGINS: $(ALLOWED_ORIGINS)"
	@set -a; source $(ENV_FILE_PROD); set +a; \
	export KEYCLOAK_URL="$(KEYCLOAK_URL)"; \
	export CORS_ALLOWED_ORIGINS="$(CORS_ALLOWED_ORIGINS)"; \
	export ALLOWED_ORIGINS="$(ALLOWED_ORIGINS)"; \
	export POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL API_KEY BASE_URL LLM_PROVIDER MODEL ENVIRONMENT DEBUG BYPASS_AUTH ALLOWED_HOSTS SMTP_HOST SMTP_PORT SMTP_FROM_EMAIL SMTP_USE_TLS SMTP_USE_SSL KEYCLOAK_REALM KEYCLOAK_CLIENT_ID KEYCLOAK_DB_USER KEYCLOAK_DB_PASSWORD KEYCLOAK_ADMIN_PASSWORD VITE_API_BASE_URL VITE_BYPASS_AUTH VITE_ENVIRONMENT USE_ML_RECOMMENDATIONS; \
	helm upgrade --install $(PROJECT_NAME) ./deploy/helm/spending-monitor \
		--namespace $(NAMESPACE) \
		--set global.imageRegistry=$(REGISTRY_URL) \
		--set global.imageRepository=$(REPOSITORY) \
		--set global.imageTag=$(IMAGE_TAG) \
		--set routes.sharedHost="$(PROJECT_NAME)-$(NAMESPACE).$(CLUSTER_DOMAIN)" \
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
	@echo "Cleaning up llamastack storage..."
	@podman volume rm spending-transaction-monitor_llamastack-data 2>/dev/null || true
	@echo "✅ All local services stopped and storage cleaned"

.PHONY: build-local
build-local:
	@echo "Building local Podman images with 'local' tag..."
	podman-compose -f podman-compose.yml -f podman-compose.build.yml build
	@echo "✅ Local images built and tagged successfully"

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

.PHONY: build-run-local
build-run-local: setup-dev-env build-local
	@echo "Starting all services locally with freshly built images (tagged as 'local')..."
	@echo "This will start: PostgreSQL, API, UI, nginx proxy, and SMTP server"
	@echo "Services will be available at:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - API (proxied): http://localhost:3000/api/*"
	@echo "  - API (direct): http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - SMTP Web UI: http://localhost:3002"
	@echo "  - Database: localhost:5432"
	@echo ""
	IMAGE_TAG=local podman-compose -f podman-compose.yml -f podman-compose.build.yml up -d
	@echo ""
	@echo "Waiting for database to be ready..."
	@sleep 15
	@echo "Database migrations and seeding are handled automatically by the migrations container..."
	@echo ""
	@echo "✅ All services started and database is ready!"
	@echo ""
	@echo "To also start pgAdmin for database management, run:"
	@echo "  IMAGE_TAG=local podman-compose -f podman-compose.yml -f podman-compose.build.yml --profile tools up -d pgadmin"
	@echo "  Then access pgAdmin at: http://localhost:8080"
	@echo ""
	@echo "To view logs: make logs-local"
	@echo "To stop services: make stop-local"

# Development environment with infrastructure containers + local dev servers
.PHONY: dev
dev: setup-dev-env
	@echo "🚀 Starting development environment..."
	@echo "========================================"
	@echo ""
	@echo "🔍 Step 0: Checking port availability..."
	@./scripts/check-dev-ports.sh check
	@echo ""
	@echo "📦 Step 1: Checking infrastructure containers..."
	@if ! podman ps --format "{{.Names}}" | grep -q "^postgres$$"; then \
		echo "🔄 Starting PostgreSQL container..."; \
		podman-compose -f podman-compose.yml up -d postgres; \
		echo "⏳ Waiting for PostgreSQL to be healthy..."; \
		timeout=60; \
		while [ $$timeout -gt 0 ] && ! podman ps --format "{{.Names}}\t{{.Status}}" | grep "postgres" | grep -q "healthy"; do \
			sleep 2; \
			timeout=$$((timeout - 2)); \
		done; \
		if [ $$timeout -le 0 ]; then echo "❌ PostgreSQL failed to start"; exit 1; fi; \
		echo "✅ PostgreSQL is healthy"; \
	else \
		echo "✅ PostgreSQL already running"; \
	fi
	@if ! podman ps --format "{{.Names}}" | grep -q "spending-monitor-keycloak"; then \
		echo "🔄 Starting Keycloak container..."; \
		podman-compose -f podman-compose.yml up -d keycloak; \
		echo "⏳ Waiting for Keycloak to be ready (this takes ~60 seconds)..."; \
		timeout=120; \
		while [ $$timeout -gt 0 ] && ! podman ps --format "{{.Names}}\t{{.Status}}" | grep "spending-monitor-keycloak" | grep -q "healthy"; do \
			sleep 3; \
			timeout=$$((timeout - 3)); \
		done; \
		if [ $$timeout -le 0 ]; then echo "⚠️  Keycloak may still be starting (continuing anyway)"; fi; \
		echo "✅ Keycloak container started"; \
	else \
		echo "✅ Keycloak already running"; \
	fi
	@if ! podman ps --format "{{.Names}}" | grep -q "spending-monitor-smtp"; then \
		echo "🔄 Starting SMTP container..."; \
		podman-compose -f podman-compose.yml up -d smtp4dev; \
		echo "✅ SMTP4dev started"; \
	else \
		echo "✅ SMTP4dev already running"; \
	fi
	@if ! podman ps --format "{{.Names}}" | grep -q "spending-monitor-llamastack"; then \
		echo "🔄 Starting LlamaStack container..."; \
		podman-compose -f podman-compose.yml up -d llamastack; \
		echo "✅ LlamaStack started"; \
	else \
		echo "✅ LlamaStack already running"; \
	fi
	@echo ""
	@echo "📊 Step 2: Setting up database..."
	@pnpm db:upgrade || echo "⚠️  Database migration may have failed (continuing anyway)"
	@echo ""
	@echo "🌱 Step 3: Ensuring sample data exists..."
	@if ! pnpm db:verify > /dev/null 2>&1; then \
		echo "🔄 Seeding database with sample data..."; \
		pnpm db:seed; \
	else \
		echo "✅ Database already has data"; \
	fi
	@echo ""
	@echo "🚀 Step 4: Starting development servers..."
	@echo "==========================================="
	@echo "Starting API, UI, and Storybook in parallel using Turbo..."
	@echo ""
	@echo "📝 NOTE: This will run in the foreground. To stop, press Ctrl+C"
	@echo "         Infrastructure containers will remain running."
	@echo ""
	@echo "🌐 Services will be available at:"
	@echo "   • Frontend:  http://localhost:3000"
	@echo "   • API Docs:  http://localhost:8000/docs"
	@echo "   • Storybook: http://localhost:6006"
	@echo "   • SMTP UI:   http://localhost:3002"
	@echo "   • Keycloak:  http://localhost:8080/admin"
	@echo ""
	@sleep 2
	pnpm dev

.PHONY: stop-dev
stop-dev:
	@echo "🛑 Stopping development servers..."
	@pkill -f "pnpm.*dev" 2>/dev/null || true
	@pkill -f "turbo dev" 2>/dev/null || true
	@pkill -f "uvicorn.*src.main:app" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@pkill -f "storybook dev" 2>/dev/null || true
	@echo "✅ Development servers stopped"
	@echo ""
	@echo "ℹ️  Infrastructure containers are still running."
	@echo "   To stop them too, run: make stop-local"

.PHONY: check-ports
check-ports:
	@./scripts/check-dev-ports.sh check

.PHONY: check-all-ports
check-all-ports:
	@./scripts/check-dev-ports.sh check-all

.PHONY: port-info
port-info:
	@./scripts/check-dev-ports.sh info

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
	@echo ""
	@echo "ℹ️  Note: For OpenShift deployments, user sync happens automatically in the migration job"
	@echo "ℹ️  For local development, run 'make keycloak-sync-users' if needed"
	@echo ""

.PHONY: seed-keycloak-with-users
seed-keycloak-with-users:
	@echo "🔐 Setting up Keycloak realm and syncing database users..."
	@if [ -f .env.production ]; then \
		echo "Using .env.production for Keycloak configuration..."; \
		set -a && . ./.env.production && set +a; \
	fi; \
	pnpm seed:keycloak-with-users

# Keycloak management targets (using Python package)
# These targets load environment from .env.production and run the Python CLI

.PHONY: keycloak-users
keycloak-users:
	@if [ -f .env.production ]; then \
		set -a && . ./.env.production && set +a && \
		export KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_ADMIN_PASSWORD && \
		cd packages/auth && PYTHONPATH=src uv run python -m keycloak.cli list-users; \
	else \
		echo "❌ Error: .env.production not found"; \
		exit 1; \
	fi

.PHONY: keycloak-users-all
keycloak-users-all:
	@if [ -f .env.production ]; then \
		set -a && . ./.env.production && set +a && \
		cd packages/auth && PYTHONPATH=src uv run python -m keycloak.cli list-users --include-test-users; \
	else \
		echo "❌ Error: .env.production not found"; \
		exit 1; \
	fi

.PHONY: keycloak-sync-users
keycloak-sync-users:
	@echo "🔄 Syncing database users to Keycloak..."
	@if [ -f .env.production ]; then \
		set -a && . ./.env.production && set +a && \
		export KEYCLOAK_URL KEYCLOAK_REALM KEYCLOAK_ADMIN_PASSWORD DATABASE_URL && \
		cd packages/auth && PYTHONPATH=src uv run python -m keycloak.cli sync-users; \
	else \
		echo "❌ Error: .env.production not found"; \
		exit 1; \
	fi

.PHONY: setup-data
setup-data:
	@echo "🚀 Setting up data: Running migrations, then seeding database and Keycloak..."
	pnpm setup:data
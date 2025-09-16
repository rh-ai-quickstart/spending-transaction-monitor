<!-- omit from toc -->
# Spending Transaction Monitor

Alerting for credit card transactions with rule-based fraud detection and location-based security monitoring.

For contribution guidelines and repo conventions, see [CONTRIBUTING.md](CONTRIBUTING.md).
<!-- omit from toc -->
## Table of contents

- [Overview](#overview)
- [How it works](#how-it-works)
- [Getting started](#getting-started)
- [Components](#components)
- [Standards](#standards)
- [Releases](#releases)
- [Structure](#structure)

## Overview

- Monorepo managed with Turborepo
- UI: React + Vite
- API: FastAPI (async SQLAlchemy)
- DB: PostgreSQL with SQLAlchemy models and Alembic migrations

Packages
- `packages/ui`: web app and Storybook
- `packages/api`: API service and routes
- `packages/db`: models, engine, Alembic, seed/verify scripts
- `packages/ingestion-service`: transaction ingestion service with Kafka integration
- `packages/evaluation`: rule evaluation (scaffold)
- `packages/alerts`: alert delivery (scaffold)
- `packages/configs/*`: shared ESLint/Prettier configs

## How it works

- Users create alert rules (amount, merchant, category, timeframe, location; notification methods: email/SMS/push/webhook).
- Location-based fraud detection captures user GPS coordinates for enhanced security monitoring.
- Incoming transactions are stored and evaluated against active rules, including location-based risk assessment.
- Triggered rules produce alert notifications which are delivered via configured channels.

```mermaid
graph TD

  %% UI
  subgraph UI["UI (packages/ui)"]
    U["User"] --> WUI["Web UI"]
  end

  %% API
  subgraph API["API (packages/api)"]
    API_APP["FastAPI App"]
    IN["Transaction API"]
  end

  %% Evaluation
  subgraph EVAL["Evaluation (packages/evaluation)"]
    EV["Rule Evaluation Service"]
  end

  %% Alerts
  subgraph ALERTS["Alerts (packages/alerts)"]
    AL["Alerts Service"]
  end

  %% DB
  subgraph DB["DB (packages/db) - PostgreSQL"]
    USERS["users"]
    CARDS["credit_cards"]
    AR["alert_rules"]
    TRX["transactions"]
    AN["alert_notifications"]
  end

  %% Delivery
  subgraph DELIV["Delivery Channels"]
    EM["Email"]
    SM["SMS"]
    PS["Push"]
    WH["Webhook"]
  end

  %% External Source
  subgraph EXT["External"]
    TS["Transaction Source"]
  end

  %% Rule authoring
  WUI -->|Create/Update Rule| API_APP
  API_APP -->|Persist| AR

  %% Transaction ingestion
  TS --> IN
  IN --> API_APP
  API_APP -->|Store| TRX

  %% Evaluation path
  API_APP -->|Evaluate| EV
  EV -->|Read| AR
  EV -->|Read| TRX
  EV -->|Create| AN
  EV -->|Dispatch| AL

  %% Alerts delivery
  AL -->|Update| AN
  AL --> EM
  AL --> SM
  AL --> PS
  AL --> WH
```

## Getting started

Prerequisites: Node 18+, pnpm 9+, Python 3.11+, uv, Podman (preferred) or Docker

Install
```bash
pnpm setup
```

**🚀 Start Development Mode** (starts DB, API, UI with auth bypassed)
```bash
pnpm dev
```

This command:
- Starts PostgreSQL database
- Starts FastAPI backend on port 8000  
- Starts React UI on port 5173
- **Automatically enables development mode auth bypass** 🔓

The UI will show a yellow banner: "🔓 Development Mode - Auth Bypassed" when running.

**Backend-only development** (API + Database with test data)
```bash
pnpm dev:backend     # Complete backend setup + start
pnpm backend:setup   # Setup only (DB + migrations + seed)
pnpm backend:start   # Start API server only (port 8002)
pnpm backend:stop    # Stop database
```

Common tasks
```bash
pnpm build
pnpm test
pnpm lint
pnpm format
pnpm db:revision
pnpm db:verify
```

Dev URLs
- Web UI: http://localhost:5173 (shows dev mode banner)
- API (full stack): http://localhost:8000 (auth bypass enabled)
- API (backend-only): http://localhost:8002
- API Docs: http://localhost:8000/docs
- Component Storybook: http://localhost:6006

### 🔧 Development Mode (Authentication Bypass)

**Quick Start for New Developers:**
```bash
git clone <repo>
pnpm setup
pnpm dev          # 🔓 Auth automatically bypassed in development
```
Visit http://localhost:5173 - you'll see a yellow banner and can use the app immediately as "John Doe" without any authentication setup.

**How It Works:**
- **Purpose**: Skip OAuth2/OIDC setup for faster development
- **Auto-enabled**: When `VITE_ENVIRONMENT=development` (default)
- **Visual indicator**: 🔓 Yellow banner: "Development Mode - Auth Bypassed"
- **Mock user**: Automatically signed in as "John Doe" with admin roles
- **Security**: Only works in development builds, never in production

**Environment Controls:**
```bash
# Default: Auth bypass enabled (recommended for development)
pnpm dev

# To test real Keycloak authentication in development:
VITE_BYPASS_AUTH=false pnpm dev

# Production: Auth always required (automatic)
VITE_ENVIRONMENT=production
```

**Troubleshooting:**
- **No dev banner?** Check console for "Development auth provider initialized"  
- **Customize mock user:** Edit `packages/ui/src/constants/auth.ts`
- **Test real auth:** See [`docs/auth/INTEGRATION.md`](docs/auth/INTEGRATION.md) for Keycloak setup

Manual DB control (optional)
```bash
pnpm db:start    # podman compose (fallback to docker compose)
pnpm db:upgrade
pnpm db:seed
pnpm db:stop
```

Python virtual environments
```bash
# Each Python package uses uv-managed venvs under the package directory
pnpm --filter @spending-monitor/api install:deps
pnpm --filter @spending-monitor/db install:deps
```

## Components

- API (`packages/api`): health, users, transactions; async DB session; foundation for rule evaluation and NLP integration
- DB (`packages/db`): SQLAlchemy models, Alembic migrations, seed/verify; local Postgres via Podman/Docker
- UI (`packages/ui`): React app and components in Storybook

## Standards

- Conventional Commits; commitlint enforces messages
- Branch names must match: `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`, `test/*`, `ci/*`, `build/*`, `perf/*`
- Hooks
  - pre-commit: UI Prettier/ESLint; API Ruff format/check on staged files
  - pre-push: format:check, lint, test; commitlint on commit range; branch name check

## Releases

Automated with semantic-release on CI, using commit messages to drive versioning and changelogs. Configuration in `.releaserc`.

## Structure

```
spending-transaction-monitor/
├── packages/
│   ├── api/
│   ├── db/
│   ├── ui/
│   ├── ingestion-service/
│   └── configs/
├── docs/
├── turbo.json
├── pnpm-workspace.yaml
└── package.json
```

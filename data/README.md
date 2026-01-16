# Test Data

This directory contains shared test data used across the application.

## Overview

- `sample_users.csv`: sample user records (used for demos/dev seeding)
- `sample_transactions.csv`: sample transaction records (used for demos/dev seeding)
- `test_users.yaml`: source-of-truth test users used by both Keycloak and DB seeding
- `generate_sample_data.py`: helper to generate `sample_users.csv` / `sample_transactions.csv`

## generate_sample_data.py

Generates `data/sample_users.csv` and `data/sample_transactions.csv` from a large source dataset.

**Input**:
- `credit_card_transactions.csv` (expected in the repo root; not stored in this directory)

**Usage**:

```bash
# Run from the repo root
python data/generate_sample_data.py
```

## test_users.yaml

Centralized test user data used by both:
- **Keycloak seeding** (`pnpm seed:keycloak`) - creates authentication users
- **Database seeding** (`pnpm seed:db`) - creates user records with full profiles

### Why This Approach?

Previously, test users were defined separately in Keycloak and database seeding scripts, which could lead to:
- Authentication users existing without database records (404 errors)
- Database users without authentication (can't log in)
- Data inconsistencies between systems

By using a single YAML file as the source of truth, we ensure:
- ✅ Users can authenticate (Keycloak knows them)
- ✅ Users have data (database has their profile)
- ✅ Easy to add new test users (one file to update)
- ✅ Consistent test data across environments

### Fields

**Authentication fields** (used by Keycloak):
- `username` - Keycloak username
- `email` - User's email address
- `password` - Plain text password (test only!)
- `first_name` - Given name
- `last_name` - Family name
- `roles` - Array of roles (user, admin)

**Database profile fields** (used by database seeding):
- All authentication fields above, plus:
- `phone_number` - Contact number
- `address_*` - Full address (street, city, state, zipcode, country)
- `credit_limit` - Credit card limit
- `credit_balance` - Current balance
- `location_consent_given` - Location tracking consent
- `last_app_location_*` - Last known app location
- `last_transaction_*` - Last transaction location
- `card_*` - Credit card details

### Adding New Test Users

1. Edit `test_users.yaml`
2. Add a new user with all required fields (copy existing user as template)
3. Run `pnpm seed:all` to seed both Keycloak and database

### Usage

```bash
# Seed both Keycloak and database with users from test_users.yaml
pnpm seed:all

# Or seed individually:
pnpm seed:keycloak           # Keycloak only
pnpm seed:db                  # Database only
```


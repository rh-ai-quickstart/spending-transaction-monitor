# E2E Tests

End-to-end tests for the Spending Monitor UI using [Playwright](https://playwright.dev/).

## Prerequisites

1. **Start the application** (required for tests to run):

   ```bash
   # From the project root
   make run-local
   ```

   This starts all services including:
   - Frontend at http://localhost:3000
   - API at http://localhost:8000
   - PostgreSQL, Keycloak, etc.

2. **Configure test environment** (optional):

   By default, tests run against `http://localhost:3000`. You can override this:

   ```bash
   E2E_BASE_URL=http://localhost:3000 pnpm e2e
   ```

## Running Tests

From the `packages/ui` directory:

```bash
# Run all e2e tests
pnpm e2e

# Run tests with UI mode (interactive debugging)
pnpm e2e:ui

# Run tests in debug mode
pnpm e2e:debug

# View the HTML test report
pnpm e2e:report
```

### Running Specific Tests

```bash
# Run a specific test file
pnpm e2e app.spec.ts

# Run tests matching a pattern
pnpm e2e --grep "dashboard"

# Run tests in a specific browser
pnpm e2e --project=chromium
```

## Test Structure

```
e2e/
├── fixtures/
│   └── test-fixtures.ts    # Shared test utilities and constants
├── app.spec.ts             # Basic app smoke tests
├── dashboard.spec.ts       # Dashboard functionality tests
├── alerts.spec.ts          # Alert rules CRUD tests
├── transactions.spec.ts    # Transactions page tests
└── README.md               # This file
```

## Writing Tests

### Basic Test Example

```typescript
import { test, expect } from '@playwright/test';

test('should display dashboard', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  const header = page.locator('header');
  await expect(header).toBeVisible();
});
```

### Using Custom Fixtures

```typescript
import { test, expect, SELECTORS } from './fixtures/test-fixtures';

test('should show transaction list', async ({ page, appReady }) => {
  const transactionList = page.locator(SELECTORS.transactionList);
  await expect(transactionList).toBeVisible();
});
```

## Authentication

By default, tests expect `BYPASS_AUTH=true` in the development environment.

For testing with Keycloak authentication:

1. Ensure Keycloak is running and configured
2. Update test fixtures with valid test credentials
3. Implement login helper in `test-fixtures.ts`

## CI/CD Integration

Tests can be run in CI with:

```yaml
- name: Run E2E Tests
  run: |
    cd packages/ui
    pnpm e2e --reporter=github
```

## Debugging Failed Tests

1. **View trace files**: After a failed test, open the trace:

   ```bash
   npx playwright show-trace test-results/*/trace.zip
   ```

2. **Screenshots**: Failed tests automatically capture screenshots in `test-results/`

3. **Debug mode**: Run with `--debug` for step-by-step execution:
   ```bash
   pnpm e2e:debug
   ```

## Configuration

See `playwright.config.ts` for full configuration options including:

- Browser projects (chromium, firefox, webkit)
- Timeouts
- Screenshot and video settings
- Reporter configuration

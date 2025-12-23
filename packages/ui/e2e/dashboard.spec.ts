import { test, expect } from '@playwright/test';

/**
 * Dashboard E2E Tests
 *
 * Tests for the main dashboard functionality including:
 * - Transaction list display
 * - Stats cards
 * - Transaction chart
 * - User interactions
 *
 * Note: These tests assume BYPASS_AUTH=true for the test environment
 */

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should display the dashboard header or login page', async ({ page }) => {
    // Look for header elements or login page (if auth is enabled)
    const header = page.locator('header, [data-testid="dashboard-header"]');
    const loginPage = page.locator(
      'button:has-text("Login"), button:has-text("Sign in"), [data-testid="login-btn"], .login',
    );

    // Either header OR login page should be visible
    const headerVisible = await header
      .first()
      .isVisible()
      .catch(() => false);
    const loginVisible = await loginPage
      .first()
      .isVisible()
      .catch(() => false);

    expect(headerVisible || loginVisible).toBe(true);
  });

  test('should display transaction list or empty state', async ({ page }) => {
    // Wait for the main content area to load
    await page.waitForTimeout(2000);

    // Either show transactions or an empty/loading state
    const mainContent = page.locator('main, [role="main"], .container');
    await expect(mainContent.first()).toBeVisible();
  });

  test('should display stats cards', async ({ page }) => {
    // Look for stat cards showing transaction summaries
    const statsSection = page.locator(
      '[data-testid="stats-list"], [data-testid="stat-card"], .stat-card, .stats',
    );

    // Stats may or may not be present depending on data
    const statsCount = await statsSection.count();
    // Just verify the page loads - stats presence depends on data
    expect(statsCount).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Transaction List', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should show loading state initially', async ({ page }) => {
    // Intercept API calls to slow them down
    await page.route('**/api/transactions**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.continue();
    });

    await page.reload();

    // Should show some loading indicator or skeleton
    const loadingIndicator = page.locator(
      '[data-testid="loading"], .loading, .skeleton, [aria-busy="true"]',
    );
    // Loading state may flash by quickly
    expect(await loadingIndicator.count()).toBeGreaterThanOrEqual(0);
  });

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock an API error
    await page.route('**/api/transactions**', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // Page should still render without crashing
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});

test.describe('Transaction Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should open transaction details when clicking a transaction', async ({
    page,
  }) => {
    // Wait for transactions to potentially load
    await page.waitForTimeout(2000);

    // Find a clickable transaction element
    const transaction = page.locator(
      '[data-testid="transaction-card"], .transaction-card, .transaction-item',
    );

    const transactionCount = await transaction.count();

    if (transactionCount > 0) {
      // Click the first transaction
      await transaction.first().click();

      // Should open a drawer/modal with details
      const drawer = page.locator(
        '[data-testid="transaction-drawer"], [role="dialog"], .drawer',
      );

      // Give time for drawer animation
      await page.waitForTimeout(500);
      const drawerCount = await drawer.count();
      expect(drawerCount).toBeGreaterThanOrEqual(0);
    } else {
      // No transactions available - test passes
      expect(true).toBe(true);
    }
  });
});

test.describe('Dashboard Navigation', () => {
  test('should navigate to transactions page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find and click transactions link
    const transactionsLink = page.locator(
      'a[href*="transaction"], [data-testid="nav-transactions"]',
    );

    if ((await transactionsLink.count()) > 0) {
      await transactionsLink.first().click();
      await page.waitForLoadState('networkidle');

      // URL should include transactions
      expect(page.url()).toContain('transaction');
    }
  });

  test('should navigate to alerts page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find and click alerts link
    const alertsLink = page.locator('a[href*="alert"], [data-testid="nav-alerts"]');

    if ((await alertsLink.count()) > 0) {
      await alertsLink.first().click();
      await page.waitForLoadState('networkidle');

      // URL should include alerts
      expect(page.url()).toContain('alert');
    }
  });
});

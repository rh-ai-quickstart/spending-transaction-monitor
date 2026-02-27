import { test as base, expect, Page } from '@playwright/test';

/**
 * Custom test fixtures for e2e tests
 *
 * These fixtures provide common setup and utilities for testing
 * the Spending Monitor application.
 */

// Extend the base test with custom fixtures
export const test = base.extend<{
  /**
   * Navigate to the app and wait for it to be ready
   */
  appReady: void;
}>({
  appReady: async ({ page }, use) => {
    // Navigate to the app
    await page.goto('/');

    // Wait for DOM to be ready (better than networkidle for apps with polling)
    await page.waitForLoadState('domcontentloaded');

    // Wait for auth check to complete
    // First check if the auth message appears (it might not if auth is already bypassed)
    const authCheckMsg = page.locator('text="Checking authentication"');
    const authMsgExists = await authCheckMsg.isVisible().catch(() => false);

    if (authMsgExists) {
      // If auth message exists, wait for it to disappear (up to 20 seconds)
      await authCheckMsg.waitFor({ state: 'hidden', timeout: 20000 }).catch(() => {});
    }

    // Additional wait to ensure auth state has settled
    await page.waitForTimeout(1500);

    // Wait for React to hydrate and render - check for app-specific content
    const mainContentLoaded = await page
      .waitForSelector('header, main, nav, [data-testid="dashboard-header"]', {
        timeout: 15000,
      })
      .catch(() => null);

    // If main content found, wait a bit more for dynamic content to load
    if (mainContentLoaded) {
      await page.waitForTimeout(1000);
    }

    await use();
  },
});

export { expect };

/**
 * Test data constants
 */
export const TEST_USER = {
  email: 'testuser@example.com',
  password: 'password123',
};

export const TEST_ADMIN = {
  email: 'adminuser@example.com',
  password: 'password123',
};

/**
 * Common selectors used across tests
 */
export const SELECTORS = {
  // Navigation
  dashboardLink: '[data-testid="nav-dashboard"]',
  transactionsLink: '[data-testid="nav-transactions"]',
  alertsLink: '[data-testid="nav-alerts"]',

  // Dashboard
  transactionList: '[data-testid="transaction-list"]',
  transactionCard: '[data-testid="transaction-card"]',
  statsCard: '[data-testid="stat-card"]',

  // Alert Rules
  alertRuleCard: '[data-testid="alert-rule-card"]',
  createAlertButton: '[data-testid="create-alert-btn"]',
  alertForm: '[data-testid="alert-form"]',

  // Auth
  loginButton: '[data-testid="login-btn"]',
  logoutButton: '[data-testid="logout-btn"]',
  userAvatar: '[data-testid="user-avatar"]',
};

/**
 * Helper to wait for authentication check to complete
 */
export async function waitForAuthCheck(page: Page) {
  // First check if the auth message appears
  const authCheckMsg = page.locator('text="Checking authentication"');
  const authMsgExists = await authCheckMsg.isVisible().catch(() => false);

  if (authMsgExists) {
    // If auth message exists, wait for it to disappear (up to 20 seconds)
    await authCheckMsg.waitFor({ state: 'hidden', timeout: 20000 }).catch(() => {});
  }

  // Additional wait to ensure auth state has settled
  await page.waitForTimeout(1500);
}

/**
 * Helper to wait for API response
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  options?: { timeout?: number },
) {
  return page.waitForResponse(
    (response) =>
      (typeof urlPattern === 'string'
        ? response.url().includes(urlPattern)
        : urlPattern.test(response.url())) && response.status() === 200,
    { timeout: options?.timeout || 10000 },
  );
}

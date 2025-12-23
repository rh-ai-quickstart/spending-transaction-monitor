import { test as base, expect } from '@playwright/test';

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

    // Wait for the app to be interactive
    // In dev/bypass mode, we should see the dashboard
    // In auth mode, we should see the login page
    await page.waitForLoadState('networkidle');

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
 * Helper to wait for API response
 */
export async function waitForApiResponse(
  page: ReturnType<(typeof base)['extend']> extends (arg: infer T) => unknown
    ? T extends { page: infer P }
      ? P
      : never
    : never,
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

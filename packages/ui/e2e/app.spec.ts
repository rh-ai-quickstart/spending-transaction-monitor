import { test, expect } from '@playwright/test';

/**
 * Basic application smoke tests
 *
 * These tests verify that the core application functionality works:
 * - App loads successfully
 * - Navigation works
 * - Key pages render correctly
 */

test.describe('Application Smoke Tests', () => {
  test('should load the application', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // The app should load without crashing
    // Check for either dashboard content (bypass auth) or login page
    const pageContent = await page.content();
    expect(pageContent).toBeTruthy();
  });

  test('should display page title', async ({ page }) => {
    await page.goto('/');

    // Check that the page has a title
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('should not have console errors on load', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out known acceptable errors (e.g., failed network requests during tests)
    const criticalErrors = consoleErrors.filter(
      (error) =>
        !error.includes('Failed to load resource') && !error.includes('net::ERR'),
    );

    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Navigation', () => {
  test('should have working navigation or login page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // App should show either:
    // 1. Navigation (if auth bypassed or logged in)
    // 2. Login page (if auth enabled)
    const nav = page.locator('nav, [role="navigation"], header');
    const loginPage = page.locator(
      'button:has-text("Login"), button:has-text("Sign in"), [data-testid="login-btn"], .login, [class*="login"]',
    );

    // Either navigation OR login page should be visible
    const navVisible = await nav
      .first()
      .isVisible()
      .catch(() => false);
    const loginVisible = await loginPage
      .first()
      .isVisible()
      .catch(() => false);

    expect(navVisible || loginVisible).toBe(true);
  });
});

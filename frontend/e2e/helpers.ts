import { expect, type Page } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Repo root, so tests can reach the real sample reports without a copy. */
export const REPO_ROOT = path.resolve(__dirname, '..', '..');

export const sampleReport = (name: string) =>
  path.join(REPO_ROOT, 'sample_reports', 'providers', name);

export const uniqueEmail = () =>
  `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;

export const PASSWORD = 'secret12345';

/** Register a fresh account and land on the dashboard. */
export async function registerAndLogin(page: Page, email = uniqueEmail()) {
  await page.goto('/');
  await page.getByRole('tab', { name: 'Sign up' }).click();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('Your reports')).toBeVisible();
  return email;
}

/**
 * Upload a report and wait for the UI to show the finished analysis.
 *
 * Waits on what the user actually sees (the Summary heading) rather than polling the API
 * directly - that way the test fails if the backend finishes but the frontend never
 * reflects it, which is exactly the class of bug worth catching here.
 */
export async function uploadAndAwaitResults(page: Page, filePath: string) {
  await page.locator('input[type="file"]').setInputFiles(filePath);
  await page.waitForURL(/\/reports\/\d+/);
  await expect(page.getByRole('heading', { name: 'Summary' })).toBeVisible({
    timeout: Number(process.env.PIPELINE_TIMEOUT_MS ?? 600_000) - 30_000,
  });
}

/** Collect uncaught errors and console.error output so a test can assert the page was clean. */
export function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(`${e.name}: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`[console.error] ${m.text()}`);
  });
  return errors;
}

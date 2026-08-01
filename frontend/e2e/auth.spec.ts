import { expect, test } from '@playwright/test';
import { collectPageErrors, PASSWORD, registerAndLogin, uniqueEmail } from './helpers';

test('login page renders without any page errors', async ({ page }) => {
  const errors = collectPageErrors(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'ReportLens' })).toBeVisible();
  await expect(page.getByLabel('Email')).toBeVisible();
  await expect(page.getByLabel('Password')).toBeVisible();
  expect(errors).toEqual([]);
});

test('unauthenticated visitors are redirected to login', async ({ page }) => {
  await page.goto('/reports/1');
  await expect(page).toHaveURL(/\/login/);
});

test('register, then log out, then log back in', async ({ page }) => {
  const email = await registerAndLogin(page);

  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByText('Your reports')).toBeVisible();
});

test('wrong password shows an error instead of logging in', async ({ page }) => {
  const email = await registerAndLogin(page);
  await page.getByRole('button', { name: 'Log out' }).click();

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill('definitely-not-the-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();

  await expect(page.getByText(/incorrect email or password/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test('registering an already-used email surfaces the server error', async ({ page }) => {
  const email = uniqueEmail();
  await registerAndLogin(page, email);
  await page.getByRole('button', { name: 'Log out' }).click();

  await page.getByRole('tab', { name: 'Sign up' }).click();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page.getByText(/already registered/i)).toBeVisible();
});

test('session survives a page reload', async ({ page }) => {
  await registerAndLogin(page);
  await page.reload();
  await expect(page.getByText('Your reports')).toBeVisible();
});

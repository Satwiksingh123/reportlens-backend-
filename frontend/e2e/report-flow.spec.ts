import { expect, test } from '@playwright/test';
import {
  collectPageErrors,
  registerAndLogin,
  sampleReport,
  uploadAndAwaitResults,
} from './helpers';

test('empty dashboard invites the first upload', async ({ page }) => {
  await registerAndLogin(page);
  await expect(page.getByText(/no reports yet/i)).toBeVisible();
  await expect(page.getByText(/drop a lab report here/i)).toBeVisible();
});

test('upload returns immediately and shows live processing progress', async ({ page }) => {
  await registerAndLogin(page);

  const started = Date.now();
  await page.locator('input[type="file"]').setInputFiles(sampleReport('drlogy_vitb12.pdf'));
  await page.waitForURL(/\/reports\/\d+/);
  const elapsed = Date.now() - started;

  // The whole point of PIPELINE_MODE=thread: navigation happens on the upload response, so
  // if the backend blocked on OCR+LLM this would take minutes and the user would stare at
  // "Uploading...". 30s is a loose ceiling that still catches a genuinely blocking upload.
  expect(elapsed, 'upload should not block on the pipeline').toBeLessThan(30_000);

  // the progress stepper is the user's only signal that anything is happening
  await expect(page.getByText('Reading report')).toBeVisible();
  await expect(page.getByText('Extracting values')).toBeVisible();
  await expect(page.getByText('Generating explanations')).toBeVisible();
});

test('a real report is analysed end to end and rendered correctly', async ({ page }) => {
  const errors = collectPageErrors(page);
  await registerAndLogin(page);
  await uploadAndAwaitResults(page, sampleReport('drlogy_vitb12.pdf'));

  // the actual measured value from this report, not a placeholder
  await expect(page.getByText('452.00', { exact: false })).toBeVisible();
  await expect(page.getByText('Vitamin B12').first()).toBeVisible();
  await expect(page.getByText('Reference:', { exact: false })).toBeVisible();

  // safety: the disclaimer the backend bakes into every explanation must reach the screen
  await expect(
    page.getByText(/consult a qualified doctor/i).first(),
  ).toBeVisible();

  // RAG grounding is exposed rather than hidden
  await page.getByRole('button', { name: /show source/i }).first().click();
  await expect(page.getByText(/MedlinePlus/).first()).toBeVisible();

  expect(errors, 'page should render without JS errors').toEqual([]);
});

test('a multi-biomarker panel renders every row with a status pill', async ({ page }) => {
  await registerAndLogin(page);
  await uploadAndAwaitResults(page, sampleReport('drlogy_electrolytes.pdf'));

  // this panel has several analytes - each should be its own card with a value
  for (const analyte of ['Sodium', 'Potassium', 'Chloride']) {
    await expect(page.getByText(analyte, { exact: true }).first()).toBeVisible();
  }

  const pills = page.getByText(/^(Low|Normal|High)$/);
  expect(await pills.count(), 'every parsed row should show a status pill').toBeGreaterThan(2);
});

test('analysed report appears on the dashboard and reopens', async ({ page }) => {
  await registerAndLogin(page);
  await uploadAndAwaitResults(page, sampleReport('drlogy_vitb12.pdf'));

  await page.getByRole('link', { name: /Reports/ }).click();
  await expect(page.getByText('drlogy_vitb12.pdf')).toBeVisible();
  await expect(page.getByText('Completed')).toBeVisible();

  await page.getByText('drlogy_vitb12.pdf').click();
  await expect(page.getByRole('heading', { name: 'Summary' })).toBeVisible();
});

test('one user cannot open another user\'s report', async ({ page }) => {
  await registerAndLogin(page);
  await uploadAndAwaitResults(page, sampleReport('drlogy_vitb12.pdf'));
  const victimUrl = page.url();

  await page.getByRole('link', { name: /Reports/ }).click();
  await page.getByRole('button', { name: 'Log out' }).click();
  await registerAndLogin(page); // a different account

  await page.goto(victimUrl);
  await expect(page.getByText(/couldn't load this report/i)).toBeVisible();
});

test('an unsupported file type is rejected with a clear message', async ({ page }) => {
  await registerAndLogin(page);

  // the dropzone filters by type client-side, so assert via the alert it raises
  const dialogs: string[] = [];
  page.on('dialog', async (d) => {
    dialogs.push(d.message());
    await d.dismiss();
  });

  await page.locator('input[type="file"]').setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not a lab report'),
  });

  await expect.poll(() => dialogs.length).toBeGreaterThan(0);
  expect(dialogs[0]).toMatch(/unsupported file type/i);
});

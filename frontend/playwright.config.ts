import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests against a REAL running stack (Vite + the API + whatever OCR/LLM the
 * backend is configured with). They are deliberately not mocked: every bug these were
 * written for - an IPv6-only bind, an upload that blocked on the whole pipeline - was
 * invisible to mocked or HTTP-level tests and only showed up in an actual browser.
 *
 * Both servers must already be running (see the repo README). BASE_URL and API_URL let you
 * point at a different host/port.
 */
export default defineConfig({
  testDir: './e2e',
  // The pipeline is genuinely slow on CPU (OCR + a local LLM, ~30s per biomarker), so a
  // single test legitimately runs for minutes. PIPELINE_TIMEOUT_MS overrides per-run.
  timeout: Number(process.env.PIPELINE_TIMEOUT_MS ?? 600_000),
  expect: { timeout: 15_000 },
  // Serial: the backend runs the pipeline on a small thread pool, and parallel uploads
  // would just queue behind each other while inflating every test's wall-clock time.
  workers: 1,
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});

# ReportLens frontend

React + TypeScript + Vite + Tailwind CSS v4 + React Router + TanStack Query. A single-page
app: register/login, upload a lab report, watch it process, read the results.

## Run it

```bash
npm install
cp .env.example .env.local   # VITE_API_URL, defaults to http://localhost:8000
npm run dev
```

Needs the backend running and reachable at `VITE_API_URL` (see the root `README.md` for the
no-Docker or Docker paths) with that origin allowed in the backend's `CORS_ORIGINS` — the
backend's default already includes `http://localhost:5173`.

## Structure

- `src/api/client.ts` — thin fetch wrapper: base URL, bearer token injection, a shared
  `ApiError`, and a 401 handler hook that logs the user out from anywhere in the app.
- `src/api/types.ts` — TypeScript types mirroring the backend's Pydantic schemas.
- `src/context/AuthContext.tsx` — token storage (localStorage) and auth state.
- `src/pages/` — `AuthPage`, `Dashboard` (list + upload), `ReportDetail` (polls while
  processing, then shows the summary and per-biomarker results).
- `src/components/` — presentational pieces (status badges, the processing-steps stepper,
  the upload dropzone, a result card).
- `e2e/` — Playwright tests that drive a real browser against a real running stack.

## End-to-end tests

```bash
npm run test:e2e            # headless
npm run test:e2e:headed     # watch it happen in a browser
npx playwright test e2e/auth.spec.ts   # just the fast auth specs
```

Both servers must already be running (`./scripts/dev.sh` from the repo root does that).
Nothing is mocked: these exist because every bug they were written for — a dev server bound
only to IPv6, an upload that blocked on the whole OCR+LLM pipeline, a "session expired"
message shown for a mistyped password — was invisible to unit and HTTP-level tests and only
appeared in a real browser.

`auth.spec.ts` is fast (~30s). `report-flow.spec.ts` runs real reports through OCR and a
local LLM, so it takes minutes; `PIPELINE_TIMEOUT_MS` overrides the timeout if your machine
is slower.

## Notes

- Report processing is asynchronous on the backend; `ReportDetail` polls
  `GET /api/reports/{id}` every ~2.5s until the status is `completed` or `failed`.
  `Dashboard`'s list does the same (every 3s) only while a report is still in progress.
- Every explanation the backend returns already ends with a medical disclaimer — the UI
  never strips or overrides it.

# E2E Tests

End-to-end tests for Taggarr Web UI using Playwright.

## Prerequisites

1. Install Playwright and its dependencies:

```bash
npm install -D @playwright/test
npx playwright install
```

2. Ensure the backend and frontend are set up:

```bash
# Backend
cd /path/to/taggarr
uv sync

# Frontend
cd frontend
npm install
```

## Running Tests

### Start the servers first

```bash
# Terminal 1: Start the backend
taggarr serve --port 8080

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

### Run all E2E tests

```bash
npx playwright test
```

### Run specific test file

```bash
npx playwright test auth.spec.ts
```

### Run in headed mode (see the browser)

```bash
npx playwright test --headed
```

### Run with debug UI

```bash
npx playwright test --ui
```

## Test Structure

- `playwright.config.ts` - Playwright configuration
- `auth.spec.ts` - Authentication flow tests (login, logout, setup)

## Writing New Tests

1. Create a new `.spec.ts` file in this directory
2. Import Playwright's test utilities:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Feature Name", () => {
  test("should do something", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Taggarr/);
  });
});
```

## CI Integration

The tests are configured to:

- Start the frontend dev server automatically
- Wait for the server to be available before running tests
- Skip server startup if already running (for local development)

In CI, ensure the backend is running before tests execute:

```yaml
- name: Run E2E tests
  run: |
    taggarr serve --port 8080 &
    sleep 5
    npx playwright test
```

## Troubleshooting

### Tests timeout waiting for server

Ensure both backend and frontend are running:

- Backend: `http://localhost:8080`
- Frontend: `http://localhost:3000`

### Browser not installed

Run: `npx playwright install`

### Tests fail with authentication errors

Some tests require a pre-existing user. Set up test fixtures or use database seeding before running tests.

import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.describe("Setup Flow", () => {
    test("should show setup page when no users exist", async ({ page }) => {
      await page.goto("/");
      // If no users exist, should redirect to setup
      // This test requires a fresh database state
      const url = page.url();
      expect(url).toMatch(/\/(setup|login)/);
    });

    test("should allow creating first admin user", async ({ page }) => {
      await page.goto("/setup");

      // Check for setup form elements
      const usernameInput = page.getByLabel(/username/i);
      const passwordInput = page.getByLabel(/password/i);
      const submitButton = page.getByRole("button", {
        name: /create|setup|submit/i,
      });

      // Verify form elements exist
      await expect(usernameInput).toBeVisible();
      await expect(passwordInput).toBeVisible();
      await expect(submitButton).toBeVisible();
    });
  });

  test.describe("Login Flow", () => {
    test("should show login page", async ({ page }) => {
      await page.goto("/login");

      // Check for login form elements
      await expect(page.getByLabel(/username/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(
        page.getByRole("button", { name: /login|sign in/i }),
      ).toBeVisible();
    });

    test("should show error for invalid credentials", async ({ page }) => {
      await page.goto("/login");

      await page.getByLabel(/username/i).fill("invalid_user");
      await page.getByLabel(/password/i).fill("wrong_password");
      await page.getByRole("button", { name: /login|sign in/i }).click();

      // Should show error message
      await expect(page.getByText(/invalid|incorrect|error/i)).toBeVisible();
    });

    test("should redirect to dashboard after successful login", async ({
      page,
    }) => {
      // This test requires a pre-existing user
      // In CI, this would be set up via test fixtures
      await page.goto("/login");

      await page.getByLabel(/username/i).fill("admin");
      await page.getByLabel(/password/i).fill("admin_password");
      await page.getByRole("button", { name: /login|sign in/i }).click();

      // Should redirect to dashboard or home
      await expect(page).toHaveURL(/\/(dashboard|home|$)/);
    });
  });

  test.describe("Protected Routes", () => {
    test("should redirect unauthenticated users to login", async ({ page }) => {
      await page.goto("/settings");

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test("should redirect unauthenticated users from instances page", async ({
      page,
    }) => {
      await page.goto("/instances");

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("Logout", () => {
    test("should clear session on logout", async ({ page }) => {
      // First login (assuming user exists)
      await page.goto("/login");
      await page.getByLabel(/username/i).fill("admin");
      await page.getByLabel(/password/i).fill("admin_password");
      await page.getByRole("button", { name: /login|sign in/i }).click();

      // Find and click logout button
      const logoutButton = page.getByRole("button", {
        name: /logout|sign out/i,
      });
      if (await logoutButton.isVisible()) {
        await logoutButton.click();
      }

      // Should be redirected to login
      await expect(page).toHaveURL(/\/login/);

      // Trying to access protected route should redirect to login
      await page.goto("/settings");
      await expect(page).toHaveURL(/\/login/);
    });
  });
});

import assert from "node:assert/strict";
import test from "node:test";
import { chromium } from "playwright-core";
import { createServer } from "vite";
import { existsSync } from "node:fs";

const chrome = process.env.CHROME_PATH || [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].find(existsSync);

test("remove hides a wedding member immediately and deletes only on Save", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const server = await createServer({ server: { port: 0 } });
  await server.listen();
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  try {
    const page = await browser.newPage();
    const requests = [];
    await page.route("http://localhost:8000/**", async (route) => {
      const request = route.request();
      requests.push(`${request.method()} ${new URL(request.url()).pathname}`);
      const path = new URL(request.url()).pathname;
      let body = {};
      if (path === "/weddings/1") body = {
        id: 1, client_id: 2, wedding_date: "2026-06-01", status: 1,
        bridal_trial_status: "not_interested",
        party_members: [{ id: 12, role: "P", hairstyle: "D", assistant: true }],
      };
      if (path === "/clients/2") body = { id: 2, name: "Test Bride" };
      if (path === "/pricing-versions") body = [];
      await route.fulfill({ status: request.method() === "DELETE" ? 204 : path.endsWith("/invoice") ? 404 : 200, contentType: "application/json", body: JSON.stringify(body) });
    });
    // No confirmation should be required for a change that is still cancellable.
    await page.goto(`http://localhost:${server.httpServer.address().port}/test/profile-fixture.html`);
    await page.getByRole("button", { name: "Edit" }).nth(1).click();
    assert.equal(await page.locator(".party-member-row").count(), 2);
    await page.getByRole("button", { name: "Remove Bride" }).click();
    assert.equal(await page.locator(".party-member-row").count(), 1);
    assert.equal(requests.some((request) => request.startsWith("DELETE ")), false);
    const deleted = page.waitForRequest((request) => request.method() === "DELETE" && request.url().endsWith("/party-members/11"));
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await deleted;
    await page.getByRole("button", { name: "Edit" }).nth(1).waitFor();
    assert.equal(await page.locator(".party-member-row").count(), 1);
  } finally {
    await browser.close();
    await server.close();
  }
});

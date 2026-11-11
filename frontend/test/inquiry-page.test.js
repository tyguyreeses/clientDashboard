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

async function openInquiry() {
  const server = await createServer({ server: { port: 0 } });
  await server.listen();
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  const page = await browser.newPage();
  await page.goto(`http://localhost:${server.httpServer.address().port}/inquiry`);
  return { server, browser, page };
}

async function fillInquiry(page) {
  const futureDate = new Date(Date.now() + 60 * 86400000).toISOString().slice(0, 10);
  await page.getByLabel(/Full name/).fill("Taylor Bride");
  await page.locator('input[type="email"]').fill("taylor@example.com");
  await page.getByLabel(/Instagram handle/).fill("@taylor");
  await page.locator('input[type="date"]').fill(futureDate);
  await page.getByLabel(/Getting-ready address/).fill("123 Main Street");
  await page.locator('input[type="time"]').fill("10:30");
  for (const choice of ["Home", "Yes, it’s firm", "Just looking around :)", "No thanks, I just wanted you!", "Instagram"]) {
    await page.getByLabel(choice, { exact: true }).check();
  }
  await page.getByLabel("Yes please!", { exact: true }).nth(0).check();
  await page.getByLabel("Yes please!", { exact: true }).nth(1).check();
  await page.getByRole("checkbox").check();
}

test("inquiry route renders a form with non-dropdown finite-choice controls", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const { server, browser, page } = await openInquiry();
  try {
    assert.equal(await page.locator("form").count(), 1);
    assert.equal(await page.locator("select").count(), 0);
    assert.ok(await page.locator('input[type="radio"], input[type="checkbox"]').count() > 0);
  } finally {
    await browser.close();
    await server.close();
  }
});

test("dates beyond the one-year window show a clickable Instagram contact", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const { server, browser, page } = await openInquiry();
  try {
    await page.locator('input[type="date"]').fill("2035-01-01");
    const guidance = page.getByRole("alert");
    await guidance.waitFor();
    assert.match(await guidance.innerText(), /DM @hairby\.maddieee on Instagram/);
    assert.equal(await guidance.locator("a").getAttribute("href"), "https://ig.me/m/hairby.maddieee");
  } finally {
    await browser.close();
    await server.close();
  }
});

test("success confirmation appears only after the inquiry request succeeds", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const { server, browser, page } = await openInquiry();
  try {
    let releaseResponse;
    const responseGate = new Promise((resolve) => { releaseResponse = resolve; });
    await page.route("**/api/inquiry", async (route) => {
      await responseGate;
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ message: "saved" }) });
    });
    await fillInquiry(page);
    const request = page.waitForRequest("**/api/inquiry");
    await page.getByRole("button", { name: "Send inquiry" }).click();
    await request;
    assert.equal(await page.getByText("Your inquiry has been received!").count(), 0);
    releaseResponse();
    await page.getByRole("heading", { name: "Your inquiry has been received!" }).waitFor();
  } finally {
    await browser.close();
    await server.close();
  }
});

test("failed inquiry submission preserves answers and shows an actionable error", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const { server, browser, page } = await openInquiry();
  try {
    await page.route("**/api/inquiry", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Please try again later." }) }));
    await fillInquiry(page);
    await page.getByRole("button", { name: "Send inquiry" }).click();
    await page.getByRole("alert").waitFor();

    assert.equal(await page.getByLabel(/Instagram handle/).inputValue(), "@taylor");
    assert.match(await page.getByRole("alert").innerText(), /Please try again later/);
  } finally {
    await browser.close();
    await server.close();
  }
});

test("non-JSON inquiry failures preserve answers and show a retry message", { skip: !chrome && "Chrome not installed (set CHROME_PATH)" }, async () => {
  const { server, browser, page } = await openInquiry();
  try {
    await page.route("**/api/inquiry", (route) => route.fulfill({ status: 503, contentType: "text/html", body: "Service unavailable" }));
    await fillInquiry(page);
    await page.getByRole("button", { name: "Send inquiry" }).click();
    await page.getByRole("alert").waitFor();

    assert.equal(await page.getByLabel(/Instagram handle/).inputValue(), "@taylor");
    assert.match(await page.getByRole("alert").innerText(), /couldn't submit your inquiry.*try again/i);
  } finally {
    await browser.close();
    await server.close();
  }
});

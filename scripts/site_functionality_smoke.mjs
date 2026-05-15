import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const outDir = path.join(root, "artifacts", "site-smoke");
const baseUrl = process.env.WR3_SITE_BASE_URL || "http://127.0.0.1:3001";
const viewport = { width: 390, height: 780 };

function routeName(route) {
  return route === "/" ? "home" : route.replaceAll("/", "_").replace(/^_/, "");
}

async function pageHealth(page) {
  return page.evaluate(() => {
    const horizontalOverflow =
      document.documentElement.scrollWidth > window.innerWidth + 1 ||
      document.body.scrollWidth > window.innerWidth + 1;
    const visibleErrorText = [...document.querySelectorAll(".error-box, .tg-inline-error")]
      .map((node) => node.textContent?.trim())
      .filter(Boolean);
    return {
      title: document.title,
      path: window.location.pathname,
      innerWidth: window.innerWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      horizontalOverflow,
      visibleErrorText
    };
  });
}

async function screenshot(page, name) {
  const relativePath = path.join("artifacts", "site-smoke", `${name}.png`);
  await page.screenshot({
    path: path.join(root, relativePath),
    fullPage: false
  });
  return relativePath;
}

async function runStep(results, page, name, fn) {
  const started = Date.now();
  const entry = {
    name,
    status: "unknown",
    duration_ms: 0,
    screenshot: null,
    health: null,
    error: null
  };
  try {
    await fn();
    entry.health = await pageHealth(page);
    entry.screenshot = await screenshot(page, name.replaceAll(/[^a-zA-Z0-9_-]/g, "_"));
    if (entry.health.horizontalOverflow) {
      throw new Error(`horizontal overflow: ${entry.health.documentScrollWidth}px > ${entry.health.innerWidth}px`);
    }
    if (entry.health.visibleErrorText.length) {
      throw new Error(`visible UI error: ${entry.health.visibleErrorText.join(" | ")}`);
    }
    entry.status = "passed";
  } catch (error) {
    entry.status = "failed";
    entry.error = error instanceof Error ? error.message : String(error);
    try {
      entry.health = await pageHealth(page);
      entry.screenshot = await screenshot(page, `${name.replaceAll(/[^a-zA-Z0-9_-]/g, "_")}-failed`);
    } catch {
      // Keep the original failure readable even if the page is gone.
    }
  } finally {
    entry.duration_ms = Date.now() - started;
    results.push(entry);
  }
}

async function openRoute(page, route) {
  const response = await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle", timeout: 25000 });
  if (!response || response.status() >= 400) {
    throw new Error(`HTTP ${response?.status() || "no response"} for ${route}`);
  }
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport,
    deviceScaleFactor: 2,
    isMobile: true
  });
  const consoleErrors = [];
  page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") {
      const text = message.text();
      if (!text.includes("Failed to load resource: the server responded with a status of 404")) {
        consoleErrors.push(`console: ${text}`);
      }
    }
  });

  const results = [];

  await runStep(results, page, "home_load", async () => {
    await openRoute(page, "/");
    await page.getByText("Проверка контрактов и багов.").first().waitFor({ timeout: 8000 });
    await page.getByText("Быстрый скан").first().waitFor({ timeout: 8000 });
    await page.getByRole("button", { name: /Очередь багов/ }).waitFor({ timeout: 8000 });
    await page.getByRole("button", { name: /Обращение/ }).waitFor({ timeout: 8000 });
  });

  await runStep(results, page, "command_center_quick_scan_flow", async () => {
    await openRoute(page, "/");
    await page.locator(".cockpit-quick-scan").getByRole("button", { name: /Запустить скан/ }).click();
    await page.waitForURL(/\/audits\//, { timeout: 25000 });
    await page.getByText(/Стадии|Findings|Оценка|Score/i).first().waitFor({ timeout: 25000 });
  });

  await runStep(results, page, "finding_task_actions_flow", async () => {
    await openRoute(page, "/");
    await page.getByRole("button", { name: /Очередь багов/ }).click();
    const firstTask = page.locator(".finding-task").first();
    await firstTask.waitFor({ timeout: 10000 });
    await firstTask.click();
    const detail = page.locator(".cockpit-detail");
    await detail.getByRole("button", { name: /Создать отчёт/ }).click();
    await page.getByText(/Черновик баг-репорта|Черновик приватного письма/).first().waitFor({ timeout: 8000 });
    await detail.getByRole("button", { name: /Проверено/ }).click();
    await detail.getByRole("button", { name: /Сохранить доказательства/ }).click();
  });

  await runStep(results, page, "engine_and_legal_cards", async () => {
    await openRoute(page, "/");
    await page.getByRole("button", { name: /Движок/ }).click();
    await page.getByText("Здоровье движка").first().waitFor({ timeout: 10000 });
    await page.getByText("Радар bug bounty").first().waitFor({ timeout: 10000 });
    await page.getByRole("button", { name: /Обращение/ }).click();
    await page.getByText("Юридические проверки").first().waitFor({ timeout: 10000 });
  });

  await runStep(results, page, "mini_app_scan_flow", async () => {
    await openRoute(page, "/tg");
    await page.getByRole("button", { name: /Запустить скан/ }).click();
    await page.getByText(/Вердикт|Скан создан|Оценка/i).first().waitFor({ timeout: 25000 });
  });

  await runStep(results, page, "mini_app_bounty_flow", async () => {
    await openRoute(page, "/tg");
    await page.getByRole("button", { name: "Баунти" }).click();
    await page.getByText("Радар bug bounty").waitFor({ timeout: 8000 });
    await page.locator(".tg-toggle-row input").check();
    await page.getByRole("button", { name: /Безопасный скан/ }).click();
    await page.getByText(/безопасный bounty-скан|Скан создан|Кандидатов пока нет/i).first().waitFor({ timeout: 25000 });
  });

  for (const route of ["/dashboard", "/tools", "/integrations", "/disclosure", "/billing", "/telegram-emulator"]) {
    await runStep(results, page, `route_${routeName(route)}`, async () => {
      await openRoute(page, route);
      await page.waitForTimeout(300);
    });
  }

  await browser.close();

  const report = {
    kind: "site_functionality_smoke",
    created_at: new Date().toISOString(),
    base_url: baseUrl,
    viewport,
    summary: {
      total: results.length,
      passed: results.filter((item) => item.status === "passed").length,
      failed: results.filter((item) => item.status === "failed").length,
      console_errors: consoleErrors.length
    },
    console_errors: consoleErrors.slice(0, 20),
    results
  };

  await fs.writeFile(path.join(outDir, "site-functionality-smoke.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report.summary, null, 2));
  if (report.summary.failed > 0 || report.summary.console_errors > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

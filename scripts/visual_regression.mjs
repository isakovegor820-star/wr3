import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const outDir = path.join(root, "artifacts", "visual-regression");
const baseUrl = process.env.WR3_VISUAL_BASE_URL || "http://127.0.0.1:3001";
const routes = ["/", "/tg", "/dashboard", "/disclosure"];
const viewports = [
  { name: "mobile360", width: 360, height: 680, isMobile: true },
  { name: "mini397", width: 397, height: 694, isMobile: true },
  { name: "desktop1280", width: 1280, height: 900, isMobile: false }
];

function safeRouteName(route) {
  return route === "/" ? "home" : route.replaceAll("/", "_").replace(/^_/, "");
}

async function inspectPage(page) {
  return page.evaluate(() => {
    const offenders = [...document.querySelectorAll("body *")]
      .map((el) => {
        const rect = el.getBoundingClientRect();
        const text = (el.textContent || "").trim().slice(0, 80);
        return {
          tag: el.tagName.toLowerCase(),
          className: String(el.className || ""),
          text,
          left: rect.left,
          right: rect.right,
          top: rect.top,
          bottom: rect.bottom
        };
      })
      .filter((item) => item.right > window.innerWidth + 1 || item.left < -1)
      .slice(0, 20);
    return {
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      horizontalOverflow:
        document.documentElement.scrollWidth > window.innerWidth + 1 ||
        document.body.scrollWidth > window.innerWidth + 1,
      offenders
    };
  });
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const results = [];
  let failed = false;

  for (const viewport of viewports) {
    const page = await browser.newPage({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: viewport.isMobile ? 2 : 1,
      isMobile: viewport.isMobile
    });
    for (const route of routes) {
      const url = `${baseUrl}${route}`;
      const result = {
        route,
        viewport: viewport.name,
        url,
        status: "unknown",
        screenshot: path.join("artifacts", "visual-regression", `${safeRouteName(route)}-${viewport.name}.png`),
        metrics: null,
        error: null
      };
      try {
        const response = await page.goto(url, { waitUntil: "networkidle", timeout: 20000 });
        result.httpStatus = response?.status() || 0;
        if (!response || response.status() >= 400) {
          throw new Error(`HTTP ${response?.status() || "no-response"}`);
        }
        if (route === "/tg") {
          const moreButton = page.getByRole("button", { name: /Ещё/ }).last();
          await moreButton.click().catch(() => {});
          await page.waitForTimeout(250);
        }
        const screenshotPath = path.join(root, result.screenshot);
        await page.screenshot({ path: screenshotPath, fullPage: false });
        result.metrics = await inspectPage(page);
        result.status = result.metrics.horizontalOverflow ? "failed" : "passed";
        if (result.status === "failed") {
          failed = true;
        }
      } catch (error) {
        failed = true;
        result.status = "failed";
        result.error = error instanceof Error ? error.message : String(error);
      }
      results.push(result);
    }
    await page.close();
  }

  await browser.close();
  const report = {
    kind: "visual_regression",
    created_at: new Date().toISOString(),
    base_url: baseUrl,
    summary: {
      total: results.length,
      passed: results.filter((item) => item.status === "passed").length,
      failed: results.filter((item) => item.status === "failed").length
    },
    results
  };
  await fs.writeFile(
    path.join(outDir, "visual-regression-report.json"),
    JSON.stringify(report, null, 2)
  );
  console.log(JSON.stringify(report.summary, null, 2));
  process.exit(failed ? 1 : 0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
